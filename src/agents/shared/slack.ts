import { IncomingWebhook } from '@slack/webhook';

type SlackMessage = {
  title: string;
  text: string;
};

export async function sendSlackMessage(message: SlackMessage): Promise<void> {
  const url = process.env.SLACK_WEBHOOK_URL;

  if (!url) {
    console.warn('SLACK_WEBHOOK_URL is not configured');
    return;
  }

  const webhook = new IncomingWebhook(url);

  try {
    await webhook.send({
      text: message.title,
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: message.title
          }
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: message.text
          }
        }
      ]
    });
  } catch (error) {
    const err = error as { code?: string; message?: string };
    console.warn(`Slack notification skipped: ${err.code ?? err.message ?? 'request failed'}`);
  }
}
