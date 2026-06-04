import fs from 'fs-extra';
import type { NormalizedTestResult } from '../shared/types';

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

  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'text/plain; version=0.0.4'
    },
    body: metrics
  });

  if (!response.ok) {
    throw new Error(`Pushgateway metrics push failed with status ${response.status}`);
  }
}

export async function pushGrafanaMetrics(results: NormalizedTestResult[]) {
  const total = results.length;
  const passed = results.filter((r) => r.status === 'passed').length;
  const failed = results.filter((r) => r.status === 'failed' || r.status === 'timedOut').length;
  const skipped = results.filter((r) => r.status === 'skipped').length;

  const passRate = total === 0 ? 0 : passed / total;

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

# HELP playwright_pass_rate Playwright pass rate
# TYPE playwright_pass_rate gauge
playwright_pass_rate ${passRate}
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
