import dotenv from 'dotenv';
import axios from 'axios';
import { getJiraEnvSummary, validateJiraAccess, verifyJiraAuth } from '../shared/jira';

dotenv.config({
  path: process.env.ENV_NAME ? `./env-files/.env.${process.env.ENV_NAME}` : './env-files/.env.demo',
  override: true
});

async function main() {
  const env = getJiraEnvSummary();

  console.log('Jira env loaded');
  console.log(`Base URL: ${env.baseURL || '<missing>'}`);
  console.log(`Email: ${env.email || '<missing>'}`);
  console.log(`Token configured: ${env.hasToken ? 'yes' : 'no'}`);
  console.log(`Token length: ${env.tokenLength}`);
  console.log(`Project key: ${env.projectKey || '<missing>'}`);
  console.log(`Project id: ${env.projectId || '<missing>'}`);
  console.log(`Issue type: ${env.issueType || '<default>'}`);

  await probeJiraAuth();

  const user = await verifyJiraAuth();
  console.log(`Jira auth OK: ${user.displayName ?? user.accountId}`);

  await validateJiraAccess();
  console.log('Jira project access OK');
}

async function probeJiraAuth() {
  try {
    await axios.get(`${process.env.JIRA_BASE_URL}/rest/api/3/myself`, {
      auth: {
        username: process.env.JIRA_EMAIL ?? '',
        password: process.env.JIRA_API_TOKEN ?? ''
      },
      headers: {
        Accept: 'application/json'
      }
    });
  } catch (error) {
    if (!axios.isAxiosError(error)) {
      throw error;
    }

    console.error(`Direct Jira auth status: ${error.response?.status ?? '<none>'}`);
    console.error(`Direct Jira auth code: ${error.code ?? '<none>'}`);
    console.error(`Direct Jira auth message: ${error.message}`);

    const data = error.response?.data;
    if (data) {
      console.error(`Direct Jira response: ${JSON.stringify(data)}`);
    }

    throw error;
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Jira auth check failed: ${message}`);
  process.exit(1);
});
