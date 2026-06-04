import dotenv from 'dotenv';
import { parseLatestAgentResults } from './parse-results';
import { summarizeFailures } from './failure-summary';
import { upsertJiraBugs } from './jira-bugs';
import { updateConfluenceReport } from './confluence-report';
import { sendDailySlackDigest } from './slack-digest';
import { pushGrafanaMetrics } from './grafana-metrics';
import { writeJson } from '../shared/state-store';

dotenv.config({
  path: process.env.ENV_NAME ? `./env-files/.env.${process.env.ENV_NAME}` : './env-files/.env.demo',
  override: !process.env.CI
});

async function main() {
  console.log('Reporting Agent started');

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

  await pushGrafanaMetrics(results);
  await updateConfluenceReport(results, summaries, jira);
  await sendDailySlackDigest(results, summaries);

  console.log('Reporting Agent completed');
}

main().catch((error) => {
  console.error('Reporting Agent failed', error);
  process.exit(1);
});
