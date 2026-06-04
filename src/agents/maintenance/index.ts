import { scanTests } from './scan-tests';
import { findDeadTests } from './dead-tests';
import { detectCoverageDrift } from './coverage-drift';
import { checkDependencyHealth } from './dependency-health';
import { findRedundantTests } from './redundant-tests';
import { writeJson } from '../shared/state-store';
import { sendSlackMessage } from '../shared/slack';

async function main() {
  console.log('Maintenance Agent started');

  const registry = await scanTests('tests/**/*.spec.ts');

  const findings = [
    ...(await findDeadTests(registry, 30)),
    ...(await detectCoverageDrift(registry)),
    ...(await checkDependencyHealth()),
    ...(await findRedundantTests(registry))
  ];

  await writeJson('test-registry.json', registry);
  await writeJson('latest-maintenance-findings.json', {
    createdAt: new Date().toISOString(),
    total: findings.length,
    findings
  });

  if (findings.length > 0) {
    await sendSlackMessage({
      title: 'Maintenance Agent findings',
      text: `Maintenance Agent found ${findings.length} item(s). Check latest-maintenance-findings.json.`
    });
  }

  console.log(`Maintenance Agent completed. Findings: ${findings.length}`);
}

main().catch((error) => {
  console.error('Maintenance Agent failed', error);
  process.exit(1);
});
