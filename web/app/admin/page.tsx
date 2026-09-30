'use client';

// Admin console: recycler verification workflow, dispute queue, AI review queue,
// analytics, and dataset-quality checks.

import { useCallback, useEffect, useState } from 'react';

import { api, RecyclerOrg } from '@/api/client';
import {
  adminApi,
  AnalyticsOverview,
  Dispute,
  Escalation,
  MaterialCategory,
  ValidationRun,
} from '@/api/admin';
import { useSupabaseAuth } from '@/auth/useSupabaseAuth';
import { AuthForm, AuthLoading } from '@/components/AuthForm';

type Tab = 'overview' | 'recyclers' | 'disputes' | 'review' | 'data';

const TABS: { key: Tab; label: string; roles?: string[] }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'recyclers', label: 'Recycler verification' },
  { key: 'disputes', label: 'Disputes' },
  { key: 'review', label: 'AI review' },
  { key: 'data', label: 'Data quality' },
];

const ADMIN_ROLES = ['super_admin', 'platform_admin', 'operations_admin', 'data_ai_admin', 'support'];

export default function AdminPage() {
  const { session, ready, signOut } = useSupabaseAuth();
  const [tab, setTab] = useState<Tab>('overview');
  const [roles, setRoles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [recyclers, setRecyclers] = useState<RecyclerOrg[]>([]);
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [runs, setRuns] = useState<ValidationRun[]>([]);
  const [categories, setCategories] = useState<MaterialCategory[]>([]);
  const [audioCov, setAudioCov] = useState<{ coverage: number; audio_available: number } | null>(null);

  const token = session?.accessToken;
  const isAdmin = roles.some((r) => ADMIN_ROLES.includes(r));

  const load = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const me = await api.me(token);
      setRoles(me.roles);
      const [ov, rec, dis, esc, cats] = await Promise.allSettled([
        adminApi.analytics(token),
        api.recyclers(token),
        adminApi.disputes(token),
        adminApi.escalations(token),
        adminApi.categories(token),
      ]);
      if (ov.status === 'fulfilled') setOverview(ov.value);
      if (rec.status === 'fulfilled') setRecyclers(rec.value);
      if (dis.status === 'fulfilled') setDisputes(dis.value);
      if (esc.status === 'fulfilled') setEscalations(esc.value);
      if (cats.status === 'fulfilled') setCategories(cats.value);
      if (me.roles.some((r) => ADMIN_ROLES.includes(r))) {
        const [r2, a2] = await Promise.allSettled([
          adminApi.validationRuns(token),
          adminApi.audioCoverage(token, 'hi'),
        ]);
        if (r2.status === 'fulfilled') setRuns(r2.value);
        if (a2.status === 'fulfilled') setAudioCov(a2.value);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [token]);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  // Render nothing until auth settles — otherwise an anonymous visitor briefly
  // sees the signed-in admin shell (a real bug found in browser testing).
  if (!ready) return <AuthLoading />;

  if (!session) {
    return <AuthForm title="Kabadi Mitra — Admin" subtitle="Operations console" />;
  }

  return (
    <main style={S.page}>
      <header style={S.header}>
        <h1 style={S.h1}>Kabadi Mitra — Admin</h1>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={S.pill}>{roles.join(', ') || 'no roles'}</span>
          <button style={S.ghost} onClick={signOut}>Sign out</button>
        </div>
      </header>

      {!isAdmin ? (
        <p style={S.warn}>
          You are signed in but do not hold an admin role. Admin tabs are read-only
          and write actions will be refused by the API.
        </p>
      ) : null}

      {/* Buttons in a plain group with an accessible label. A `tablist` would
          require full tab-panel semantics; this UI swaps content in place, so a
          labelled group is both valid and honest. The site header already owns
          the page's single `nav` landmark. */}
      <div role="group" aria-label="Admin sections" style={S.nav}>
        {TABS.map((t) => (
          <button
            key={t.key}
            aria-pressed={tab === t.key}
            style={tab === t.key ? S.tabActive : S.tab}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
        <button style={S.ghost} disabled={busy} onClick={load}><span style={{ fontSize: 12 }}>refresh</span></button>
      </div>

      {error ? <p style={S.err}>{error}</p> : null}

      {tab === 'overview' ? (
        <section>
          {overview ? (
            <>
              <h2 style={S.h2}>Platform</h2>
              <div style={S.grid}>
                {Object.entries(overview.counts).map(([k, v]) => (
                  <div key={k} style={S.stat}>
                    <div style={S.statLabel}>{k.replace(/_/g, ' ')}</div>
                    <div style={S.statValue}>{v}</div>
                  </div>
                ))}
              </div>
              <h2 style={S.h2}>Money</h2>
              <div style={S.grid}>
                <div style={S.stat}>
                  <div style={S.statLabel}>net earnings</div>
                  <div style={S.statValue}>₹{overview.money.net_earnings_total}</div>
                </div>
                <div style={S.stat}>
                  <div style={S.statLabel}>paid</div>
                  <div style={S.statValue}>₹{overview.money.payments_confirmed_total}</div>
                </div>
                <div style={S.stat}>
                  <div style={S.statLabel}>outstanding</div>
                  <div style={{ ...S.statValue, color: '#b45309' }}>₹{overview.money.outstanding}</div>
                </div>
                <div style={S.stat}>
                  <div style={S.statLabel}>completion rate</div>
                  <div style={S.statValue}>{overview.completion_rate}%</div>
                </div>
              </div>
              <h2 style={S.h2}>Transactions by status</h2>
              <table style={S.table}>
                <thead><tr><th>Status</th><th>Count</th></tr></thead>
                <tbody>
                  {Object.entries(overview.transactions_by_status).map(([k, v]) => (
                    <tr key={k}><td>{k}</td><td>{v}</td></tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : <p style={S.muted}>No analytics available.</p>}
        </section>
      ) : null}

      {tab === 'recyclers' ? (
        <section>
          <h2 style={S.h2}>Recycler verification</h2>
          <table style={S.table}>
            <thead>
              <tr><th>Name</th><th>GSTIN</th><th>Status</th><th>Verified</th><th>Expiry</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {recyclers.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>{r.gstin ?? '—'}</td>
                  <td style={{ color: r.verified ? '#15803d' : '#b45309', fontWeight: 700 }}>{r.status}</td>
                  <td>{r.verified ? 'yes' : 'no'}</td>
                  <td>{String((r.authorization ?? {})['expiry_date'] ?? '—')}</td>
                  <td>
                    <button
                      style={S.ghost}
                      disabled={busy}
                      onClick={async () => {
                        setBusy(true);
                        try {
                          await adminApi.setPickup(token!, r.id, { provides_pickup: true });
                          await load();
                        } finally { setBusy(false); }
                      }}
                    >
                      offer pickup
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {tab === 'disputes' ? (
        <section>
          <h2 style={S.h2}>Dispute queue ({disputes.filter((d) => d.status === 'open').length} open)</h2>
          {disputes.length === 0 ? <p style={S.muted}>No disputes.</p> : disputes.map((d) => (
            <div key={d.id} style={S.card}>
              <strong>{d.reason_code ?? 'other'}</strong> — {d.reason}
              <div style={S.muted}>
                {d.recycler_name ?? 'unknown recycler'} · {d.created_at?.slice(0, 10)} · {d.status}
              </div>
              {d.status === 'open' ? (
                <button
                  style={S.button}
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await adminApi.resolveDispute(token!, d.id, 'Resolved by platform review');
                      await load();
                    } finally { setBusy(false); }
                  }}
                >
                  Resolve
                </button>
              ) : (
                <div style={S.good}>resolved: {d.resolution}</div>
              )}
            </div>
          ))}
        </section>
      ) : null}

      {tab === 'review' ? (
        <section>
          <h2 style={S.h2}>AI review queue ({escalations.length})</h2>
          <p style={S.muted}>
            Uncertain classifications are reviewed by a recycler first, then by an
            admin. Every resolution is stored as a training candidate.
          </p>
          {escalations.length === 0 ? <p style={S.muted}>Nothing awaiting review.</p> : escalations.map((e) => (
            <div key={e.id} style={S.card}>
              <div>
                <strong>{e.item_description ?? 'unspecified item'}</strong>
                {e.weight_kg != null ? ` · ${e.weight_kg} kg` : ''}
              </div>
              <div style={S.muted}>stage: {e.stage} · {e.reason ?? 'no reason given'}</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                <select
                  style={S.input}
                  defaultValue=""
                  onChange={async (ev) => {
                    if (!ev.target.value) return;
                    setBusy(true);
                    try {
                      await adminApi.resolveEscalation(token!, e.id, ev.target.value, 'admin review');
                      await load();
                    } finally { setBusy(false); }
                  }}
                >
                  <option value="" disabled>set correct category…</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                {e.stage === 'recycler' ? (
                  <button
                    style={S.ghost}
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      try {
                        await adminApi.escalateToAdmin(token!, e.id);
                        await load();
                      } finally { setBusy(false); }
                    }}
                  >
                    escalate to admin
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </section>
      ) : null}

      {tab === 'data' ? (
        <section>
          <h2 style={S.h2}>Dataset quality</h2>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            {['price', 'recycler', 'material', 'transaction'].map((d) => (
              <button
                key={d}
                style={S.ghost}
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await adminApi.validateDataset(token!, d);
                    await load();
                  } finally { setBusy(false); }
                }}
              >
                validate {d}
              </button>
            ))}
            <button style={S.ghost} disabled={busy}
              onClick={async () => { await adminApi.refreshHistory(token!); await load(); }}>
              refresh price history
            </button>
            <button style={S.ghost} disabled={busy}
              onClick={async () => { await adminApi.refreshReliability(token!); await load(); }}>
              refresh reliability
            </button>
          </div>

          {audioCov ? (
            <p style={S.warn}>
              Safety audio coverage (hi): {audioCov.audio_available} of 10 topics (
              {Math.round(audioCov.coverage * 100)}%). Voice assets are recorded and
              uploaded separately.
            </p>
          ) : null}

          <table style={S.table}>
            <thead>
              <tr><th>When</th><th>Dataset</th><th>Status</th><th>Issues</th><th>Errors</th></tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td>{r.started_at?.slice(0, 16).replace('T', ' ')}</td>
                  <td>{r.dataset}</td>
                  <td style={{ color: r.status === 'failed' ? '#b91c1c' : r.status === 'passed' ? '#15803d' : '#b45309', fontWeight: 700 }}>
                    {r.status}
                  </td>
                  <td>{r.issues_found}</td>
                  <td>{String((r.summary as Record<string, unknown>)?.errors ?? '—')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </main>
  );
}

const S: Record<string, React.CSSProperties> = {
  page: { padding: 24, fontFamily: 'system-ui, sans-serif', color: '#111827' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  h1: { fontSize: 24, margin: 0, color: '#14532d' },
  h2: { fontSize: 19, marginTop: 26 },
  muted: { color: '#4B5563', fontSize: 14 },
  card: { background: '#f4f6f5', borderRadius: 12, padding: 14, marginBottom: 10 },
  nav: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 },
  tab: { padding: '8px 14px', borderRadius: 8, border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer' },
  tabActive: { padding: '8px 14px', borderRadius: 8, border: '1px solid #14532d', background: '#dcfce7', color: '#14532d', fontWeight: 700, cursor: 'pointer' },
  button: { padding: '8px 14px', borderRadius: 8, border: 'none', background: '#14532d', color: '#fff', fontWeight: 700, cursor: 'pointer' },
  ghost: { padding: '6px 10px', borderRadius: 8, border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer' },
  input: { padding: 8, borderRadius: 8, border: '1px solid #d1d5db', fontSize: 14 },
  pill: { padding: '4px 10px', borderRadius: 999, background: '#dcfce7', color: '#14532d', fontSize: 13, fontWeight: 700 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 },
  stat: { background: '#f4f6f5', borderRadius: 12, padding: 12 },
  statLabel: { fontSize: 13, color: '#4B5563', textTransform: 'capitalize' },
  statValue: { fontSize: 22, fontWeight: 800, color: '#14532d' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 14 },
  err: { color: '#991B1B', fontWeight: 600 },
  warn: { color: '#92400E', fontWeight: 600 },
  good: { color: '#15803d', fontWeight: 700 },
};
