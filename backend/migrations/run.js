// Migration runner for Kabadi Mitra (PostgreSQL + PostGIS).
// Applies backend/migrations/*.sql in filename order, tracking applied files in
// schema_migrations. Run from repo root:
//   node backend/migrations/run.js
// Requires DATABASE_URL in .env (loaded automatically) or as the first argument.

const { Client } = require('pg');
const fs = require('fs');
const path = require('path');

const MIGRATIONS_DIR = __dirname;
const ENV_PATH = path.join(__dirname, '..', '..', '.env');

try {
  process.loadEnvFile(ENV_PATH);
} catch {
  // .env optional — fall back to process env / CLI arg.
}

const connectionString = process.env.DATABASE_URL || process.argv[2];
if (!connectionString) {
  console.error('DATABASE_URL not set. Provide it via .env or as the first argument.');
  process.exit(1);
}

async function main() {
  const client = new Client({
    connectionString,
    ssl: { rejectUnauthorized: false },
  });
  await client.connect();

  await client.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version    text PRIMARY KEY,
      applied_at timestamptz NOT NULL DEFAULT now()
    );
  `);

  const files = fs
    .readdirSync(MIGRATIONS_DIR)
    .filter((f) => f.endsWith('.sql'))
    .sort();

  const { rows } = await client.query('SELECT version FROM schema_migrations');
  const applied = new Set(rows.map((r) => r.version));

  let appliedCount = 0;
  for (const file of files) {
    if (applied.has(file)) continue;
    const sql = fs.readFileSync(path.join(MIGRATIONS_DIR, file), 'utf8');
    process.stdout.write(`Applying ${file}... `);
    await client.query('BEGIN');
    try {
      await client.query(sql);
      await client.query('INSERT INTO schema_migrations(version) VALUES ($1)', [file]);
      await client.query('COMMIT');
      appliedCount += 1;
      process.stdout.write('done\n');
    } catch (err) {
      await client.query('ROLLBACK');
      process.stdout.write('FAILED\n');
      throw err;
    }
  }

  console.log(
    appliedCount === 0
      ? 'No new migrations to apply.'
      : `Applied ${appliedCount} migration(s).`,
  );
  await client.end();
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
