import axios from 'axios';
import fs from 'fs-extra';
import FormData from 'form-data';

type JiraApiErrorData = {
  errorMessages?: string[];
  errors?: Record<string, string>;
};

type CreatedJiraIssue = {
  key: string;
};

type JiraPermission = {
  havePermission: boolean;
};

type JiraIssuePayload = {
  fields: {
    project: {
      id?: string;
      key?: string;
    };
    issuetype: {
      name: string;
    };
    summary: string;
    description: ReturnType<typeof toJiraDescription>;
    labels: string[];
  };
};

type JiraUser = {
  accountId: string;
  displayName?: string;
  emailAddress?: string;
};

type JiraIssue = {
  key: string;
  fields: {
    summary?: string;
    description?: unknown;
    updated: string;
    status?: unknown;
    labels?: string[];
  };
};

function jiraClient() {
  const baseURL = process.env.JIRA_BASE_URL;
  const email = process.env.JIRA_EMAIL;
  const token = process.env.JIRA_API_TOKEN;

  if (!baseURL || !email || !token) {
    throw new Error('Missing Jira environment variables');
  }

  return axios.create({
    baseURL,
    auth: {
      username: email,
      password: token
    },
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    }
  });
}

export function getJiraEnvSummary() {
  return {
    baseURL: process.env.JIRA_BASE_URL ?? '',
    email: process.env.JIRA_EMAIL ?? '',
    hasToken: Boolean(process.env.JIRA_API_TOKEN),
    tokenLength: process.env.JIRA_API_TOKEN?.length ?? 0,
    projectKey: process.env.JIRA_PROJECT_KEY ?? '',
    projectId: process.env.JIRA_PROJECT_ID ?? '',
    issueType: process.env.JIRA_ISSUE_TYPE ?? ''
  };
}

function toJiraDescription(text: string) {
  return {
    type: 'doc',
    version: 1,
    content: text.split('\n').map((line) => ({
      type: 'paragraph',
      content: line
        ? [
            {
              type: 'text',
              text: line.replace(/^\*\*(.*)\*\*$/, '$1'),
              marks: /^\*\*.*\*\*$/.test(line)
                ? [
                    {
                      type: 'strong'
                    }
                  ]
                : undefined
            }
          ]
        : []
    }))
  };
}

function getJiraErrorMessage(error: unknown) {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : String(error);
  }

  const cause = error.cause;
  const responseStatus =
    error.response?.status ??
    (axios.isAxiosError(cause) ? cause.response?.status : undefined);

  if (responseStatus === 401) {
    return (
      'Jira authentication failed with status 401. ' +
      'Check JIRA_EMAIL and JIRA_API_TOKEN, revoke any exposed token, and create a fresh Atlassian API token.'
    );
  }

  const responseData =
    error.response?.data ??
    (axios.isAxiosError(cause) ? cause.response?.data : undefined);
  const data = responseData as JiraApiErrorData | undefined;
  const messages = [
    ...(data?.errorMessages ?? []),
    ...Object.entries(data?.errors ?? {}).map(([field, message]) => `${field}: ${message}`)
  ];

  return messages.length > 0
    ? messages.join('; ')
    : `Jira API request failed with status ${responseStatus ?? 'unknown'}`;
}

async function jiraRequest<T>(request: () => Promise<{ data: T }>): Promise<T> {
  try {
    const response = await request();
    return response.data;
  } catch (error) {
    throw new Error(getJiraErrorMessage(error));
  }
}

export async function verifyJiraAuth(): Promise<JiraUser> {
  const client = jiraClient();
  return jiraRequest<JiraUser>(() => client.get('/rest/api/3/myself'));
}

function sanitizeLabel(label: string) {
  return label.replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 255);
}

function buildCreateIssuePayload(input: {
  projectId?: string;
  projectKey?: string;
  issueType: string;
  summary: string;
  description: string;
  fingerprint: string;
  labels?: string[];
}): JiraIssuePayload {
  return {
    fields: {
      project: input.projectId
        ? { id: input.projectId }
        : { key: input.projectKey },
      issuetype: {
        name: input.issueType
      },
      summary: input.summary,
      description: toJiraDescription(input.description),
      labels: [
        'playwright-auto',
        `fp-${input.fingerprint.slice(0, 12)}`,
        ...(input.labels ?? [])
      ].map(sanitizeLabel)
    }
  };
}

export async function validateJiraAccess(): Promise<void> {
  const client = jiraClient();
  const projectKey = process.env.JIRA_PROJECT_KEY;
  const projectId = process.env.JIRA_PROJECT_ID;

  if (!projectKey && !projectId) {
    throw new Error('Missing JIRA_PROJECT_KEY or JIRA_PROJECT_ID');
  }

  const projectIdOrKey = projectId ?? projectKey;

  await jiraRequest(() => client.get('/rest/api/3/myself'));

  try {
    await jiraRequest(() => client.get(`/rest/api/3/project/${projectIdOrKey}`));
  } catch (error) {
    throw new Error(
      `Jira project ${projectIdOrKey} is not visible to this API user. ` +
        'Check JIRA_PROJECT_KEY/JIRA_PROJECT_ID and project access.'
    );
  }

  const permissionData = await jiraRequest<{ permissions: Record<string, JiraPermission> }>(() =>
    client.get('/rest/api/3/mypermissions', {
      params: {
        projectKey: projectKey && !projectId ? projectKey : undefined,
        projectId,
        permissions: 'BROWSE_PROJECTS,CREATE_ISSUES'
      }
    })
  );

  const canBrowse = permissionData.permissions.BROWSE_PROJECTS?.havePermission;
  const canCreate = permissionData.permissions.CREATE_ISSUES?.havePermission;

  if (!canBrowse || !canCreate) {
    throw new Error(
      `Jira API user lacks permission for project ${projectIdOrKey}. ` +
        `BROWSE_PROJECTS=${Boolean(canBrowse)}, CREATE_ISSUES=${Boolean(canCreate)}.`
    );
  }
}

export async function searchJiraIssueByFingerprint(fingerprint: string) {
  const client = jiraClient();

  const jql = `labels = "fp-${fingerprint.slice(0, 12)}" AND statusCategory != Done`;

  const data = await jiraRequest<{ issues?: Array<{ key: string }> }>(() =>
    client.post('/rest/api/3/search/jql', {
      jql,
      maxResults: 1,
      fields: ['key', 'summary', 'status']
    })
  );

  return data.issues?.[0];
}

export async function createJiraBug(input: {
  summary: string;
  description: string;
  fingerprint: string;
  labels?: string[];
}): Promise<CreatedJiraIssue> {
  const client = jiraClient();

  const projectKey = process.env.JIRA_PROJECT_KEY;
  const projectId = process.env.JIRA_PROJECT_ID;
  const issueTypes = process.env.JIRA_ISSUE_TYPE
    ? [process.env.JIRA_ISSUE_TYPE]
    : ['Task', 'Bug'];

  if (!projectKey && !projectId) {
    throw new Error('Missing JIRA_PROJECT_KEY or JIRA_PROJECT_ID');
  }

  const errors: string[] = [];

  for (const issueType of issueTypes) {
    try {
      return await jiraRequest<CreatedJiraIssue>(() =>
        client.post(
          '/rest/api/3/issue',
          buildCreateIssuePayload({
            projectId,
            projectKey,
            issueType,
            summary: input.summary,
            description: input.description,
            fingerprint: input.fingerprint,
            labels: input.labels
          })
        )
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      errors.push(`${issueType}: ${message}`);
    }
  }

  throw new Error(`Unable to create Jira issue. ${errors.join(' | ')}`);
}

export async function updateJiraIssueSummary(issueKey: string, summary: string) {
  const client = jiraClient();

  await jiraRequest(() =>
    client.put(`/rest/api/3/issue/${issueKey}`, {
      fields: {
        summary
      }
    })
  );
}

export async function addJiraComment(issueKey: string, text: string) {
  const client = jiraClient();

  await jiraRequest(() =>
    client.post(`/rest/api/3/issue/${issueKey}/comment`, {
      body: toJiraDescription(text)
    })
  );
}

export async function getJiraIssue(issueKey: string): Promise<JiraIssue> {
  const client = jiraClient();

  return jiraRequest<JiraIssue>(() =>
    client.get(`/rest/api/3/issue/${issueKey}`, {
      params: {
        fields: 'summary,description,updated,status,labels'
      }
    })
  );
}

export async function addJiraIssueComment(issueKey: string, text: string) {
  return addJiraComment(issueKey, text);
}

export async function attachFileToJira(issueKey: string, filePath?: string) {
  if (!filePath || !(await fs.pathExists(filePath))) {
    return;
  }

  const baseURL = process.env.JIRA_BASE_URL;
  const email = process.env.JIRA_EMAIL;
  const token = process.env.JIRA_API_TOKEN;

  if (!baseURL || !email || !token) {
    throw new Error('Missing Jira environment variables');
  }

  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));

  await jiraRequest(() =>
    axios.post(
      `${baseURL}/rest/api/3/issue/${issueKey}/attachments`,
      form,
      {
        auth: {
          username: email,
          password: token
        },
        headers: {
          ...form.getHeaders(),
          'X-Atlassian-Token': 'no-check'
        }
      }
    )
  );
}
