'use client';

import { useCallback, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

import { api, ApiError, PriceBoardRow, RecyclerOrg, SafetyTopic } from '@/api/client';
import { useSupabaseAuth } from '@/auth/useSupabaseAuth';
import { AuthForm, AuthLoading } from '@/components/AuthForm';

const NearbyMap = dynamic(() => import('@/components/NearbyMap'), { ssr: false });

type Tab = 'prices' | 'safety' | 'recyclers' | 'incoming';

const TABS: { key: Tab; label: string }[] = [
  { key: 'prices', label: 'Price board' },
  { key: 'safety', label: 'Safety' },
  { key: 'recyclers', label: 'Recyclers' },
  { key: 'incoming', label: 'Incoming' },
];

const PUNE = { lat: 18.5204, lng: 73.8567 };

export default function Dashboard() {
  const { session, ready, signOut } = useSupabaseAuth();
  const [tab, setTab] = useState<Tab>('prices');
  const [roles, setRoles] = useState<string[]>([]);

  const [board, setBoard] = useState<PriceBoardRow[]>([]);
  const [safety, setSafety] = useState<SafetyTopic[]>([]);
  const [recyclers, setRecyclers] = useState<RecyclerOrg[]>([]);
  const [nearby, setNearby] = useState<Awaited<ReturnType<typeof api.nearby>>>([]);
  const [incoming, setIncoming] = useState<Awaited<ReturnType<typeof api.incoming>>>({
    count: 0,
    items: [],
  });
  const [qrCache, setQrCache] = useState<Record<string, { checksum: string }>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const token = session?.accessToken;

  const load = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const [me, b, s, n] = await Promise.all([
        api.me(token),
        api.priceBoard(token, 'Pune'),
        api.safetyTopics(token),
        api.nearby(token, PUNE.lat, PUNE.lng, 60),
      ]);
      setRoles(me.roles);
      setBoard(b.board);
      setSafety(s.topics);
      setNearby(n);
      // Recycler and incoming views are role-scoped; a 403 there is expected.
      if (me.roles.some((r) => ['recycler', 'super_admin', 'platform_admin'].includes(r))) {
        const [recs, inc] = await Promise.allSettled([
          api.recyclers(token),
          api.incoming(token),
        ]);
        if (recs.status === 'fulfilled') setRecyclers(recs.value);
        if (inc.status === 'fulfilled') setIncoming(inc.value);
        // Fetch verification checksums for each handover reference.
        const refs = (inc.status === 'fulfilled' ? inc.value.items : [])
          .map((t) => t.reference)
          .filter((r): r is string => Boolean(r));
        const qr = await Promise.allSettled(
          refs.map((r) => api.qr(token!, 'handover', r)),
        );
        const map: Record<string, { checksum: string }> = {};
        qr.forEach((q, i) => {
          if (q.status === 'fulfilled' && refs[i]) {
            map[refs[i]] = { checksum: q.value.checksum };
          }
        });
        setQrCache(map);
      }
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    }
  }, [token]);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  // Render nothing until auth settles, so an anonymous visitor never sees the
  // signed-in shell. (Found by browser testing on /admin.)
  if (!ready) return <AuthLoading />;

  if (!session) {
    return <AuthForm title="Kabadi Mitra" subtitle="Operations dashboard" />;
  }

  return (
    <main style={S.page}>
      <header style={S.header}>
        <h1 style={S.h1}>Kabadi Mitra</h1>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span style={S.muted}>{session?.email}</span>
          <span style={S.pill}>{roles.join(', ') || 'no roles'}</span>
          <button style={S.ghost} onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>

      {/* Buttons in a plain labelled group. A `tablist` would require full
          tab-panel semantics; this UI swaps content in place. The site header
          already owns the page's single `nav` landmark. */}
      <div role="group" aria-label="Dashboard sections" style={S.nav}>
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
        <button
          style={S.ghost}
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await api.refreshHistory(token!);
              await load();
            } finally {
              setBusy(false);
            }
          }}
        >
          Refresh prices
        </button>
      </div>

      {error ? <p style={S.err}>{error}</p> : null}

      {tab === 'prices' ? (
        <section>
          <h2 style={S.h2}>Today&rsquo;s buying rates — Pune</h2>
          <div style={S.grid}>
            {board.map((b) => (
              <div key={b.code} style={S.stat}>
                <div style={S.statLabel}>{b.name}</div>
                <div style={S.statValue}>
                  {b.current_price != null ? `₹${b.current_price}` : '—'}
                  <span style={S.muted}>/kg</span>
                </div>
                <div
                  style={{
                    color:
                      b.direction === 'rising'
                        ? '#15803d'
                        : b.direction === 'falling'
                          ? '#92400E'
                          : '#4B5563',
                    fontWeight: 700,
                  }}
                >
                  {b.direction} {b.pct_change > 0 ? '+' : ''}
                  {b.pct_change}% · {b.samples} samples
                </div>
              </div>
            ))}
          </div>
          <h2 style={S.h2}>Nearby verified recyclers</h2>
          <NearbyMap recyclers={nearby} center={[PUNE.lng, PUNE.lat]} />
          <ul>
            {nearby.map((r) => (
              <li key={r.id}>
                {r.name} — {r.distance_km} km
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {tab === 'safety' ? (
        <section>
          <h2 style={S.h2}>Safety guidance</h2>
          {safety.map((s) => (
            <div
              key={s.id}
              style={{
                ...S.card,
                borderLeft: `6px solid ${
                  s.severity === 'critical' ? '#991B1B' : '#92400E'
                }`,
              }}
            >
              <strong>{s.title}</strong>
              {s.short_text ? <p style={S.muted}>{s.short_text}</p> : null}
              {s.dont_text ? (
                <p>
                  <span style={S.bad}>NEVER:</span> {s.dont_text}
                </p>
              ) : null}
              {s.do_text ? (
                <p>
                  <span style={S.good}>DO:</span> {s.do_text}
                </p>
              ) : null}
            </div>
          ))}
        </section>
      ) : null}

      {tab === 'recyclers' ? (
        <section>
          <h2 style={S.h2}>Recyclers</h2>
          <table style={S.table}>
            <thead>
              <tr>
                <th>Name</th>
                <th>GSTIN</th>
                <th>Status</th>
                <th>Verified</th>
                <th>Expiry</th>
              </tr>
            </thead>
            <tbody>
              {recyclers.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>{r.gstin ?? '—'}</td>
                  <td>{r.status}</td>
                  <td>{r.verified ? 'yes' : 'no'}</td>
                  <td>
                    {String((r.authorization ?? {})['expiry_date'] ?? '—')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {tab === 'incoming' ? (
        <section>
          <h2 style={S.h2}>Incoming transactions</h2>
          {incoming.count === 0 ? (
            <p style={S.muted}>No transactions assigned yet.</p>
          ) : (
            <table style={S.table}>
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th>Weight (kg)</th>
                  <th>Value</th>
                  <th>QR</th>
                  <th>Confirm</th>
                </tr>
              </thead>
              <tbody>
                {incoming.items.map((t) => (
                  <tr key={t.transaction_id}>
                    <td>{t.reference ?? '—'}</td>
                    <td>{t.status}</td>
                    <td>{t.date?.slice(0, 10)}</td>
                    <td>{t.weight_kg ?? '—'}</td>
                    <td>{t.value != null ? `₹${t.value}` : '—'}</td>
                    <td>
                      {t.reference ? (
                        <code style={{ fontSize: 11 }}>{qrCache[t.reference]?.checksum ?? '···'}</code>
                      ) : ('—')}
                    </td>
                    <td>
                      {t.reference ? (
                        <button
                          style={S.ghost}
                          onClick={async () => {
                            await api.confirmHandover(token!, t.reference!);
                            load();
                          }}
                        >
                          Confirm
                        </button>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ) : null}
    </main>
  );
}

const S: Record<string, React.CSSProperties> = {
  page: { padding: 24, fontFamily: 'system-ui, sans-serif', color: '#111827' },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  h1: { fontSize: 26, margin: 0, color: '#14532d' },
  h2: { fontSize: 20, marginTop: 28 },
  muted: { color: '#4B5563', fontSize: 14 },
  card: {
    background: '#f4f6f5',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  nav: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 },
  tab: {
    padding: '8px 14px',
    borderRadius: 8,
    border: '1px solid #d1d5db',
    background: '#fff',
    cursor: 'pointer',
  },
  tabActive: {
    padding: '8px 14px',
    borderRadius: 8,
    border: '1px solid #14532d',
    background: '#dcfce7',
    color: '#14532d',
    fontWeight: 700,
    cursor: 'pointer',
  },
  button: {
    padding: '10px 16px',
    borderRadius: 8,
    border: 'none',
    background: '#14532d',
    color: '#fff',
    fontWeight: 700,
    cursor: 'pointer',
  },
  ghost: {
    padding: '8px 12px',
    borderRadius: 8,
    border: '1px solid #d1d5db',
    background: '#fff',
    cursor: 'pointer',
  },
  input: {
    padding: 10,
    borderRadius: 8,
    border: '1px solid #d1d5db',
    fontSize: 15,
  },
  pill: {
    padding: '4px 10px',
    borderRadius: 999,
    background: '#dcfce7',
    color: '#14532d',
    fontSize: 13,
    fontWeight: 700,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: 12,
  },
  stat: { background: '#f4f6f5', borderRadius: 12, padding: 14 },
  statLabel: { fontSize: 14, color: '#4B5563' },
  statValue: { fontSize: 24, fontWeight: 800, color: '#14532d' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 14 },
  err: { color: '#991B1B', fontWeight: 600 },
  warn: { color: '#92400E', fontWeight: 600 },
  good: { color: '#15803d', fontWeight: 800 },
  bad: { color: '#991B1B', fontWeight: 800 },
};
