// expo-sqlite implementation of LocalStore.
//
// The sync layer depends only on the LocalStore interface, so this adapter is
// swappable and the offline logic stays unit-testable under plain Node.

import * as SQLite from 'expo-sqlite';

import {
  CollectorProfile,
  Lot,
  LotItem,
  PendingOperation,
} from '../types';
import { LocalStore } from './store';

const DB_NAME = 'kabadi-mitra.db';

export class SqliteStore implements LocalStore {
  private db: SQLite.SQLiteDatabase | null = null;

  async open(): Promise<void> {
    if (this.db) return;
    this.db = await SQLite.openDatabaseAsync(DB_NAME);
    await this.db.execAsync(`
      PRAGMA journal_mode = WAL;

      CREATE TABLE IF NOT EXISTS collector_profile (
        user_id TEXT PRIMARY KEY,
        display_name TEXT,
        collector_type TEXT NOT NULL DEFAULT 'picker',
        preferred_language TEXT
      );

      CREATE TABLE IF NOT EXISTS lots (
        id TEXT PRIMARY KEY,
        title TEXT,
        notes TEXT,
        latitude REAL,
        longitude REAL,
        pickup_address TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        synced_at TEXT
      );

      CREATE TABLE IF NOT EXISTS lot_items (
        id TEXT PRIMARY KEY,
        lot_id TEXT NOT NULL,
        collector_category_id TEXT,
        material_category_id TEXT,
        material_subcategory_id TEXT,
        kind TEXT,
        description TEXT,
        quantity INTEGER NOT NULL DEFAULT 1,
        declared_weight_kg REAL,
        condition_id TEXT,
        classification_source TEXT NOT NULL DEFAULT 'collector'
      );
      CREATE INDEX IF NOT EXISTS idx_lot_items_lot ON lot_items(lot_id);

      CREATE TABLE IF NOT EXISTS operations (
        idempotency_key TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        payload TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        created_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_operations_status ON operations(status);

      -- Offline cache for read-only reference data (price board, safety, taxonomy).
      CREATE TABLE IF NOT EXISTS cache (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
    `);
  }

  private require(): SQLite.SQLiteDatabase {
    if (!this.db) throw new Error('SqliteStore.open() must be awaited first');
    return this.db;
  }

  // --- collector profile -----------------------------------------------------

  async saveCollectorProfile(p: CollectorProfile): Promise<void> {
    const db = this.require();
    await db.runAsync(
      `INSERT OR REPLACE INTO collector_profile
        (user_id, display_name, collector_type, preferred_language)
       VALUES (?, ?, ?, ?)`,
      p.user_id,
      p.display_name ?? null,
      p.collector_type ?? 'picker',
      p.preferred_locale ?? null,
    );
  }

  async getCollectorProfile(): Promise<CollectorProfile | null> {
    const db = this.require();
    const row = await db.getFirstAsync<Record<string, unknown>>(
      'SELECT * FROM collector_profile LIMIT 1',
    );
    if (!row) return null;
    return {
      user_id: row.user_id as string,
      display_name: (row.display_name as string) ?? '',
      collector_type: (row.collector_type as CollectorProfile['collector_type']) ?? 'picker',
      preferred_locale: (row.preferred_language as string) ?? 'en',
    };
  }

  // --- lots ------------------------------------------------------------------

  private static toLot(r: Record<string, unknown>): Lot {
    return {
      id: r.id as string,
      title: (r.title as string) ?? null,
      notes: (r.notes as string) ?? null,
      latitude: (r.latitude as number) ?? null,
      longitude: (r.longitude as number) ?? null,
      pickup_address: (r.pickup_address as string) ?? null,
      status: r.status as Lot['status'],
      synced_at: (r.synced_at as string) ?? null,
    };
  }

  async saveLot(lot: Lot): Promise<void> {
    const db = this.require();
    await db.runAsync(
      `INSERT OR REPLACE INTO lots
        (id, title, notes, latitude, longitude, pickup_address, status, synced_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      lot.id,
      lot.title ?? null,
      lot.notes ?? null,
      lot.latitude ?? null,
      lot.longitude ?? null,
      lot.pickup_address ?? null,
      lot.status,
      lot.synced_at ?? null,
    );
  }

  async getLot(id: string): Promise<Lot | null> {
    const db = this.require();
    const row = await db.getFirstAsync<Record<string, unknown>>(
      'SELECT * FROM lots WHERE id = ?',
      id,
    );
    return row ? SqliteStore.toLot(row) : null;
  }

  async listLots(): Promise<Lot[]> {
    const db = this.require();
    const rows = await db.getAllAsync<Record<string, unknown>>(
      'SELECT * FROM lots ORDER BY rowid DESC',
    );
    return rows.map(SqliteStore.toLot);
  }

  async updateLot(id: string, patch: Partial<Lot>): Promise<void> {
    const existing = await this.getLot(id);
    if (!existing) return;
    await this.saveLot({ ...existing, ...patch, id });
  }

  // --- lot items -------------------------------------------------------------

  async saveLotItem(i: LotItem): Promise<void> {
    const db = this.require();
    await db.runAsync(
      `INSERT OR REPLACE INTO lot_items
        (id, lot_id, collector_category_id, material_category_id,
         material_subcategory_id, kind, description, quantity,
         declared_weight_kg, condition_id, classification_source)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      i.id,
      i.lot_id,
      i.collector_category_id ?? null,
      i.material_category_id ?? null,
      i.material_subcategory_id ?? null,
      i.kind ?? null,
      i.description ?? null,
      i.quantity ?? 1,
      i.declared_weight_kg ?? null,
      i.condition_id ?? null,
      i.classification_source ?? 'collector',
    );
  }

  async listLotItems(lotId: string): Promise<LotItem[]> {
    const db = this.require();
    const rows = await db.getAllAsync<Record<string, unknown>>(
      'SELECT * FROM lot_items WHERE lot_id = ?',
      lotId,
    );
    return rows.map((r) => ({
      id: r.id as string,
      lot_id: r.lot_id as string,
      collector_category_id: (r.collector_category_id as string) ?? null,
      material_category_id: (r.material_category_id as string) ?? null,
      material_subcategory_id: (r.material_subcategory_id as string) ?? null,
      kind: (r.kind as LotItem['kind']) ?? null,
      description: (r.description as string) ?? null,
      quantity: (r.quantity as number) ?? 1,
      declared_weight_kg: (r.declared_weight_kg as number) ?? null,
      condition_id: (r.condition_id as string) ?? null,
      classification_source:
        (r.classification_source as LotItem['classification_source']) ?? 'collector',
    }));
  }

  // --- operations (outbox) ---------------------------------------------------

  private static toOp(r: Record<string, unknown>): PendingOperation {
    return {
      idempotency_key: r.idempotency_key as string,
      entity_type: r.entity_type as PendingOperation['entity_type'],
      entity_id: r.entity_id as string,
      payload: JSON.parse(r.payload as string) as Record<string, unknown>,
      status: r.status as PendingOperation['status'],
      attempts: (r.attempts as number) ?? 0,
      last_error: (r.last_error as string) ?? null,
    };
  }

  async enqueueOperation(op: PendingOperation): Promise<void> {
    const db = this.require();
    await db.runAsync(
      `INSERT OR REPLACE INTO operations
        (idempotency_key, entity_type, entity_id, payload, status, attempts, last_error, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      op.idempotency_key,
      op.entity_type,
      op.entity_id,
      JSON.stringify(op.payload),
      op.status ?? 'pending',
      op.attempts ?? 0,
      op.last_error ?? null,
      new Date().toISOString(),
    );
  }

  async getOperation(key: string): Promise<PendingOperation | null> {
    const db = this.require();
    const row = await db.getFirstAsync<Record<string, unknown>>(
      'SELECT * FROM operations WHERE idempotency_key = ?',
      key,
    );
    return row ? SqliteStore.toOp(row) : null;
  }

  async pendingOperations(): Promise<PendingOperation[]> {
    const db = this.require();
    const rows = await db.getAllAsync<Record<string, unknown>>(
      "SELECT * FROM operations WHERE status = 'pending' ORDER BY created_at",
    );
    return rows.map(SqliteStore.toOp);
  }

  async failedOperations(): Promise<PendingOperation[]> {
    const db = this.require();
    const rows = await db.getAllAsync<Record<string, unknown>>(
      "SELECT * FROM operations WHERE status = 'failed' ORDER BY created_at",
    );
    return rows.map(SqliteStore.toOp);
  }

  async syncedOperationCount(): Promise<number> {
    const db = this.require();
    const row = await db.getFirstAsync<{ n: number }>(
      "SELECT count(*) AS n FROM operations WHERE status = 'synced'",
    );
    return row?.n ?? 0;
  }

  async markOperationSynced(key: string): Promise<void> {
    const db = this.require();
    await db.runAsync(
      "UPDATE operations SET status = 'synced', last_error = NULL WHERE idempotency_key = ?",
      key,
    );
  }

  async markOperationFailed(key: string, error: string): Promise<void> {
    const db = this.require();
    await db.runAsync(
      'UPDATE operations SET status = ?, attempts = attempts + 1, last_error = ? WHERE idempotency_key = ?',
      'failed',
      error,
      key,
    );
  }

  async markOperationPending(key: string): Promise<void> {
    const db = this.require();
    await db.runAsync(
      "UPDATE operations SET status = 'pending' WHERE idempotency_key = ?",
      key,
    );
  }

  // --- cache -----------------------------------------------------------------

  async getCached(key: string): Promise<string | null> {
    const db = this.require();
    const row = await db.getFirstAsync<{ value: string }>(
      'SELECT value FROM cache WHERE key = ?',
      key,
    );
    return row?.value ?? null;
  }

  async setCached(key: string, value: string): Promise<void> {
    const db = this.require();
    await db.runAsync(
      'INSERT OR REPLACE INTO cache (key, value, updated_at) VALUES (?, ?, ?)',
      key,
      value,
      new Date().toISOString(),
    );
  }
}
