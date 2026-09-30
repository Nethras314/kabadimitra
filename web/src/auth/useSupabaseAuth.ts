'use client';

// Supabase Auth session hook for the dashboard.
//
// The session token is held in React state only; nothing sensitive is written to
// localStorage. `ready` stays false until Supabase has actually resolved a
// session, so callers can avoid rendering an authenticated shell to a visitor
// who has not signed in yet.

import { useCallback, useEffect, useState } from 'react';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? '';
const SUPABASE_ANON = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? '';

type SupabaseClient = {
  auth: {
    getSession(): Promise<{ data: { session: AuthSession | null } }>;
    onAuthStateChange(
      cb: (event: string, session: AuthSession | null) => void,
    ): { data: { subscription: { unsubscribe(): void } } };
    signInWithPassword(c: { email: string; password: string }): Promise<AuthResult>;
    signUp(c: {
      email: string;
      password: string;
      options?: { data?: Record<string, unknown> };
    }): Promise<AuthResult>;
    signOut(): Promise<{ error: unknown }>;
  };
};

interface AuthSession {
  access_token: string;
  user: { id: string; email?: string };
}

interface AuthResult {
  data: { session: AuthSession | null };
  error: { message: string } | null;
}

// One client per page. Creating a new Supabase client on every render (or in
// every hook instance) triggers "Multiple GoTrueClient instances detected" and
// can produce undefined behaviour from concurrent token refreshes.
let clientPromise: Promise<SupabaseClient> | null = null;

function getClient(): Promise<SupabaseClient> {
  if (!clientPromise) {
    clientPromise = import('@supabase/supabase-js').then(({ createClient }) =>
      createClient(SUPABASE_URL, SUPABASE_ANON, {
        auth: { persistSession: true, autoRefreshToken: true },
      }) as unknown as SupabaseClient,
    );
  }
  return clientPromise;
}

export interface Session {
  accessToken: string;
  userId: string;
  email: string | null;
}

export type AuthState = 'loading' | 'authenticated' | 'anonymous';

export function useSupabaseAuth() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const configured = Boolean(SUPABASE_URL && SUPABASE_ANON);

  useEffect(() => {
    if (!configured) {
      // Without configuration there can be no session; report ready so the UI
      // can explain the problem rather than spin forever.
      setReady(true);
      return;
    }
    let cancelled = false;

    (async () => {
      try {
        const client = await getClient();
        const { data } = await client.auth.getSession();
        if (cancelled) return;
        if (data.session) {
          setSession({
            accessToken: data.session.access_token,
            userId: data.session.user.id,
            email: data.session.user.email ?? null,
          });
        }
        client.auth.onAuthStateChange((_e, s) => {
          if (cancelled) return;
          setSession(
            s
              ? { accessToken: s.access_token, userId: s.user.id, email: s.user.email ?? null }
              : null,
          );
        });
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'auth unavailable');
        }
      } finally {
        // Always settle, even on failure, so the UI never hangs on "loading".
        if (!cancelled) setReady(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (!configured) throw new Error('Supabase is not configured');
      const client = await getClient();
      const { data, error: err } = await client.auth.signInWithPassword({ email, password });
      if (err) throw err;
      if (data.session) {
        setSession({
          accessToken: data.session.access_token,
          userId: data.session.user.id,
          email: data.session.user.email ?? null,
        });
      }
    },
    [configured],
  );

  /**
   * Self-service registration. Supabase may require email confirmation; when
   * `session` is null the account exists but cannot sign in until confirmed.
   */
  const signUp = useCallback(
    async (
      email: string,
      password: string,
      meta: { fullName?: string; phone?: string } = {},
    ): Promise<{ needsConfirmation: boolean }> => {
      if (!configured) throw new Error('Supabase is not configured');
      const client = await getClient();
      const { data, error: err } = await client.auth.signUp({
        email,
        password,
        options: { data: meta },
      });
      if (err) throw err;
      if (data.session) {
        setSession({
          accessToken: data.session.access_token,
          userId: data.session.user.id,
          email: data.session.user.email ?? null,
        });
        return { needsConfirmation: false };
      }
      return { needsConfirmation: true };
    },
    [configured],
  );

  const signOut = useCallback(async () => {
    if (configured) {
      const client = await getClient();
      await client.auth.signOut();
    }
    setSession(null);
  }, [configured]);

  const state: AuthState = !ready ? 'loading' : session ? 'authenticated' : 'anonymous';

  return { session, ready, error, signIn, signUp, signOut, configured, state };
}
