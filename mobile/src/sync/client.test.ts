import assert from 'node:assert/strict';
import { test } from 'node:test';

import { SyncQueue } from './queue';
import { SyncClient } from './client';

test('flush marks synced on applied and replayed', async () => {
  const q = new SyncQueue();
  q.enqueue({ idempotencyKey: 'k1', entityType: 'lot', id: 'id1', payload: {} });
  q.enqueue({ idempotencyKey: 'k2', entityType: 'lot', id: 'id2', payload: {} });

  const api = {
    post: async () => ({
      results: [
        { idempotencyKey: 'k1', entityId: 'id1', status: 'applied' as const },
        { idempotencyKey: 'k2', entityId: 'id2', status: 'replayed' as const },
      ],
    }),
  };

  const client = new SyncClient(q, api);
  const results = await client.flush();
  assert.equal(results.length, 2);
  assert.equal(q.pending().length, 0);
});

test('flush marks failed on error result', async () => {
  const q = new SyncQueue();
  q.enqueue({ idempotencyKey: 'k1', entityType: 'lot', id: 'id1', payload: {} });

  const api = {
    post: async () => ({
      results: [{ idempotencyKey: 'k1', status: 'error' as const, error: 'bad' }],
    }),
  };

  const client = new SyncClient(q, api);
  await client.flush();
  assert.equal(q.pending().length, 0);
  assert.equal(q.size(), 1);

  q.retryFailed();
  assert.equal(q.pending().length, 1);
});
