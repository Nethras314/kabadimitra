import assert from 'node:assert/strict';
import { test } from 'node:test';

import { PendingOperation } from '../types';
import { ExponentialBackoff } from './retry';

function failed(attempts: number): PendingOperation {
  return {
    idempotency_key: 'k',
    entity_type: 'lot',
    entity_id: 'id',
    payload: {},
    status: 'failed',
    attempts,
    last_error: 'x',
  };
}

test('retries while attempts are below maxAttempts', () => {
  const policy = new ExponentialBackoff(3);
  assert.equal(policy.shouldRetry(failed(0)), true);
  assert.equal(policy.shouldRetry(failed(2)), true);
  assert.equal(policy.shouldRetry(failed(3)), false);
  assert.equal(policy.shouldRetry(failed(4)), false);
});

test('non-failed operations are not retried', () => {
  const policy = new ExponentialBackoff(3);
  const pending = { ...failed(0), status: 'pending' as const };
  assert.equal(policy.shouldRetry(pending), false);
});

test('exponential backoff grows with each attempt', () => {
  const policy = new ExponentialBackoff(3, 1000, 2);
  assert.equal(policy.delayMs(0), 1000);
  assert.equal(policy.delayMs(1), 2000);
  assert.equal(policy.delayMs(2), 4000);
});
