// Sync client: flushes the outbox to the backend and reconciles results.
// The backend is authoritative; a `replayed` result is treated as success
// (no duplicate was created).

import { SyncOperation, SyncResult } from '../types';
import { SyncQueue } from './queue';

export interface SyncApi {
  post(operations: SyncOperation[]): Promise<{ results: SyncResult[] }>;
}

export class SyncClient {
  constructor(
    private queue: SyncQueue,
    private api: SyncApi,
  ) {}

  async flush(): Promise<SyncResult[]> {
    const ops = this.queue.pending();
    if (ops.length === 0) return [];

    const { results } = await this.api.post(ops);

    for (const r of results) {
      if (r.status === 'applied' || r.status === 'replayed') {
        this.queue.markSynced(r.idempotencyKey);
      } else {
        this.queue.markFailed(r.idempotencyKey);
      }
    }
    return results;
  }
}
