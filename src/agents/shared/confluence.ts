import axios from 'axios';
import { resilientCall } from './resilience';

type ConfluenceApiError = {
  message?: string;
  errors?: Array<{
    message?: string;
    title?: string;
    detail?: string;
  }>;
};

type ConfluencePage = {
  id: string;
  status: string;
  title: string;
  version: {
    number: number;
  };
};

function confluenceClient() {
  const baseURL = process.env.CONFLUENCE_BASE_URL;
  const email = process.env.CONFLUENCE_EMAIL;
  const token = process.env.CONFLUENCE_API_TOKEN;

  if (!baseURL || !email || !token) {
    throw new Error('Missing Confluence environment variables');
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

function getConfluenceErrorMessage(error: unknown) {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : String(error);
  }

  const data = error.response?.data as ConfluenceApiError | undefined;
  const errors = data?.errors
    ?.map((item) => item.message ?? item.title ?? item.detail)
    .filter(Boolean);

  if (errors && errors.length > 0) {
    return errors.join('; ');
  }

  return data?.message ?? `Confluence API request failed with status ${error.response?.status ?? 'unknown'}`;
}

async function confluenceRequest<T>(request: () => Promise<{ data: T }>): Promise<T> {
  return resilientCall('confluence-api', async () => {
    try {
      const response = await request();
      return response.data;
    } catch (error) {
      throw new Error(getConfluenceErrorMessage(error));
    }
  });
}

export async function getConfluencePage(pageId: string): Promise<ConfluencePage> {
  const client = confluenceClient();

  return confluenceRequest<ConfluencePage>(() =>
    client.get(`/wiki/api/v2/pages/${pageId}`, {
      params: {
        'body-format': 'storage'
      }
    })
  );
}

export async function updateConfluencePage(input: {
  pageId: string;
  title: string;
  version: number;
  status?: string;
  html: string;
}) {
  const client = confluenceClient();
  const nextVersion = input.status === 'draft' ? 1 : input.version + 1;

  await confluenceRequest(() =>
    client.put(`/wiki/api/v2/pages/${input.pageId}`, {
      id: input.pageId,
      status: 'current',
      title: input.title,
      body: {
        representation: 'storage',
        value: input.html
      },
      version: {
        number: nextVersion
      }
    })
  );
}
