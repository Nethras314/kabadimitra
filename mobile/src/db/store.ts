// Local persistence abstraction. The sync layer depends on this interface so it
// stays pure and testable; an expo-sqlite adapter implements it on-device.

import { CollectorProfile, Lot, LotItem, PendingOperation } from '../types';

export interface LocalStore {
  // collector profile
  saveCollectorProfile(profile: CollectorProfile): Promise<void>;
  getCollectorProfile(): Promise<CollectorProfile | null>;

  // lots
  saveLot(lot: Lot): Promise<void>;
  getLot(id: string): Promise<Lot | null>;
  listLots(): Promise<Lot[]>;
  updateLot(id: string, patch: Partial<Lot>): Promise<void>;

  // lot items
  saveLotItem(item: LotItem): Promise<void>;
  listLotItems(lotId: string): Promise<LotItem[]>;

  // pending operations (outbox)
  enqueueOperation(operation: PendingOperation): Promise<void>;
  getOperation(idempotencyKey: string): Promise<PendingOperation | null>;
  pendingOperations(): Promise<PendingOperation[]>;
  failedOperations(): Promise<PendingOperation[]>;
  syncedOperationCount(): Promise<number>;
  markOperationSynced(idempotencyKey: string): Promise<void>;
  markOperationFailed(idempotencyKey: string, error: string): Promise<void>;
  markOperationPending(idempotencyKey: string): Promise<void>;

  // cache
  getCached(key: string): Promise<string | null>;
  setCached(key: string, value: string): Promise<void>;
}

/** In-memory LocalStore — used by tests and as a reference implementation. */
export class InMemoryStore implements LocalStore {
  private profiles = new Map<string, CollectorProfile>();
  private lots = new Map<string, Lot>();
  private items = new Map<string, LotItem>();
  private operations = new Map<string, PendingOperation>();
  private cache = new Map<string, string>();

  async saveCollectorProfile(profile: CollectorProfile): Promise<void> {
    this.profiles.set(profile.user_id, { ...profile });
  }

  async getCollectorProfile(): Promise<CollectorProfile | null> {
    for (const p of this.profiles.values()) return { ...p };
    return null;
  }

  async saveLot(lot: Lot): Promise<void> {
    this.lots.set(lot.id, { ...lot });
  }

  async getLot(id: string): Promise<Lot | null> {
    const lot = this.lots.get(id);
    return lot ? { ...lot } : null;
  }

  async listLots(): Promise<Lot[]> {
    return [...this.lots.values()].map((l) => ({ ...l }));
  }

  async updateLot(id: string, patch: Partial<Lot>): Promise<void> {
    const lot = this.lots.get(id);
    if (lot) this.lots.set(id, { ...lot, ...patch });
  }

  async saveLotItem(item: LotItem): Promise<void> {
    this.items.set(item.id, { ...item });
  }

  async listLotItems(lotId: string): Promise<LotItem[]> {
    return [...this.items.values()].filter((i) => i.lot_id === lotId).map((i) => ({ ...i }));
  }

  async enqueueOperation(operation: PendingOperation): Promise<void> {
    this.operations.set(operation.idempotency_key, { ...operation });
  }

  async getOperation(idempotencyKey: string): Promise<PendingOperation | null> {
    const op = this.operations.get(idempotencyKey);
    return op ? { ...op } : null;
  }

  async pendingOperations(): Promise<PendingOperation[]> {
    return [...this.operations.values()]
      .filter((o) => o.status === 'pending')
      .map((o) => ({ ...o }));
  }

  async failedOperations(): Promise<PendingOperation[]> {
    return [...this.operations.values()]
      .filter((o) => o.status === 'failed')
      .map((o) => ({ ...o }));
  }

  async syncedOperationCount(): Promise<number> {
    return [...this.operations.values()].filter((o) => o.status === 'synced').length;
  }

  async markOperationSynced(idempotencyKey: string): Promise<void> {
    const op = this.operations.get(idempotencyKey);
    if (op) this.operations.set(idempotencyKey, { ...op, status: 'synced', last_error: null });
  }

  async markOperationFailed(idempotencyKey: string, error: string): Promise<void> {
    const op = this.operations.get(idempotencyKey);
    if (op) {
      this.operations.set(idempotencyKey, {
        ...op,
        status: 'failed',
        attempts: op.attempts + 1,
        last_error: error,
      });
    }
  }

  async markOperationPending(idempotencyKey: string): Promise<void> {
    const op = this.operations.get(idempotencyKey);
    if (op) this.operations.set(idempotencyKey, { ...op, status: 'pending' });
  }

  async getCached(key: string): Promise<string | null> {
    return this.cache.has(key) ? this.cache.get(key)! : null;
  }

  async setCached(key: string, value: string): Promise<void> {
    this.cache.set(key, value);
  }
}
