// Backend sync client. Serializes the snake_case wire contract directly.
// EXPO_PUBLIC_API_URL is injected at build time (see .env.example).

import { SyncOperation, SyncResponse } from '../types';

export interface SyncApi {
  post(operations: SyncOperation[]): Promise<SyncResponse>;
}

export class ApiClient implements SyncApi {
  constructor(
    private readonly baseUrl: string = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000',
    private readonly getToken: () => string | null = () => null,
  ) {}

  async post(operations: SyncOperation[]): Promise<SyncResponse> {
    const token = this.getToken();
    const res = await fetch(`${this.baseUrl}/api/v1/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ operations }),
    });
    if (!res.ok) throw new Error(`sync failed: ${res.status}`);
    return (await res.json()) as SyncResponse;
  }
}
