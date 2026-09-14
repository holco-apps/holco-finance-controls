import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("mcp"), "install the mcp extra for wire tests")
class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_lifecycle_and_hidden_signoff(self):
        from mcp import Client, StdioServerParameters
        with tempfile.TemporaryDirectory() as directory:
            params = StdioServerParameters(command=sys.executable,
                args=["-m", "holco_finance_controls.server"],
                env={**os.environ, "HOLCO_CONTROLS_DB": str(Path(directory) / "controls.db")})

            async def call(client, name, args):
                r = await client.call_tool(name, args)
                self.assertFalse(r.is_error, r)
                return r.structured_content or json.loads(r.content[0].text)

            async with Client(params) as client:
                listed = await client.list_tools()
                self.assertEqual(len(listed.tools), 6)
                self.assertNotIn("sign_off", [t.name for t in listed.tools])
                protocols = await call(client, "list_control_protocols", {})
                self.assertEqual(set(protocols["packs"]), set(protocols["input_contracts"]))
                self.assertEqual(protocols["input_contracts"]["financial_workbook"]["source_count"], 2)
                src = await call(client, "register_control_source", {"content": "id,expected,observed\na,1,2\n"})
                plan = await call(client, "prepare_control_plan", {"source_ids": [src["source_id"]], "pack": "reconciliation_csv"})
                run = await call(client, "start_control_run", {"plan_id": plan["plan_id"], "approved_plan_sha256": plan["plan_sha256"]})
                rid = run["run_id"]
                await call(client, "advance_control_run", {"run_id": rid, "max_controls": 1})
            # The stdio subprocess exited: the next client must resume the same run.
            async with Client(params) as client:
                final = await call(client, "advance_control_run", {"run_id": rid, "max_controls": 2})
                self.assertEqual(final["outcome"], "FAIL")
                self.assertEqual(final["executed"], 2)
                self.assertEqual(final["counts"]["NOT_RUN"], 0)
                reports = await asyncio.gather(*[call(client, "get_control_report", {"run_id": rid}) for _ in range(3)])
                self.assertTrue(all(r["report_sha256"] == final["report_sha256"] for r in reports))
