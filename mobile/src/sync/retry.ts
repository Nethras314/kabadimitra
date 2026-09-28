// Retry strategy for failed sync operations.

import { PendingOperation } from '../types';

export interface RetryPolicy {
  /** Maximum attempts before an operation is left failed for manual review. */
  maxAttempts: number;
  shouldRetry(operation: PendingOperation): boolean;
  delayMs(attempt: number): number;
}

/** Exponential backoff with a hard attempt cap. */
export class ExponentialBackoff implements RetryPolicy {
  constructor(
    public readonly maxAttempts = 3,
    private readonly baseDelayMs = 1000,
    private readonly factor = 2,
  ) {}

  shouldRetry(operation: PendingOperation): boolean {
    return operation.status === 'failed' && operation.attempts < this.maxAttempts;
  }

  delayMs(attempt: number): number {
    return this.baseDelayMs * Math.pow(this.factor, attempt);
  }
}
