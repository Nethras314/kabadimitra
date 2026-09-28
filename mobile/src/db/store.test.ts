import assert from 'node:assert/strict';
import { test } from 'node:test';

import { InMemoryStore } from './store';

test('save and retrieve a lot', async () => {
  const s = new InMemoryStore();
  await s.saveLot({ id: 'lot-1', status: 'draft', title: 'Monitor' });
  const lot = await s.getLot('lot-1');
  assert.equal(lot?.title, 'Monitor');
  assert.equal(lot?.status, 'draft');
});

test('update lot status', async () => {
  const s = new InMemoryStore();
  await s.saveLot({ id: 'lot-1', status: 'draft' });
  await s.updateLot('lot-1', { status: 'synced', synced_at: '2026-09-27T00:00:00Z' });
  assert.equal((await s.getLot('lot-1'))?.status, 'synced');
});

test('save and list lot items', async () => {
  const s = new InMemoryStore();
  await s.saveLotItem({
    id: 'item-1',
    lot_id: 'lot-1',
    quantity: 2,
    classification_source: 'collector',
  });
  const items = await s.listLotItems('lot-1');
  assert.equal(items.length, 1);
  assert.equal(items[0].quantity, 2);
});

test('pending operation lifecycle', async () => {
  const s = new InMemoryStore();
  await s.enqueueOperation({
    idempotency_key: 'k',
    entity_type: 'lot',
    entity_id: 'id',
    payload: {},
    status: 'pending',
    attempts: 0,
  });
  assert.equal((await s.pendingOperations()).length, 1);

  await s.markOperationFailed('k', 'boom');
  const failed = await s.failedOperations();
  assert.equal(failed.length, 1);
  assert.equal(failed[0].attempts, 1);

  await s.markOperationPending('k');
  assert.equal((await s.pendingOperations()).length, 1);

  await s.markOperationSynced('k');
  assert.equal(await s.syncedOperationCount(), 1);
  assert.equal((await s.pendingOperations()).length, 0);
});

test('cache get/set round-trips and misses cleanly', async () => {
  const s = new InMemoryStore();
  await s.setCached('materials', '{"a":1}');
  assert.equal(await s.getCached('materials'), '{"a":1}');
  assert.equal(await s.getCached('missing'), null);
});
