import assert from 'node:assert/strict';
import { test } from 'node:test';

import { InMemoryStore } from '../db/store';
import { SyncQueue } from './queue';

test('enqueue stores a pending operation', async () => {
  const q = new SyncQueue(new InMemoryStore());
  await q.enqueue('lot', 'lot-1', 'KC-LOT-000001', { title: 'x' });
  const pending = await q.pending();
  assert.equal(pending.length, 1);
  assert.equal(pending[0].entity_type, 'lot');
  assert.equal(pending[0].entity_id, 'lot-1');
  assert.equal(pending[0].idempotency_key, 'KC-LOT-000001');
});

test('markSynced removes an operation from pending', async () => {
  const q = new SyncQueue(new InMemoryStore());
  await q.enqueue('lot', 'lot-1', 'KC-LOT-000001', {});
  await q.markSynced('KC-LOT-000001');
  assert.equal((await q.pending()).length, 0);
});

test('markFailed records error and increments attempts', async () => {
  const store = new InMemoryStore();
  const q = new SyncQueue(store);
  await q.enqueue('lot', 'lot-1', 'KC-LOT-000001', {});
  await q.markFailed('KC-LOT-000001', 'boom');
  const failed = await store.failedOperations();
  assert.equal(failed.length, 1);
  assert.equal(failed[0].attempts, 1);
  assert.equal(failed[0].last_error, 'boom');
});

test('retryFailed re-marks only retriable operations pending', async () => {
  const store = new InMemoryStore();
  const q = new SyncQueue(store);
  await q.enqueue('lot', 'a', 'K-A', {});
  await q.enqueue('lot', 'b', 'K-B', {});
  await q.markFailed('K-A', 'err');
  await q.markFailed('K-B', 'err');

  const retried = await q.retryFailed(() => true);
  assert.equal(retried, 2);
  assert.equal((await q.pending()).length, 2);
});
