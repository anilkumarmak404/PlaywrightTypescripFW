import dotenv from 'dotenv';
import { scanTests } from './scan-tests';
import { findDeadTests } from './dead-tests';
import { detectCoverageDrift } from './coverage-drift';
import { checkDependencyHealth } from './dependency-health';
import { findRedundantTests } from './redundant-tests';
import { writeJson } from '../shared/state-store';
import { sendSlackMessage } from '../shared/slack';
import type { MaintenanceFinding } from '../shared/types';

dotenv.config({
  path: process.env.ENV_NAME ? `./env-files/.env.${process.env.ENV_NAME}` : './env-files/.env.demo',
  override: !process.env.CI
});

function formatFinding(finding: MaintenanceFinding) {
  return `- *${finding.severity.toUpperCase()}* ${finding.type}: ${finding.message}`;
}

function buildMaintenanceSlackDigest(findings: MaintenanceFinding[]) {
  const high = findings.filter((f) => f.severity === 'high').length;
  const medium = findings.filter((f) => f.severity === 'medium').length;
  const low = findings.filter((f) => f.severity === 'low').length;

  const byType = findings.reduce<Record<string, number>>((summary, finding) => {
    summary[finding.type] = (summary[finding.type] ?? 0) + 1;
    return summary;
  }, {});

  const typeSummary = Object.entries(byType)
    .map(([type, count]) => `${type}: ${count}`)
    .join(', ');

  const topFindings = findings
    .sort((a, b) => {
      const rank = { high: 3, medium: 2, low: 1 };
      return rank[b.severity] - rank[a.severity];
    })
    .slice(0, 8)
    .map(formatFinding)
    .join('\n');

  return [
    `*Total findings:* ${findings.length}`,
    `*Severity:* High ${high}, Medium ${medium}, Low ${low}`,
    `*Types:* ${typeSummary}`,
    ``,
    `*Top findings:*`,
    topFindings
  ].join('\n');
}

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
      text: buildMaintenanceSlackDigest(findings)
    });
  }

  console.log(`Maintenance Agent completed. Findings: ${findings.length}`);
}

main().catch((error) => {
  console.error('Maintenance Agent failed', error);
  process.exit(1);
});
