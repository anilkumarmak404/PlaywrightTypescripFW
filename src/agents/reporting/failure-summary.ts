import type { FailureSummary, NormalizedTestResult } from '../shared/types';

function classifyFailure(test: NormalizedTestResult): FailureSummary['classification'] {
  const error = `${test.errorMessage ?? ''}\n${test.stack ?? ''}`.toLowerCase();

  if (error.includes('timeout') || error.includes('timed out')) {
    return 'flaky';
  }

  if (error.includes('locator') || error.includes('strict mode violation')) {
    return 'test_bug';
  }

  if (error.includes('500') || error.includes('api') || error.includes('network')) {
    return 'environment_issue';
  }

  if (error.includes('expect') || error.includes('to be visible') || error.includes('to have text')) {
    return 'product_bug';
  }

  return 'unknown';
}

export async function summarizeFailures(
  failures: NormalizedTestResult[]
): Promise<FailureSummary[]> {
  return failures.map((failure) => {
    const classification = classifyFailure(failure);

    return {
      testId: failure.testId,
      classification,
      owner: failure.owner,
      summary: `Test ${failure.testId} failed in feature ${failure.feature}.`,
      probableCause: failure.errorMessage ?? 'No error message captured.',
      suggestedAction:
        classification === 'test_bug'
          ? 'Review selector, locator, or test data.'
          : classification === 'environment_issue'
            ? 'Check service health, API response, network, or test environment.'
            : classification === 'flaky'
              ? 'Review timeout, wait condition, unstable data, or retry history.'
              : 'Review application behavior against expected result.'
    };
  });
}
