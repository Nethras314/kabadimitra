// Admin operations API. Extends the public dashboard client with the
// verification, dispute, escalation, analytics and dataset-quality calls.

import { api, API_BASE, ApiError } from './client';

export interface ValidationIssue {
  id: string;
  severity: 'info' | 'warning' | 'error';
  code: string;
  entity_type: string | null;
  entity_id: string | null;
  message: string;
}

export interface ValidationRun {
  id: string;
  dataset: string;
  status: 'running' | 'passed' | 'warning' | 'failed';
  rows_scanned: number;
  issues_found: number;
  summary: Record<string, unknown>;
  started_at: string;
  finished_at: string | null;
}

export interface Dispute {
  id: string;
  transaction_id: string;
  reason: string;
  reason_code: string | null;
  status: string;
  resolution: string | null;
  created_at: string;
  recycler_name: string | null;
}

export interface Escalation {
  id: string;
  decision_id: string;
  lot_item_id: string | null;
  stage: string;
  reason: string | null;
  resolution: string | null;
  created_at: string;
  item_description: string | null;
  weight_kg: number | null;
}

export interface AnalyticsOverview {
  generated_at: string;
  counts: Record<string, number>;
  money: { net_earnings_total: number; payments_confirmed_total: number; outstanding: number };
  transactions_by_status: Record<string, number>;
  completion_rate: number;
}

export interface MaterialCategory {
  id: string;
  code: string;
  name: string;
}

async function req<T>(path: string, token: string, init?: RequestInit): Promise<T> {
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
      const b = (await res.json()) as { detail?: string };
      if (b?.detail) detail = b.detail;
    } catch {
      /* non-JSON */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const adminApi = {
  analytics: (t: string) => req<AnalyticsOverview>('/api/v1/admin/analytics/overview', t),

  disputes: (t: string, status?: string) =>
    req<Dispute[]>(`/api/v1/disputes${status ? `?status=${status}` : ''}`, t),

  resolveDispute: (t: string, id: string, resolution: string, status = 'resolved') =>
    req<{ id: string; status: string }>(`/api/v1/disputes/${id}/resolve`, t, {
      method: 'POST',
      body: JSON.stringify({ resolution, status }),
    }),

  escalations: (t: string, stage?: string) =>
    req<Escalation[]>(`/api/v1/ai-escalations${stage ? `?stage=${stage}` : ''}`, t),

  resolveEscalation: (t: string, id: string, categoryId: string, note?: string) =>
    req<{ id: string; stage: string }>(`/api/v1/ai-escalations/${id}/resolve`, t, {
      method: 'POST',
      body: JSON.stringify({ category_id: categoryId, note }),
    }),

  escalateToAdmin: (t: string, id: string) =>
    req<{ id: string; stage: string }>(
      `/api/v1/ai-escalations/${id}/escalate-to-admin`,
      t,
      { method: 'POST' },
    ),

  createRecycler: (t: string, body: Record<string, unknown>) =>
    req<{ id: string; name: string; status: string; verified: boolean }>(
      '/api/v1/recycler/organizations',
      t,
      { method: 'POST', body: JSON.stringify(body) },
    ),

  setPickup: (t: string, recyclerId: string, body: Record<string, unknown>) =>
    req<unknown>(`/api/v1/admin/recyclers/${recyclerId}/pickup`, t, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  setAcceptance: (t: string, recyclerId: string, categoryId: string, accepted: boolean) =>
    req<unknown>(`/api/v1/admin/recyclers/${recyclerId}/acceptance`, t, {
      method: 'POST',
      body: JSON.stringify({ material_category_id: categoryId, is_accepted: accepted }),
    }),

  categories: (t: string) =>
    req<MaterialCategory[]>('/api/v1/admin/material-categories', t),

  validateDataset: (t: string, dataset: string) =>
    req<{ run_id: string; status: string; issues: number; errors: number; warnings: number }>(
      `/api/v1/admin/datasets/validate?dataset=${dataset}`,
      t,
      { method: 'POST' },
    ),

  validationRuns: (t: string) => req<ValidationRun[]>('/api/v1/admin/datasets/validation-runs', t),

  validationIssues: (t: string, runId: string) =>
    req<ValidationIssue[]>(`/api/v1/admin/datasets/validation-runs/${runId}/issues`, t),

  refreshHistory: (t: string) => req<{ refreshed: number }>('/api/v1/pricing/refresh-history', t, { method: 'POST' }),

  refreshReliability: (t: string) =>
    req<{ refreshed: number }>('/api/v1/recycler/reliability/refresh', t, { method: 'POST' }),

  audioCoverage: (t: string, locale: string) =>
    req<{ locale: string; total_topics: number; audio_available: number; coverage: number }>(
      `/api/v1/safety/audio-availability?locale=${locale}`,
      t,
    ),
};
