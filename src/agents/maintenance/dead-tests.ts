import type { TestRegistryItem, MaintenanceFinding } from '../shared/types';
import { readJson } from '../shared/state-store';

type HistoryItem = {
  testId: string;
  runAt: string;
};

export async function findDeadTests(
  registry: TestRegistryItem[],
  olderThanDays = 30
): Promise<MaintenanceFinding[]> {
  const history = await readJson<HistoryItem[]>('test-history.json', []);

  const cutoff = Date.now() - olderThanDays * 24 * 60 * 60 * 1000;

  return registry
    .filter((test) => {
      const runs = history.filter((h) => h.testId === test.id);

      if (runs.length === 0) {
        return true;
      }

      const latestRun = runs
        .map((r) => new Date(r.runAt).getTime())
        .filter((time) => !Number.isNaN(time))
        .sort((a, b) => b - a)[0];

      return latestRun === undefined || latestRun < cutoff;
    })
    .map((test) => ({
      type: 'dead_test',
      severity: 'medium',
      message: `Test ${test.id} has not run in ${olderThanDays}+ days`,
      payload: test
    }));
}
