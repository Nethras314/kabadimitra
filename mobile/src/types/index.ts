// Offline-first data-layer types.
//
// The sync contract mirrors the backend `/api/v1/sync` wire format (snake_case)
// exactly, so no key-mapping layer is required at the transport boundary
// (ADR-0029).

// --- Wire contract (matches backend /api/v1/sync) ---

export type EntityType = 'lot' | 'lot_item' | 'transaction' | 'weight' | 'payment';

export type SyncResultStatus = 'applied' | 'replayed' | 'error';

export interface SyncOperation<T = Record<string, unknown>> {
  idempotency_key: string;
  entity_type: EntityType;
  id: string;
  payload: T;
}

export interface SyncResult {
  idempotency_key: string;
  entity_id: string | null;
  status: SyncResultStatus;
  error?: string | null;
}

export interface SyncResponse {
  results: SyncResult[];
}

// --- Local domain entities (snake_case, mirror SQLite + backend payloads) ---

export type LotStatus = 'draft' | 'ready' | 'synced';

export interface Lot {
  id: string;
  title?: string | null;
  notes?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  pickup_address?: string | null;
  status: LotStatus;
  synced_at?: string | null;
}

export type MaterialKind = 'equipment' | 'recovered_material';
export type ClassificationSource = 'collector' | 'ai' | 'recycler' | 'admin';

export interface LotItem {
  id: string;
  lot_id: string;
  collector_category_id?: string | null;
  material_category_id?: string | null;
  material_subcategory_id?: string | null;
  kind?: MaterialKind | null;
  description?: string | null;
  quantity: number;
  declared_weight_kg?: number | null;
  condition_id?: string | null;
  classification_source: ClassificationSource;
}

export type ImageKind = 'capture' | 'quality_check' | 'handover' | 'other';

export interface LotImage {
  id: string;
  lot_id: string;
  lot_item_id?: string | null;
  cloudinary_public_id?: string | null;
  cloudinary_url?: string | null;
  image_kind: ImageKind;
  is_primary: boolean;
}

export type WeightType = 'declared' | 'pickup' | 'final';
export type WeightSource = 'collector' | 'recycler' | 'scale';

export interface WeightRecord {
  id: string;
  transaction_id: string;
  weight_type: WeightType;
  weight_kg: number;
  source: WeightSource;
}

export interface CollectorProfile {
  user_id: string;
  collector_type: 'picker' | 'kabadiwala';
  display_name: string;
  preferred_locale: string;
}

// --- Pending operations (offline outbox) ---

export type OperationStatus = 'pending' | 'synced' | 'failed';

export interface PendingOperation {
  idempotency_key: string;
  entity_type: EntityType;
  entity_id: string;
  payload: Record<string, unknown>;
  status: OperationStatus;
  attempts: number;
  last_error?: string | null;
}

export type ConnectivityState = 'online' | 'offline';

export interface SyncStatusSummary {
  connectivity: ConnectivityState;
  pending: number;
  synced: number;
  failed: number;
}
