"""Local stdio MCP tools. A separate database per operator is mandatory."""
import base64
import binascii
import os
from typing import Any
from pathlib import Path

from .engine import Engine
from .contracts import input_contracts
from .packs import CATALOG, MAX_BYTES, VERSION


def build_server(engine):
    from mcp.server import MCPServer
    server = MCPServer("HOLCO Finance Controls")

    @server.tool()
    def list_control_protocols() -> dict[str, Any]:
        """Describe supported control packs, input contracts and limits."""
        contracts = input_contracts()
        return dict(version=VERSION, packs=CATALOG, max_input_bytes=MAX_BYTES,
                    formats={name: "; ".join(source["format"] for source in contract["sources"])
                             for name, contract in contracts.items()},
                    input_contracts=contracts)


    @server.tool()
    def register_control_source(content: str, encoding: str = "utf8") -> dict[str, Any]:
        """Store authorised content locally and return an opaque source ID. No file paths or URLs."""
        if len(content) > MAX_BYTES * 4 // 3 + 4:
            raise ValueError("encoded input too large")
        if encoding == "utf8":
            raw = content.encode("utf-8")
        elif encoding == "base64":
            try:
                raw = base64.b64decode(content, validate=True)
            except (binascii.Error, ValueError):
                raise ValueError("invalid base64") from None
        else:
            raise ValueError("encoding must be utf8 or base64")
        return engine.register(raw)

    @server.tool()
    def prepare_control_plan(source_ids: list[str], pack: str, tolerance: str = "0.01", supersedes: str | None = None, policy: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return exact scope, exclusions and hash. Show the plan to the requester before starting."""
        return engine.plan(source_ids, pack, tolerance, supersedes, policy)

    @server.tool()
    def start_control_run(plan_id: str, approved_plan_sha256: str) -> dict[str, Any]:
        """Create a run for the approved plan hash. This does not constitute human sign-off."""
        return engine.start(plan_id, approved_plan_sha256)

    @server.tool()
    def advance_control_run(run_id: str, max_controls: int = 2) -> dict[str, Any]:
        """Execute or resume bounded controls; completed results persist across restarts."""
        return engine.advance(run_id, max_controls)

    @server.tool()
    def get_control_report(run_id: str) -> dict[str, Any]:
        """Retrieve complete results, evidence hashes, missing controls and pending human review."""
        return engine.get(run_id)

    return server


def main():
    path = os.environ.get("HOLCO_CONTROLS_DB")
    if not path or not Path(path).is_absolute():
        raise SystemExit("Set HOLCO_CONTROLS_DB to an absolute private database path")
    engine = Engine(Path(path))
    try:
        build_server(engine).run()
    finally:
        engine.close()


if __name__ == "__main__":
    main()
