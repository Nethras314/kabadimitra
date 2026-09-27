# Offline Sync

> Phase 6 deliverable. The mobile client works offline (SQLite); the backend is
> authoritative. This documents the sync contract and the backend-side
> implementation.

## 1. Principle

The backend is authoritative. Clients capture work offline and push batches of
changes when connectivity returns. Every operation carries an **idempotency
key**; a retried batch replays results instead of creating duplicates.

## 2. Idempotency contract

- Each operation has a unique `idempotency_key` (e.g. `KC-LOT-260926-000482`).
- The backend records the key in `sync_operations` together with the created
  `entity_id` and `status = applied`.
- A repeated key returns `status = replayed` with the original `entity_id` — it
  does **not** create a duplicate and does **not** return an error.

Entities use client-generated UUID primary keys (ADR-0011), so the client does
not need a server round-trip to obtain IDs.

## 3. Endpoint

`POST /api/v1/sync`

```json
{
  "operations": [
    {"idempotency_key": "KC-LOT-…", "entity_type": "lot", "id": "<uuid>", "payload": {"title": "…"}},
    {"idempotency_key": "KC-ITEM-…", "entity_type": "lot_item", "id": "<uuid>", "payload": {"lot_id": "<uuid>", "material_category_id": "…"}}
  ]
}
```

Response:

```json
{
  "results": [
    {"idempotency_key": "KC-LOT-…", "entity_id": "<uuid>", "status": "applied"},
    {"idempotency_key": "KC-ITEM-…", "entity_id": "<uuid>", "status": "applied"}
  ]
}
```

Supported `entity_type`s: `lot`, `lot_item`, `transaction`, `weight`, `payment`.

## 4. Ordering & atomicity

Operations are applied in order; each operation is committed independently (a
failed operation does not roll back the rest). The client must order operations
so dependencies precede dependents (lot → item → transaction → weight/payment).

## 5. Ownership & validation

The backend resolves the collector and enforces ownership on parent references
(`lot_item.lot_id`, `transaction.lot_id`, `weight.transaction_id`,
`payment.transaction_id`). Payloads are validated with Pydantic models.

## 6. Conflict handling

- **Create** operations are idempotent (replay).
- There is no automatic merge of concurrent edits: the backend is authoritative
  and the last applied write wins. Complex conflicts surface for review rather
  than being silently merged.

## 7. Not yet implemented (Phase 7, client-side)

- Mobile SQLite schema and the client sync queue.
- Cached price information and safety content.
- `material_image` sync (images upload directly to Cloudinary; only metadata is
  synced — to be added to the batch contract).
