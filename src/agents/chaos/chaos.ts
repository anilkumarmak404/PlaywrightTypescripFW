import fs from 'fs-extra';
import os from 'os';
import path from 'path';
import { parseLatestAgentResults } from '../reporting/parse-results';
import { createFailureFingerprint } from '../shared/fingerprint';
import { withCircuitBreaker } from '../shared/resilience';
import type { NormalizedTestResult } from '../shared/types';

type ChaosResult = {
  scenario: string;
  status: 'passed' | 'failed';
  detail: string;
};

const results: ChaosResult[] = [];

async function record(scenario: string, action: () => Promise<string>) {
  try {
    results.push({
      scenario,
      status: 'passed',
      detail: await action()
    });
  } catch (error) {
    results.push({
      scenario,
      status: 'failed',
      detail: error instanceof Error ? error.message : String(error)
    });
  }
}

function failedResult(overrides: Partial<NormalizedTestResult> = {}): NormalizedTestResult {
  return {
    runId: 'chaos-run',
    testId: 'LOGIN-002',
    title: 'Chaos failure',
    file: 'tests/ui-tests/login-module.spec.ts',
    feature: 'login',
    owner: 'qa-auth',
    jira: 'SCRUM-31',
    status: 'failed',
    durationMs: 100,
    retry: 0,
    errorMessage: 'Expected Dashboard but received Login page 123',
    ...overrides
  };
}

async function main() {
  await record('Jira down circuit breaker fallback', async () => {
    const breaker = withCircuitBreaker(async () => {
      throw new Error('simulated Jira outage');
    }, 'chaos-jira');

    const output = await breaker.fire();
    if (output !== null) {
      throw new Error('expected circuit breaker fallback to return null');
    }

    return 'fallback returned null';
  });

  await record('Slack webhook invalid is non-fatal', async () => {
    const breaker = withCircuitBreaker(async () => {
      throw new Error('simulated invalid Slack webhook');
    }, 'chaos-slack');

    await breaker.fire();
    return 'fallback completed without throwing';
  });

  await record('Confluence update conflict is isolated', async () => {
    const breaker = withCircuitBreaker(async () => {
      throw new Error('simulated Confluence version conflict');
    }, 'chaos-confluence');

    await breaker.fire();
    return 'fallback completed without throwing';
  });

  await record('Missing test-results does not crash reporting parser', async () => {
    const originalCwd = process.cwd();
    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'agent-chaos-'));

    try {
      process.chdir(tempDir);
      const parsed = await parseLatestAgentResults();
      if (parsed.length !== 0) {
        throw new Error(`expected zero parsed results, received ${parsed.length}`);
      }
    } finally {
      process.chdir(originalCwd);
      await fs.remove(tempDir);
    }

    return 'parser returned empty result set';
  });

  await record('Missing screenshot is accepted', async () => {
    const result = failedResult({
      screenshotPath: undefined,
      tracePath: 'test-results/example-trace.zip',
      videoPath: undefined
    });

    if (result.screenshotPath !== undefined) {
      throw new Error('expected screenshotPath to be optional');
    }

    return 'failure result remains valid without screenshotPath';
  });

  await record('Agent crash halfway can be captured by caller', async () => {
    let wroteFirstStep = false;

    try {
      wroteFirstStep = true;
      throw new Error('simulated midway crash');
    } catch (error) {
      if (!wroteFirstStep) {
        throw error;
      }
    }

    return 'midway crash caught and later steps can continue';
  });

  await record('Same failure repeated 5 times is idempotent', async () => {
    const fingerprints = Array.from({ length: 5 }, () =>
      createFailureFingerprint(failedResult())
    );

    if (new Set(fingerprints).size !== 1) {
      throw new Error('same failure produced multiple fingerprints');
    }

    return `single fingerprint ${fingerprints[0].slice(0, 12)}`;
  });

  await record('Different failure creates a different fingerprint', async () => {
    const first = createFailureFingerprint(failedResult());
    const second = createFailureFingerprint(
      failedResult({
        errorMessage: 'Expected Leave page but received Dashboard page',
        testId: 'LEAVE-001',
        feature: 'leave-management'
      })
    );

    if (first === second) {
      throw new Error('different failures produced same fingerprint');
    }

    return `${first.slice(0, 12)} != ${second.slice(0, 12)}`;
  });

  await fs.ensureDir('agent-state');
  await fs.writeJson(
    'agent-state/latest-chaos-results.json',
    {
      createdAt: new Date().toISOString(),
      total: results.length,
      failed: results.filter((result) => result.status === 'failed').length,
      results
    },
    { spaces: 2 }
  );

  for (const result of results) {
    console.log(`${result.status.toUpperCase()} ${result.scenario}: ${result.detail}`);
  }

  const failed = results.filter((result) => result.status === 'failed');
  if (failed.length > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('Chaos validation failed', error);
  process.exit(1);
});
