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
VERSION = "0.6.0"

# Machine-readable reason codes. Any INCONCLUSIVE or NOT_RUN result must carry
# one: a regulator does not accept "the computer could not conclude" without
# knowing whether evidence was missing, input invalid or over limits, a
# precondition unmet, the control excluded by an accountable plan decision, or
# simply not executed yet. INVALID_INPUT and INPUT_LIMIT_EXCEEDED predate this
# enforcement (0.4.1) and keep their published meaning.
REASON_CODES = ("INVALID_INPUT", "INPUT_LIMIT_EXCEEDED", "MISSING_EVIDENCE",
                "PRECONDITION_FAILED", "EXCLUDED_BY_PLAN", "NOT_EXECUTED")

# Default-deny universal layer: a plan may only exclude controls listed here.
# Everything absent from this map is universal and cannot be deselected.
EXCLUDABLE = {
    "fec_tsv": ("duplicates",),
    "dossier_review": ("variations", "explanations"),
    "dossier_review_xlsx": ("variations", "explanations"),
    "financial_workbook": ("analytical_variances", "context_review"),
}

CATALOG = {
    "financial_workbook": ["workbook_scope", "workbook_errors", "formula_units", "financial_equations", "analytical_variances", "context_review"],
    "dossier_review_xlsx": ["source_scope", "reconciliations", "variations", "explanations", "review_coverage"],
    "dossier_review": ["source_scope", "reconciliations", "variations", "explanations", "review_coverage"],
    "excel_reconciliation": ["comparison_scope", "mapped_amounts"],
    "excel_snapshot": ["snapshot_scope", "cell_errors", "formula_references", "declared_equations"],
    "reconciliation_csv": ["population", "amounts", "aggregate_amounts"],
    "fec_tsv": ["population", "dates", "amounts", "entry_balance", "duplicates"],
    "workbook_xlsx": ["population", "stored_errors", "broken_references", "formula_caches"],
    "workbook_comparison": ["population", "numeric_stability"],
    "erp_agent_response": ["source_provenance", "extraction_coverage", "request_scope", "claim_sources", "claim_amounts", "tool_policy"],
}


class InputLimitError(ValueError):
    def __init__(self, name, maximum):
        self.limit = dict(name=name, maximum=maximum)
        super().__init__(f"input limit exceeded: {name} maximum {maximum}")


# How many located findings a control reports inline. Matches the existing cap used by the
# snapshot controls (`addresses=…[:100]`), so every pack answers "where" the same way.
# The cap never hides its own effect: controls also report how many findings were omitted.
EVIDENCE_CAP = 100

# A caller that must audit every location, rather than read the first hundred, may raise the
# cap through the plan policy. Bounded, because an unbounded evidence list turns a control
# result into an unbounded payload. The bound matches the snapshot pack's cell limit.
MAX_EVIDENCE_CAP = 10_000


def evidence_cap(policy):
    """Resolve the located-findings cap from a plan policy. Default 100, hard bound 10 000.

    Rejects rather than clamps: a caller that asked for 50 000 locations and silently received
    10 000 would compute a recall against a truncated set and never know it.
    """
    if not policy or "evidence_cap" not in policy:
        return EVIDENCE_CAP
    cap = policy["evidence_cap"]
    if isinstance(cap, bool) or not isinstance(cap, int) or not 0 < cap <= MAX_EVIDENCE_CAP:
        raise ValueError(f"evidence_cap must be an integer in 1..{MAX_EVIDENCE_CAP}")
    return cap


def cell_order(key):
    """Sort key giving a stable, human-ordered walk over (sheet, A1) cell references.

    Two reasons this exists, and both matter more than they look:

    1. **Reproducibility.** Cells are collected in a set union, and set iteration order over
       tuples of strings varies between processes. A capped list of findings drawn from an
       unordered walk would report a *different* 100 cells on every run, from identical
       inputs. A control whose evidence changes without its inputs changing is not a control.
    2. **Readability.** Plain string ordering puts V10 before V9. Splitting the column letters
       from the row number keeps a reviewer walking the sheet the way they read it.
    """
    sheet, coord = key
    match = re.fullmatch(r"([A-Z]{1,3})([0-9]+)", coord)
    if not match:  # unreachable: coordinates are validated at parse time
        return (sheet, "", 0, coord)
    column, row = match.groups()
    return (sheet, len(column), column, int(row))


def number(value: str) -> Decimal:
    try:
        result = Decimal(value.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise ValueError("invalid decimal") from None
    if (not result.is_finite() or abs(result) > Decimal("1e30")
            or result.as_tuple().exponent < -100):
        raise ValueError("non-finite or out-of-range decimal")
    return result


def result(code, observed, expected, status="PASS", reason_code=None, **extra):
    if status in {"INCONCLUSIVE", "NOT_RUN"}:
        if reason_code not in REASON_CODES:
            raise ValueError(f"a {status} result requires a machine-readable reason_code among: " + ", ".join(REASON_CODES))
        extra["reason_code"] = reason_code
    elif reason_code is not None:
        raise ValueError("only INCONCLUSIVE or NOT_RUN results carry a reason_code")
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
        if len(rows) >= 100_000:
            raise InputLimitError("rows", 100_000)
        if None in row or any(v is None for v in row.values()):
            raise ValueError("malformed record")
        rows.append(row)
    return rows


def workbook(raw: bytes):
    try:
        return _workbook(raw)
    except KeyError:
        raise ValueError("missing OOXML part or required attribute") from None


def _workbook(raw: bytes):
    """Read raw OOXML values, avoiding parser-created date conversion errors."""
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos = z.infolist()
        if len(infos) > 2000:
            raise InputLimitError("archive_entries", 2000)
        if len({i.filename for i in infos}) != len(infos):
            raise ValueError("duplicate archive entry")
        if sum(i.file_size for i in infos) > 100 * 1024 * 1024:
            raise InputLimitError("uncompressed_bytes", 100 * 1024 * 1024)
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
                    raise InputLimitError("visited_cells", 2_000_000)
                if all(c.find("s:" + tag, ns) is None for tag in ("f", "v", "is")):
                    continue
                if len(cells) >= MAX_CELLS:
                    raise InputLimitError("stored_cells", MAX_CELLS)
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
    if pack not in CATALOG or code not in CATALOG[pack]:
        raise ValueError("unknown control pack or code")
    tol = number(tolerance)
    if tol < 0:
        raise ValueError("tolerance must be nonnegative")
    # Resolved here, deliberately outside the try below. That handler turns ValueError into
    # INCONCLUSIVE/INVALID_INPUT, which means "this source cannot be interpreted". A caller
    # who passes an unusable evidence_cap would then be told the client's workbook is at
    # fault. A caller error must surface as a caller error.
    cap = evidence_cap(policy)
    try:
        if pack == "financial_workbook":
            from .financial_workbook import control
            return control(code, sources, tol, policy or {})
        if pack in {"dossier_review", "dossier_review_xlsx"}:
            from .dossier_review import review_control
            return review_control(code, sources[0], tol, policy or {})
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
                return result(code, stats, "at least one stored cell", "PASS" if cells else "INCONCLUSIVE",
                              reason_code=None if cells else "MISSING_EVIDENCE")
            if code == "numeric_stability":
                other, _ = workbook(sources[1])
                changed = missing = compared = 0
                largest = Decimal(0)
                # A count is not a finding. "521 cells differ" tells a reviewer that something
                # is wrong and nothing about where, so it cannot be acted on, defended to an
                # auditor, or scored against an expected set of locations. Both outcomes are
                # therefore located: the cells that moved, and the cells that could not be
                # compared at all, since the latter bound what this control is able to see.
                divergences, uncomparable = [], []
                for key in sorted(cells.keys() | other.keys(), key=cell_order):
                    a, b = cells.get(key), other.get(key)
                    if a is None or b is None:
                        missing += 1
                        if len(uncomparable) < cap:
                            uncomparable.append(dict(sheet=key[0], cell=key[1],
                                                     reason="absent from one workbook"))
                    elif a[0] == "n" and b[0] == "n" and a[1] is not None and b[1] is not None:
                        delta = abs(number(a[1]) - number(b[1]))
                        compared += 1
                        largest = max(largest, delta)
                        if delta > tol:
                            changed += 1
                            if len(divergences) < cap:
                                divergences.append(dict(sheet=key[0], cell=key[1],
                                                        left=a[1], right=b[1], delta=str(delta)))
                    else:
                        # Equal missing caches, errors or unsupported text are not numeric evidence.
                        missing += 1
                        if len(uncomparable) < cap:
                            uncomparable.append(dict(sheet=key[0], cell=key[1],
                                                     reason="not numeric on both sides"))
                status = "FAIL" if changed else "INCONCLUSIVE" if missing or not compared else "PASS"
                return result(code, dict(compared=compared, above_tolerance=changed,
                                         uncomparable=missing, maximum_absolute_delta=str(largest),
                                         divergences=divergences,
                                         divergences_omitted=changed - len(divergences),
                                         uncomparable_locations=uncomparable,
                                         uncomparable_omitted=missing - len(uncomparable),
                                         evidence_cap=cap),
                              dict(absolute_tolerance=str(tol), same_population=True), status,
                              reason_code="MISSING_EVIDENCE" if status == "INCONCLUSIVE" else None)
            count = stats[code]
            return result(code, count, 0, "FAIL" if count else "PASS")
        rows = table(sources[0], pack == "fec_tsv")
        if code == "population":
            return result(code, len(rows), "at least one record", "PASS" if rows else "INCONCLUSIVE",
                          reason_code=None if rows else "MISSING_EVIDENCE")
        if not rows:
            return result(code, 0, "records required", "INCONCLUSIVE", reason_code="MISSING_EVIDENCE")
        if pack == "reconciliation_csv":
            if len({r["id"] for r in rows}) != len(rows) or any(not r["id"].strip() for r in rows):
                raise ValueError("missing or duplicate identifiers")
            if code == "aggregate_amounts":
                # Per-line tolerance is exploitable by splitting one drift into many
                # sub-tolerance lines; signed drifts are summed overall and per
                # optional "group" column (counterparty, period). Aggregate drift is
                # a signal, framed REVIEW, never an automatic FAIL.
                has_group = "group" in rows[0]
                net, grouped = Decimal(0), {}
                for r in rows:
                    signed = number(r["observed"]) - number(r["expected"])
                    net += signed
                    if has_group:
                        key = r["group"].strip()
                        if not key:
                            raise ValueError("empty group identifier")
                        grouped[key] = grouped.get(key, Decimal(0)) + signed
                offenders = sorted(k for k, v in grouped.items() if abs(v) > tol)
                drifted = abs(net) > tol or bool(offenders)
                return result(code, dict(net_signed_drift=str(net), groups=len(grouped),
                                         groups_above_tolerance=offenders[:100]),
                              dict(absolute_tolerance=str(tol),
                                   aggregation="signed observed minus expected, summed overall and per optional group column"),
                              "REVIEW" if drifted else "PASS")
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
        invalid = 0
        for r in rows:
            if not r["JournalCode"].strip() or not r["EcritureNum"].strip():
                raise ValueError("entry identifiers required")
            debit, credit = number(r["Debit"]), number(r["Credit"])
            if debit < 0 or credit < 0 or (debit and credit):
                invalid += 1
            key = (r["JournalCode"], r["EcritureNum"])
            balances[key] = balances.get(key, Decimal(0)) + debit - credit
        if code == "amounts":
            return result(code, dict(checked_rows=len(rows), invalid_amount_rows=invalid),
                          dict(invalid_amount_rows=0, rule="nonnegative debit and credit; not both nonzero"),
                          "FAIL" if invalid else "PASS")
        if invalid:
            return result(code, dict(invalid_amount_rows=invalid), "valid amounts before entry balancing", "INCONCLUSIVE",
                          reason_code="PRECONDITION_FAILED")
        bad = sum(abs(v) > tol for v in balances.values())
        return result(code, dict(checked_entries=len(balances), unbalanced_entries=bad),
                      dict(unbalanced_entries=0, absolute_tolerance=str(tol)), "FAIL" if bad else "PASS")
    except InputLimitError as exc:
        return result(code, "input exceeds supported processing limit", "input within published limits",
                      "INCONCLUSIVE", reason_code="INPUT_LIMIT_EXCEEDED", limit=exc.limit)
    except (ValueError, UnicodeError, zipfile.BadZipFile, ET.ParseError, csv.Error):
        return result(code, "source cannot be interpreted for this control", "valid supported input",
                      "INCONCLUSIVE", reason_code="INVALID_INPUT")


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
            return result(code, "empty source or claims", "nonempty records and claims", "INCONCLUSIVE",
                          reason_code="MISSING_EVIDENCE")
        by_id = {r["id"]: r for r in records}
        if (len(by_id) != len(records) or len({c["id"] for c in claims}) != len(claims)
                or any(not isinstance(r["id"], str) or not r["id"] for r in records + claims)):
            raise ValueError("duplicate or missing IDs")
        if code == "source_provenance":
            return result(code, "receipt checked only by persistent engine", "trusted capture receipt", "INCONCLUSIVE",
                          reason_code="PRECONDITION_FAILED")
        if code == "request_scope":
            keys = {"required_period": "period", "required_currency": "currency", "required_scope": "scope"}
            if any(not policy.get(k) for k in keys):
                return result(code, "request criteria missing from plan", "approved period, currency and scope", "INCONCLUSIVE",
                              reason_code="PRECONDITION_FAILED")
            matches = all(all(c[field] == policy[k] for k, field in keys.items()) for c in claims)
            return result(code, dict(matches_approved_request=matches), "all claims satisfy approved request criteria", "PASS" if matches else "FAIL")
        if code == "extraction_coverage":
            coverage = snapshot["coverage"]
            complete = (coverage.get("complete") is True and coverage.get("next_cursor") is None
                        and type(coverage.get("expected_records")) is int
                        and coverage["expected_records"] == len(records))
            return result(code, dict(received=len(records), complete=complete),
                          "complete extraction, no next cursor, expected count matches", "PASS" if complete else "INCONCLUSIVE",
                          reason_code=None if complete else "MISSING_EVIDENCE")
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
            return result(code, "missing trace or tool policy", "trusted read-only trace and explicit allowed tools", "INCONCLUSIVE",
                          reason_code="MISSING_EVIDENCE" if allowed else "PRECONDITION_FAILED")
        seen = {c["name"] for c in calls}
        bad = any(c["name"] not in allowed or c.get("operation") != "read" or c.get("status") != "success" for c in calls)
        bad |= not set(required) <= seen
        return result(code, dict(calls=len(calls), policy_satisfied=not bad),
                      "allowed, successful read-only calls; required tools present", "FAIL" if bad else "PASS")
    except (ValueError, KeyError, TypeError, AttributeError):
        return result(code, "invalid ERP snapshot or answer schema", "documented JSON schema", "INCONCLUSIVE",
                      reason_code="INVALID_INPUT")
