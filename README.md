# Playwright TypeScript Automation Framework

Enterprise-ready Playwright TypeScript framework with UI tests, API tests, Page Object Model, reusable fixtures, environment-based execution, Allure reporting, Confluence reporting, Grafana metrics, and AI-style maintenance/reporting agents.

## What This Framework Contains

| Area | Purpose |
| --- | --- |
| `tests/` | UI and API test specs |
| `pages/` | Page Object Model classes |
| `fixtures/` | Playwright custom fixtures for POMs, utilities, hooks |
| `utils/` | Common UI/API helpers and encryption utilities |
| `data/` | Test data for UI and API modules |
| `config/` | Feature maps, owners, and quality gate rules |
| `src/reporters/` | Custom Playwright reporter for AI/reporting data |
| `src/agents/maintenance/` | Agents for dead tests, coverage drift, dependency health, redundant tests |
| `src/agents/reporting/` | Agents for Confluence, Jira, Slack, Grafana, PDF reporting |
| `src/agents/chaos/` | Chaos checks for framework resilience |
| `observability/` | Prometheus, Pushgateway, and Grafana dashboard setup |
| `env-files/` | Environment examples for dev, QA, demo |

## Prerequisites

Install these before running the framework:

- Node.js LTS
- npm
- Git
- Docker Desktop, only needed for Grafana/Prometheus observability
- Java, only if using Allure CLI locally

Check versions:

```bash
node -v
npm -v
git --version
docker version
```

## Initial Setup

Install dependencies:

```bash
npm install
```

Install Playwright browsers:

```bash
npx playwright install
```

Create local environment files from examples:

```bash
copy env-files\.env.demo.example env-files\.env.demo
copy env-files\.env.qa.example env-files\.env.qa
copy env-files\.env.dev.example env-files\.env.dev
```

Do not commit real `.env` files. They can contain secrets such as Slack webhooks, Jira tokens, Confluence tokens, and API keys.

## Environment Variables

Common values used by the framework:

| Variable | Purpose |
| --- | --- |
| `BASE_URL` | UI application base URL |
| `API_BASE_URL` | API test base URL |
| `SECRET_KEY` | Encryption/decryption key for utility methods |
| `SLACK_WEBHOOK_URL` | Slack digest integration |
| `PUSHGATEWAY_URL` | Grafana/Prometheus Pushgateway URL |
| `PUSHGATEWAY_JOB` | Pushgateway job name |
| `CONFLUENCE_BASE_URL` | Atlassian Confluence base URL |
| `CONFLUENCE_EMAIL` | Confluence account email |
| `CONFLUENCE_API_TOKEN` | Confluence API token |
| `CONFLUENCE_PAGE_ID` | Confluence page to update |
| `JIRA_BASE_URL` | Jira base URL |
| `JIRA_EMAIL` | Jira account email |
| `JIRA_API_TOKEN` | Jira API token |

## Test Metadata Standard

Each enterprise test should include metadata in the title:

```ts
test('@id:LOGIN-001 @feature:login @owner:qa-auth @jira:HRM-LOGIN-001 user can login', async ({ loginPage }) => {
  // test steps
});
```

The custom reporter extracts:

- `@id`
- `@feature`
- `@owner`
- `@jira`

This metadata powers maintenance agents, Confluence reporting, Jira defect creation, and ownership dashboards.

## Running Tests

Run all tests:

```bash
npm run test:e2e
```

Run demo environment:

```bash
npm run test_demo
```

Run demo Chromium headed:

```bash
npm run test_demo_cr_hd
```

Run demo Firefox headed:

```bash
npm run test_demo_ff_hd
```

Run demo WebKit headed:

```bash
npm run test_demo_web_hd
```

Run API tests:

```bash
npm run test_demo_api
```

Run smoke tests:

```bash
npm run test_qa_cr_hd_@SMOKE
```

## Reports

Playwright HTML report is generated in:

```text
playwright-report/
```

JSON/JUnit results are generated in:

```text
test-results/
```

Allure results/report:

```bash
npm run clean:allure
npm run test_qa_cr_hd_@SMOKE
npm run report:allure
npm run report:allure:open
```

These report folders are generated artifacts and should not be committed.

## AI Agent Reporting Flow

The framework has a custom reporter:

```text
src/reporters/agent-json-reporter.ts
```

It writes normalized execution data to:

```text
agent-state/test-history.json
reports/ai-summary/latest-agent-results.json
```

Run reporting agent:

```bash
npm run agent:reporting
```

The reporting agent can:

- Parse latest Playwright results
- Summarize failures
- Create/update Jira bugs
- Update Confluence report
- Send Slack digest
- Push Grafana metrics

## Maintenance Agents

Run all maintenance checks:

```bash
npm run agent:maintenance
```

Individual maintenance commands:

```bash
npm run agent:requirements
npm run agent:chaos
```

Maintenance agents check:

- Dead tests
- Coverage drift
- Requirement drift
- Dependency health
- Redundant tests
- Framework resilience

## Confluence Report

Confluence report code:

```text
src/agents/reporting/confluence-report.ts
```

Before running, configure:

```env
CONFLUENCE_BASE_URL=
CONFLUENCE_EMAIL=
CONFLUENCE_API_TOKEN=
CONFLUENCE_PAGE_ID=
```

Then run:

```bash
npm run agent:reporting
```

The report includes:

- Overall health badge
- Current execution summary
- Feature quality table
- Owner view table
- Failure summary
- Latest result snapshot

## Grafana Dashboard

Start observability stack:

```bash
npm run observability:up
```

Open Grafana:

```text
http://localhost:3000
```

Default login:

```text
admin / admin
```

Dashboard file:

```text
observability/grafana/dashboards/playwright-quality.json
```

Metrics are pushed by:

```text
src/agents/reporting/grafana-metrics.ts
```

Run metrics push:

```bash
npm run agent:reporting
```

Dashboard panels show:

- Current Run Total
- Current Run Passed
- Current Run Failed
- Current Run Skipped
- Current Run Flaky
- Current Run Pass Rate
- Today Runs
- Today Total
- Today Passed
- Today Failed
- Today Skipped
- Today Flaky

If dashboard changes do not appear, restart Grafana:

```bash
docker compose restart grafana
```

## Folder Cleanup Policy

Keep source folders:

```text
src/
tests/
pages/
fixtures/
utils/
data/
config/
observability/
env-files/*.example
```

Do not commit generated folders:

```text
node_modules/
test-results/
playwright-report/
allure-results/
allure-report/
reports/
agent-state/
playwright/.auth/
```

These are already covered in `.gitignore`.

## Enterprise CI Flow

Recommended CI stages:

```bash
npm ci
npx playwright install --with-deps
npx tsc --noEmit
npm run test:e2e
npm run agent:maintenance
npm run agent:reporting
```

Recommended quality gates:

- No `test.only`
- TypeScript compile must pass
- Required metadata in every test
- Minimum pass rate
- Maximum skipped tests
- Maximum flaky tests
- No critical dependency issues
- Reports published as CI artifacts

## Framework Design

Page Object Model:

```text
pages/Loginpage.ts
pages/Dashboardpage.ts
pages/Userpage.ts
```

Fixture chain:

```text
@playwright/test
  -> fixtures/pom-fixtures.ts
  -> fixtures/common-fixtures.ts
  -> fixtures/hooks-fixture.ts
```

Tests should import from the final fixture when they need full framework support:

```ts
import { test, expect } from '../../fixtures/hooks-fixture';
```

## Recommended Enterprise Improvements

1. Add a `BasePage` for shared navigation, waits, and common UI actions.
2. Standardize locator strategy using role-based and test-id locators.
3. Move all secrets to CI secret storage.
4. Add pull request checks for TypeScript, Playwright tests, and agents.
5. Add code owners for feature areas.
6. Add retry/flaky tracking policy.
7. Add test data setup and teardown strategy.
8. Add API contract checks for backend dependencies.
9. Publish Playwright, Allure, Confluence, and Grafana reports from CI.
10. Keep generated artifacts out of Git.

## Troubleshooting

Docker error:

```text
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified
```

Fix:

```bash
Start Docker Desktop
docker version
npm run observability:up
```

Grafana dashboard not updated:

```bash
docker compose restart grafana
```

Missing Confluence update:

- Check `CONFLUENCE_PAGE_ID`
- Check API token
- Check page permissions
- Run `npm run agent:reporting`

Missing Slack message:

- Use `SLACK_WEBHOOK_URL`
- Do not use misspelled names such as `LACK_WEBHOOK_URL`

Missing test result data:

```bash
npm run test:e2e
npm run agent:reporting
```

## Git Workflow

Check changes:

```bash
git status
```

Commit:

```bash
git add .
git commit -m "Improve enterprise framework docs and reporting"
```

Push:

```bash
git push origin main
```

