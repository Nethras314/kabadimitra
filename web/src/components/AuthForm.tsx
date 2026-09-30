'use client';

// Sign-in / sign-up form shared by the dashboard and the admin console.
//
// Renders nothing until auth has settled, so an anonymous visitor never sees a
// brief flash of the signed-in shell.

import { useState } from 'react';

import { useSupabaseAuth } from '@/auth/useSupabaseAuth';

const style: Record<string, React.CSSProperties> = {
  page: { padding: 24, fontFamily: 'system-ui, sans-serif', color: '#111827' },
  card: { background: '#f4f6f5', borderRadius: 12, padding: 16, maxWidth: 420 },
  h1: { fontSize: 24, margin: 0, color: '#14532d' },
  muted: { color: '#6b7280', fontSize: 14 },
  input: {
    padding: 10,
    borderRadius: 8,
    border: '1px solid #d1d5db',
    fontSize: 15,
    width: '100%',
    boxSizing: 'border-box',
  },
  button: {
    padding: '10px 16px',
    borderRadius: 8,
    border: 'none',
    background: '#14532d',
    color: '#fff',
    fontWeight: 700,
    cursor: 'pointer',
    width: '100%',
  },
  ghost: {
    padding: '8px',
    border: 'none',
    background: 'transparent',
    color: '#14532d',
    cursor: 'pointer',
    textDecoration: 'underline',
    width: '100%',
  },
  err: { color: '#b91c1c', fontWeight: 600, fontSize: 14 },
  ok: { color: '#15803d', fontWeight: 600, fontSize: 14 },
  warn: { color: '#b45309', fontWeight: 600 },
};

export function AuthForm({ title, subtitle }: { title: string; subtitle: string }) {
  const { signIn, signUp, configured } = useSupabaseAuth();
  const [mode, setMode] = useState<'in' | 'up'>('in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    setBusy(true);
    try {
      if (mode === 'in') {
        await signIn(email, password);
      } else {
        const { needsConfirmation } = await signUp(email, password, {
          fullName: fullName || undefined,
          phone: phone || undefined,
        });
        setMsg(
          needsConfirmation
            ? 'Account created. Check your email to confirm, then sign in.'
            : 'Account created. You are signed in.',
        );
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={style.page}>
      <div style={style.card}>
        <h1 style={style.h1}>{title}</h1>
        <p style={style.muted}>{subtitle}</p>
        {!configured ? (
          <p style={style.warn}>
            Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and
            NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.
          </p>
        ) : null}

        <form onSubmit={submit} style={{ display: 'grid', gap: 10 }}>
          {mode === 'up' ? (
            <>
              <input
                style={style.input}
                placeholder="Full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
              />
              <input
                style={style.input}
                placeholder="Phone (optional)"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                autoComplete="tel"
              />
            </>
          ) : null}
          <input
            style={style.input}
            placeholder="Email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <input
            style={style.input}
            placeholder="Password"
            type="password"
            required
            minLength={mode === 'up' ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'up' ? 'new-password' : 'current-password'}
          />
          <button style={style.button} type="submit" disabled={busy}>
            {busy ? 'Please wait…' : mode === 'in' ? 'Sign in' : 'Create account'}
          </button>
          {msg ? <p style={style.ok}>{msg}</p> : null}
          {err ? <p style={style.err}>{err}</p> : null}
        </form>

        <button
          style={style.ghost}
          type="button"
          onClick={() => {
            setMode(mode === 'in' ? 'up' : 'in');
            setErr(null);
            setMsg(null);
          }}
        >
          {mode === 'in' ? 'No account? Create one' : 'Already registered? Sign in'}
        </button>
      </div>
    </main>
  );
}

/** Shown while Supabase resolves a session. Renders no authenticated shell. */
export function AuthLoading() {
  return (
    <main style={style.page}>
      <p style={style.muted}>Checking sign-in…</p>
    </main>
  );
}
