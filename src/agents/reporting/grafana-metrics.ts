import fs from 'fs-extra';
import type { NormalizedTestResult } from '../shared/types';
import { resilientCall } from '../shared/resilience';

function escapeLabelValue(value: string) {
  return value.replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/"/g, '\\"');
}

function encodePushgatewayPathValue(value: string) {
  return encodeURIComponent(value.replace(/\s+/g, '-').toLowerCase());
}

async function pushToPushgateway(metrics: string) {
  const pushgatewayUrl = process.env.PUSHGATEWAY_URL;

  if (!pushgatewayUrl) {
    console.warn('PUSHGATEWAY_URL is not configured');
    return;
  }

  const job = encodePushgatewayPathValue(process.env.PUSHGATEWAY_JOB ?? 'playwright-reporting');
  const environment = encodePushgatewayPathValue(process.env.ENV_NAME ?? 'demo');
  const url = `${pushgatewayUrl.replace(/\/$/, '')}/metrics/job/${job}/environment/${environment}`;

  const response = await resilientCall('pushgateway', () => fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'text/plain; version=0.0.4'
    },
    body: metrics
  }));

  if (!response.ok) {
    throw new Error(`Pushgateway metrics push failed with status ${response.status}`);
  }
}

export async function pushGrafanaMetrics(results: NormalizedTestResult[]) {
  const total = results.length;
  const passed = results.filter((r) => r.status === 'passed').length;
  const failed = results.filter((r) => r.status === 'failed' || r.status === 'timedOut').length;
  const skipped = results.filter((r) => r.status === 'skipped').length;
  const flaky = results.filter((r) => r.status === 'flaky').length;
  const unknown = results.filter((r) => r.status === 'unknown').length;

  const passRate = total === 0 ? 0 : passed / total;
  const runId = results[0]?.runId ?? `empty-${Date.now()}`;
  const latestRunAt = results
    .map((result) => result.runAt)
    .filter(Boolean)
    .sort()
    .at(-1);
  const runStartedAt = latestRunAt ? Math.floor(new Date(latestRunAt).getTime() / 1000) : Math.floor(Date.now() / 1000);
  const runLabel = `run_id="${escapeLabelValue(runId)}"`;

  const metrics = `
# HELP playwright_tests_total Total Playwright tests
# TYPE playwright_tests_total gauge
playwright_tests_total ${total}

# HELP playwright_tests_passed Passed Playwright tests
# TYPE playwright_tests_passed gauge
playwright_tests_passed ${passed}

# HELP playwright_tests_failed Failed Playwright tests
# TYPE playwright_tests_failed gauge
playwright_tests_failed ${failed}

# HELP playwright_tests_skipped Skipped Playwright tests
# TYPE playwright_tests_skipped gauge
playwright_tests_skipped ${skipped}

# HELP playwright_tests_flaky Flaky Playwright tests
# TYPE playwright_tests_flaky gauge
playwright_tests_flaky ${flaky}

# HELP playwright_tests_unknown Unknown Playwright tests
# TYPE playwright_tests_unknown gauge
playwright_tests_unknown ${unknown}

# HELP playwright_pass_rate Playwright pass rate
# TYPE playwright_pass_rate gauge
playwright_pass_rate ${passRate}

# HELP playwright_run_info Playwright run marker. Value is always 1.
# TYPE playwright_run_info gauge
playwright_run_info{${runLabel}} 1

# HELP playwright_run_started_at_seconds Playwright run timestamp in Unix seconds
# TYPE playwright_run_started_at_seconds gauge
playwright_run_started_at_seconds{${runLabel}} ${runStartedAt}

# HELP playwright_run_tests_total Total tests for one Playwright run
# TYPE playwright_run_tests_total gauge
playwright_run_tests_total{${runLabel}} ${total}

# HELP playwright_run_tests_passed Passed tests for one Playwright run
# TYPE playwright_run_tests_passed gauge
playwright_run_tests_passed{${runLabel}} ${passed}

# HELP playwright_run_tests_failed Failed tests for one Playwright run
# TYPE playwright_run_tests_failed gauge
playwright_run_tests_failed{${runLabel}} ${failed}

# HELP playwright_run_tests_skipped Skipped tests for one Playwright run
# TYPE playwright_run_tests_skipped gauge
playwright_run_tests_skipped{${runLabel}} ${skipped}

# HELP playwright_run_tests_flaky Flaky tests for one Playwright run
# TYPE playwright_run_tests_flaky gauge
playwright_run_tests_flaky{${runLabel}} ${flaky}

# HELP playwright_run_tests_unknown Unknown tests for one Playwright run
# TYPE playwright_run_tests_unknown gauge
playwright_run_tests_unknown{${runLabel}} ${unknown}
`;

  await fs.ensureDir('reports/metrics');
  const normalizedMetrics = `${metrics.trim()}\n`;

  await fs.writeFile('reports/metrics/playwright.prom', normalizedMetrics);

  try {
    await pushToPushgateway(normalizedMetrics);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.warn(`Pushgateway metrics push skipped: ${message}`);
  }
}
