import type { FailureSummary, NormalizedTestResult } from '../shared/types';
import { getConfluencePage, updateConfluencePage } from '../shared/confluence';
import type { JiraSyncResult } from './jira-bugs';

function percent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatDuration(durationMs: number) {
  if (!Number.isFinite(durationMs)) return '0 ms';
  if (durationMs < 1000) return `${durationMs} ms`;
  return `${(durationMs / 1000).toFixed(1)} sec`;
}

function averageDuration(results: NormalizedTestResult[]) {
  if (results.length === 0) return 0;
  const totalDuration = results.reduce((total, result) => total + result.durationMs, 0);
  return Math.round(totalDuration / results.length);
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function jiraLinkFor(testId: string, jiraResults: JiraSyncResult[]) {
  const jira = jiraResults.find((item) => item.testId === testId);

  if (!jira?.issueKey || !jira.issueUrl) {
    return jira?.status === 'skipped'
      ? `Skipped: ${escapeHtml(jira.message ?? 'No Jira issue created')}`
      : 'Not created';
  }

  return `<a href="${escapeHtml(jira.issueUrl)}">${escapeHtml(jira.issueKey)}</a> (${jira.status})`;
}

function statusMacro(title: string, colour: 'Blue' | 'Green' | 'Red' | 'Yellow' | 'Purple' | 'Grey') {
  return [
    '<ac:structured-macro ac:name="status" ac:schema-version="1">',
    `<ac:parameter ac:name="title">${escapeHtml(title)}</ac:parameter>`,
    `<ac:parameter ac:name="colour">${colour}</ac:parameter>`,
    '<ac:parameter ac:name="subtle">false</ac:parameter>',
    '</ac:structured-macro>'
  ].join('');
}

function panelMacro(title: string, body: string, type: 'info' | 'note' | 'success' | 'warning') {
  return [
    `<ac:structured-macro ac:name="${type}" ac:schema-version="1">`,
    `<ac:parameter ac:name="title">${escapeHtml(title)}</ac:parameter>`,
    '<ac:rich-text-body>',
    body,
    '</ac:rich-text-body>',
    '</ac:structured-macro>'
  ].join('');
}

function metricCard(label: string, value: string | number, colour: 'Blue' | 'Green' | 'Red' | 'Yellow' | 'Grey') {
  return `
    <td>
      <p><strong>${escapeHtml(label)}</strong></p>
      <p>${statusMacro(String(value), colour)}</p>
    </td>
  `;
}

function classificationStatus(classification: FailureSummary['classification']) {
  if (classification === 'product_bug') return statusMacro('PRODUCT BUG', 'Red');
  if (classification === 'test_bug') return statusMacro('TEST BUG', 'Yellow');
  if (classification === 'environment_issue') return statusMacro('ENV ISSUE', 'Purple');
  if (classification === 'flaky') return statusMacro('FLAKY', 'Blue');
  return statusMacro('UNKNOWN', 'Grey');
}

function statusSummary(status: NormalizedTestResult['status']) {
  if (status === 'passed') return statusMacro('PASSED', 'Green');
  if (status === 'failed' || status === 'timedOut') return statusMacro('FAILED', 'Red');
  if (status === 'skipped') return statusMacro('SKIPPED', 'Yellow');
  if (status === 'flaky') return statusMacro('FLAKY', 'Blue');
  return statusMacro('UNKNOWN', 'Grey');
}

function outcomeSummary(total: number, failed: number, passRate: number) {
  if (total === 0) {
    return {
      badge: statusMacro('NO RESULTS', 'Grey')
    };
  }

  if (failed > 0) {
    return {
      badge: statusMacro('FAILURES FOUND', 'Red')
    };
  }

  if (passRate >= 0.9) {
    return {
      badge: statusMacro('HEALTHY', 'Green')
    };
  }

  return {
    badge: statusMacro('REVIEW', 'Yellow')
  };
}

function buildBreakdownRows(
  results: NormalizedTestResult[],
  groupBy: (result: NormalizedTestResult) => string
) {
  const groups = new Map<string, NormalizedTestResult[]>();

  for (const result of results) {
    const key = groupBy(result) || 'unknown';
    groups.set(key, [...(groups.get(key) ?? []), result]);
  }

  return [...groups.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, group]) => {
      const passed = group.filter((result) => result.status === 'passed').length;
      const failed = group.filter((result) => result.status === 'failed' || result.status === 'timedOut').length;
      const skipped = group.filter((result) => result.status === 'skipped').length;
      const flaky = group.filter((result) => result.status === 'flaky').length;
      const passRate = group.length === 0 ? 0 : passed / group.length;

      return `
      <tr>
        <td><strong>${escapeHtml(name)}</strong></td>
        <td>${escapeHtml(String(group.length))}</td>
        <td>${statusMacro(String(passed), 'Green')}</td>
        <td>${statusMacro(String(failed), failed > 0 ? 'Red' : 'Green')}</td>
        <td>${statusMacro(String(skipped), skipped > 0 ? 'Yellow' : 'Green')}</td>
        <td>${statusMacro(String(flaky), flaky > 0 ? 'Blue' : 'Green')}</td>
        <td>${statusMacro(percent(passRate), passRate >= 0.9 ? 'Green' : 'Red')}</td>
      </tr>
    `;
    })
    .join('');
}

export async function updateConfluenceReport(
  results: NormalizedTestResult[],
  summaries: FailureSummary[],
  jiraResults: JiraSyncResult[] = []
) {
  const pageId = process.env.CONFLUENCE_PAGE_ID;

  if (!pageId) {
    console.warn('CONFLUENCE_PAGE_ID is not configured');
    return;
  }

  const page = await getConfluencePage(pageId);

  const total = results.length;
  const passed = results.filter((r) => r.status === 'passed').length;
  const failed = results.filter((r) => r.status === 'failed' || r.status === 'timedOut').length;
  const skipped = results.filter((r) => r.status === 'skipped').length;
  const flaky = results.filter((r) => r.status === 'flaky').length;
  const unknown = results.filter((r) => r.status === 'unknown').length;
  const avgDuration = averageDuration(results);

  const passRate = total === 0 ? 0 : passed / total;
  const outcome = outcomeSummary(total, failed, passRate);
  const runId = results[0]?.runId ?? 'N/A';
  const latestRunAt = results
    .map((result) => result.runAt)
    .filter(Boolean)
    .sort()
    .at(-1) ?? new Date().toISOString();

  const failureRows = summaries
    .map(
      (s) => `
      <tr>
        <td><strong>${escapeHtml(s.testId)}</strong></td>
        <td>${classificationStatus(s.classification)}</td>
        <td>${escapeHtml(s.owner)}</td>
        <td>${escapeHtml(s.summary)}</td>
        <td>${escapeHtml(s.probableCause)}</td>
        <td>${escapeHtml(s.suggestedAction)}</td>
        <td>${jiraLinkFor(s.testId, jiraResults)}</td>
      </tr>
    `
    )
    .join('');

  const resultRows = results
    .slice(0, 25)
    .map(
      (result) => `
      <tr>
        <td><strong>${escapeHtml(result.testId)}</strong></td>
        <td>${statusSummary(result.status)}</td>
        <td>${escapeHtml(result.feature)}</td>
        <td>${escapeHtml(result.owner)}</td>
        <td>${escapeHtml(formatDuration(result.durationMs))}</td>
        <td>${escapeHtml(result.jira)}</td>
      </tr>
    `
    )
    .join('');

  const featureRows = buildBreakdownRows(results, (result) => result.feature);
  const ownerRows = buildBreakdownRows(results, (result) => result.owner);

  const html = `
    <h1><strong>Playwright Automation Quality Report</strong></h1>

    <table>
      <tr>
        <td><strong>Overall Health</strong><br />${outcome.badge}</td>
        <td><strong>Run ID</strong><br /><code>${escapeHtml(runId)}</code></td>
        <td><strong>Latest Result Time</strong><br />${escapeHtml(latestRunAt)}</td>
        <td><strong>Report Updated</strong><br />${escapeHtml(new Date().toISOString())}</td>
      </tr>
    </table>

    <h2>Execution Summary</h2>
    <table>
      <tr>
        ${metricCard('Total Tests', total, 'Blue')}
        ${metricCard('Passed', passed, 'Green')}
        ${metricCard('Failed', failed, failed > 0 ? 'Red' : 'Green')}
        ${metricCard('Skipped', skipped, skipped > 0 ? 'Yellow' : 'Green')}
        ${metricCard('Flaky', flaky, flaky > 0 ? 'Blue' : 'Green')}
      </tr>
      <tr>
        ${metricCard('Pass Rate', percent(passRate), passRate >= 0.9 ? 'Green' : 'Red')}
        ${metricCard('Unknown', unknown, unknown > 0 ? 'Grey' : 'Green')}
        ${metricCard('Average Duration', formatDuration(avgDuration), 'Blue')}
        ${metricCard('Failures Reviewed', summaries.length, summaries.length > 0 ? 'Yellow' : 'Green')}
        ${metricCard('Jira Links', jiraResults.length, jiraResults.length > 0 ? 'Blue' : 'Grey')}
      </tr>
    </table>

    <h2>Feature Quality</h2>
    <table>
      <tr>
        <th>Feature</th>
        <th>Total</th>
        <th>Passed</th>
        <th>Failed</th>
        <th>Skipped</th>
        <th>Flaky</th>
        <th>Pass Rate</th>
      </tr>
      ${featureRows || `<tr><td colspan="7">${statusMacro('NO FEATURE DATA', 'Grey')}</td></tr>`}
    </table>

    <h2>Owner View</h2>
    <table>
      <tr>
        <th>Owner</th>
        <th>Total</th>
        <th>Passed</th>
        <th>Failed</th>
        <th>Skipped</th>
        <th>Flaky</th>
        <th>Pass Rate</th>
      </tr>
      ${ownerRows || `<tr><td colspan="7">${statusMacro('NO OWNER DATA', 'Grey')}</td></tr>`}
    </table>

    <h2>Failure Summary</h2>
    <table>
      <tr>
        <th>Test ID</th>
        <th>Classification</th>
        <th>Owner</th>
        <th>Summary</th>
        <th>Probable Cause</th>
        <th>Suggested Action</th>
        <th>Jira Bug</th>
      </tr>
      ${failureRows || `<tr><td colspan="7">${statusMacro('NO FAILURES', 'Green')}</td></tr>`}
    </table>

    <h2>Latest Result Snapshot</h2>
    <table>
      <tr>
        <th>Test ID</th>
        <th>Status</th>
        <th>Feature</th>
        <th>Owner</th>
        <th>Duration</th>
        <th>Jira Ref</th>
      </tr>
      ${resultRows || `<tr><td colspan="6">${statusMacro('NO RESULTS', 'Grey')}</td></tr>`}
    </table>
  `;

  await updateConfluencePage({
    pageId,
    title: page.title,
    version: page.version.number,
    status: page.status,
    html
  });
}
