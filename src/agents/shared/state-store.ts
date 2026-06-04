import fs from 'fs-extra';
import path from 'path';

const STATE_DIR = path.resolve('agent-state');

async function ensureStateDir() {
  await fs.ensureDir(STATE_DIR);
}

export async function readJson<T>(fileName: string, fallback: T): Promise<T> {
  await ensureStateDir();

  const fullPath = path.join(STATE_DIR, fileName);

  if (!(await fs.pathExists(fullPath))) {
    return fallback;
  }

  return fs.readJson(fullPath) as Promise<T>;
}

export async function writeJson<T>(fileName: string, data: T): Promise<void> {
  await ensureStateDir();

  const fullPath = path.join(STATE_DIR, fileName);

  await fs.writeJson(fullPath, data, { spaces: 2 });
}

export async function appendJsonArray<T>(fileName: string, item: T): Promise<void> {
  const existing = await readJson<T[]>(fileName, []);
  existing.push(item);
  await writeJson(fileName, existing);
}
