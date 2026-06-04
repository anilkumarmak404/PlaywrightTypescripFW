import crypto from 'crypto';
import dotenv from 'dotenv';
import { scanTests } from './scan-tests';
import { getJiraIssue, addJiraIssueComment } from '../shared/jira';
import { readJson, writeJson } from '../shared/state-store';
import { sendSlackMessage } from '../shared/slack';

dotenv.config({
  path: process.env.ENV_NAME ? `./env-files/.env.${process.env.ENV_NAME}` : './env-files/.env.demo',
  override: !process.env.CI
});

type RequirementSnapshot = {
  jiraKey: string;
  hash: string;
  updatedAt: string;
  linkedTests: string[];
};

type SkippedRequirement = {
  jiraKey: string;
  reason: string;
  linkedTests: string[];
};

function hashText(text: string) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

function extractPlainTextFromAdf(node: any): string {
  if (!node) return '';

  if (typeof node === 'string') return node;

  if (Array.isArray(node)) {
    return node.map(extractPlainTextFromAdf).join('\n');
  }

  const text = node.text ? `${node.text}\n` : '';
  const children = node.content ? extractPlainTextFromAdf(node.content) : '';

  return `${text}${children}`;
}

async function main() {
  console.log('Requirements Drift Agent started');

  const registry = await scanTests('tests/**/*.spec.ts');

  const snapshots = await readJson<Record<string, RequirementSnapshot>>(
    'requirement-snapshots.json',
    {}
  );

  const jiraKeys = [...new Set(registry.map((test) => test.jira).filter((x) => x !== 'UNKNOWN'))];

  const driftItems = [];
  const skippedItems: SkippedRequirement[] = [];

  for (const jiraKey of jiraKeys) {
    let issue: Awaited<ReturnType<typeof getJiraIssue>>;

    try {
      issue = await getJiraIssue(jiraKey);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const linkedTests = registry
        .filter((test) => test.jira === jiraKey)
        .map((test) => test.id);

      skippedItems.push({
        jiraKey,
        reason: message,
        linkedTests
      });
      console.warn(`Requirements drift skipped ${jiraKey}: ${message}`);
      continue;
    }

    const descriptionText = extractPlainTextFromAdf(issue.fields.description);
    const newHash = hashText(descriptionText);

    const previous = snapshots[jiraKey];

    const linkedTests = registry
      .filter((test) => test.jira === jiraKey)
      .map((test) => test.id);

    if (previous && previous.hash !== newHash) {
      driftItems.push({
        jiraKey,
        oldHash: previous.hash,
        newHash,
        linkedTests,
        updatedAt: issue.fields.updated
      });

      await addJiraIssueComment(
        jiraKey,
        `Automation drift detected. Linked tests require review: ${linkedTests.join(', ')}`
      );
    }

    snapshots[jiraKey] = {
      jiraKey,
      hash: newHash,
      updatedAt: issue.fields.updated,
      linkedTests
    };
  }

  await writeJson('requirement-snapshots.json', snapshots);
  await writeJson('latest-requirement-drift.json', {
    createdAt: new Date().toISOString(),
    status:
      driftItems.length > 0
        ? 'drift_detected'
        : skippedItems.length > 0
          ? 'completed_with_skipped_links'
          : 'no_drift',
    snapshotCount: Object.keys(snapshots).length,
    skippedCount: skippedItems.length,
    driftItems,
    skippedItems
  });

  if (driftItems.length > 0) {
    await sendSlackMessage({
      title: 'Requirements drift detected',
      text: driftItems
        .map((d) => `*${d.jiraKey}* changed. Linked tests: ${d.linkedTests.join(', ')}`)
        .join('\n')
    });
  }

  if (driftItems.length === 0 && skippedItems.length > 0) {
    await sendSlackMessage({
      title: 'Requirements drift skipped Jira links',
      text: [
        `*Skipped Jira links:* ${skippedItems.length}`,
        `These @jira tags do not exist or are not visible to the configured Jira user.`,
        ``,
        skippedItems
          .slice(0, 10)
          .map((item) => `- *${item.jiraKey}* linked tests: ${item.linkedTests.join(', ')}`)
          .join('\n'),
        skippedItems.length > 10 ? `...and ${skippedItems.length - 10} more` : '',
        ``,
        `Update test @jira tags to real Jira issue keys from project ${process.env.JIRA_PROJECT_KEY ?? '<project>'}, for example SCRUM-31.`
      ]
        .filter(Boolean)
        .join('\n')
    });
  }

  console.log(
    `Requirements Drift Agent completed. Drift items: ${driftItems.length}. ` +
      `Snapshots: ${Object.keys(snapshots).length}. Skipped links: ${skippedItems.length}.`
  );
}

main().catch((error) => {
  console.error('Requirements Drift Agent failed', error);
  process.exit(1);
});
