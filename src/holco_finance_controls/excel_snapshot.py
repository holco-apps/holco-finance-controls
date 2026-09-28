"""Read-only observations from a spreadsheet client, never a reconstructed XLSX."""
import json
import re
from decimal import Decimal, localcontext

ADDRESS = re.compile(r"[A-Z]{1,3}[1-9][0-9]{0,6}\Z")

SCOPE = re.compile(r"([A-Z]{1,3})([1-9][0-9]{0,6}):([A-Z]{1,3})([1-9][0-9]{0,6})\Z")
REFERENCE = re.compile(r"(?<![A-Z0-9_])\$?([A-Z]{1,3})\$?([1-9][0-9]{0,6})(?![A-Z0-9_])")


def formula_references(formula):
    """Return A1 references in one observed-sheet formula without evaluating it.

    This deliberately recognises only local A1 references.  Cross-sheet and
    structured references stay outside this snapshot control's asserted scope.
    """
    expression = re.sub(r'"(?:[^"]|"")*"', '', (formula or "").upper())
    return {column.replace("$", "") + row for column, row in REFERENCE.findall(expression)}


def column_number(column):
    value = 0
    for character in column:
        value = value * 26 + ord(character) - 64
    return value


def scope_addresses(scope):
    match = SCOPE.fullmatch(scope)
    if not match:
        raise ValueError("snapshot scope must be one A1 range")
    start_column, start_row, end_column, end_row = match.groups()
    start_column, end_column = column_number(start_column), column_number(end_column)
    start_row, end_row = int(start_row), int(end_row)
    if start_column > end_column or start_row > end_row:
        raise ValueError("invalid snapshot scope")
    if (end_column - start_column + 1) * (end_row - start_row + 1) > 40_000:
        raise ValueError("snapshot scope too large")
    expected = set()
    for column in range(start_column, end_column + 1):
        text = ""
        value = column
        while value:
            value, remainder = divmod(value - 1, 26)
            text = chr(65 + remainder) + text
        expected.update(text + str(row) for row in range(start_row, end_row + 1))
    return expected


def dependency_findings(cells):
    # The local A1 graph cannot resolve sheet-qualified or structured references.
    # Exclude the whole expression rather than confusing another sheet's A1 with
    # this sheet's A1. An excluded formula is unknown, never proof of no cycle.
    unsupported = []
    formulas = {}
    for address, cell in cells.items():
        formula = cell.get("formula")
        if formula is None:
            continue
        expression = re.sub(r'"(?:[^"]|"")*"', '', formula)
        expression = re.sub(r"#REF!", "", expression, flags=re.I)
        expression = expression.upper()
        # Functions with dynamic references and ranges need a richer parser.
        # Function names (e.g. LOG10) must not be mistaken for cell addresses.
        calls = re.findall(r"([A-Z_][A-Z0-9_.]*)\s*\(", expression)
        simple = re.sub(r"[A-Z_][A-Z0-9_.]*\s*(?=\()", "", expression)
        remainder = REFERENCE.sub("", simple)
        if (any(token in expression for token in ("!", "[", ":"))
                or any(name not in {"SUM", "MIN", "MAX", "ABS", "ROUND", "ROUNDUP",
                                    "ROUNDDOWN", "IF", "IFERROR", "COUNT", "COUNTA",
                                    "AVERAGE", "LOG10", "SQRT", "AND", "OR", "NOT"}
                       for name in calls)
                or re.search(r"[^0-9\s=+*/^%(),.<>\-]", remainder)):
            unsupported.append(address)
            continue
        formulas[address] = formula_references(simple)
    graph = {address: {ref for ref in refs if ref in formulas}
             for address, refs in formulas.items()}
    unresolved = sorted({ref for refs in formulas.values() for ref in refs if ref not in cells})
    missing = sum("formula" not in cell for cell in cells.values())
    direct = sorted(address for address, refs in formulas.items() if address in refs)
    # Iterative Kosaraju traversal: every member of each cyclic component is
    # reported, including vertices reached after a previous DFS branch finished.
    visited, finished = set(), []
    for root in graph:
        if root in visited:
            continue
        visited.add(root)
        frames = [(root, iter(sorted(graph[root])))]
        while frames:
            node, targets = frames[-1]
            target = next(targets, None)
            if target is None:
                finished.append(node)
                frames.pop()
            elif target not in visited:
                visited.add(target)
                frames.append((target, iter(sorted(graph[target]))))
    reverse = {node: set() for node in graph}
    for node, targets in graph.items():
        for target in targets:
            reverse[target].add(node)
    assigned, cycles = set(), set()
    for root in reversed(finished):
        if root in assigned:
            continue
        component, pending = set(), [root]
        assigned.add(root)
        while pending:
            node = pending.pop()
            component.add(node)
            for target in reverse[node] - assigned:
                assigned.add(target)
                pending.append(target)
        if len(component) > 1 or root in graph[root]:
            cycles.update(component)
    return dict(direct_self_references=direct[:100], circular_references=sorted(cycles)[:100],
                direct_count=len(direct), circular_count=len(cycles), formula_cells=len(formulas),
                missing_formula_view=missing,
                unresolved_reference_count=len(unresolved),
                unresolved_reference_addresses=unresolved[:100],
                unsupported_formula_count=len(unsupported),
                unsupported_formula_addresses=sorted(unsupported)[:100])


def parse_snapshot(raw):
    from .packs import number
    data = json.loads(raw)
    for key in ("workbook", "sheet", "scope", "captured_at"):
        if not isinstance(data.get(key), str) or not 0 < len(data[key]) <= 250:
            raise ValueError("snapshot metadata missing")
    rows = data.get("cells")
    if not isinstance(rows, list) or not 0 < len(rows) <= 10000:
        raise ValueError("snapshot needs 1..10000 observed cells")
    cells = {}
    for cell in rows:
        address = cell.get("address", "")
        if not isinstance(address, str) or not ADDRESS.fullmatch(address) or address in cells:
            raise ValueError("invalid or duplicate cell")
        if "value" not in cell or isinstance(cell["value"], (dict, list)):
            raise ValueError("missing scalar value")
        if isinstance(cell["value"], (int, float)) and not isinstance(cell["value"], bool):
            number(str(cell["value"]))
        for key in ("formula", "error"):
            if cell.get(key) is not None and (not isinstance(cell[key], str) or len(cell[key]) > 8192):
                raise ValueError("invalid cell observation")
        cells[address] = cell
    if len(scope_addresses(data["scope"])) > len(cells) * 4:
        raise ValueError("snapshot scope is broader than observed cells")
    if set(cells) - scope_addresses(data["scope"]):
        raise ValueError("observed cells outside snapshot scope")
    checks = data.get("checks", [])
    if not isinstance(checks, list) or len(checks) > 500:
        raise ValueError("check limit")
    ids = set()
    for check in checks:
        cid = check.get("id")
        if not isinstance(cid, str) or not 0 < len(cid) <= 100 or cid in ids:
            raise ValueError("invalid or duplicate check id")
        ids.add(cid)
        if not ADDRESS.fullmatch(str(check.get("target", ""))):
            raise ValueError("invalid target")
        terms = check.get("terms")
        if not isinstance(terms, list) or not 0 < len(terms) <= 100:
            raise ValueError("invalid equation")
        for term in terms:
            if not ADDRESS.fullmatch(str(term.get("address", ""))) or term["address"] == check["target"]:
                raise ValueError("invalid or self-referential equation")
            if number(term.get("coefficient", "1")) == 0:
                raise ValueError("zero term")
    return data, cells


def parse_reconciliation(sources):
    """Explicit mapping, not matching rows by position or model inference."""
    if len(sources) != 2:
        raise ValueError("reconciliation requires two snapshots")
    left, lc = parse_snapshot(sources[0])
    right, rc = parse_snapshot(sources[1])
    comparisons = left.get("comparisons", [])
    if not isinstance(comparisons, list) or len(comparisons) > 500:
        raise ValueError("comparison limit")
    ids = set()
    for item in comparisons:
        if not isinstance(item, dict) or set(item) != {"id", "left", "right"}:
            raise ValueError("invalid comparison")
        cid = item.get("id")
        if not isinstance(cid, str) or not 0 < len(cid) <= 100 or cid in ids:
            raise ValueError("invalid or duplicate comparison id")
        ids.add(cid)
        if any(not ADDRESS.fullmatch(str(item.get(k, ""))) for k in ("left", "right")):
            raise ValueError("invalid comparison address")
        if left["workbook"] == right["workbook"] and left["sheet"] == right["sheet"] and item["left"] == item["right"]:
            raise ValueError("self comparison is not independent evidence")
    return left, lc, right, rc, comparisons


def observed_number(cell):
    """Missing error observation is not evidence that the cell has no error."""
    from .packs import number
    if "error" not in cell or cell["error"] is not None or type(cell.get("value")) not in (int, float):
        raise ValueError("missing numeric observation")
    return number(str(cell["value"]))


def reconciliation_control(code, sources, tolerance):
    from .packs import number, result
    left, lc, right, rc, comparisons = parse_reconciliation(sources)
    if code == "comparison_scope":
        return result(code, dict(mapped_pairs=len(comparisons),
                                 scopes=[{k: s[k] for k in ("sheet", "scope", "captured_at")} for s in (left, right)]),
                      "only explicitly mapped observations; entity, period, currency and mapping suitability require review", "REVIEW")
    if code != "mapped_amounts":
        raise ValueError("unknown reconciliation control")
    findings = []
    for item in comparisons:
        try:
            values = []
            for cells, key in ((lc, "left"), (rc, "right")):
                cell = cells[item[key]]
                values.append(observed_number(cell))
            with localcontext() as ctx:
                ctx.prec = 160
                delta = values[0] - values[1]
            findings.append(dict(**item, observed=str(values[0]), expected=str(values[1]), delta=str(delta),
                                 status="FAIL" if abs(delta) > tolerance else "PASS"))
        except (KeyError, ValueError):
            findings.append(dict(**item, status="INCONCLUSIVE", reason="missing, nonnumeric or untyped observation"))
    statuses = [f["status"] for f in findings]
    status = "FAIL" if "FAIL" in statuses else "INCONCLUSIVE" if not statuses or "INCONCLUSIVE" in statuses else "PASS"
    return result(code, dict(checks=findings), "mapped amounts agree within approved tolerance; differences are not automatically rounding", status,
                  reason_code="MISSING_EVIDENCE" if status == "INCONCLUSIVE" else None)


def snapshot_control(code, raw, tolerance):
    from .packs import number, result
    data, cells = parse_snapshot(raw)
    if code == "snapshot_scope":
        return result(code, dict(sheet=data["sheet"], scope=data["scope"], observed_cells=len(cells),
                                 captured_at=data["captured_at"], provenance="client supplied, not independently attested"),
                      "only submitted cells are covered; no claim about full workbook", "REVIEW")
    if code == "cell_errors":
        errors = [a for a, c in cells.items() if c.get("error")]
        missing = sum("error" not in c for c in cells.values())
        return result(code, dict(addresses=errors[:100], count=len(errors), missing_error_type=missing),
                      "no typed Excel errors in submitted cells",
                      "FAIL" if errors else "INCONCLUSIVE" if missing else "PASS",
                      reason_code="MISSING_EVIDENCE" if not errors and missing else None)
    if code == "formula_references":
        # Ignore string literals: ="#REF!" is not a broken reference.
        broken = [a for a, c in cells.items() if re.search(r"#REF!", re.sub(r'"(?:[^"]|"")*"', '', c.get("formula") or ""), re.I)]
        missing = sum("formula" not in c for c in cells.values())
        return result(code, dict(addresses=broken[:100], count=len(broken), missing_formula_view=missing),
                      "no explicit #REF! outside string literals; no formula execution",
                      "FAIL" if broken else "INCONCLUSIVE" if missing else "PASS",
                      reason_code="MISSING_EVIDENCE" if not broken and missing else None)
    if code == "formula_dependencies":
        observed = dependency_findings(cells)
        has_cycle = observed["direct_count"] or observed["circular_count"]
        incomplete = (observed["missing_formula_view"] or observed["unsupported_formula_count"]
                      or observed["unresolved_reference_count"])
        finding = result(code, observed,
                         "no direct self-reference or circular dependency among supported observed local formulas; unsupported expressions excluded; no formula execution",
                         "FAIL" if has_cycle else "INCONCLUSIVE" if incomplete else "PASS",
                         reason_code="MISSING_EVIDENCE" if not has_cycle and incomplete else None)
        return finding
    if code == "declared_equations":
        findings = []
        for check in data.get("checks", []):
            addresses = [check["target"]] + [t["address"] for t in check["terms"]]
            try:
                values = {}
                for address in addresses:
                    cell = cells[address]
                    values[address] = observed_number(cell)
                with localcontext() as ctx:
                    ctx.prec = 160
                    expected = sum((values[t["address"]] * number(t.get("coefficient", "1")) for t in check["terms"]), Decimal(0))
                    delta = abs(values[check["target"]] - expected)
                findings.append(dict(id=check["id"], target=check["target"], sources=addresses[1:],
                                     expected=str(expected), observed=str(values[check["target"]]), delta=str(delta),
                                     status="FAIL" if delta > tolerance else "PASS"))
            except (KeyError, ValueError):
                findings.append(dict(id=check["id"], status="INCONCLUSIVE", reason="missing, nonnumeric or erroneous source"))
        statuses = [f["status"] for f in findings]
        status = "FAIL" if "FAIL" in statuses else "INCONCLUSIVE" if not statuses or "INCONCLUSIVE" in statuses else "PASS"
        return result(code, dict(checks=findings), "target equals declared weighted sum within approved tolerance; rule suitability requires review", status,
                      reason_code="MISSING_EVIDENCE" if status == "INCONCLUSIVE" else None)
    raise ValueError("unknown snapshot control")
