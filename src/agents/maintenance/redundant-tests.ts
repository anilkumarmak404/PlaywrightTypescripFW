import type { TestRegistryItem, MaintenanceFinding } from '../shared/types';

function normalizeTitle(title: string) {
  return title
    .replace(/@[a-zA-Z0-9-_:]+/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

export async function findRedundantTests(
  registry: TestRegistryItem[]
): Promise<MaintenanceFinding[]> {
  const findings: MaintenanceFinding[] = [];

  const byFeature = new Map<string, TestRegistryItem[]>();

  for (const test of registry) {
    const existing = byFeature.get(test.feature) ?? [];
    existing.push(test);
    byFeature.set(test.feature, existing);
  }

  for (const [feature, tests] of byFeature.entries()) {
    const seen = new Map<string, TestRegistryItem[]>();

    for (const test of tests) {
      const normalized = normalizeTitle(test.title);
      const group = seen.get(normalized) ?? [];
      group.push(test);
      seen.set(normalized, group);
    }

    for (const group of seen.values()) {
      if (group.length > 1) {
        findings.push({
          type: 'redundant_test',
          severity: 'low',
          message: `Possible duplicate tests found in feature ${feature}`,
          payload: {
            feature,
            tests: group.map((t) => ({
              id: t.id,
              file: t.file,
              title: t.title
            }))
          }
        });
      }
    }
  }

  return findings;
}
