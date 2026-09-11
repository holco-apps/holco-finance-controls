"""Bounded read-only control packs. No execution of workbook formulas or macros."""
from __future__ import annotations

import csv
import io
import json
import posixpath
import re
import zipfile
from decimal import Decimal, InvalidOperation, localcontext
from functools import wraps
from xml.etree import ElementTree as ET

MAX_BYTES = 10 * 1024 * 1024
MAX_CELLS = 500_000
VERSION = "0.3.0"
CATALOG = {
    "excel_reconciliation": ["comparison_scope", "mapped_amounts"],
    "excel_snapshot": ["snapshot_scope", "cell_errors", "formula_references", "declared_equations"],
    "reconciliation_csv": ["population", "amounts"],
    "fec_tsv": ["population", "dates", "amounts", "entry_balance", "duplicates"],
    "workbook_xlsx": ["population", "stored_errors", "broken_references", "formula_caches"],
    "workbook_comparison": ["population", "numeric_stability"],
    "erp_agent_response": ["source_provenance", "extraction_coverage", "request_scope", "claim_sources", "claim_amounts", "tool_policy"],
}


def number(value: str) -> Decimal:
    try:
        result = Decimal(value.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise ValueError("invalid decimal") from None
    if (not result.is_finite() or abs(result) > Decimal("1e30")
            or result.as_tuple().exponent < -100):
        raise ValueError("non-finite or out-of-range decimal")
    return result


def result(code, observed, expected, status="PASS", **extra):
    return dict(control_id=code, status=status, observed=observed,
                expected=expected, rule_version=VERSION, **extra)


def table(raw: bytes, fec=False):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter="\t" if fec else ",")
    required = {"JournalCode", "EcritureNum", "EcritureDate", "Debit", "Credit"} if fec else {"id", "expected", "observed"}
    fields = reader.fieldnames or []
    if not required <= set(fields) or len(fields) != len(set(fields)):
        raise ValueError("missing or duplicate columns")
    rows = []
    for row in reader:
        if len(rows) >= 100_000 or None in row or any(v is None for v in row.values()):
            raise ValueError("row limit or malformed record")
        rows.append(row)
    return rows


def workbook(raw: bytes):
    """Read raw OOXML values, avoiding parser-created date conversion errors."""
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos = z.infolist()
        if (len(infos) > 2000 or len({i.filename for i in infos}) != len(infos)
                or sum(i.file_size for i in infos) > 100 * 1024 * 1024):
            raise ValueError("workbook archive limits exceeded")
        if any("vbaProject" in i.filename for i in infos):
            raise ValueError("macro-enabled workbook unsupported")

        def xml(path):
            data = z.read(path)
            if b"\x00" in data or re.search(br"<!\s*(DOCTYPE|ENTITY)", data, re.I):
                raise ValueError("XML declarations unsupported")
            return ET.fromstring(data)

        rels = {r.attrib["Id"]: r.attrib["Target"] for r in xml("xl/_rels/workbook.xml.rels")
                if r.attrib.get("TargetMode") != "External"}
        root = xml("xl/workbook.xml")
        cells = {}
        formulas = errors = broken = missing_cache = visited = 0
        for index, sheet in enumerate(root.findall("s:sheets/s:sheet", ns), 1):
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rels[rid]
            path = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
            if not path.startswith("xl/"):
                raise ValueError("invalid worksheet relationship")
            for c in xml(path).iter("{" + ns["s"] + "}c"):
                visited += 1
                if visited > 2_000_000:
                    raise ValueError("styled cell limit exceeded")
                if all(c.find("s:" + tag, ns) is None for tag in ("f", "v", "is")):
                    continue
                if len(cells) >= MAX_CELLS:
                    raise ValueError("cell limit exceeded")
                coord = c.attrib.get("r", "")
                if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]{0,6}", coord):
                    raise ValueError("invalid cell reference")
                key = (sheet.attrib["name"], coord)
                if key in cells:
                    raise ValueError("duplicate cell reference")
                f, v = c.find("s:f", ns), c.find("s:v", ns)
                val = v.text if v is not None else None
                kind = c.attrib.get("t", "n")
                formulas += f is not None
                broken += f is not None and "#REF!" in (f.text or "")
                missing_cache += f is not None and (v is None or val is None)
                errors += kind == "e"
                cells[key] = (kind, val)
        broken += sum("#REF!" in (n.text or "") for n in root.findall("s:definedNames/s:definedName", ns))
        return cells, dict(cells=len(cells), formulas=formulas, stored_errors=errors,
                           broken_references=broken, formula_caches=missing_cache)


def exact_money(method):
    @wraps(method)
    def call(*args, **kwargs):
        with localcontext() as ctx:
            ctx.prec = 160
            return method(*args, **kwargs)
    return call


@exact_money
def execute(pack: str, code: str, sources: list[bytes], tolerance: str, policy=None):
    tol = number(tolerance)
    try:
        if pack == "excel_reconciliation":
            from .excel_snapshot import reconciliation_control
            return reconciliation_control(code, sources, tol)
        if pack == "excel_snapshot":
            from .excel_snapshot import snapshot_control
            return snapshot_control(code, sources[0], tol)
        if pack == "erp_agent_response":
            return erp_control(code, sources, tol, policy or {})
        if pack.startswith("workbook"):
            cells, stats = workbook(sources[0])
            if code == "population":
                return result(code, stats, "at least one stored cell", "PASS" if cells else "INCONCLUSIVE")
            if code == "numeric_stability":
                other, _ = workbook(sources[1])
                changed = missing = compared = 0
                largest = Decimal(0)
                for key in cells.keys() | other.keys():
                    a, b = cells.get(key), other.get(key)
                    if a is None or b is None:
                        missing += 1
                    elif a[0] == "n" and b[0] == "n" and a[1] is not None and b[1] is not None:
                        delta = abs(number(a[1]) - number(b[1]))
                        compared += 1
                        changed += delta > tol
                        largest = max(largest, delta)
                    elif a != b:
                        missing += 1
                status = "FAIL" if changed else "INCONCLUSIVE" if missing or not compared else "PASS"
                return result(code, dict(compared=compared, above_tolerance=changed,
                                         uncomparable=missing, maximum_absolute_delta=str(largest)),
                              dict(absolute_tolerance=str(tol), same_population=True), status)
            count = stats[code]
            return result(code, count, 0, "FAIL" if count else "PASS")
        rows = table(sources[0], pack == "fec_tsv")
        if code == "population":
            return result(code, len(rows), "at least one record", "PASS" if rows else "INCONCLUSIVE")
        if not rows:
            return result(code, 0, "records required", "INCONCLUSIVE")
        if pack == "reconciliation_csv":
            if len({r["id"] for r in rows}) != len(rows) or any(not r["id"].strip() for r in rows):
                raise ValueError("missing or duplicate identifiers")
            deltas = [abs(number(r["observed"]) - number(r["expected"])) for r in rows]
            bad = sum(d > tol for d in deltas)
            return result(code, dict(compared=len(deltas), above_tolerance=bad,
                                     maximum_absolute_delta=str(max(deltas))),
                          dict(absolute_tolerance=str(tol)), "FAIL" if bad else "PASS")
        if code == "dates":
            from datetime import datetime
            bad = 0
            for r in rows:
                try:
                    if not re.fullmatch(r"\d{8}", r["EcritureDate"]):
                        raise ValueError()
                    datetime.strptime(r["EcritureDate"], "%Y%m%d")
                except ValueError:
                    bad += 1
            return result(code, bad, 0, "FAIL" if bad else "PASS")
        if code == "duplicates":
            bad = len(rows) - len({tuple(sorted(r.items())) for r in rows})
            return result(code, bad, 0, "FAIL" if bad else "PASS")
        balances = {}
        for r in rows:
            if not r["JournalCode"].strip() or not r["EcritureNum"].strip():
                raise ValueError("entry identifiers required")
            debit, credit = number(r["Debit"]), number(r["Credit"])
            if debit < 0 or credit < 0 or (debit and credit):
                raise ValueError("invalid debit/credit combination")
            key = (r["JournalCode"], r["EcritureNum"])
            balances[key] = balances.get(key, Decimal(0)) + debit - credit
        bad = sum(abs(v) > tol for v in balances.values()) if code == "entry_balance" else 0
        return result(code, bad, 0, "FAIL" if bad else "PASS")
    except (ValueError, KeyError, UnicodeError, zipfile.BadZipFile, ET.ParseError, csv.Error):
        return result(code, "source cannot be interpreted for this control", "valid supported input", "INCONCLUSIVE")


def erp_control(code, sources, tol, policy):
    """Snapshot is the comparison source; agent never supplies expected amounts.

    Provenance fields are declarations, not authentication. A production gateway
    must register the raw connector response and trace itself, outside the model.
    """
    try:
        snapshot, answer = (json.loads(raw) for raw in sources)
        records, claims = snapshot["records"], answer["claims"]
        if not isinstance(records, list) or not isinstance(claims, list) or len(records) > 100_000 or len(claims) > 1000:
            raise ValueError("invalid population")
        if not records or not claims:
            return result(code, "empty source or claims", "nonempty records and claims", "INCONCLUSIVE")
        by_id = {r["id"]: r for r in records}
        if (len(by_id) != len(records) or len({c["id"] for c in claims}) != len(claims)
                or any(not isinstance(r["id"], str) or not r["id"] for r in records + claims)):
            raise ValueError("duplicate or missing IDs")
        if code == "source_provenance":
            return result(code, "receipt checked only by persistent engine", "trusted capture receipt", "INCONCLUSIVE")
        if code == "request_scope":
            keys = {"required_period": "period", "required_currency": "currency", "required_scope": "scope"}
            if any(not policy.get(k) for k in keys):
                return result(code, "request criteria missing from plan", "approved period, currency and scope", "INCONCLUSIVE")
            matches = all(all(c[field] == policy[k] for k, field in keys.items()) for c in claims)
            return result(code, dict(matches_approved_request=matches), "all claims satisfy approved request criteria", "PASS" if matches else "FAIL")
        if code == "extraction_coverage":
            coverage = snapshot["coverage"]
            complete = (coverage.get("complete") is True and coverage.get("next_cursor") is None
                        and type(coverage.get("expected_records")) is int
                        and coverage["expected_records"] == len(records))
            return result(code, dict(received=len(records), complete=complete),
                          "complete extraction, no next cursor, expected count matches", "PASS" if complete else "INCONCLUSIVE")
        if code in {"claim_sources", "claim_amounts"}:
            bad = unknown = 0
            max_delta = Decimal(0)
            for c in claims:
                refs = c["record_ids"]
                if (not isinstance(refs, list) or not refs or len(refs) != len(set(refs))
                        or any(r not in by_id for r in refs)):
                    unknown += 1
                    continue
                selected = [by_id[r] for r in refs]
                if any(r["currency"] != c["currency"] or r["period"] != c["period"] for r in selected):
                    unknown += 1
                    continue
                if c.get("scope") == "all_period_records":
                    expected_ids = {r["id"] for r in records if r["currency"] == c["currency"] and r["period"] == c["period"]}
                    if set(refs) != expected_ids:
                        unknown += 1
                        continue
                elif c.get("scope") != "selected_records":
                    unknown += 1
                    continue
                if code == "claim_amounts":
                    expected = sum((number(r["amount"]) for r in selected), Decimal(0))
                    delta = abs(number(c["amount"]) - expected)
                    bad += delta > tol
                    max_delta = max(max_delta, delta)
            return result(code, dict(claims=len(claims), unsupported=unknown, mismatches=bad,
                                     maximum_absolute_delta=str(max_delta)),
                          dict(aggregation="sum of referenced ERP records", absolute_tolerance=str(tol)),
                          "FAIL" if bad or unknown else "PASS")
        # Trace belongs to the connector snapshot, never to the agent answer.
        calls = snapshot.get("tool_calls")
        allowed, required = policy.get("allowed_tools", []), policy.get("required_tools", [])
        if not allowed or not isinstance(calls, list) or not calls:
            return result(code, "missing trace or tool policy", "trusted read-only trace and explicit allowed tools", "INCONCLUSIVE")
        seen = {c["name"] for c in calls}
        bad = any(c["name"] not in allowed or c.get("operation") != "read" or c.get("status") != "success" for c in calls)
        bad |= not set(required) <= seen
        return result(code, dict(calls=len(calls), policy_satisfied=not bad),
                      "allowed, successful read-only calls; required tools present", "FAIL" if bad else "PASS")
    except (ValueError, KeyError, TypeError, AttributeError):
        return result(code, "invalid ERP snapshot or answer schema", "documented JSON schema", "INCONCLUSIVE")
