"""Reproducible, fictitious XLSX starter. No customer data or runtime dependency."""
import io
import zipfile
from xml.sax.saxutils import escape
from .review_xlsx import HEADERS, SHEET


def template_bytes():
    rows = [HEADERS,
            ["Ventes", "2025", 100000, 125000, 125000, "Nouveau contrat", 25000, "Contrat à examiner"],
            ["Charges externes", "2025", 30000, 42000, 41000, "Hausse des loyers", 8000, "Bail à examiner"],
            ["Salaires", "2025", 60000, 60500, 60500, "", "", ""]]
    guide = [["HOLCO Control — modèle de revue, données fictives"],
             ["Remplacez les exemples de la feuille Revue HOLCO par vos données autorisées."],
             ["Conservez son nom, les huit colonnes et leurs en-têtes en première ligne."],
             ["Montants en EUR, au plus 2 000 postes ; collez les valeurs, sans formules ni cellules fusionnées."],
             ["L'exercice doit correspondre à celui choisi dans HOLCO Control."],
             ["Toutes les lignes remplies sont incluses, même masquées ou filtrées."],
             ["Les autres feuilles ne font pas partie de cette revue métier."],
             ["N et Reporting sont des montants déclarés ici, sans connexion automatique à un ERP."],
             ["Les pièces citées doivent être examinées par le réviseur ; leur contenu n'est pas lu."],
             ["Le modèle comporte volontairement des écarts et ne vaut pas validation professionnelle."]]

    def sheet(data, widths):
        rendered = []
        for i, row in enumerate(data, 1):
            cells = []
            for j, value in enumerate(row):
                ref = f"{chr(65+j)}{i}"
                if isinstance(value, int):
                    cells.append(f'<c r="{ref}"><v>{value}</v></c>')
                else:
                    cells.append(f'<c r="{ref}" t="inlineStr" s="{1 if i == 1 else 0}"><is><t xml:space="preserve">{escape(value)}</t></is></c>')
            rendered.append(f'<row r="{i}">' + ''.join(cells) + '</row>')
        cols = ''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths, 1))
        return ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews>'
                f'<cols>{cols}</cols><sheetData>{"".join(rendered)}</sheetData></worksheet>')

    contents = {
        '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': f'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{SHEET}" sheetId="1" r:id="rId1"/><sheet name="Mode emploi" sheetId="2" r:id="rId2"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        'xl/styles.xml': '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF284F8A"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf fontId="0" fillId="0" borderId="0" xfId="0"/><xf fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
        'xl/worksheets/sheet1.xml': sheet(rows, [25, 12, 18, 18, 18, 30, 22, 30]),
        'xl/worksheets/sheet2.xml': sheet(guide, [125]),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data.encode())
    return buffer.getvalue()


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_bytes(template_bytes())
