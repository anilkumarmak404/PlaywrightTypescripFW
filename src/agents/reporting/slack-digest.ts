import type { FailureSummary, NormalizedTestResult } from '../shared/types';
import { sendSlackMessage } from '../shared/slack';

export async function sendDailySlackDigest(
  results: NormalizedTestResult[],
  summaries: FailureSummary[]
) {
  const total = results.length;
  const passed = results.filter((r) => r.status === 'passed').length;
  const failed = results.filter((r) => r.status === 'failed' || r.status === 'timedOut').length;
  const skipped = results.filter((r) => r.status === 'skipped').length;

  const passRate = total === 0 ? 0 : (passed / total) * 100;

  const topFailures = summaries
    .slice(0, 5)
    .map((s) => `- ${s.testId} - ${s.classification} - ${s.owner}`)
    .join('\n');

  await sendSlackMessage({
    title: 'Daily Playwright Quality Digest',
    text: [
      `*Total:* ${total}`,
      `*Passed:* ${passed}`,
      `*Failed:* ${failed}`,
      `*Skipped:* ${skipped}`,
      `*Pass rate:* ${passRate.toFixed(2)}%`,
      ``,
      `*Top failures:*`,
      topFailures || 'No failures'
    ].join('\n')
  });
}
