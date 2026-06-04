import fs from 'fs-extra';
import type { NormalizedTestResult } from '../shared/types';
import { logger } from '../shared/logger';

export async function parseLatestAgentResults(): Promise<NormalizedTestResult[]> {
  const path = 'reports/ai-summary/latest-agent-results.json';

  if (!(await fs.pathExists(path))) {
    logger.warn(`Missing ${path}. Reporting agent will continue with zero test results.`);
    return [];
  }

  const data = await fs.readJson(path);

  return data.results.map((item: any) => {
    let status: NormalizedTestResult['status'] = 'unknown';

    if (item.status === 'passed') status = 'passed';
    else if (item.status === 'failed') status = 'failed';
    else if (item.status === 'timedOut') status = 'timedOut';
    else if (item.status === 'skipped') status = 'skipped';
    else if (item.status === 'flaky') status = 'flaky';

    return {
      runId: item.runId,
      testId: item.testId,
      title: item.title,
      file: item.file,
      feature: item.feature,
      owner: item.owner,
      jira: item.jira,
      status,
      durationMs: item.durationMs,
      retry: item.retry,
      errorMessage: item.errorMessage,
      stack: item.stack,
      tracePath: item.tracePath,
      screenshotPath: item.screenshotPath,
      videoPath: item.videoPath,
      runAt: item.runAt
    };
  });
}
