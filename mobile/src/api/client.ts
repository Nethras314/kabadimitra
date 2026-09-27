// Thin fetch wrapper for the Kabadi Mitra backend.
// EXPO_PUBLIC_API_URL is injected at build time (see .env.example).

import { SyncOperation, SyncResult } from '../types';

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export class ApiClient {
  constructor(
    private baseUrl: string = BASE_URL,
    private getToken: () => string | null = () => null,
  ) {}

  private headers(): Record<string, string> {
    const token = this.getToken();
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  async postSync(operations: SyncOperation[]): Promise<{ results: SyncResult[] }> {
    const res = await fetch(`${this.baseUrl}/api/v1/sync`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify({ operations }),
    });
    if (!res.ok) throw new Error(`sync failed: ${res.status}`);
    return (await res.json()) as { results: SyncResult[] };
  }
}
