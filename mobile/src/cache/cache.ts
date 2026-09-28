// Read-only local cache (materials, prices, safety). Values are JSON-encoded
// strings persisted by the LocalStore and read back when offline.

import { LocalStore } from '../db/store';

export const CACHE_KEYS = {
  materials: 'materials',
  price: (materialCategoryId: string) => `price:${materialCategoryId}`,
  safety: 'safety',
} as const;

export class LocalCache {
  constructor(private readonly store: LocalStore) {}

  async getJSON<T>(key: string): Promise<T | null> {
    const raw = await this.store.getCached(key);
    if (raw === null) return null;
    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  }

  async setJSON(key: string, value: unknown): Promise<void> {
    await this.store.setCached(key, JSON.stringify(value));
  }

  getMaterials<T>(): Promise<T | null> {
    return this.getJSON<T>(CACHE_KEYS.materials);
  }

  setMaterials(value: unknown): Promise<void> {
    return this.setJSON(CACHE_KEYS.materials, value);
  }

  getPrice<T>(materialCategoryId: string): Promise<T | null> {
    return this.getJSON<T>(CACHE_KEYS.price(materialCategoryId));
  }

  setPrice(materialCategoryId: string, value: unknown): Promise<void> {
    return this.setJSON(CACHE_KEYS.price(materialCategoryId), value);
  }

  getSafety<T>(): Promise<T | null> {
    return this.getJSON<T>(CACHE_KEYS.safety);
  }

  setSafety(value: unknown): Promise<void> {
    return this.setJSON(CACHE_KEYS.safety, value);
  }
}
