import CircuitBreaker from 'opossum';
import { logger } from './logger';

type AsyncFn = (...args: any[]) => Promise<any>;

export function withCircuitBreaker<T extends AsyncFn>(fn: T, name: string) {
  const breaker = new CircuitBreaker(fn, {
    timeout: 10_000,
    errorThresholdPercentage: 50,
    resetTimeout: 30_000
  });

  breaker.fallback(() => {
    logger.warn(`Circuit breaker fallback triggered for ${name}`);
    return null;
  });

  breaker.on('open', () => logger.warn(`Circuit breaker opened for ${name}`));
  breaker.on('halfOpen', () => logger.warn(`Circuit breaker half-open for ${name}`));
  breaker.on('close', () => logger.info(`Circuit breaker closed for ${name}`));

  return breaker;
}

export async function withRetry<T>(
  action: () => Promise<T>,
  name: string,
  attempts = 3,
  delayMs = 500
): Promise<T> {
  let lastError: unknown;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await action();
    } catch (error) {
      lastError = error;
      logger.warn(`${name} attempt ${attempt}/${attempts} failed: ${errorMessage(error)}`);

      if (attempt < attempts) {
        await new Promise((resolve) => setTimeout(resolve, delayMs * attempt));
      }
    }
  }

  throw lastError;
}

export async function resilientCall<T>(
  name: string,
  action: () => Promise<T>,
  fallback?: T
): Promise<T> {
  const breaker = withCircuitBreaker(async () => withRetry(action, name), name);
  const result = await breaker.fire();

  if (result === null) {
    if (fallback !== undefined) {
      return fallback;
    }

    throw new Error(`Circuit breaker fallback triggered for ${name}`);
  }

  return result as T;
}

export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}
