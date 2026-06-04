import crypto from 'crypto';
import type { NormalizedTestResult } from './types';

export function createFailureFingerprint(test: NormalizedTestResult): string {
  const normalizedError = (test.errorMessage ?? '')
    .replace(/\d+/g, '<num>')
    .replace(/\s+/g, ' ')
    .slice(0, 500);

  const raw = [
    test.testId,
    test.feature,
    normalizedError,
    test.file
  ].join('|');

  return crypto.createHash('sha256').update(raw).digest('hex');
}
