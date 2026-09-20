// Subprocess/JSON example, not an MCP client. No npm dependencies.
import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
const executable = process.env.HOLCO_CONTROLS_DEMO || 'holco-controls-demo';
const output = process.argv[2] || 'demo-node';
const result = spawnSync(executable, ['--output', output, '--format', 'json'], {
  encoding: 'utf8', timeout: 30_000, maxBuffer: 4 * 1024 * 1024,
});
if (result.error) throw result.error;
if (result.status !== 0) throw new Error(`Demo failed (${result.status}): ${result.stderr}`);
const report = JSON.parse(result.stdout);
assert.equal(report.schema, 'holco.demo/v1');
assert.equal(report.acceptance, 'PASS');
assert.deepEqual(report.stages.map(stage => stage.actual), ['INCONCLUSIVE', 'FAIL', 'PASS', 'REVIEW']);
assert.equal(report.human_approval_recorded, false);
assert.equal(report.failed_report_preserved, true);
console.log('PASS JavaScript → Python engine → JSON: failure retained, correction linked, human review pending.');
