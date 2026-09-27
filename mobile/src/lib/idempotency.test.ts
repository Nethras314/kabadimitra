import assert from 'node:assert/strict';
import { test } from 'node:test';

import { makeIdempotencyKey } from './idempotency';
import { uuidv4 } from './uuid';

test('idempotency key matches approved format', () => {
  const d = new Date(2026, 8, 26); // 2026-09-26
  assert.equal(makeIdempotencyKey('lot', d, 482), 'KC-LOT-260926-000482');
  assert.equal(makeIdempotencyKey('item', d, 7), 'KC-ITEM-260926-000007');
});

test('uuidv4 is a valid v4 uuid', () => {
  const id = uuidv4();
  assert.match(
    id,
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
});
