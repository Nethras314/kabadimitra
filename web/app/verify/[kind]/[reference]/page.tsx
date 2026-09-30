import type { Metadata } from 'next';

// Public record verification. Intentionally a server component: a scanner
// (often on a phone with no session, poor connectivity, or no login) must be
// able to open this from a printed QR code and get a definitive answer.

export const metadata: Metadata = {
  title: 'Verify record — Kabadi Mitra',
  description: 'Verify the authenticity of a Kabadi Mitra handover or dispute record.',
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export default async function VerifyPage({
  params,
}: {
  params: { kind: string; reference: string };
}) {
  const { kind, reference } = params;
  const valid = kind === 'handover' || kind === 'dispute';

  let record: Record<string, unknown> | null = null;
  let error: string | null = null;

  if (!valid) {
    error = 'Unknown record type.';
  } else {
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/verify/${kind}/${encodeURIComponent(reference)}`,
        { cache: 'no-store' },
      );
      if (res.status === 404) {
        error = 'No record found for this reference.';
      } else if (!res.ok) {
        error = `Verification service unavailable (${res.status}).`;
      } else {
        record = (await res.json()) as Record<string, unknown>;
      }
    } catch {
      error = 'Could not reach the verification service.';
    }
  }

  const style = {
    page: {
      padding: 24,
      fontFamily: 'system-ui, sans-serif',
      color: '#111827',
      maxWidth: 640,
      margin: '0 auto',
    } as React.CSSProperties,
    card: {
      background: '#f4f6f5',
      borderRadius: 12,
      padding: 20,
      marginTop: 16,
    } as React.CSSProperties,
    h1: { fontSize: 24, color: '#14532d', margin: 0 } as React.CSSProperties,
    row: {
      display: 'flex',
      justifyContent: 'space-between',
      paddingVertical: 8,
      borderBottom: '1px solid #e5e7eb',
    } as React.CSSProperties,
    label: { color: '#4B5563', fontSize: 14 } as React.CSSProperties,
    value: { fontWeight: 700, textAlign: 'right' } as React.CSSProperties,
    ok: { color: '#15803d', fontWeight: 800, fontSize: 18 } as React.CSSProperties,
    pending: {
      color: '#92400E',
      fontWeight: 800,
      fontSize: 18,
    } as React.CSSProperties,
    err: { color: '#991B1B', fontWeight: 700 } as React.CSSProperties,
    muted: {
      color: '#4B5563',
      fontSize: 14,
      marginTop: 12,
    } as React.CSSProperties,
    code: { fontFamily: 'ui-monospace, monospace', fontSize: 13 } as React.CSSProperties,
  };

  const confirmed = record?.state === 'confirmed';

  return (
    <main style={style.page}>
      <h1 style={style.h1}>Kabadi Mitra — Record verification</h1>

      {error ? (
        <div style={style.card}>
          <p style={style.err} role="alert">
            {error}
          </p>
          <p style={style.muted}>
            A genuine Kabadi Mitra reference always begins with a letter and
            contains only letters and digits.
          </p>
        </div>
      ) : null}

      {record ? (
        <div style={style.card}>
          <p style={confirmed ? style.ok : style.pending}>
            {confirmed
              ? '✓ Confirmed by the recycler'
              : '⧗ Awaiting recycler confirmation'}
          </p>

          <div style={style.row}>
            <span style={style.label}>Reference</span>
            <span style={{ ...style.value, ...style.code }}>
              {String(record.reference)}
            </span>
          </div>
          <div style={style.row}>
            <span style={style.label}>Type</span>
            <span style={style.value}>{String(record.kind)}</span>
          </div>
          <div style={style.row}>
            <span style={style.label}>Status</span>
            <span style={style.value}>{String(record.status)}</span>
          </div>
          {record.weight_kg != null ? (
            <div style={style.row}>
              <span style={style.label}>Weight</span>
              <span style={style.value}>{String(record.weight_kg)} kg</span>
            </div>
          ) : null}
          {record.photo_count != null ? (
            <div style={style.row}>
              <span style={style.label}>Photos</span>
              <span style={style.value}>{String(record.photo_count)}</span>
            </div>
          ) : null}
          {record.recycler_name ? (
            <div style={style.row}>
              <span style={style.label}>Recycler</span>
              <span style={style.value}>{String(record.recycler_name)}</span>
            </div>
          ) : null}
          {record.authorization_status ? (
            <div style={style.row}>
              <span style={style.label}>Authorization</span>
              <span style={style.value}>{String(record.authorization_status)}</span>
            </div>
          ) : null}
          <div style={style.row}>
            <span style={style.label}>Checksum</span>
            <span style={{ ...style.value, ...style.code }}>
              {String(record.checksum)}
            </span>
          </div>

          <p style={style.muted}>
            The checksum is derived from the reference itself, so a printed label
            cannot be altered without the check failing.
          </p>
        </div>
      ) : null}
    </main>
  );
}
