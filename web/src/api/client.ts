// Web API client. A Supabase access token is required for every call — the
// dashboard never talks to the database directly.

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

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

export interface SafetyTopic {
  id: string;
  code: string;
  severity: 'critical' | 'high' | 'medium' | 'info';
  title: string;
  short_text: string | null;
  do_text: string | null;
  dont_text: string | null;
  pictograms: { kind: 'do' | 'dont'; icon_key: string }[];
}

export interface EstimateResult {
  material_category_id: string;
  weight_kg: number;
  price_per_kg: { avg: number; min: number; max: number };
  gross_value: { low: number; mid: number; high: number };
  estimated_value: { low: number; mid: number; high: number };
  transport_cost: number;
  samples: number;
  region: string;
  city_specific: boolean;
  disclaimer: string;
}

export interface EarningsSummary {
  total_earned: number;
  total_paid: number;
  total_pending_due: number;
  transaction_count: number;
  completed_count: number;
}

export interface IncomingTransaction {
  transaction_id: string;
  reference: string | null;
  status: string;
  date: string;
  weight_kg: number | null;
  value: number | null;
  item_count: number;
}

export interface RecyclerOrg {
  id: string;
  organization_id: string;
  name: string;
  gstin: string | null;
  registration_number: string | null;
  status: string;
  verified: boolean;
  authorization: Record<string, unknown> | null;
}

export interface MatchExplanation {
  recycler_name: string;
  score: number | null;
  factors: Record<string, { score: number; weight: number; detail?: string }>;
  distance_km: number | null;
  transport_cost: number | null;
  net_earnings: number | null;
  in_service_area: boolean | null;
  pickup_available: boolean | null;
  reliability_score: number | null;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  me: (t: string) =>
    request<{ sub: string; roles: string[]; organization_id: string | null }>('/api/v1/me', t),
  priceBoard: (t: string, city?: string) =>
    request<{ count: number; board: PriceBoardRow[] }>(
      `/api/v1/pricing/board?locale=en${city ? `&city=${encodeURIComponent(city)}` : ''}`,
      t,
    ),
  safetyTopics: (t: string) =>
    request<{ count: number; topics: SafetyTopic[] }>('/api/v1/safety/topics?locale=en', t),
  earnings: (t: string) =>
    request<{ summary: EarningsSummary; items: unknown[] }>('/api/v1/collectors/me/earnings', t),
  estimate: (t: string, categoryId: string, weightKg: number, city?: string, transportKm?: number) => {
    const q = new URLSearchParams({
      material_category_id: categoryId,
      weight_kg: String(weightKg),
    });
    if (city) q.set('city', city);
    if (transportKm) q.set('transport_km', String(transportKm));
    return request<EstimateResult>(`/api/v1/pricing/estimate-value?${q}`, t);
  },
  nearby: (t: string, lat: number, lng: number, radiusKm = 50) =>
    request<
      {
        id: string;
        name: string;
        distance_km: number;
        latitude: number | null;
        longitude: number | null;
      }[]
    >(`/api/v1/recycler/nearby?lat=${lat}&lng=${lng}&radius_km=${radiusKm}`, t),
  recyclers: (t: string) => request<RecyclerOrg[]>('/api/v1/recycler/organizations', t),
  verifiedRecyclers: (t: string) => request<RecyclerOrg[]>('/api/v1/recycler/verified', t),
  incoming: (t: string) =>
    request<{ count: number; items: IncomingTransaction[] }>(
      '/api/v1/recycler/incoming-transactions',
      t,
    ),
  refreshHistory: (t: string) =>
    request<{ refreshed: number }>('/api/v1/pricing/refresh-history', t, { method: 'POST' }),
  refreshReliability: (t: string) =>
    request<{ refreshed: number }>('/api/v1/recycler/reliability/refresh', t, { method: 'POST' }),
  confirmHandover: (t: string, ref: string) =>
    request<{ status: string }>(`/api/v1/handover/${encodeURIComponent(ref)}/confirm`, t, {
      method: 'POST',
    }),
  handover: (t: string, ref: string) =>
    request<Record<string, unknown>>(`/api/v1/handover/${encodeURIComponent(ref)}`, t),
  qr: (t: string, kind: 'handover' | 'dispute', ref: string) =>
    request<{ checksum: string; verify_url: string; state: string }>(
      `/api/v1/qr/${kind}/${encodeURIComponent(ref)}`,
      t,
    ),
};
