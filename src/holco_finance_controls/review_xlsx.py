"""Read an explicitly named review table; never evaluate formulas or guess mappings."""
import csv
import io
import posixpath
import re
import zipfile
from xml.etree import ElementTree as ET

from .packs import workbook

SHEET = "Revue HOLCO"
HEADERS = ["Poste", "Exercice", "N-1", "N", "Reporting", "Explication", "Montant expliqué", "Pièce"]
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


class ReviewFormatError(ValueError):
    """A bounded, user-facing format error, without embedding source values."""


def read_xlsx_review(raw, required=True):
    workbook(raw)  # Existing archive, macro, XML, cell and relationship limits.
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        def xml(path):
            data = archive.read(path)
            if b"\x00" in data or re.search(br"<!\s*(DOCTYPE|ENTITY)", data, re.I):
                raise ReviewFormatError("Déclarations XML non prises en charge.")
            return ET.fromstring(data)

        sheets = xml("xl/workbook.xml").findall("s:sheets/s:sheet", NS)
        selected = [s for s in sheets if s.get("name") == SHEET]
        if not selected:
            if required:
                raise ReviewFormatError("Utilisez le modèle Excel et sa feuille « Revue HOLCO ».")
            return None
        if len(selected) != 1 or selected[0].get("state", "visible") != "visible":
            raise ReviewFormatError("La feuille de revue doit être unique et visible.")
        rels = {r.get("Id"): r.get("Target") for r in xml("xl/_rels/workbook.xml.rels")
                if r.get("TargetMode") != "External"}
        target = rels[selected[0].get(RID)]
        path = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
        root = xml(path)
        if root.find("s:mergeCells", NS) is not None:
            raise ReviewFormatError("Séparez les cellules fusionnées dans la feuille de revue.")
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ["".join(t.text or "" for t in item.iter("{" + NS["s"] + "}t"))
                      for item in xml("xl/sharedStrings.xml").findall("s:si", NS)]
            if len(shared) > 100000 or any(len(t) > 2000 for t in shared):
                raise ReviewFormatError("Le texte du classeur dépasse les limites du modèle.")
        rows = {}
        for cell in root.findall("s:sheetData/s:row/s:c", NS):
            value, formula, inline = cell.find("s:v", NS), cell.find("s:f", NS), cell.find("s:is", NS)
            if value is None and formula is None and inline is None:
                continue
            coord = cell.get("r", "")
            match = re.fullmatch(r"([A-H])([1-9][0-9]*)", coord)
            if not match or int(match[2]) > 2001:
                raise ReviewFormatError("La revue accepte les colonnes A à H et 2 000 lignes de données.")
            if formula is not None:
                raise ReviewFormatError("Collez les valeurs dans la feuille de revue : ses formules ne sont pas recalculées.")
            kind = cell.get("t", "n")
            text = value.text or "" if value is not None else ""
            if kind == "inlineStr":
                text = "".join(t.text or "" for t in cell.findall("s:is//s:t", NS))
            elif kind == "s":
                if not re.fullmatch(r"[0-9]+", text) or int(text) >= len(shared):
                    raise ReviewFormatError("Une référence de texte du classeur est invalide.")
                text = shared[int(text)]
            elif kind not in {"n", "str"}:
                raise ReviewFormatError("Une cellule de revue contient une erreur ou un type non pris en charge.")
            if len(text) > 2000:
                raise ReviewFormatError("Une cellule de revue dépasse 2 000 caractères.")
            if not text.strip():
                continue
            rows.setdefault(int(match[2]), [""] * 8)[ord(match[1]) - ord("A")] = text
        if rows.pop(1, None) != HEADERS:
            raise ReviewFormatError("Conservez les huit en-têtes du modèle Excel sur la première ligne.")
        if not rows:
            raise ReviewFormatError("Ajoutez au moins un poste dans la feuille de revue.")
        from .dossier_review import FIELDS, read_review
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";")
        writer.writerow(FIELDS)
        line_numbers = sorted(rows)
        writer.writerows(rows[n] for n in line_numbers)
        parsed = read_review(out.getvalue().encode())
        for row, line in zip(parsed, line_numbers):
            row["line"] = line
            row["sheet"] = SHEET
        scope = dict(sheet=SHEET, range=f"A1:H{max(line_numbers)}", rows=len(parsed),
                     excluded_sheets=[s.get("name") for s in sheets if s.get("name") != SHEET],
                     values_only=True, hidden_rows_included=True)
        return parsed, scope
