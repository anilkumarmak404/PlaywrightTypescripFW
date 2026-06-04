import fs from 'fs-extra';
import yaml from 'yaml';
import simpleGit from 'simple-git';
import { minimatch } from 'minimatch';
import type { TestRegistryItem, MaintenanceFinding } from '../shared/types';

type FeatureMap = {
  features: Record<
    string,
    {
      owner: string;
      jiraProject: string;
      code: string[];
      tests: string[];
    }
  >;
};

export async function detectCoverageDrift(
  registry: TestRegistryItem[]
): Promise<MaintenanceFinding[]> {
  const raw = await fs.readFile('config/feature-map.yml', 'utf-8');
  const featureMap = yaml.parse(raw) as FeatureMap;

  const git = simpleGit({ baseDir: process.cwd() });
  const diff = await getChangedFiles(git);

  const changedFiles = diff
    .split('\n')
    .map((x) => x.trim())
    .filter(Boolean);

  const findings: MaintenanceFinding[] = [];

  for (const [featureName, featureConfig] of Object.entries(featureMap.features)) {
    const changedCode = changedFiles.filter((file) =>
      featureConfig.code.some((pattern) => minimatch(file, pattern))
    );

    if (changedCode.length === 0) {
      continue;
    }

    const relatedTestChanged = changedFiles.some((file) =>
      featureConfig.tests.some((pattern) => minimatch(file, pattern))
    );

    const existingTests = registry.filter((test) => test.feature === featureName);

    if (!relatedTestChanged || existingTests.length === 0) {
      findings.push({
        type: 'coverage_drift',
        severity: 'high',
        message: `Code changed for feature ${featureName}, but no matching test update was found`,
        payload: {
          feature: featureName,
          owner: featureConfig.owner,
          changedCode,
          existingTests: existingTests.map((t) => t.id)
        }
      });
    }
  }

  return findings;
}

async function getChangedFiles(git: ReturnType<typeof simpleGit>): Promise<string> {
  try {
    return await git.diff(['--name-only', 'origin/main...HEAD']);
  } catch {
    try {
      return await git.diff(['--name-only', 'HEAD']);
    } catch {
      return '';
    }
  }
}
