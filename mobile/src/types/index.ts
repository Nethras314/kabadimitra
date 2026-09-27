// Entity and sync types shared across the mobile data layer.
// These mirror the backend /api/v1/sync contract.

export type EntityType = 'lot' | 'lot_item' | 'transaction' | 'weight' | 'payment';

export type MaterialKind = 'equipment' | 'recovered_material';

export interface Lot {
  id: string;
  title?: string;
  notes?: string;
  latitude?: number;
  longitude?: number;
  pickupAddress?: string;
  status: 'draft' | 'ready' | 'synced';
}

export interface LotItem {
  id: string;
  lotId: string;
  collectorCategoryId?: string;
  materialCategoryId?: string;
  materialSubcategoryId?: string;
  kind?: MaterialKind;
  description?: string;
  quantity: number;
  declaredWeightKg?: number;
  classificationSource: 'collector' | 'ai' | 'recycler' | 'admin';
}

export interface Weight {
  id: string;
  transactionId: string;
  weightType: 'declared' | 'pickup' | 'final';
  weightKg: number;
  source: 'collector' | 'recycler' | 'scale';
}

export interface Payment {
  id: string;
  transactionId: string;
  method: 'cash' | 'upi' | 'bank_transfer';
  amount: number;
  reference?: string;
}

export interface SyncOperation<T = unknown> {
  idempotencyKey: string;
  entityType: EntityType;
  id: string;
  payload: T;
}

export type SyncStatus = 'applied' | 'replayed' | 'error';

export interface SyncResult {
  idempotencyKey: string;
  entityId?: string | null;
  status: SyncStatus;
  error?: string | null;
}
