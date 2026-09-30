// Backend client. Serializes the snake_case wire contract directly.
// EXPO_PUBLIC_API_URL is injected at build time (see .env.example).
//
// Reads (price board, safety, estimates, earnings) are cached by the caller so
// the app still works with no connectivity.

import { getAccessToken, refreshAccessToken } from '../auth/session';
import { SyncOperation, SyncResponse } from '../types';

export const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface SyncApi {
  post(operations: SyncOperation[]): Promise<SyncResponse>;
}

export interface PriceBoardRow {
  material_category_id: string;
  code: string;
  name: string;
  current_price: number | null;
  avg_price: number | null;
  min_price: number | null;
  max_price: number | null;
  samples: number;
  direction: 'rising' | 'falling' | 'stable';
  icon: string;
  pct_change: number;
}

export interface EstimateResult {
  material_category_id: string;
  weight_kg: number;
  currency: string;
  price_per_kg: { avg: number; min: number; max: number };
  estimated_value: { low: number; mid: number; high: number };
  samples: number;
  region: string;
  city_specific: boolean;
  disclaimer: string;
}

export interface SafetyTopic {
  id: string;
  code: string;
  severity: 'critical' | 'high' | 'medium' | 'info';
  title: string;
  short_text: string | null;
  do_text: string | null;
  dont_text: string | null;
  audio_url: string | null;
  pictograms: { kind: 'do' | 'dont'; icon_key: string }[];
}

export interface EarningsSummary {
  total_earned: number;
  total_paid: number;
  total_pending_due: number;
  transaction_count: number;
  completed_count: number;
}

export interface EarningsItem {
  transaction_id: string;
  status: string;
  date: string;
  weight_kg: number | null;
  recycler_name: string | null;
  earned: number;
  paid: number;
  pending: number;
  state: 'paid' | 'due';
}

export interface NearbyRecycler {
  id: string;
  name: string;
  distance_km: number;
  latitude: number | null;
  longitude: number | null;
}

export interface CollectorCategory {
  id: string;
  code: string;
  name: string;
  sort_order: number;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
    message?: string,
  ) {
    super(message ?? `${path} failed: ${status}`);
    this.name = 'ApiError';
  }
}

/**
 * The token seam the API client depends on. Injected rather than imported
 * directly so tests can exercise the auth headers without a live Supabase
 * project. The production default is the real session module — it must never
 * degrade to a null-returning stub, because an unauthenticated request is
 * indistinguishable from an offline one at the UI layer.
 */
export interface AuthTokenSource {
  getAccessToken(): Promise<string | null>;
  refreshAccessToken(): Promise<string | null>;
}

export const sessionTokenSource: AuthTokenSource = { getAccessToken, refreshAccessToken };

export class ApiClient implements SyncApi {
  constructor(
    private readonly baseUrl: string = API_BASE,
    private readonly auth: AuthTokenSource = sessionTokenSource,
  ) {}

  /**
   * Every request carries a bearer token. The backend rejects unauthenticated
   * reads with 401, so omitting the header is not a graceful degradation — it
   * turns every screen into a permanent offline state.
   *
   * A 401 triggers at most one forced refresh and retry: the token may simply
   * have expired between the proactive refresh and this call. The retry is only
   * attempted when the refresh actually produced a new token — replaying the
   * request with the same rejected credentials would be a wasted round trip
   * and, against a revoked session, an unbounded hammer on the API.
   */
  private async request<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
    const token = await this.auth.getAccessToken();
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {}),
      },
    });

    if (res.status === 401 && !retried) {
      const fresh = await this.auth.refreshAccessToken();
      if (fresh) return this.request<T>(path, init, true);
    }

    if (!res.ok) throw new ApiError(res.status, path);
    return (await res.json()) as T;
  }

  async post(operations: SyncOperation[]): Promise<SyncResponse> {
    return this.request<SyncResponse>('/api/v1/sync', {
      method: 'POST',
      body: JSON.stringify({ operations }),
    });
  }

  priceBoard(city?: string, locale = 'en') {
    const q = new URLSearchParams({ locale });
    if (city) q.set('city', city);
    return this.request<{ city: string; count: number; board: PriceBoardRow[] }>(
      `/api/v1/pricing/board?${q}`,
    );
  }

  estimateValue(materialCategoryId: string, weightKg: number, city?: string) {
    const q = new URLSearchParams({
      material_category_id: materialCategoryId,
      weight_kg: String(weightKg),
    });
    if (city) q.set('city', city);
    return this.request<EstimateResult>(`/api/v1/pricing/estimate-value?${q}`);
  }

  safetyTopics(locale = 'en') {
    return this.request<{ count: number; topics: SafetyTopic[] }>(
      `/api/v1/safety/topics?locale=${locale}`,
    );
  }

  safetyForCategories(categoryIds: string[], locale = 'en') {
    const q = new URLSearchParams({ locale });
    categoryIds.forEach((c) => q.append('category_ids', c));
    return this.request<{ count: number; topics: SafetyTopic[] }>(
      `/api/v1/safety/for-categories?${q}`,
    );
  }

  earnings() {
    return this.request<{ summary: EarningsSummary; items: EarningsItem[] }>(
      '/api/v1/collectors/me/earnings',
    );
  }

  nearbyRecyclers(lat: number, lng: number, radiusKm = 50) {
    const q = new URLSearchParams({
      lat: String(lat),
      lng: String(lng),
      radius_km: String(radiusKm),
    });
    return this.request<NearbyRecycler[]>(`/api/v1/recycler/nearby?${q}`);
  }

  collectorCategories(locale = 'en') {
    return this.request<CollectorCategory[]>(
      `/api/v1/taxonomy/collector-categories?locale=${locale}`,
    );
  }

  async matches(lotId: string) {
    return this.request<unknown[]>(`/api/v1/lots/${lotId}/matches`);
  }

  matchExplanation(lotId: string, matchId: string) {
    return this.request<{
      recycler_name: string;
      score: number | null;
      factors: Record<string, { score: number; weight: number; detail?: string }>;
      transport_cost: number | null;
      net_earnings: number | null;
      in_service_area: boolean | null;
      pickup_available: boolean | null;
    }>(`/api/v1/lots/${lotId}/matches/${matchId}/explanation`);
  }

  quotes(lotId: string) {
    return this.request<
      {
        id: string;
        recycler_name: string;
        price_per_kg: number | null;
        total_price: number | null;
        status: string;
      }[]
    >(`/api/v1/lots/${lotId}/quotes`);
  }

  acceptQuote(quoteId: string) {
    return this.request<{ status: string; transaction_id: string }>(
      `/api/v1/quotes/${quoteId}/accept`,
      { method: 'POST' },
    );
  }

  createTransaction(lotId: string, body: { match_id?: string; recycler_organization_id?: string } = {}) {
    return this.request<{ id: string; status: string }>(`/api/v1/lots/${lotId}/transactions`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  transition(transactionId: string, toStatus: string) {
    return this.request<{ status: string }>(
      `/api/v1/transactions/${transactionId}/transition`,
      { method: 'POST', body: JSON.stringify({ to_status: toStatus }) },
    );
  }

  addWeight(transactionId: string, weightType: string, weightKg: number) {
    return this.request<unknown>(`/api/v1/transactions/${transactionId}/weights`, {
      method: 'POST',
      body: JSON.stringify({ weight_type: weightType, weight_kg: weightKg }),
    });
  }

  createHandover(transactionId: string) {
    return this.request<{ reference: string; status: string }>(
      `/api/v1/transactions/${transactionId}/handover`,
      { method: 'POST' },
    );
  }

  mediaUploadParams() {
    return this.request<{
      cloud_name: string;
      api_key: string;
      timestamp: number;
      signature: string;
    }>('/api/v1/media/upload-params');
  }

  attachImage(
    lotId: string,
    itemId: string,
    body: {
      cloudinary_public_id: string;
      cloudinary_url: string;
      is_primary?: boolean;
      mime_type?: string;
      width?: number;
      height?: number;
    },
  ) {
    return this.request<unknown>(
      `/api/v1/lots/${lotId}/items/${itemId}/images`,
      { method: 'POST', body: JSON.stringify(body) },
    );
  }

  classifyItem(itemId: string, imageId?: string) {
    return this.request<{
      decision_id: string;
      provider: string;
      confidence: number;
      predicted_category_id: string | null;
      suggested_action: string;
      detected_material_types: string[] | null;
      quality_flags: Record<string, unknown>;
    }>(`/api/v1/lot-items/${itemId}/classify`, {
      method: 'POST',
      body: JSON.stringify({ image_id: imageId ?? null }),
    });
  }

  confirmDecision(decisionId: string) {
    return this.request<unknown>(`/api/v1/ai-decisions/${decisionId}/confirm`, {
      method: 'POST',
    });
  }

  correctDecision(
    decisionId: string,
    correctedCategoryId: string,
    correctionType = 'category',
  ) {
    return this.request<unknown>(`/api/v1/ai-decisions/${decisionId}/correct`, {
      method: 'POST',
      body: JSON.stringify({
        corrected_category_id: correctedCategoryId,
        correction_type: correctionType,
      }),
    });
  }
}
