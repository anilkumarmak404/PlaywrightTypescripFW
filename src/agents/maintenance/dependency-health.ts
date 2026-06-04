import { execSync } from 'child_process';
import type { MaintenanceFinding } from '../shared/types';

type NpmOutdatedInfo = {
  current?: string;
  wanted?: string;
  latest?: string;
};

export async function checkDependencyHealth(): Promise<MaintenanceFinding[]> {
  const findings: MaintenanceFinding[] = [];
  const output = getNpmOutdatedOutput();

  if (!output) {
    return findings;
  }

  const outdated = JSON.parse(output || '{}') as Record<string, NpmOutdatedInfo>;

  for (const [pkg, info] of Object.entries(outdated)) {
    if (!info.current || !info.latest) {
      continue;
    }

    const isPlaywright = pkg.includes('playwright');

    findings.push({
      type: 'dependency_update',
      severity: isPlaywright ? 'high' : 'low',
      message: `${pkg} is outdated. Current: ${info.current}, latest: ${info.latest}`,
      payload: {
        package: pkg,
        current: info.current,
        wanted: info.wanted,
        latest: info.latest
      }
    });
  }

  return findings;
}

function getNpmOutdatedOutput(): string {
  try {
    return execSync('npm outdated --json', {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'ignore']
    });
  } catch (error) {
    const npmError = error as { stdout?: string | Buffer };
    return npmError.stdout?.toString() ?? '';
  }
}
