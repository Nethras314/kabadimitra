// Offline-first sync orchestrator.
//
//   local capture -> SQLite (draft) -> pending operation -> API -> server ack
//   -> local operation marked synced.
//
// The backend is authoritative. Every mutation carries an idempotency key so a
// retried batch never creates duplicates; a `replayed` server response is
// success, not an error.

import { LocalStore } from '../db/store';
import { SyncApi } from '../api/client';
import { Connectivity } from '../lib/connectivity';
import { RetryPolicy, ExponentialBackoff } from './retry';
import { SyncQueue } from './queue';
import { makeIdempotencyKey } from '../lib/idempotency';
import { uuidv4 } from '../lib/uuid';
import {
  Lot,
  LotItem,
  SyncOperation,
  SyncResponse,
  SyncResult,
  SyncStatusSummary,
} from '../types';

export interface LotInput {
  title?: string | null;
  notes?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  pickup_address?: string | null;
}

export interface LotItemInput {
  lot_id: string;
  collector_category_id?: string | null;
  material_category_id?: string | null;
  material_subcategory_id?: string | null;
  kind?: LotItem['kind'];
  description?: string | null;
  quantity?: number;
  declared_weight_kg?: number | null;
  condition_id?: string | null;
}

export class SyncService {
  private sequence = 0;

  constructor(
    private readonly store: LocalStore,
    private readonly api: SyncApi,
    private readonly connectivity: Connectivity,
    private readonly retryPolicy: RetryPolicy = new ExponentialBackoff(),
    private readonly queue: SyncQueue = new SyncQueue(store),
    private readonly now: () => Date = () => new Date(),
  ) {}

  private nextIdempotencyKey(entityType: string): string {
    this.sequence = (this.sequence + 1) % 1_000_000;
    return makeIdempotencyKey(entityType, this.now(), this.sequence);
  }

  // --- offline capture -------------------------------------------------------

  async createLot(input: LotInput = {}): Promise<Lot> {
    const lot: Lot = {
      id: uuidv4(),
      status: 'draft',
      title: input.title ?? null,
      notes: input.notes ?? null,
      latitude: input.latitude ?? null,
      longitude: input.longitude ?? null,
      pickup_address: input.pickup_address ?? null,
    };
    await this.store.saveLot(lot);
    await this.queue.enqueue('lot', lot.id, this.nextIdempotencyKey('lot'), {
      title: lot.title ?? null,
      notes: lot.notes ?? null,
      latitude: lot.latitude ?? null,
      longitude: lot.longitude ?? null,
      pickup_address: lot.pickup_address ?? null,
    });
    return lot;
  }

  async addItem(input: LotItemInput): Promise<LotItem> {
    const item: LotItem = {
      id: uuidv4(),
      lot_id: input.lot_id,
      collector_category_id: input.collector_category_id ?? null,
      material_category_id: input.material_category_id ?? null,
      material_subcategory_id: input.material_subcategory_id ?? null,
      kind: input.kind ?? null,
      description: input.description ?? null,
      quantity: input.quantity ?? 1,
      declared_weight_kg: input.declared_weight_kg ?? null,
      condition_id: input.condition_id ?? null,
      classification_source: 'collector',
    };
    await this.store.saveLotItem(item);
    await this.queue.enqueue('lot_item', item.id, this.nextIdempotencyKey('item'), {
      lot_id: item.lot_id,
      collector_category_id: item.collector_category_id,
      material_category_id: item.material_category_id,
      material_subcategory_id: item.material_subcategory_id,
      kind: item.kind,
      description: item.description,
      quantity: item.quantity,
      declared_weight_kg: item.declared_weight_kg,
      condition_id: item.condition_id,
      classification_source: item.classification_source,
    });
    return item;
  }

  // --- sync ------------------------------------------------------------------

  /**
   * Push pending operations to the backend. Returns null when offline or when a
   * network failure interrupted the request (operations stay pending — a retry
   * is safe because idempotency keys make it a no-op server-side).
   */
  async flush(): Promise<SyncResponse | null> {
    if (!(await this.connectivity.isOnline())) {
      return null;
    }

    await this.queue.retryFailed((op) => this.retryPolicy.shouldRetry(op));

    const pending = await this.queue.pending();
    if (pending.length === 0) {
      return { results: [] };
    }

    const operations: SyncOperation[] = pending.map((op) => ({
      idempotency_key: op.idempotency_key,
      entity_type: op.entity_type,
      id: op.entity_id,
      payload: op.payload,
    }));

    let response: SyncResponse;
    try {
      response = await this.api.post(operations);
    } catch {
      return null;
    }

    await this.reconcile(response.results);
    return response;
  }

  async sync(): Promise<SyncStatusSummary> {
    await this.flush();
    return this.status();
  }

  async status(): Promise<SyncStatusSummary> {
    const [online, pending, failed, synced] = await Promise.all([
      this.connectivity.isOnline(),
      this.queue.pending(),
      this.store.failedOperations(),
      this.store.syncedOperationCount(),
    ]);
    return {
      connectivity: online ? 'online' : 'offline',
      pending: pending.length,
      synced,
      failed: failed.length,
    };
  }

  private async reconcile(results: SyncResult[]): Promise<void> {
    for (const result of results) {
      if (result.status === 'applied' || result.status === 'replayed') {
        await this.queue.markSynced(result.idempotency_key);
        await this.confirmEntitySynced(result.idempotency_key);
      } else {
        await this.queue.markFailed(result.idempotency_key, result.error ?? 'unknown error');
      }
    }
  }

  /** Mark the local entity synced once the server has acknowledged the operation. */
  private async confirmEntitySynced(idempotencyKey: string): Promise<void> {
    const op = await this.store.getOperation(idempotencyKey);
    if (!op) return;
    if (op.entity_type === 'lot') {
      await this.store.updateLot(op.entity_id, {
        status: 'synced',
        synced_at: this.now().toISOString(),
      });
    }
  }
}
