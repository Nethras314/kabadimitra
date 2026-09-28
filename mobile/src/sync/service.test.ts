import assert from 'node:assert/strict';
import { test } from 'node:test';

import { InMemoryStore } from '../db/store';
import { StaticConnectivity } from '../lib/connectivity';
import { SyncApi } from '../api/client';
import { SyncOperation, SyncResponse } from '../types';
import { ExponentialBackoff } from './retry';
import { SyncService } from './service';

class FakeApi implements SyncApi {
  received: SyncOperation[][] = [];
  replayMode = false;
  errorMode = false;
  failNext = false;

  async post(operations: SyncOperation[]): Promise<SyncResponse> {
    if (this.failNext) {
      this.failNext = false;
      throw new Error('network down');
    }
    this.received.push(operations);
    const status = this.replayMode ? 'replayed' : this.errorMode ? 'error' : 'applied';
    return {
      results: operations.map((op) => ({
        idempotency_key: op.idempotency_key,
        entity_id: status === 'error' ? null : op.id,
        status: status as 'applied' | 'replayed' | 'error',
        error: status === 'error' ? 'server error' : null,
      })),
    };
  }
}

function makeService(opts: { conn?: StaticConnectivity; api?: FakeApi; maxAttempts?: number } = {}) {
  const store = new InMemoryStore();
  const conn = opts.conn ?? new StaticConnectivity(true);
  const api = opts.api ?? new FakeApi();
  const svc = new SyncService(store, api, conn, new ExponentialBackoff(opts.maxAttempts ?? 3));
  return { store, conn, api, svc };
}

test('airplane mode: create lot offline, then reconnect and sync', async () => {
  const conn = new StaticConnectivity(false);
  const { store, api, svc } = makeService({ conn });

  const lot = await svc.createLot({ title: 'Old monitor' });
  assert.equal(lot.status, 'draft');

  // Offline: flush is a no-op and does not hit the network.
  assert.equal(await svc.flush(), null);
  assert.equal(api.received.length, 0);
  assert.equal((await store.getLot(lot.id))?.status, 'draft');

  // Reconnect and sync.
  conn.setOnline(true);
  const result = await svc.sync();
  assert.equal(result.connectivity, 'online');
  assert.equal(result.pending, 0);
  assert.equal(result.synced, 1);

  assert.equal(api.received.length, 1);
  assert.equal(api.received[0].length, 1);
  assert.equal(api.received[0][0].entity_type, 'lot');
  assert.ok(api.received[0][0].idempotency_key.startsWith('KC-LOT-'));
  assert.equal((await store.getLot(lot.id))?.status, 'synced');
});

test('repeated sync does not resend already-synced operations', async () => {
  const { api, svc } = makeService();
  await svc.createLot({ title: 'x' });
  await svc.sync();
  await svc.sync();
  assert.equal(api.received.length, 1);
});

test('duplicate prevention: a replayed server response is success, not failure', async () => {
  const api = new FakeApi();
  api.replayMode = true;
  const { store, svc } = makeService({ api });

  const lot = await svc.createLot({ title: 'x' });
  const result = await svc.sync();

  assert.equal(result.failed, 0);
  assert.equal(result.synced, 1);
  assert.equal((await store.getLot(lot.id))?.status, 'synced');
});

test('interrupted sync leaves operations pending; retry succeeds', async () => {
  const api = new FakeApi();
  const { store, svc } = makeService({ api });

  const lot = await svc.createLot({ title: 'x' });

  // The connection drops mid-flush (network failure, not a server verdict).
  api.failNext = true;
  assert.equal(await svc.flush(), null);
  assert.equal((await store.getLot(lot.id))?.status, 'draft');
  assert.equal((await store.pendingOperations()).length, 1);

  // On reconnect the pending operation is applied — idempotency prevents dupes.
  const result = await svc.sync();
  assert.equal(result.synced, 1);
  assert.equal(result.pending, 0);
  assert.equal((await store.getLot(lot.id))?.status, 'synced');
});

test('server error marks operation failed and it is retried on the next sync', async () => {
  const api = new FakeApi();
  api.errorMode = true;
  const { store, svc } = makeService({ api });

  await svc.createLot({ title: 'x' });
  await svc.sync();
  assert.equal((await store.failedOperations()).length, 1);

  // Server recovers; the failed operation is retried and applied.
  api.errorMode = false;
  const result = await svc.sync();
  assert.equal(result.failed, 0);
  assert.equal(result.synced, 1);
});

test('operation stays failed after exhausting retries', async () => {
  const api = new FakeApi();
  api.errorMode = true;
  const { store, svc } = makeService({ api, maxAttempts: 3 });

  await svc.createLot({ title: 'x' });
  await svc.sync(); // attempt 1
  await svc.sync(); // attempt 2
  await svc.sync(); // attempt 3
  await svc.sync(); // no retry left

  const failed = await store.failedOperations();
  assert.equal(failed.length, 1);
  assert.equal(failed[0].attempts, 3);
});
