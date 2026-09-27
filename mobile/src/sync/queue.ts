// In-memory outbox queue for pending sync operations.
// A SQLite-backed adapter (src/db) persists the same shape for offline durability.

import { SyncOperation } from '../types';

type QueueStatus = 'pending' | 'synced' | 'failed';

interface QueueEntry<T = unknown> {
  op: SyncOperation<T>;
  status: QueueStatus;
  attempts: number;
}

export class SyncQueue {
  private entries: QueueEntry[] = [];

  enqueue(op: SyncOperation): void {
    this.entries.push({ op, status: 'pending', attempts: 0 });
  }

  pending(): SyncOperation[] {
    return this.entries.filter((e) => e.status === 'pending').map((e) => e.op);
  }

  markSynced(idempotencyKey: string): void {
    const e = this.entries.find((e) => e.op.idempotencyKey === idempotencyKey);
    if (e) {
      e.status = 'synced';
      e.attempts += 1;
    }
  }

  markFailed(idempotencyKey: string): void {
    const e = this.entries.find((e) => e.op.idempotencyKey === idempotencyKey);
    if (e) {
      e.status = 'failed';
      e.attempts += 1;
    }
  }

  retryFailed(): void {
    for (const e of this.entries) {
      if (e.status === 'failed') e.status = 'pending';
    }
  }

  size(): number {
    return this.entries.length;
  }
}
