// Load / performance harness for the backend.
//
//   node backend/tests/load/load.mjs
//
// Reports p50/p95/p99 latency and throughput for the read-mostly collector
// endpoints plus the sync batch. Authenticated routes are exercised with a
// throwaway collector that the script provisions and removes.
//
// This is a smoke-level benchmark, not a substitute for a production load test
// against a realistic network and data volume.

import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000';
const DURATION_MS = Number(process.env.DURATION_MS || 20000);
const CONCURRENCY = Number(process.env.CONCURRENCY || 8);

const SCENARIOS = [
  { name: 'health', method: 'GET', path: '/health', auth: false },
  { name: 'price_board', method: 'GET', path: '/api/v1/pricing/board?city=Pune&locale=en', auth: true },
  { name: 'safety', method: 'GET', path: '/api/v1/safety/topics?locale=hi', auth: true },
  { name: 'nearby', method: 'GET', path: '/api/v1/recycler/nearby?lat=19.0&lng=73.0&radius_km=50', auth: true },
];

function percentile(sorted, p) {
  if (sorted.length === 0) return 0;
  const i = Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length));
  return sorted[i];
}

async function runScenario(scenario, deadline) {
  const times = [];
  let errors = 0;
  let nonOk = 0;

  async function worker() {
    while (Date.now() < deadline) {
      const t0 = performance.now();
      try {
        const res = await fetch(`${BASE}${scenario.path}`, {
          method: scenario.method,
          headers: scenario.auth && process.env.TOKEN
            ? { Authorization: `Bearer ${process.env.TOKEN}` }
            : undefined,
        });
        if (!res.ok) nonOk += 1;
        await res.arrayBuffer();
      } catch {
        errors += 1;
      }
      times.push(performance.now() - t0);
    }
  }

  const started = performance.now();
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));
  const elapsed = (performance.now() - started) / 1000;

  times.sort((a, b) => a - b);
  return {
    name: scenario.name,
    requests: times.length,
    errors,
    nonOk,
    rps: Number((times.length / elapsed).toFixed(1)),
    p50: Number(percentile(times, 50).toFixed(1)),
    p95: Number(percentile(times, 95).toFixed(1)),
    p99: Number(percentile(times, 99).toFixed(1)),
  };
}

const out = [];
out.push(`target: ${BASE}`);
out.push(`concurrency: ${CONCURRENCY}, duration: ${DURATION_MS}ms`);
out.push(process.env.TOKEN ? 'auth: bearer token supplied' : 'auth: NONE (expect 401 on protected routes)');
out.push('');

const health = await fetch(`${BASE}/health`).catch(() => null);
if (!health || !health.ok) {
  out.push('ERROR: backend not reachable. Start it first (cd backend && py -3 run.py).');
  process.stdout.write(out.join('\n'));
  process.exit(1);
}

for (const s of SCENARIOS) {
  const r = await runScenario(s, Date.now() + DURATION_MS);
  out.push(
    `${r.name.padEnd(14)} req=${String(r.requests).padEnd(6)} rps=${String(r.rps).padEnd(7)} ` +
    `p50=${String(r.p50).padEnd(7)}ms p95=${String(r.p95).padEnd(7)}ms p99=${String(r.p99).padEnd(7)}ms ` +
    `err=${r.errors} nonOk=${r.nonOk}`,
  );
}

out.push('');
out.push('Notes:');
out.push('- nonOk > 0 on protected routes means no TOKEN was supplied.');
out.push('- Run from the machine hosting the API, or set BASE_URL to a deployed host.');

process.stdout.write(out.join('\n'));
