// Local SQLite schema (offline working database). The backend remains
// authoritative; these tables mirror the entities a collector works with
// offline plus the outbox (pending_operations) and read-only cache tables.

export const SQLITE_SCHEMA = `
CREATE TABLE IF NOT EXISTS collector_profile (
  user_id          TEXT PRIMARY KEY,
  collector_type   TEXT NOT NULL CHECK (collector_type IN ('picker','kabadiwala')),
  display_name     TEXT NOT NULL,
  preferred_locale TEXT NOT NULL DEFAULT 'en'
);

CREATE TABLE IF NOT EXISTS materials (
  id            TEXT PRIMARY KEY,
  code          TEXT NOT NULL,
  name          TEXT NOT NULL,
  kind          TEXT NOT NULL,
  category_type TEXT NOT NULL DEFAULT 'collector',
  sort_order    INTEGER NOT NULL DEFAULT 0,
  updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS lots (
  id             TEXT PRIMARY KEY,
  title          TEXT,
  notes          TEXT,
  latitude       REAL,
  longitude      REAL,
  pickup_address TEXT,
  status         TEXT NOT NULL DEFAULT 'draft',
  synced_at      TEXT
);

CREATE TABLE IF NOT EXISTS lot_items (
  id                      TEXT PRIMARY KEY,
  lot_id                  TEXT NOT NULL,
  collector_category_id   TEXT,
  material_category_id    TEXT,
  material_subcategory_id TEXT,
  kind                    TEXT,
  description             TEXT,
  quantity                INTEGER NOT NULL DEFAULT 1,
  declared_weight_kg      REAL,
  condition_id            TEXT,
  classification_source   TEXT NOT NULL DEFAULT 'collector',
  FOREIGN KEY (lot_id) REFERENCES lots(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lot_images (
  id                   TEXT PRIMARY KEY,
  lot_id               TEXT NOT NULL,
  lot_item_id          TEXT,
  cloudinary_public_id TEXT,
  cloudinary_url       TEXT,
  image_kind           TEXT NOT NULL DEFAULT 'capture',
  is_primary           INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (lot_id) REFERENCES lots(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS weights (
  id             TEXT PRIMARY KEY,
  transaction_id TEXT NOT NULL,
  weight_type    TEXT NOT NULL CHECK (weight_type IN ('declared','pickup','final')),
  weight_kg      REAL NOT NULL,
  source         TEXT NOT NULL DEFAULT 'collector'
);

CREATE TABLE IF NOT EXISTS cached_prices (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS safety_content (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS pending_operations (
  idempotency_key TEXT PRIMARY KEY,
  entity_type     TEXT NOT NULL,
  entity_id       TEXT NOT NULL,
  payload         TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
  attempts        INTEGER NOT NULL DEFAULT 0,
  last_error      TEXT,
  created_at      TEXT
);
`;
