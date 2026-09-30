// Supabase session management for the mobile client.
//
// Design constraints:
//  - The API client needs a token synchronously. Awaiting a network refresh
//    inside the request path would stall every screen behind one round trip, so
//    the access token is cached in memory and refreshed proactively, a minute
//    before expiry.
//  - Only the access token is cached. The refresh token lives in the Supabase
//    client, which persists it via AsyncStorage and rotates it on refresh.
//  - `getAccessToken` is the single seam the API client depends on. If it returns
//    null the API returns 401 and there is nothing to retry, so the app must
//    gate on the session rather than optimistically firing requests.

import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

// EXPO_PUBLIC_* names are inlined into the bundle at build time by Expo.
//
// The Supabase key is accepted under two names. `..._PUBLISHABLE_KEY` is the
// current Supabase convention and matches the web client; `..._SUPABASE_KEY`
// is the older name that appears in existing .env files. Both carry the same
// publishable/anon key, so either is safe to expose in a client bundle — the
// service-role key is NOT, and must never be given an EXPO_PUBLIC_ prefix.
const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL ?? '';
const SUPABASE_ANON_KEY =
  process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY ??
  process.env.EXPO_PUBLIC_SUPABASE_KEY ??
  '';

export const authConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

// Refresh this long before the token actually expires, so a request started
// right at the boundary still carries a valid token.
const REFRESH_MARGIN_MS = 60_000;

export interface AuthUser {
  id: string;
  email: string | null;
}

let client: SupabaseClient | null = null;

function getClient(): SupabaseClient {
  if (!client) {
    client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        // React Native has no browser storage events; Supabase's default
        // detection emits a warning and can skip legitimate cross-tab
        // synchronisation on native.
        detectSessionInUrl: false,
      },
    });
  }
  return client;
}

let cachedToken: string | null = null;
let expiresAt = 0;
// De-duplicates concurrent refreshes: several screens mounting at once share
// one in-flight token request rather than each triggering their own.
let inFlightRefresh: Promise<string | null> | null = null;

function applySession(session: { access_token: string; expires_at?: number } | null): void {
  if (session) {
    cachedToken = session.access_token;
    // Supabase omits expires_at in some refresh paths; treat that as "valid for
    // an hour" rather than "already expired", which would loop forever.
    expiresAt = session.expires_at ? session.expires_at * 1000 : Date.now() + 3_600_000;
  } else {
    cachedToken = null;
    expiresAt = 0;
  }
}

/**
 * Return a usable access token, refreshing proactively when the cached one is
 * expired or about to expire. Returns null when signed out or when the refresh
 * fails, which callers must treat as "not authenticated" rather than retrying.
 */
export async function getAccessToken(): Promise<string | null> {
  if (!authConfigured) return null;

  if (cachedToken && Date.now() < expiresAt - REFRESH_MARGIN_MS) {
    return cachedToken;
  }

  if (!inFlightRefresh) {
    inFlightRefresh = (async () => {
      try {
        // Read the stored session to learn the real expiry rather than trusting
        // our own cache, then refresh explicitly. Relying on getSession() alone
        // can hand back the same already-expired token, which would make every
        // request 401 and turn the app into a permanent offline state.
        const { data: stored } = await getClient().auth.getSession();
        if (stored.session) applySession(stored.session);

        if (cachedToken && Date.now() < expiresAt - REFRESH_MARGIN_MS) {
          return cachedToken;
        }

        const { data, error } = await getClient().auth.refreshSession();
        if (error || !data.session) {
          applySession(null);
          return null;
        }
        applySession(data.session);
        return cachedToken;
      } catch {
        applySession(null);
        return null;
      } finally {
        inFlightRefresh = null;
      }
    })();
  }

  return inFlightRefresh;
}

/** Force a token refresh, bypassing the cache. Used to recover from a 401. */
export async function refreshAccessToken(): Promise<string | null> {
  if (!authConfigured) return null;
  try {
    const { data, error } = await getClient().auth.refreshSession();
    if (error || !data.session) {
      applySession(null);
      return null;
    }
    applySession(data.session);
    return cachedToken;
  } catch {
    applySession(null);
    return null;
  }
}

function currentUser(session: { user: { id: string; email?: string | null } } | null): AuthUser | null {
  if (!session?.user) return null;
  return { id: session.user.id, email: session.user.email ?? null };
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  if (!authConfigured) return null;
  const { data } = await getClient().auth.getSession();
  applySession(data.session);
  return currentUser(data.session);
}

export async function signIn(email: string, password: string): Promise<AuthUser> {
  if (!authConfigured) throw new Error('Supabase is not configured');
  const { data, error } = await getClient().auth.signInWithPassword({ email, password });
  if (error) throw error;
  if (!data.session) throw new Error('No session returned');
  applySession(data.session);
  return currentUser(data.session)!;
}

/**
 * Register a new collector. Supabase may require email confirmation, in which
 * case no session is returned and the account cannot sign in until confirmed.
 */
export async function signUp(
  email: string,
  password: string,
  meta: { fullName?: string; phone?: string } = {},
): Promise<{ user: AuthUser | null; needsConfirmation: boolean }> {
  if (!authConfigured) throw new Error('Supabase is not configured');
  const { data, error } = await getClient().auth.signUp({
    email,
    password,
    options: { data: meta },
  });
  if (error) throw error;
  applySession(data.session);
  const user = currentUser(data.session);
  return { user, needsConfirmation: !data.session };
}

export async function signOut(): Promise<void> {
  if (!authConfigured) {
    applySession(null);
    return;
  }
  try {
    await getClient().auth.signOut();
  } finally {
    applySession(null);
    await AsyncStorage.removeItem(KEY_LOCALE);
  }
}

export function onAuthStateChange(
  handler: (user: AuthUser | null) => void,
): () => void {
  if (!authConfigured) {
    // No client, so no events; report the signed-out state once so callers do
    // not wait forever for a first event.
    handler(null);
    return () => {};
  }

  const { data } = getClient().auth.onAuthStateChange((_event, session) => {
    applySession(session);
    handler(currentUser(session));
  });

  return () => data.subscription.unsubscribe();
}

// --- Locale preference -------------------------------------------------------
// The chosen language is a device-local setting, not user data, so it is kept
// in AsyncStorage. Previously it reset to the default on every cold start.

const KEY_LOCALE = 'kabadi-mitra:locale';

export async function loadLocale(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(KEY_LOCALE);
  } catch {
    return null;
  }
}

export async function saveLocale(locale: string): Promise<void> {
  try {
    await AsyncStorage.setItem(KEY_LOCALE, locale);
  } catch {
    // Preference persistence is best-effort; the in-memory value still applies.
  }
}
