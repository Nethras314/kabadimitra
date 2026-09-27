// Local SQLite schema (offline working database). The backend remains
// authoritative; these tables mirror the entities a collector edits offline.

export const SQLITE_SCHEMA = `
CREATE TABLE IF NOT EXISTS lots (
  id TEXT PRIMARY KEY,
  title TEXT,
  notes TEXT,
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
  classification_source TEXT NOT NULL DEFAULT 'collector',
  FOREIGN KEY (lot_id) REFERENCES lots(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_queue (
  idempotency_key TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0
);
`;
