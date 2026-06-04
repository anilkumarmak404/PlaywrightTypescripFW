export type AgentStatus = 'PASS' | 'WARN' | 'FAIL' | 'TODO';

export type FrameworkFeature =
  | 'auth'
  | 'pim-employee-management'
  | 'api-mocking'
  | 'restful-booker-api'
  | 'google-place-api'
  | 'framework-core';

export type FrameworkOwner =
  | 'qa-auth'
  | 'qa-hr'
  | 'qa-api'
  | 'qa-platform';

export type FrameworkJiraProject =
  | 'HRM-AUTH'
  | 'HRM-PIM'
  | 'HRM-MOCK'
  | 'API-BOOKER'
  | 'API-GOOGLE'
  | 'HRM-FW';

export type FrameworkBusinessArea =
  | 'Authentication'
  | 'Employee Management'
  | 'API Integration'
  | 'Test Infrastructure';

export type FrameworkProject =
  | 'setup'
  | 'chromium'
  | 'firefox'
  | 'webkit'
  | 'apiTest';

export type AgentResult = {
  name: string;
  status: AgentStatus;
  summary: string;
  details?: string[];
  recommendations?: string[];
};

export type FeatureMap = {
  features: Partial<Record<FrameworkFeature, FeatureConfig>>;
};

export type FeatureConfig = {
  owner: FrameworkOwner;
  jiraProject: FrameworkJiraProject;
  businessArea?: FrameworkBusinessArea;
  code: string[];
  tests: string[];
};

export type OwnersConfig = {
  owners: Partial<Record<FrameworkOwner, OwnerConfig>>;
};

export type OwnerConfig = {
  slack: string;
  email: string;
};

export type QualityGatesConfig = {
  releaseReadiness: ReleaseReadinessGate;
  maintenance?: MaintenanceGate;
  reporting?: ReportingGate;
};

export type ReleaseReadinessGate = {
  minPassRate: number;
  maxFlakyRate: number;
  maxCriticalFailures: number;
  maxOpenAutomationBugs: number;
  minFeatureCoverage: number;
};

export type MaintenanceGate = {
  maxStaleTestDays: number;
  maxSkippedTests: number;
  maxDuplicateTestTitles: number;
  requireTestMetadata: Array<'id' | 'feature' | 'owner' | 'jira'>;
};

export type ReportingGate = {
  failBuildOnNoGo: boolean;
  includeTraceAttachments: boolean;
  includeScreenshots: boolean;
};

export type TestMetadata = {
  id: string;
  feature: FrameworkFeature | string;
  owner: FrameworkOwner | string;
  jira: string;
};

export type TestRegistryItem = {
  id: string;
  title: string;
  file: string;
  feature: FrameworkFeature | string;
  owner: FrameworkOwner | string;
  jira: string;
  tags: string[];
};

export type TestRegistryEntry = {
  id: string;
  title: string;
  file: string;
  project?: string;
  metadata: TestMetadata;
  tags: string[];
};

export type NormalizedTestResult = {
  runId: string;
  testId: string;
  title: string;
  file: string;
  feature: FrameworkFeature | string;
  owner: FrameworkOwner | string;
  jira: string;
  status: 'passed' | 'failed' | 'flaky' | 'skipped' | 'timedOut' | 'unknown';
  durationMs: number;
  retry: number;
  errorMessage?: string;
  stack?: string;
  tracePath?: string;
  screenshotPath?: string;
  videoPath?: string;
  runAt?: string;
};

export type FailureSummary = {
  testId: string;
  classification: 'product_bug' | 'test_bug' | 'environment_issue' | 'flaky' | 'unknown';
  summary: string;
  probableCause: string;
  suggestedAction: string;
  owner: FrameworkOwner | string;
};

export type MaintenanceFinding = {
  type: 'dead_test' | 'coverage_drift' | 'dependency_update' | 'redundant_test';
  severity: 'low' | 'medium' | 'high';
  message: string;
  payload: Record<string, unknown>;
};

export type CoverageDriftResult = {
  feature: FrameworkFeature | string;
  changedCode: string[];
  changedTests: string[];
  hasCoverageDrift: boolean;
  owner: FrameworkOwner | string;
  jiraProject: FrameworkJiraProject | string;
};

export type TestHistoryItem = {
  runId: string;
  testId: string;
  project: FrameworkProject | string;
  status: NormalizedTestResult['status'];
  durationMs: number;
  retry: number;
  executedAt: string;
};

export type RequirementSnapshot = {
  jira: string;
  feature: FrameworkFeature | string;
  hash: string;
  acceptanceCriteria: string[];
  capturedAt: string;
};

export type FailureFingerprint = {
  fingerprint: string;
  testId: string;
  classification: FailureSummary['classification'];
  firstSeenAt: string;
  lastSeenAt: string;
  count: number;
};

export type AgentState = {
  testRegistry: TestRegistryItem[];
  testHistory: TestHistoryItem[];
  requirementSnapshots: RequirementSnapshot[];
  failureFingerprints: FailureFingerprint[];
};

export type ReleaseDecision = 'GO' | 'NO-GO';

export type ReleaseReadinessResult = {
  decision: ReleaseDecision;
  passRate: number;
  flakyRate: number;
  criticalFailures: number;
  openAutomationBugs: number;
  featureCoverage: number;
  failedGates: string[];
};
