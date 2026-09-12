"""Bounded P&L observations and explicit, reviewable mappings. No formula execution."""
import io
import json
import posixpath
import re
import unicodedata
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal
from xml.etree import ElementTree as ET

from .packs import workbook, number, result
from .review_xlsx import NS, RID, ReviewFormatError


def norm(value):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower())


ALIASES = {
    "revenue": ["CA", "Chiffre d'affaires", "Chiffre d'affaires total", "Revenue"],
    "direct": ["Coûts directs", "Direct costs"],
    "gross": ["Marge brute", "Gross margin"],
    "overhead": ["G&A", "Frais généraux"],
    "ebitda": ["EBITDA"],
    "depreciation": ["Reprises & dotations", "Dotations aux amortissements"],
    "finance": ["Résultat financier"],
    "capitalized": ["Production immobilisée"],
    "pretax": ["RCAI", "Résultat courant avant impôts"],
    "exceptional": ["Résultat exceptionnel"],
    "tax": ["Impôt sur les bénéfices", "Impôt bénéfices", "Impôts sur les bénéfices"],
    "net": ["Résultat net", "Net income"],
}
LABELS = {norm(label): key for key, labels in ALIASES.items() for label in labels}
EQUATIONS = {"gross": ["revenue", "direct"], "ebitda": ["gross", "overhead"],
             "pretax": ["ebitda", "depreciation", "finance", "capitalized"],
             "net": ["pretax", "exceptional", "tax"]}


def column(address):
    return re.match(r"[A-Z]+", address)[0]


def colnum(text):
    out = 0
    for ch in text:
        out = out * 26 + ord(ch) - 64
    return out


def colname(value):
    out = ""
    while value:
        value, rest = divmod(value-1, 26)
        out = chr(65+rest)+out
    return out


def read_book(raw):
    _, stats = workbook(raw)  # Reject macros, unsafe XML, oversized archives, duplicate cells.
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        def xml(path):
            data = archive.read(path)
            if b"\x00" in data or re.search(br"<!\s*(DOCTYPE|ENTITY)", data, re.I):
                raise ValueError("unsafe XML")
            return ET.fromstring(data)
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ["".join(x.itertext()) for x in xml("xl/sharedStrings.xml").findall("s:si", NS)]
        formats, styles = {}, []
        if "xl/styles.xml" in archive.namelist():
            s = xml("xl/styles.xml")
            formats = {int(x.get("numFmtId")): x.get("formatCode", "") for x in s.findall("s:numFmts/s:numFmt", NS)}
            styles = [int(x.get("numFmtId", "0")) for x in s.findall("s:cellXfs/s:xf", NS)]
        book = xml("xl/workbook.xml")
        props = book.find("s:workbookPr", NS)
        epoch = datetime(1904, 1, 1) if props is not None and props.get("date1904") in ("1", "true") else datetime(1899, 12, 30)
        rels = {x.get("Id"): x.get("Target") for x in xml("xl/_rels/workbook.xml.rels") if x.get("TargetMode") != "External"}
        sheets = []
        for sheet in book.findall("s:sheets/s:sheet", NS):
            target = rels[sheet.get(RID)]
            path = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
            cells, shared_formulas = {}, {}
            root = xml(path)
            for c in root.findall("s:sheetData/s:row/s:c", NS):
                a = c.get("r"); kind = c.get("t", "n")
                text = c.findtext("s:v", default="", namespaces=NS)
                if kind == "s":
                    text = shared[int(text)]
                elif kind == "inlineStr":
                    text = "".join(t.text or "" for t in c.findall("s:is//s:t", NS))
                f = c.find("s:f", NS)
                if f is not None and f.get("t") == "shared" and f.text:
                    shared_formulas[f.get("si")] = (a, f.text)
                style = int(c.get("s", "0"))
                fmtid = styles[style] if style < len(styles) else 0
                fmt = formats.get(fmtid, "0%" if fmtid in (9, 10) else "")
                period = None
                if kind == "n" and text and int(re.search(r"[0-9]+", a)[0]) <= 10:
                    numeric = number(text)
                    if Decimal(1900) <= numeric <= Decimal(2200) and numeric == int(numeric):
                        period = str(int(numeric))
                    elif (14 <= fmtid <= 22 or re.search(r"[dy]", re.sub(r'"[^\"]*"|\[[^]]*\]', '', fmt), re.I)) and 0 <= numeric <= 150000:
                        period = (epoch + timedelta(days=float(numeric))).date().isoformat()
                elif kind in ("s", "inlineStr", "str") and re.fullmatch(r"20[0-9]{2}(?:-[0-9]{2}-[0-9]{2})?", text):
                    period = text
                cells[a] = dict(value=text, kind=kind, formula=None if f is None else f.text or "",
                                format=fmt, period=period, shared_formula=f is not None and f.get("t") == "shared",
                                shared_id=None if f is None else f.get("si"))
            for a, cell in cells.items():
                if not cell["shared_formula"] or cell["formula"]:
                    continue
                anchor, expression = shared_formulas.get(cell["shared_id"], (None, ""))
                # Expand only this supported syntax; no general formula evaluator or guessed dependencies.
                if anchor and re.fullmatch(r"SUM\(\$?[A-Z]+\$?\d+:\$?[A-Z]+\$?\d+\)", expression, re.I):
                    dc = colnum(column(a))-colnum(column(anchor))
                    dr = int(re.search(r"\d+", a)[0])-int(re.search(r"\d+", anchor)[0])
                    def translate(match):
                        col = match[2] if match[1] else colname(colnum(match[2])+dc)
                        row = int(match[4])+(0 if match[3] else dr)
                        if row < 1 or not col:
                            raise ValueError("invalid shared reference")
                        return match[1]+col+match[3]+str(row)
                    cell["formula"] = re.sub(r"(\$?)([A-Z]+)(\$?)(\d+)", translate, expression)
                    cell["formula_origin"] = anchor
            # Header semantics follow actual merged ranges, never guessed fill-forward.
            for merge in root.findall("s:mergeCells/s:mergeCell", NS):
                m = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", merge.get("ref", ""))
                if not m or m[2] != m[4] or int(m[2]) > 10 or colnum(m[3])-colnum(m[1]) > 100:
                    continue
                origin = cells.get(m[1]+m[2])
                if origin and origin["kind"] in ("s", "str", "inlineStr"):
                    for n in range(colnum(m[1])+1, colnum(m[3])+1):
                        a = colname(n)+m[2]
                        if not cells.get(a, {}).get("value"):
                            cells[a] = {**origin, "merged_from": m[1]+m[2]}
            sheets.append(dict(name=sheet.get("name"), visible=sheet.get("state", "visible") == "visible", cells=cells))
        return sheets, stats


def row_mapping(sheet):
    found, labels = {}, {}
    for a, c in sheet["cells"].items():
        if colnum(column(a)) > 4 or c["kind"] not in ("s", "inlineStr", "str"):
            continue
        if "%" in c["value"]:
            continue
        key = LABELS.get(norm(c["value"]))
        if key:
            found.setdefault(key, []).append(int(re.search(r"[0-9]+", a)[0]))
            labels[key] = c["value"]
    return {key: rows[0] for key, rows in found.items() if len(rows) == 1}, labels


def detail_rows(sheet, rows, labels):
    # Every labelled line in the recognized P&L remains eligible, without a materiality filter.
    if "revenue" not in rows or "net" not in rows:
        return rows, labels
    rows, labels = dict(rows), dict(labels)
    possible = {}
    for a, cell in sheet["cells"].items():
        row = int(re.search(r"[0-9]+", a)[0])
        if colnum(column(a)) <= 4 and rows["revenue"] <= row <= rows["net"] and cell["kind"] in ("s", "str", "inlineStr") and cell["value"].strip() and "%" not in cell["value"]:
            possible.setdefault(row, []).append(cell["value"])
    for row, text in possible.items():
        if row not in rows.values() and len(text) == 1:
            key = "line_"+str(row)
            rows[key], labels[key] = row, text[0]
    return rows, labels


def discover(raw, period, selection=None):
    sheets, stats = read_book(raw)
    candidates = []
    for s in sheets:
        rows, labels = row_mapping(s)
        if not s["visible"] or not {"revenue", "ebitda"} <= rows.keys():
            continue
        rows, labels = detail_rows(s, rows, labels)
        cols = {}
        for a, cell in s["cells"].items():
            row = int(re.search(r"[0-9]+", a)[0])
            if row >= min(rows.values()) or row > 10:
                continue
            info = cols.setdefault(column(a), {"periods": [], "kinds": set(), "mode": None})
            if cell["period"] and cell["period"].startswith(str(period)):
                info["periods"].append(cell["period"])
            n = norm(cell["value"])
            if n in ("ytd", "cumul", "cumule", "fy", "annuel"):
                info["mode"] = "ytd" if n in ("ytd", "cumul", "cumule") else "annual"
            if n in ("reel", "realise", "actual", "actuals"):
                info["kinds"].add("actual")
            elif n in ("budget", "reforecast", "forecast"):
                info["kinds"].add("budget" if n == "budget" else "forecast")
        for actual, a in cols.items():
            if a["kinds"] != {"actual"} or not a["periods"]:
                continue
            ap = max(a["periods"], key=len)
            for budget, b in cols.items():
                if b["kinds"] != {"budget"} or not b["periods"] or max(b["periods"], key=len) != ap or a["mode"] != b["mode"]:
                    continue
                candidate = dict(id=f"{s['name']}|{actual}|{budget}", sheet=s["name"], actual=actual, budget=budget,
                                 period=ap, period_kind=a["mode"] or "à confirmer", rows=rows, labels=labels,
                                 label=f"{s['name']} · {a['mode'] or 'période à confirmer'} {ap} · Réel {actual} / Budget {budget}")
                candidates.append(candidate)
    if len(candidates) > 100:
        raise ReviewFormatError("Trop de correspondances possibles ; fournissez un extrait ciblé.")
    selected = next((c for c in candidates if c["id"] == selection), None) if selection else candidates[0] if len(candidates) == 1 else None
    if selection and not selected:
        raise ReviewFormatError("La correspondance choisie ne figure pas dans ce fichier et cet exercice.")
    return dict(candidates=candidates, selected=selected, requires_selection=len(candidates) > 1 and selected is None,
                sheets=[s["name"] for s in sheets], stats=stats,
                method="holco.financial-workbook/1", values="Valeurs enregistrées ; formules non recalculées",
                mapping_basis="Libellés explicites et en-têtes Réel/Budget de même période ; à confirmer au lancement",
                sign_convention="Produits positifs, charges négatives ; les équations proposées requièrent cette convention")


def context_data(raw):
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("schema") != "holco.control-context/1":
        raise ValueError("invalid context snapshot")
    for key in ("rules", "drafts", "memory", "profile"):
        if not isinstance(data.get(key), list) or len(data[key]) > 500:
            raise ValueError("context population limit")
    return data


def amount(cell):
    if cell is None or cell["kind"] != "n" or not cell["value"]:
        raise ValueError("numeric cached value missing")
    return number(cell["value"])


def item(cid, title, location, observed, expected, status):
    return dict(id=cid, title=title, location=location, observed=observed, expected=expected, status=status)


def control(code, sources, tolerance, policy):
    sheets, stats = read_book(sources[0])
    ctx = context_data(sources[1])
    scope = discover(sources[0], policy["required_period"], policy.get("pnl_mapping"))
    selected = scope["selected"]
    checks = []
    if code == "workbook_scope":
        external = sum(c["formula"] is not None and bool(re.search(r"\[[^]]+\]", c["formula"])) for s in sheets for c in s["cells"].values())
        checks.append(item("dependencies", "Sources liées au classeur", ", ".join(scope["sheets"]),
                           {"formules_avec_crochets": external, "lecture": scope["values"]},
                           "Les crochets peuvent désigner un classeur externe ou une table ; pièces sources à relire", "INCONCLUSIVE" if external else "REVIEW"))
        checks.append(item("mapping", "Période et correspondances", selected["sheet"] if selected else "Classeur",
                           selected or {"candidates": scope["candidates"]}, scope["mapping_basis"], "REVIEW" if selected else "INCONCLUSIVE"))
    elif code == "workbook_errors":
        for s in sheets:
            for a, c in s["cells"].items():
                reason = "Erreur Excel enregistrée" if c["kind"] == "e" else "Référence de formule rompue" if "#REF!" in (c["formula"] or "") else "Valeur de formule absente" if c["formula"] is not None and not c["value"] else None
                if reason:
                    checks.append(item("error:"+s["name"]+":"+a, reason, s["name"]+"!"+a, c["value"], "Valeur disponible, sans référence rompue", "INCONCLUSIVE" if reason == "Valeur de formule absente" else "FAIL"))
        if not checks:
            checks.append(item("stored-clean", "Erreurs et valeurs enregistrées", "Classeur", stats, "Aucune erreur stockée ou valeur de formule absente ; ce n’est pas un recalcul", "PASS"))
    elif code == "formula_units":
        for s in sheets:
            for a, c in s["cells"].items():
                # Only same-column SUM ranges; formula functions are never evaluated.
                if c["formula"] is None or "%" in c["format"]:
                    continue
                ranges = re.findall(r"(?i)(?<![A-Z0-9_!])SUM\(\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)\)", c["formula"])
                for left, start, right, end in ranges:
                    if left.upper() != right.upper() or int(end)-int(start) > 2000:
                        continue
                    refs = [left.upper()+str(n) for n in range(int(start), int(end)+1) if "%" in s["cells"].get(left.upper()+str(n), {}).get("format", "")]
                    if refs:
                        checks.append(item("unit:"+s["name"]+":"+a, "Un total monétaire additionne un pourcentage", s["name"]+"!"+a,
                                           {"formule": c["formula"], "origine_formule_partagée": c.get("formula_origin"), "cellules_pourcentages": refs}, "Vérifier et corriger la plage de somme", "FAIL"))
        if not checks:
            checks.append(item("units-scope", "Plages de somme examinées", "Classeur", "Aucun mélange détecté dans les SUM verticales simples", "Les autres expressions et formats restent hors couverture", "REVIEW"))
    elif code in ("financial_equations", "analytical_variances"):
        if not selected:
            checks.append(item(code+":mapping", "Correspondances nécessaires", "Classeur", "P&L non reconnu ou sélection nécessaire", "Un couple Réel/Budget et des postes identifiés", "INCONCLUSIVE"))
        else:
            s = next(s for s in sheets if s["name"] == selected["sheet"])
            rows = selected["rows"]
            if code == "analytical_variances":
                # No materiality exclusion: every recognized row remains in the report.
                for key, row in rows.items():
                    aa, ba = selected["actual"]+str(row), selected["budget"]+str(row)
                    try:
                        actual, budget = amount(s["cells"].get(aa)), amount(s["cells"].get(ba))
                        delta = actual-budget
                        observed = {"réel": str(actual), "budget": str(budget), "écart": str(delta), "écart_pct": str(delta/abs(budget)*100) if budget else None, "unité": "valeurs numériques brutes du fichier", "période": selected["period"]}
                        status = "REVIEW" if delta else "PASS"
                    except ValueError:
                        observed, status = "Montant enregistré absent ou non numérique", "INCONCLUSIVE"
                    checks.append(item("variance:"+key, selected["labels"][key]+" — réel / budget", s["name"]+"!"+aa+" / "+ba, observed, "Écart à expliquer sur pièces ; aucun seuil d’exclusion", status))
            else:
                cols = sorted({column(a) for a in s["cells"] if colnum(column(a)) > 4}, key=colnum)
                for key, terms in EQUATIONS.items():
                    if key not in rows or not set(terms) <= rows.keys():
                        checks.append(item("equation-missing:"+key, "Équation non couverte : "+key, s["name"], "Postes requis non identifiés", terms, "INCONCLUSIVE"))
                        continue
                    for col in cols:
                        target = col+str(rows[key]); cell = s["cells"].get(target)
                        if cell is None or not cell["value"] or "%" in cell["format"]:
                            continue
                        refs = [col+str(rows[t]) for t in terms]
                        try:
                            actual = amount(cell)
                            expected = sum((amount(s["cells"].get(a)) for a in refs), Decimal(0))
                            delta = actual-expected
                            observed = {"enregistré": str(actual), "somme_postes": str(expected), "écart": str(delta), "cellules": refs}
                            status = "FAIL" if abs(delta) > tolerance else "PASS"
                        except ValueError:
                            observed, status = {"cellules": refs, "motif": "Valeur numérique manquante"}, "INCONCLUSIVE"
                        checks.append(item("equation:"+target, selected["labels"][key]+" — somme des postes", s["name"]+"!"+target, observed, scope["sign_convention"], status))
    elif code == "context_review":
        for rule in ctx["rules"]:
            checks.append(item("rule:"+str(rule["id"]), rule.get("title") or "Règle du dossier à vérifier", "Console · "+str(rule["id"])+" · v"+str(rule["version"]),
                               {k: rule.get(k) for k in ("text", "scope", "scope_from", "scope_to", "source", "validated_at")},
                               "Règle conservée pour revue humaine ; le P&L seul ne prouve pas son exécution", "INCONCLUSIVE"))
        if not checks:
            checks.append(item("no-context", "Contexte du dossier", "Console", "Aucune règle active capturée", "Documenter la méthode et les pièces nécessaires", "INCONCLUSIVE"))
    else:
        raise ValueError("unknown financial workbook control")
    # Lexical associations are navigation aids, never semantic conclusions or compliance tests.
    topics = {"paie": ("paie", "salair", "social", "dotation"), "financement": ("emprunt", "bpi", "interet", "financier"),
              "ventes": ("vente", "chiffredaffaires", "factureclient", "brandcontent", "publicit"),
              "achats": ("fournisseur", "facturemanquante", "honoraire")}
    for check in checks:
        title = norm(check["title"])
        words = [word for group in topics.values() if any(word in title for word in group) for word in group]
        if words:
            related = [m for m in ctx["memory"] if any(w in norm(m.get("text", "")+m.get("title", "")) for w in words)]
            if related:
                check["related_context"] = [{"id": m["id"], "version": m["version"], "title": m["title"], "date": m.get("date"), "text": m["text"]} for m in related]
                check["association_basis"] = "Rappels associés par mots-clés ; lien causal et résolution non établis"
    if len(checks) > 5000:
        raise ReviewFormatError("Trop de constats ; fournissez un extrait ciblé.")
    statuses = [c["status"] for c in checks]
    status = "FAIL" if "FAIL" in statuses else "INCONCLUSIVE" if not statuses or "INCONCLUSIVE" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS"
    return result(code, {"checks": checks}, "Contrôles bornés sur valeurs enregistrées et contexte versionné", status,
                  limits=["Pas de recalcul Excel ni de relecture du GL externe", "Règles et mémoire : références à examiner, pas preuve de conformité", "Correspondances et convention de signes à confirmer",
                          "Unités : SUM verticales simples, y compris partagées ; autres expressions hors couverture"])
