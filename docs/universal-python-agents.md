# Universal Python Agents

This folder explains how to reuse the Python agents in any automation framework:

- Playwright TypeScript
- Selenium Java
- Cypress
- Pytest
- Generic frameworks that produce JUnit XML

The key idea is simple: every framework must produce a common result file, then the Python agents normalize it.

## Supported Inputs

| Framework | Recommended Result Format | Command Example |
| --- | --- | --- |
| Playwright TS | Existing `reports/ai-summary/latest-agent-results.json` or JUnit XML | `npx playwright test --reporter=junit` |
| Selenium Java | JUnit XML from Surefire/Failsafe | `mvn test` |
| Cypress | Mochawesome JSON or JUnit XML | `npx cypress run --reporter junit` |
| Pytest | JUnit XML | `pytest --junitxml=test-results/junit.xml` |
| Any framework | JUnit XML | Framework-specific |

## Copy To Another Framework

Copy this folder:

```text
python_agents/
```

## Python Folder Structure

The Python agents use the same domain layout as the original agent implementation:

```text
python_agents/
  cli.py
  agents/
    chaos/
      chaos.py
    maintenance/
      coverage_drift.py
      dead_tests.py
      dependency_health.py
      enterprise.py
      index.py
      redundant_tests.py
      requirements_drift.py
      scan_tests.py
    reporting/
      confluence_client.py
      failure_summary.py
      grafana_metrics.py
      index.py
      jira_client.py
      parse_results.py
      slack_digest.py
      slack_client.py
      weekly_report.py
    shared/
      adapters.py
      confluence.py
      env.py
      fingerprint.py
      github.py
      http_client.py
      io_utils.py
      jira.py
      llm.py
      logger.py
      metadata.py
      models.py
      resilience.py
      scanner.py
      slack.py
      state_store.py
```

Use `agents/` for both agent behavior and reusable shared utilities. The `agents/shared/` package contains framework-neutral clients and helpers for Jira, Confluence, Slack, file IO, fingerprints, metadata, and result parsing.

Also copy these optional config files when available:

```text
config/quality-gates.yml
.gitignore
README.md
```

## Minimum Metadata Standard

Put metadata in test names, method names, or nearby comments:

```text
@id:LOGIN-001 @feature:login @owner:qa-auth @jira:HRM-LOGIN-001
```

Required metadata:

```text
@id
@feature
@owner
@jira
```

### Playwright Example

```ts
test('@id:LOGIN-001 @feature:login @owner:qa-auth @jira:HRM-LOGIN-001 valid login', async ({ page }) => {
  // test
});
```

### Cypress Example

```js
it('@id:LOGIN-001 @feature:login @owner:qa-auth @jira:HRM-LOGIN-001 valid login', () => {
  // test
});
```

### Selenium Java Example

```java
// @id:LOGIN-001 @feature:login @owner:qa-auth @jira:HRM-LOGIN-001
@Test
void validLogin() {
    // test
}
```

## Commands

Run on Playwright:

```bash
python -m python_agents.cli all --framework playwright
```

Run on Selenium Java/JUnit:

```bash
python -m python_agents.cli all --framework selenium --results "target/surefire-reports/*.xml"
```

Run on Cypress:

```bash
python -m python_agents.cli all --framework cypress --results "cypress/reports/**/*.json"
```

Run on generic JUnit:

```bash
python -m python_agents.cli all --framework junit --results "test-results/**/*.xml"
```

Auto-detect:

```bash
python -m python_agents.cli all --framework auto
```

## NPM Shortcuts In This Framework

```bash
npm run agent:normalize
npm run agent:maintenance
npm run agent:requirements
npm run agent:jira:check
npm run agent:reporting
npm run agent:weekly-pdf
npm run agent:chaos
npm run agent:all
```

## Python Agent Parity

The main npm agent commands run the Python implementations.

| Main Command | Runs |
| --- | --- |
| `npm run agent:maintenance` | Python enterprise readiness plus dependency health |
| `npm run agent:requirements` | Python requirements drift |
| `npm run agent:reporting` | Python reporting with optional Jira/Confluence |
| `npm run agent:jira:check` | Python Jira auth/project check |
| `npm run agent:weekly-pdf` | Python weekly HTML/PDF scorecard |
| `npm run agent:chaos` | Python chaos validation |
| Full Python flow | `npm run agent:all` |

The Python reporting flow includes optional Jira issue sync and optional Confluence page update. If Jira or Confluence environment variables are missing or invalid, the Python agent writes a skipped/failed diagnostic result instead of crashing the whole run.

## What The Python Agents Produce

Primary outputs:

```text
reports/ai-summary/python-normalized-results.json
reports/ai-summary/python-agent-summary.json
reports/ai-summary/python-agent-report.md
reports/metrics/automation.prom
agent-state/python-enterprise-readiness.json
agent-state/python-latest-requirement-drift.json
agent-state/python-jira-auth-check.json
agent-state/python-weekly-report.json
agent-state/python-latest-chaos-results.json
```

If the report folder is locked, the agent writes fallback files under:

```text
agent-state/python-agents/
```

## Enterprise Checks

The Python enterprise agent checks:

- Missing metadata
- Duplicate test IDs
- Accidental focused tests such as `test.only`
- Skipped/fixme tests over the configured limit
- Required framework files
- `.gitignore` hygiene
- Tracked real `.env` files

## CI Example

### Playwright

```bash
npm ci
npx playwright install --with-deps
npm run test:e2e
python -m python_agents.cli all --framework playwright
```

### Selenium Java

```bash
mvn test
python -m python_agents.cli all --framework selenium --results "target/surefire-reports/*.xml"
```

### Cypress

```bash
npm ci
npx cypress run --reporter junit --reporter-options "mochaFile=test-results/cypress-[hash].xml"
python -m python_agents.cli all --framework junit --results "test-results/*.xml"
```

## Migration Rule

Do not rewrite every framework immediately. First make each framework export JUnit XML or JSON, then run the Python agents on top of that output.
