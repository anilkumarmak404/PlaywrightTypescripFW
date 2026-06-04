import type { FailureSummary, NormalizedTestResult } from '../shared/types';
import { getConfluencePage, updateConfluencePage } from '../shared/confluence';
import type { JiraSyncResult } from './jira-bugs';

function percent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
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

function metricCard(label: string, value: string | number, color: string) {
  return `
    <td style="width: 20%; padding: 12px; border: 1px solid ${color}; background-color: #f8fbff;">
      <p style="margin: 0; color: #42526e; font-size: 12px;"><strong>${label}</strong></p>
      <p style="margin: 6px 0 0 0; color: ${color}; font-size: 24px;"><strong>${value}</strong></p>
    </td>
  `;
}

function classificationColor(classification: FailureSummary['classification']) {
  if (classification === 'product_bug') return '#de350b';
  if (classification === 'test_bug') return '#ff991f';
  if (classification === 'environment_issue') return '#6554c0';
  if (classification === 'flaky') return '#0052cc';
  return '#6b778c';
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

  const passRate = total === 0 ? 0 : passed / total;

  const failureRows = summaries
    .map(
      (s, index) => `
      <tr style="background-color: ${index % 2 === 0 ? '#ffffff' : '#f7f8f9'};">
        <td style="padding: 8px; border: 1px solid #dfe1e6;"><strong>${escapeHtml(s.testId)}</strong></td>
        <td style="padding: 8px; border: 1px solid #dfe1e6; color: ${classificationColor(s.classification)};"><strong>${escapeHtml(s.classification)}</strong></td>
        <td style="padding: 8px; border: 1px solid #dfe1e6;">${escapeHtml(s.owner)}</td>
        <td style="padding: 8px; border: 1px solid #dfe1e6;">${escapeHtml(s.summary)}</td>
        <td style="padding: 8px; border: 1px solid #dfe1e6;">${escapeHtml(s.suggestedAction)}</td>
        <td style="padding: 8px; border: 1px solid #dfe1e6;">${jiraLinkFor(s.testId, jiraResults)}</td>
      </tr>
    `
    )
    .join('');

  const html = `
    <h1>Playwright Automation Quality Report</h1>

    <p style="color: #42526e;"><strong>Updated:</strong> ${new Date().toISOString()}</p>

    <h2>Execution Summary</h2>
    <table style="width: 100%; border-collapse: collapse;">
      <tr>
        ${metricCard('Total Tests', total, '#172b4d')}
        ${metricCard('Passed', passed, '#00875a')}
        ${metricCard('Failed', failed, failed > 0 ? '#de350b' : '#00875a')}
        ${metricCard('Skipped', skipped, skipped > 0 ? '#ff991f' : '#00875a')}
        ${metricCard('Pass Rate', percent(passRate), passRate >= 0.9 ? '#00875a' : '#de350b')}
      </tr>
    </table>

    <h2>Failure Summary</h2>
    <table style="width: 100%; border-collapse: collapse;">
      <tr style="background-color: #172b4d; color: #ffffff;">
        <th style="padding: 8px; border: 1px solid #172b4d;">Test ID</th>
        <th style="padding: 8px; border: 1px solid #172b4d;">Classification</th>
        <th style="padding: 8px; border: 1px solid #172b4d;">Owner</th>
        <th style="padding: 8px; border: 1px solid #172b4d;">Summary</th>
        <th style="padding: 8px; border: 1px solid #172b4d;">Suggested Action</th>
        <th style="padding: 8px; border: 1px solid #172b4d;">Jira Bug</th>
      </tr>
      ${failureRows || '<tr><td colspan="6" style="padding: 12px; border: 1px solid #dfe1e6; color: #00875a;"><strong>No failures in this run</strong></td></tr>'}
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
