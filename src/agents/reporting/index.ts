import dotenv from 'dotenv';
import { parseLatestAgentResults } from './parse-results';
import { summarizeFailures } from './failure-summary';
import { upsertJiraBugs } from './jira-bugs';
import { updateConfluenceReport } from './confluence-report';
import { sendDailySlackDigest } from './slack-digest';
import { pushGrafanaMetrics } from './grafana-metrics';
import { writeJson } from '../shared/state-store';
import { errorMessage } from '../shared/resilience';
import { logger } from '../shared/logger';

dotenv.config({
  path: process.env.ENV_NAME ? `./env-files/.env.${process.env.ENV_NAME}` : './env-files/.env.demo',
  override: !process.env.CI
});

async function main() {
  logger.info('Reporting Agent started');

  const results = await parseLatestAgentResults();

  const failures = results.filter(
    (r) => r.status === 'failed' || r.status === 'timedOut'
  );

  const summaries = await summarizeFailures(failures);
  const jira = await upsertJiraBugs(failures, summaries);

  await writeJson('latest-reporting-summary.json', {
    createdAt: new Date().toISOString(),
    total: results.length,
    failures: failures.length,
    summaries,
    jira
  });

  await runOptional('Push Grafana metrics', () => pushGrafanaMetrics(results));
  await runOptional('Update Confluence report', () =>
    updateConfluenceReport(results, summaries, jira)
  );
  await runOptional('Send Slack digest', () => sendDailySlackDigest(results, summaries));

  logger.info('Reporting Agent completed');
}

main().catch((error) => {
  logger.error(`Reporting Agent failed: ${errorMessage(error)}`);
  process.exit(1);
});

async function runOptional(name: string, action: () => Promise<void>) {
  try {
    await action();
  } catch (error) {
    logger.warn(`${name} skipped: ${errorMessage(error)}`);
  }
}
