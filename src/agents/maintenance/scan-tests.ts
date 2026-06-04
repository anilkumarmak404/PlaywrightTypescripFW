import fg from 'fast-glob';
import fs from 'fs-extra';
import type { TestRegistryItem } from '../shared/types';

function extractMetaFromText(text: string, file: string): TestRegistryItem[] {
  const testRegex = /test(?:\.(?:only|skip|fixme|fail|slow))?\(['"`]([^'"`]+)['"`]/g;

  const items: TestRegistryItem[] = [];
  let match: RegExpExecArray | null;

  while ((match = testRegex.exec(text)) !== null) {
    const title = match[1];

    const id = title.match(/@id:([A-Z0-9-_]+)/)?.[1];
    const feature = title.match(/@feature:([a-zA-Z0-9-_]+)/)?.[1];
    const owner = title.match(/@owner:([a-zA-Z0-9-_]+)/)?.[1];
    const jira = title.match(/@jira:([A-Z0-9-]+)/)?.[1];

    if (!id) {
      continue;
    }

    items.push({
      id,
      title,
      file,
      feature: feature ?? 'unknown',
      owner: owner ?? 'unknown',
      jira: jira ?? 'UNKNOWN',
      tags: title.match(/@[a-zA-Z0-9-_:]+/g) ?? []
    });
  }

  return items;
}

export async function scanTests(pattern = 'tests/**/*.spec.ts') {
  const files = await fg(pattern, { onlyFiles: true });

  const registry: TestRegistryItem[] = [];

  for (const file of files) {
    const text = await fs.readFile(file, 'utf-8');
    registry.push(...extractMetaFromText(text, file));
  }

  return registry;
}
