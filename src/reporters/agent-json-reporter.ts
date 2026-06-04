import type {
  Reporter,
  TestCase,
  TestResult,
  FullResult
} from '@playwright/test/reporter';
import fs from 'fs-extra';
import path from 'path';

function extractMeta(title: string) {
  const id = title.match(/@id:([A-Z0-9-_]+)/)?.[1] ?? 'UNKNOWN';
  const feature = title.match(/@feature:([a-zA-Z0-9-_]+)/)?.[1] ?? 'unknown';
  const owner = title.match(/@owner:([a-zA-Z0-9-_]+)/)?.[1] ?? 'unknown';
  const jira = title.match(/@jira:([A-Z0-9-]+)/)?.[1] ?? 'UNKNOWN';

  return { id, feature, owner, jira };
}

async function writeJsonSafely(filePath: string, data: unknown) {
  const fullPath = path.resolve(filePath);
  const dir = path.dirname(fullPath);
  const tempPath = path.join(dir, `${path.basename(filePath)}.${process.pid}.tmp`);

  await fs.ensureDir(dir);
  await fs.writeJson(tempPath, data, { spaces: 2 });

  try {
    await fs.move(tempPath, fullPath, { overwrite: true });
  } catch (error) {
    const fallbackPath = path.join(
      dir,
      `${path.basename(filePath, path.extname(filePath))}-${Date.now()}${path.extname(filePath)}`
    );

    await fs.move(tempPath, fallbackPath, { overwrite: true });
    console.warn(`Agent reporter could not overwrite ${fullPath}. Wrote ${fallbackPath} instead.`, error);
  }
}

class AgentJsonReporter implements Reporter {
  private results: any[] = [];
  private runId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;

  async onTestEnd(test: TestCase, result: TestResult) {
    const title = test.title;
    const meta = extractMeta(title);

    const attachments = result.attachments || [];

    const tracePath = attachments.find((a) => a.name === 'trace')?.path;
    const screenshotPath = attachments.find((a) => a.contentType?.includes('image'))?.path;
    const videoPath = attachments.find((a) => a.contentType?.includes('video'))?.path;

    this.results.push({
      runId: this.runId,
      testId: meta.id,
      title,
      file: test.location.file,
      feature: meta.feature,
      owner: meta.owner,
      jira: meta.jira,
      status: result.status,
      durationMs: result.duration,
      retry: result.retry,
      errorMessage: result.error?.message,
      stack: result.error?.stack,
      tracePath,
      screenshotPath,
      videoPath,
      commitSha: process.env.GITHUB_SHA,
      branch: process.env.GITHUB_REF_NAME,
      runAt: new Date().toISOString()
    });
  }

  async onEnd(result: FullResult) {
    await fs.ensureDir('agent-state');

    const historyPath = path.resolve('agent-state/test-history.json');
    const existing = (await fs.pathExists(historyPath))
      ? await fs.readJson(historyPath)
      : [];

    await writeJsonSafely(historyPath, [...existing, ...this.results]);

    await writeJsonSafely(
      'reports/ai-summary/latest-agent-results.json',
      {
        runId: this.runId,
        status: result.status,
        results: this.results
      }
    );
  }
}

export default AgentJsonReporter;
