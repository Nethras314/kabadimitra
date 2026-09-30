// Provisions real, usable accounts so the application can be demonstrated and
// tested. Idempotent: re-running resets the password on existing accounts.
//
//   PROVISION_ADMIN_PASSWORD=... PROVISION_COLLECTOR_PASSWORD=... \
//     node backend/scripts/provision-accounts.mjs
//
// Passwords are read from the environment and never stored in the repository.

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '..', '..');

// `pg` is installed under backend/migrations; resolve it from there.
const require = createRequire(path.join(ROOT, 'backend', 'migrations', 'index.js'));
const { Client } = require('pg');

function loadEnv(file) {
  if (!fs.existsSync(file)) return {};
  const out = {};
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    if (!line.trim() || line.trim().startsWith('#')) continue;
    const i = line.indexOf('=');
    if (i < 0) continue;
    out[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return out;
}

const env = {
  ...loadEnv(path.join(ROOT, '.env')),
  ...loadEnv(path.join(ROOT, 'web', '.env.local')),
  ...process.env,
};

const url = env.SUPABASE_URL ?? env.NEXT_PUBLIC_SUPABASE_URL;
const serviceKey = env.SUPABASE_SECRET_KEY;
const databaseUrl = env.DATABASE_URL;

if (!url || !serviceKey || !databaseUrl) {
  console.error('Missing SUPABASE_URL / SUPABASE_SECRET_KEY / DATABASE_URL.');
  process.exit(1);
}

const ADMIN_EMAIL = env.PROVISION_ADMIN_EMAIL ?? 'admin@kabadi.local';
const COLLECTOR_EMAIL = env.PROVISION_COLLECTOR_EMAIL ?? 'collector@kabadi.local';
const ADMIN_PASSWORD = env.PROVISION_ADMIN_PASSWORD;
const COLLECTOR_PASSWORD = env.PROVISION_COLLECTOR_PASSWORD;

if (!ADMIN_PASSWORD || !COLLECTOR_PASSWORD) {
  console.error(
    'Set PROVISION_ADMIN_PASSWORD and PROVISION_COLLECTOR_PASSWORD before running.',
  );
  process.exit(1);
}

const headers = {
  apikey: serviceKey,
  Authorization: `Bearer ${serviceKey}`,
  'Content-Type': 'application/json',
};

async function upsertUser(email, password, meta) {
  const res = await fetch(`${url}/auth/v1/admin/users`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ email, password, email_confirm: true, user_metadata: meta }),
  });
  if (res.ok) return (await res.json()).id;

  const body = await res.json().catch(() => ({}));
  const msg = String(body.msg ?? body.message ?? body.error_description ?? '');
  if (/already|registered|exists|already been/i.test(msg)) {
    const list = await fetch(`${url}/auth/v1/admin/users?per_page=200`, { headers });
    const users = (await list.json().catch(() => ({}))).users ?? [];
    const found = users.find((u) => (u.email ?? '').toLowerCase() === email.toLowerCase());
    if (found) {
      const upd = await fetch(`${url}/auth/v1/admin/users/${found.id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({ password, email_confirm: true }),
      });
      if (!upd.ok) {
        console.error('  password reset failed:', upd.status, await upd.text());
        process.exit(1);
      }
      console.log(`   (existing account, password reset)`);
      return found.id;
    }
  }
  console.error('  create failed:', res.status, JSON.stringify(body));
  process.exit(1);
}

const db = new Client({ connectionString: databaseUrl, ssl: { rejectUnauthorized: false } });

async function provision(email, password, roles, meta, withCollector) {
  console.log(`\n-> ${email}  [${roles.join(', ')}]`);
  const userId = await upsertUser(email, password, meta);

  await db.query(
    `INSERT INTO users (id, email, full_name, phone, preferred_locale)
     VALUES ($1::uuid, $2, $3, $4, 'hi')
     ON CONFLICT (id) DO UPDATE
       SET full_name = COALESCE(EXCLUDED.full_name, users.full_name)`,
    [userId, email, meta.full_name ?? null, meta.phone ?? null],
  );

  for (const code of roles) {
    const r = await db.query('SELECT id::int FROM roles WHERE code = $1', [code]);
    if (r.rowCount === 0) {
      console.error(`   role '${code}' is not seeded`);
      process.exit(1);
    }
    await db.query(
      'INSERT INTO user_roles (user_id, role_id) VALUES ($1::uuid, $2) ON CONFLICT DO NOTHING',
      [userId, r.rows[0].id],
    );
  }

  if (withCollector) {
    await db.query(
      `INSERT INTO collectors (user_id, collector_type, display_name, city, state, primary_language)
       VALUES ($1::uuid, 'picker', $2, $3, 'Maharashtra', 'hi')
       ON CONFLICT (user_id) DO UPDATE SET display_name = EXCLUDED.display_name`,
      [userId, meta.full_name ?? 'Collector', meta.city ?? 'Pune'],
    );
  }

  const check = await db.query(
    `SELECT COALESCE(array_agg(r.code ORDER BY r.code), '{}') AS roles
     FROM user_roles ur JOIN roles r ON r.id = ur.role_id
     WHERE ur.user_id = $1::uuid`,
    [userId],
  );
  console.log(`   user ${userId}`);
  console.log(`   roles: ${check.rows[0].roles.join(', ')}`);
  return userId;
}

await db.connect();
console.log('Provisioning Kabadi Mitra accounts (idempotent)…');

await provision(ADMIN_EMAIL, ADMIN_PASSWORD, ['super_admin'], {
  full_name: 'Platform Admin',
  phone: '+919800000001',
}, false);

const collectorId = await provision(COLLECTOR_EMAIL, COLLECTOR_PASSWORD,
  ['collector', 'kabadiwala'], {
    full_name: 'Demo Collector',
    phone: '+919800000002',
    city: 'Pune',
  }, true);

await db.end();

console.log('\nDone. Sign in at http://localhost:3000 with:');
console.log(`  admin     ${ADMIN_EMAIL}`);
console.log(`  collector ${COLLECTOR_EMAIL}`);
console.log(`\nCollector user id (grant recycler role for that journey): ${collectorId}`);
