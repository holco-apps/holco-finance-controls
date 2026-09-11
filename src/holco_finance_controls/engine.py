"""Persistent single-operator control engine; client input never selects a path."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from functools import wraps
from threading import RLock
from datetime import datetime, timezone
from pathlib import Path

from .packs import CATALOG, MAX_BYTES, VERSION, execute, number, result


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def aggregate(statuses):
    if "FAIL" in statuses:
        return "FAIL"
    if not statuses or any(s in {"INCONCLUSIVE", "NOT_RUN"} for s in statuses):
        return "INCONCLUSIVE"
    return "REVIEW" if "REVIEW" in statuses else "PASS"


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return call


class Engine:
    """Database path is supplied by the trusted process launcher, never an MCP tool."""

    def __init__(self, database: Path):
        self.lock = RLock()
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.database.exists():
            self.database.touch(mode=0o600)
        self.db = sqlite3.connect(str(database), timeout=30, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, sha TEXT, content BLOB);
          CREATE TABLE IF NOT EXISTS receipts(source TEXT PRIMARY KEY, raw_source TEXT);
          CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY, sha TEXT, body TEXT);
          CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, plan TEXT, body TEXT);
        """)

    @serialized
    def close(self):
        self.db.close()

    @serialized
    def register(self, content: bytes):
        if not content or len(content) > MAX_BYTES:
            raise ValueError("input must contain 1 to 10485760 bytes")
        sid = "src_" + uuid.uuid4().hex
        sha = digest(content)
        self.db.execute("INSERT INTO sources VALUES (?,?,?)", (sid, sha, content))
        return dict(source_id=sid, sha256=sha, bytes=len(content))

    def _source(self, sid):
        row = self.db.execute("SELECT sha,content FROM sources WHERE id=?", (sid,)).fetchone()
        if row is None:
            raise ValueError("unknown source")
        if digest(row[1]) != row[0]:
            raise ValueError("source integrity check failed")
        return row

    @serialized
    def capture_erp_response(self, raw_response: bytes, records: list[dict], coverage: dict, tool_calls: list[dict]):
        """Trusted connector adapter entry point, deliberately absent from MCP.

        Call immediately after receiving an ERP response. The adapter supplies
        normalized records, request trace and pagination facts, outside the LLM.
        Raw response bytes are retained separately for downstream inspection.
        """
        if not raw_response or len(raw_response) > MAX_BYTES:
            raise ValueError("invalid raw response size")
        raw_id = "src_" + uuid.uuid4().hex
        snapshot = canonical(dict(records=records, coverage=coverage, tool_calls=tool_calls,
                                  provenance=dict(raw_source_id=raw_id, raw_sha256=digest(raw_response)))).encode()
        if len(snapshot) > MAX_BYTES:
            raise ValueError("normalized snapshot too large")
        sid = "src_" + uuid.uuid4().hex
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.executemany("INSERT INTO sources VALUES (?,?,?)", [
                (raw_id, digest(raw_response), raw_response), (sid, digest(snapshot), snapshot)])
            self.db.execute("INSERT INTO receipts VALUES (?,?)", (sid, raw_id))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return dict(source_id=sid, sha256=digest(snapshot), bytes=len(snapshot))

    @serialized
    def plan(self, source_ids: list[str], pack: str, tolerance="0.01", supersedes=None, policy=None):
        if pack not in CATALOG:
            raise ValueError("unknown control pack")
        if len(source_ids) != (2 if pack in {"workbook_comparison", "erp_agent_response"} else 1):
            raise ValueError("wrong number of sources for pack")
        tol = number(tolerance)
        if tol < 0:
            raise ValueError("tolerance must be nonnegative")
        policy = policy or {}
        if set(policy) - {"allowed_tools", "required_tools", "required_period", "required_currency", "required_scope"}:
            raise ValueError("unsupported policy fields")
        for key in ("required_period", "required_currency", "required_scope"):
            if key in policy and (not isinstance(policy[key], str) or not 1 <= len(policy[key]) <= 100):
                raise ValueError("request criteria must be bounded nonempty strings")
        for key in ("allowed_tools", "required_tools"):
            names = policy.get(key, [])
            if not isinstance(names, list) or len(names) > 100 or any(not isinstance(n, str) or len(n) > 100 for n in names):
                raise ValueError("tool policy must contain bounded lists of tool names")
        if supersedes:
            self.get(supersedes)
        body = dict(protocol_version=VERSION, pack=pack, tolerance=str(tol), policy=policy,
                    sources=[dict(source_id=s, sha256=self._source(s)[0]) for s in source_ids],
                    controls=list(CATALOG[pack]), created_at=now(), supersedes=supersedes,
                    exclusions=["external source authenticity", "business plausibility", "legal compliance"],
                    required_review="trusted operator sign-off; not provided by MCP")
        sha = digest(canonical(body).encode())
        pid = "plan_" + uuid.uuid4().hex
        self.db.execute("INSERT INTO plans VALUES (?,?,?)", (pid, sha, canonical(body)))
        return dict(plan_id=pid, plan_sha256=sha, **body)

    def _plan(self, pid):
        row = self.db.execute("SELECT sha,body FROM plans WHERE id=?", (pid,)).fetchone()
        if row is None:
            raise ValueError("unknown plan")
        if digest(row[1].encode()) != row[0]:
            raise ValueError("plan integrity check failed")
        body = json.loads(row[1])
        if body["protocol_version"] != VERSION:
            raise ValueError("runner version changed; create a new plan")
        for source in body["sources"]:
            if self._source(source["source_id"])[0] != source["sha256"]:
                raise ValueError("source differs from plan")
            receipt = self.db.execute("SELECT raw_source FROM receipts WHERE source=?", (source["source_id"],)).fetchone()
            if receipt:
                snapshot = json.loads(self._source(source["source_id"])[1])
                if self._source(receipt[0])[0] != snapshot["provenance"]["raw_sha256"]:
                    raise ValueError("raw ERP receipt differs from captured response")
        return row[0], body

    @serialized
    def start(self, plan_id, approved_plan_sha256):
        sha, plan = self._plan(plan_id)
        if sha != approved_plan_sha256:
            raise ValueError("approved plan hash mismatch")
        rid = "run_" + uuid.uuid4().hex
        body = dict(run_id=rid, plan_id=plan_id, plan_sha256=sha, results=[],
                    created_at=now(), state="PLANNED", stop_reason="not_started",
                    review=None, challenge=None, supersedes=plan["supersedes"])
        self.db.execute("INSERT INTO runs VALUES (?,?,?)", (rid, plan_id, canonical(body)))
        return self.get(rid)

    def _run(self, rid):
        row = self.db.execute("SELECT body FROM runs WHERE id=?", (rid,)).fetchone()
        if row is None:
            raise ValueError("unknown run")
        return json.loads(row[0])

    @serialized
    def advance(self, run_id, max_controls=2):
        if type(max_controls) is not int or not 1 <= max_controls <= 8:
            raise ValueError("max_controls must be between 1 and 8")
        # Each completed control commits separately. A crash leaves prior results intact.
        for _ in range(max_controls):
            self.db.execute("BEGIN IMMEDIATE")
            try:
                run = self._run(run_id)
                sha, plan = self._plan(run["plan_id"])
                if sha != run["plan_sha256"]:
                    raise ValueError("run plan changed")
                index = len(run["results"])
                if run["state"] == "CLOSED" or index == len(plan["controls"]):
                    self.db.execute("COMMIT")
                    break
                data = [self._source(s["source_id"])[1] for s in plan["sources"]]
                code = plan["controls"][index]
                if plan["pack"] == "erp_agent_response" and code == "source_provenance":
                    receipt = self.db.execute("SELECT raw_source FROM receipts WHERE source=?", (plan["sources"][0]["source_id"],)).fetchone()
                    sha_raw = self._source(receipt[0])[0] if receipt else None
                    item = result(code, dict(connector_receipt_present=bool(receipt), raw_response_sha256=sha_raw),
                                  "source captured by trusted adapter outside model",
                                  "PASS" if receipt else "INCONCLUSIVE")
                else:
                    item = execute(plan["pack"], code, data, plan["tolerance"], plan["policy"])
                item["evidence"] = plan["sources"]
                item["completed_at"] = now()
                run["results"].append(item)
                complete = len(run["results"]) == len(plan["controls"])
                run.update(state="REVIEW" if complete else "INTERRUPTED",
                           stop_reason="controls_complete" if complete else "control_budget_reached")
                self.db.execute("UPDATE runs SET body=? WHERE id=?", (canonical(run), run_id))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return self.get(run_id)

    @serialized
    def get(self, run_id):
        run = self._run(run_id)
        _, plan = self._plan(run["plan_id"])
        statuses = [r["status"] for r in run["results"]]
        not_run = len(plan["controls"]) - len(statuses)
        counts = {s: statuses.count(s) for s in ("PASS", "FAIL", "REVIEW", "INCONCLUSIVE", "NOT_RUN")}
        counts["NOT_RUN"] += not_run
        technical = aggregate(statuses + ["NOT_RUN"] * not_run)
        return dict(**run, report_schema="holco.control-run/v2", plan=plan,
                    planned=len(plan["controls"]), executed=len(statuses), complete=not_run == 0,
                    counts=counts, deterministic_outcome=technical,
                    outcome=technical if technical != "PASS" or run["state"] == "CLOSED" else "REVIEW",
                    checkpoint=dict(next_control_index=len(statuses), plan_sha256=run["plan_sha256"]),
                    report_sha256=digest(canonical(run).encode()))

    @serialized
    def sign_off(self, run_id, reviewer: str, challenge_run_id: str, rationale: str):
        """Trusted local operator API only. Never expose this method as an MCP tool.

        A separate completed run evidences repeatability, not independent expertise.
        The operator must assess the challenge and declare that assessment explicitly.
        """
        if not reviewer.strip() or not rationale.strip() or run_id == challenge_run_id:
            raise ValueError("reviewer, rationale and separate challenge required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            report, challenge = self.get(run_id), self.get(challenge_run_id)
            if report["state"] == "CLOSED":
                raise ValueError("closed reviews are immutable")
            if any(r["deterministic_outcome"] != "PASS" or not r["complete"] for r in (report, challenge)):
                raise ValueError("failed or incomplete controls cannot be signed off")
            if report["plan_sha256"] != challenge["plan_sha256"]:
                raise ValueError("challenge must use the same plan and source versions")
            run = self._run(run_id)
            run.update(state="CLOSED", review=dict(reviewer=reviewer, rationale=rationale, at=now()),
                       challenge=dict(run_id=challenge_run_id, report_sha256=challenge["report_sha256"],
                                      kind="repeatability; independent expertise attested by operator"))
            self.db.execute("UPDATE runs SET body=? WHERE id=?", (canonical(run), run_id))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return self.get(run_id)
