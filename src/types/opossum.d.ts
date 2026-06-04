declare module 'opossum' {
  type CircuitBreakerOptions = {
    timeout?: number;
    errorThresholdPercentage?: number;
    resetTimeout?: number;
  };

  export default class CircuitBreaker<
    T extends (...args: any[]) => Promise<any>
  > {
    constructor(action: T, options?: CircuitBreakerOptions);
    fire(...args: Parameters<T>): ReturnType<T>;
    fallback(handler: (...args: Parameters<T>) => Awaited<ReturnType<T>> | null): void;
    on(event: string, handler: (...args: any[]) => void): void;
  }
}
