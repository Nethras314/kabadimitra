// Offline operation queue (outbox), backed by the LocalStore's pending
// operations table. The queue is the durable staging area between local work
// and the authoritative backend.

import { EntityType, PendingOperation } from '../types';
import { LocalStore } from '../db/store';

export class SyncQueue {
  constructor(private readonly store: LocalStore) {}

  async enqueue(
    entityType: EntityType,
    entityId: string,
    idempotencyKey: string,
    payload: Record<string, unknown>,
  ): Promise<void> {
    await this.store.enqueueOperation({
      idempotency_key: idempotencyKey,
      entity_type: entityType,
      entity_id: entityId,
      payload,
      status: 'pending',
      attempts: 0,
      last_error: null,
    });
  }

  async pending(): Promise<PendingOperation[]> {
    return this.store.pendingOperations();
  }

  async markSynced(idempotencyKey: string): Promise<void> {
    await this.store.markOperationSynced(idempotencyKey);
  }

  async markFailed(idempotencyKey: string, error: string): Promise<void> {
    await this.store.markOperationFailed(idempotencyKey, error);
  }

  /** Re-mark retriable failed operations as pending. Returns the retried count. */
  async retryFailed(shouldRetry: (op: PendingOperation) => boolean): Promise<number> {
    const failed = await this.store.failedOperations();
    let retried = 0;
    for (const op of failed) {
      if (shouldRetry(op)) {
        await this.store.markOperationPending(op.idempotency_key);
        retried += 1;
      }
    }
    return retried;
  }
}
