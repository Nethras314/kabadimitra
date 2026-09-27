import assert from 'node:assert/strict';
import { test } from 'node:test';

import { SyncOperation } from '../types';
import { SyncQueue } from './queue';

function op(key: string): SyncOperation {
  return { idempotencyKey: key, entityType: 'lot', id: 'id-' + key, payload: {} };
}

test('enqueue then mark synced', () => {
  const q = new SyncQueue();
  q.enqueue(op('k1'));
  assert.equal(q.pending().length, 1);
  q.markSynced('k1');
  assert.equal(q.pending().length, 0);
});

test('failed entries can be retried', () => {
  const q = new SyncQueue();
  q.enqueue(op('k1'));
  q.markFailed('k1');
  assert.equal(q.pending().length, 0);
  q.retryFailed();
  assert.equal(q.pending().length, 1);
});
