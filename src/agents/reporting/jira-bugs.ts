import type { FailureSummary, NormalizedTestResult } from '../shared/types';
import { createFailureFingerprint } from '../shared/fingerprint';
import {
  addJiraComment,
  attachFileToJira,
  createJiraBug,
  searchJiraIssueByFingerprint,
  updateJiraIssueSummary,
  validateJiraAccess
} from '../shared/jira';

export type JiraSyncResult = {
  testId: string;
  status: 'created' | 'updated' | 'skipped';
  issueKey?: string;
  issueUrl?: string;
  message?: string;
};

function buildGherkinSteps(
  failure: NormalizedTestResult,
  summary?: FailureSummary
): string {
  return [
    'Feature: Automated Playwright failure triage',
    '',
    `  Scenario: ${failure.testId} fails in ${failure.feature}`,
    `    Given the test "${failure.testId}" is executed from "${failure.file}"`,
    `    And the feature under test is "${failure.feature}"`,
    `    And the owning team is "${failure.owner}"`,
    `    When the Playwright test run "${failure.runId}" reaches this scenario`,
    `    Then the test status should be "${failure.status}"`,
    `    And the failure should be classified as "${summary?.classification ?? 'unknown'}"`,
    `    And the probable cause should be "${summary?.probableCause ?? failure.errorMessage ?? 'Unknown'}"`,
    `    And the suggested action should be "${summary?.suggestedAction ?? 'Review failure artifacts'}"`
  ].join('\n');
}

function titleCase(value: string) {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(' ');
}

function buildJiraBugTitle(
  failure: NormalizedTestResult,
  summary?: FailureSummary
) {
  const feature = titleCase(failure.feature);
  const classification = titleCase(summary?.classification ?? 'unknown');
  const status = titleCase(failure.status);

  return `[Playwright Failure] ${feature} - ${failure.testId} ${status} (${classification})`;
}

export async function upsertJiraBugs(
  failures: NormalizedTestResult[],
  summaries: FailureSummary[]
): Promise<JiraSyncResult[]> {
  const results: JiraSyncResult[] = [];

  if (
    !process.env.JIRA_BASE_URL ||
    !process.env.JIRA_EMAIL ||
    !process.env.JIRA_API_TOKEN ||
    !process.env.JIRA_PROJECT_KEY && !process.env.JIRA_PROJECT_ID
  ) {
    console.warn('Jira environment variables are not configured');
    return failures.map((failure) => ({
      testId: failure.testId,
      status: 'skipped',
      message: 'Jira environment variables are not configured'
    }));
  }

  try {
    await validateJiraAccess();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.warn(`Jira sync skipped: ${message}`);
    return failures.map((failure) => ({
      testId: failure.testId,
      status: 'skipped',
      message
    }));
  }

  for (const failure of failures) {
    try {
      const fingerprint = createFailureFingerprint(failure);
      const summary = summaries.find((s) => s.testId === failure.testId);
      const gherkinSteps = buildGherkinSteps(failure, summary);
      const jiraTitle = buildJiraBugTitle(failure, summary);

      const existing = await searchJiraIssueByFingerprint(fingerprint);

      const description = [
        `**Automated Playwright Failure**`,
        ``,
        `**Failure Details**`,
        `Test ID: ${failure.testId}`,
        `Test Title: ${failure.title}`,
        `Feature: ${titleCase(failure.feature)}`,
        `Owner: ${failure.owner}`,
        `Status: ${failure.status}`,
        `Classification: ${summary?.classification ?? 'unknown'}`,
        `Run ID: ${failure.runId}`,
        `File: ${failure.file}`,
        ``,
        `**Impact Summary**`,
        summary?.summary ?? 'No summary available',
        ``,
        `**Probable Cause**`,
        summary?.probableCause ?? failure.errorMessage ?? 'Unknown',
        ``,
        `**Suggested Action**`,
        summary?.suggestedAction ?? 'Review failure artifacts',
        ``,
        `**Bug Reproduction Steps - Cucumber / Gherkin**`,
        gherkinSteps
      ].join('\n');

      let issueKey: string;

      if (existing) {
        issueKey = existing.key;

        await updateJiraIssueSummary(issueKey, jiraTitle);
        await addJiraComment(
          issueKey,
          [
            `Failure reproduced again for test ${failure.testId}. Run ID: ${failure.runId}`,
            ``,
            `**Bug Reproduction Steps - Cucumber / Gherkin**`,
            gherkinSteps
          ].join('\n')
        );

        results.push({
          testId: failure.testId,
          status: 'updated',
          issueKey,
          issueUrl: `${process.env.JIRA_BASE_URL}/browse/${issueKey}`
        });
      } else {
        const issue = await createJiraBug({
          summary: jiraTitle,
          description,
          fingerprint,
          labels: [failure.feature, failure.owner]
        });

        issueKey = issue.key;

        results.push({
          testId: failure.testId,
          status: 'created',
          issueKey,
          issueUrl: `${process.env.JIRA_BASE_URL}/browse/${issueKey}`
        });
      }

      await attachFileToJira(issueKey, failure.tracePath);
      await attachFileToJira(issueKey, failure.screenshotPath);
      await attachFileToJira(issueKey, failure.videoPath);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.warn(`Jira sync skipped for ${failure.testId}: ${message}`);
      results.push({
        testId: failure.testId,
        status: 'skipped',
        message
      });
    }
  }

  return results;
}
