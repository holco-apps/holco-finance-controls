"""Bounded review worksheet. Explicit declarations, never an attestation or NLP judge."""
import csv
import io
from decimal import Decimal

from .packs import number, result

FIELDS = ["poste", "periode", "n_1", "n", "reporting", "explication", "montant_explique", "piece"]
LIMITS = {"variance_amount": "1000", "variance_percent": "20"}


def read_review(raw):
    if raw.startswith(b"PK"):
        from .review_xlsx import read_xlsx_review
        return read_xlsx_review(raw)[0]
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";")
    if reader.fieldnames != FIELDS:
        raise ValueError("Expected review template columns: " + ";".join(FIELDS))
    rows, seen = [], set()
    for line, row in enumerate(reader, 2):
        if len(rows) >= 2000 or None in row or any(v is None or len(v) > 2000 for v in row.values()):
            raise ValueError("Malformed or oversized review worksheet")
        if not row["poste"].strip() or row["poste"] in seen:
            raise ValueError("Missing or duplicate review item")
        seen.add(row["poste"])
        for field in ("n_1", "n", "reporting", "montant_explique"):
            row[field] = number(row[field]) if row[field].strip() else None
        row["line"] = line
        rows.append(row)
    if not rows:
        raise ValueError("Empty review population")
    return rows


def is_variation(row):
    if row["n"] is None or row["n_1"] is None:
        return None
    delta = abs(row["n"] - row["n_1"])
    return delta >= Decimal(LIMITS["variance_amount"]) and (
        row["n_1"] == 0 or delta * 100 >= abs(row["n_1"]) * Decimal(LIMITS["variance_percent"]))


def review_control(code, raw, tolerance, policy):
    rows = read_review(raw)
    checks = []

    def add(row, status, title, observed, expected):
        checks.append(dict(id=f"{code}:{row['line']}", status=status, title=title,
                           location=(f"{row['sheet']}!A{row['line']}:H{row['line']} · {row['poste']}" if row.get("sheet") else f"ligne {row['line']} · {row['poste']}"),
                           observed=observed, expected=expected))

    for row in rows:
        if code == "source_scope":
            expected = policy.get("required_period")
            status = "INCONCLUSIVE" if not expected or not row["periode"] else "PASS" if row["periode"] == expected else "FAIL"
            add(row, status, "Période de la source", row["periode"], expected or "Période à préciser")
        elif code == "reconciliations":
            a, b = row["n"], row["reporting"]
            status = "INCONCLUSIVE" if a is None or b is None else "PASS" if abs(a-b) <= tolerance else "FAIL"
            add(row, status, "Rapprochement comptabilité / reporting", str(b) if b is not None else None,
                str(a) if a is not None else "Montant comptable manquant")
        elif code == "variations":
            flag = is_variation(row)
            delta = row["n"]-row["n_1"] if flag is not None else None
            add(row, "INCONCLUSIVE" if flag is None else "REVIEW" if flag else "PASS",
                "Variation N / N-1", str(delta) if delta is not None else None,
                "Revue dès 1 000 EUR et 20 % ; base nulle : seuil absolu seul")
        elif code == "explanations":
            flag = is_variation(row)
            if flag is False:
                continue
            amount = row["montant_explique"]
            missing = flag is None or not row["explication"].strip() or not row["piece"].strip() or amount is None
            status = "INCONCLUSIVE" if missing else "REVIEW" if abs(amount-(row["n"]-row["n_1"])) <= tolerance else "FAIL"
            add(row, status, "Explication de la variation", dict(explication=row["explication"],
                montant=str(amount) if amount is not None else None, piece_declaree=row["piece"]),
                "Montant expliqué égal à la variation ; pièce citée à examiner par le réviseur")
        elif code == "review_coverage":
            missing = any(row[f] is None for f in ("n_1", "n", "reporting")) or (is_variation(row) and not row["piece"].strip())
            add(row, "INCONCLUSIVE" if missing else "REVIEW", "Point de revue",
                "Information ou référence manquante" if missing else "Données disponibles pour la revue",
                "Examen humain des pièces et de la suffisance des travaux")
        else:
            raise ValueError("Unknown review control")
    if code == "reconciliations" and all(r["n"] is not None and r["reporting"] is not None for r in rows):
        expected = sum((r["n"] for r in rows), Decimal(0))
        observed = sum((r["reporting"] for r in rows), Decimal(0))
        checks.append(dict(id="reconciliations:total", status="PASS" if abs(expected-observed)<=tolerance else "FAIL",
                           title="Total du périmètre", location="Toutes les lignes importées", observed=str(observed), expected=str(expected)))
    statuses = [c["status"] for c in checks]
    status = "FAIL" if "FAIL" in statuses else "INCONCLUSIVE" if "INCONCLUSIVE" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS"
    return result(code, dict(checks=checks, population=len(rows)),
                  "Contrôles bornés au tableau de revue déclaré", status,
                  method_version="holco.review-worksheet/1", limits=[
                      "Authenticité et exhaustivité comptables non attestées",
                      "Pièces uniquement citées dans ce tableau, non vérifiées automatiquement",
                      "Aucune analyse sémantique ni conclusion de mission professionnelle"])
