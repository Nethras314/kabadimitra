// Regression tests for the authentication defect.
//
// The original client took an optional `getToken` callback that defaulted to
// `() => null`, and the app constructed it without one. Every request therefore
// went out unauthenticated, every read returned 401, and each screen silently
// fell back to its offline banner. Nothing failed loudly, so the defect was
// invisible until a collector actually tried to use the app.
//
// These tests pin the two properties that matter: the bearer header is always
// sent when a token exists, and a 401 triggers exactly one refresh-and-retry
// rather than an unbounded loop against a revoked session.

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { ApiClient, ApiError, sessionTokenSource, type AuthTokenSource } from './client';

/** A controllable stand-in for the Supabase session module. */
class FakeAuth implements AuthTokenSource {
  token: string | null = 'valid-token';
  refreshSucceeds = true;
  refreshCalls = 0;
  getCalls = 0;

  async getAccessToken(): Promise<string | null> {
    this.getCalls += 1;
    return this.token;
  }

  async refreshAccessToken(): Promise<string | null> {
    this.refreshCalls += 1;
    if (!this.refreshSucceeds) return null;
    this.token = 'refreshed-token';
    return this.token;
  }
}

interface Captured {
  url: string;
  headers: Record<string, string>;
}

function stubFetch(
  responses: { status: number; body: unknown }[],
): { calls: Captured[]; restore: () => void } {
  const calls: Captured[] = [];
  const original = globalThis.fetch;
  let i = 0;

  globalThis.fetch = (async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), headers: (init?.headers ?? {}) as Record<string, string> });
    const spec = responses[Math.min(i, responses.length - 1)];
    i += 1;
    return {
      ok: spec.status >= 200 && spec.status < 300,
      status: spec.status,
      json: async () => spec.body,
    } as Response;
  }) as typeof fetch;

  return { calls, restore: () => { globalThis.fetch = original; } };
}

test('sends the bearer token when a session exists', async () => {
  const auth = new FakeAuth();
  const { calls, restore } = stubFetch([{ status: 200, body: { board: [] } }]);
  try {
    await new ApiClient('http://api.test', auth).priceBoard('Pune', 'en');
    assert.equal(calls.length, 1);
    assert.equal(calls[0].headers.Authorization, 'Bearer valid-token');
  } finally {
    restore();
  }
});

test('a 401 triggers exactly one refresh and retry with the new token', async () => {
  const auth = new FakeAuth();
  auth.token = 'stale-token';

  const { calls, restore } = stubFetch([
    { status: 401, body: {} },
    { status: 200, body: { summary: {}, items: [] } },
  ]);
  try {
    await new ApiClient('http://api.test', auth).earnings();
    assert.equal(auth.refreshCalls, 1, 'should refresh exactly once');
    assert.equal(calls.length, 2, 'should make exactly two attempts');
    assert.equal(calls[0].headers.Authorization, 'Bearer stale-token');
    assert.equal(calls[1].headers.Authorization, 'Bearer refreshed-token');
  } finally {
    restore();
  }
});

test('does not retry when the refresh fails on a revoked session', async () => {
  const auth = new FakeAuth();
  auth.token = 'revoked-token';
  auth.refreshSucceeds = false;

  const { calls, restore } = stubFetch([{ status: 401, body: {} }]);
  try {
    await assert.rejects(
      () => new ApiClient('http://api.test', auth).earnings(),
      (err: unknown) => {
        assert.ok(err instanceof ApiError, 'should surface a typed ApiError');
        assert.equal((err as ApiError).status, 401);
        return true;
      },
    );
    assert.equal(auth.refreshCalls, 1, 'should attempt exactly one refresh');
    // No retry: the refresh produced no new token, so replaying the request
    // with the same rejected credentials would be a wasted round trip and,
    // against a revoked session, an unbounded hammer on the API.
    assert.equal(calls.length, 1, 'must not replay with a rejected token');
  } finally {
    restore();
  }
});

test('retries at most once even when the refreshed token is also rejected', async () => {
  const auth = new FakeAuth();
  auth.token = 'stale-token';

  // Both attempts 401: the refresh "succeeded" but the new token is still bad.
  const { calls, restore } = stubFetch([{ status: 401, body: {} }]);
  try {
    await assert.rejects(() => new ApiClient('http://api.test', auth).earnings());
    assert.equal(calls.length, 2, 'original attempt plus one retry, then stop');
    assert.equal(auth.refreshCalls, 1, 'must not refresh a second time');
  } finally {
    restore();
  }
});

test('omits the header when signed out rather than sending a stale one', async () => {
  const auth = new FakeAuth();
  auth.token = null;

  const { calls, restore } = stubFetch([{ status: 401, body: {} }]);
  try {
    await assert.rejects(() => new ApiClient('http://api.test', auth).earnings());
    assert.equal(calls[0].headers.Authorization, undefined);
  } finally {
    restore();
  }
});

test('a non-401 failure is not retried', async () => {
  const auth = new FakeAuth();
  const { calls, restore } = stubFetch([{ status: 500, body: {} }]);
  try {
    await assert.rejects(() => new ApiClient('http://api.test', auth).earnings());
    assert.equal(calls.length, 1, 'a server error is not a token problem');
    assert.equal(auth.refreshCalls, 0);
  } finally {
    restore();
  }
});

test('a network failure surfaces without an auth retry', async () => {
  const auth = new FakeAuth();
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = (async () => {
    calls += 1;
    throw new Error('Network request failed');
  }) as typeof fetch;
  try {
    await assert.rejects(() => new ApiClient('http://api.test', auth).earnings());
    assert.equal(calls, 1);
    assert.equal(auth.refreshCalls, 0, 'offline is not a token problem');
  } finally {
    globalThis.fetch = original;
  }
});

test('the production default is the real session, not a null stub', async () => {
  // Guards the original defect at its root: a client built with no explicit
  // auth argument must delegate to the Supabase-backed session, so
  // `getAccessToken` reaches the real session module rather than a stub that
  // silently returns null.
  const client = new ApiClient('http://api.test');
  const auth = (client as unknown as { auth: AuthTokenSource }).auth;
  assert.equal(auth, sessionTokenSource);
  assert.equal(typeof auth.getAccessToken, 'function');
  assert.equal(typeof auth.refreshAccessToken, 'function');
});
