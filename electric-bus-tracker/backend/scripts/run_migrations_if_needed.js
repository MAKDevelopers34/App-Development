const { spawnSync } = require('child_process');
const path = require('path');

const cwd = __dirname;

const shouldRun = process.env.RUN_DB_MIGRATIONS === 'true' && process.env.SKIP_DB_MIGRATIONS !== 'true';

if (!shouldRun) {
  console.log('DB migrations skipped (set RUN_DB_MIGRATIONS=true and unset SKIP_DB_MIGRATIONS to run).');
  process.exit(0);
}

console.log('Running DB migrations/import scripts (CRASH_ON_MIGRATION_ERROR=true)');

const run = (script) => {
  const res = spawnSync('node', [path.join(__dirname, script)], {
    stdio: 'inherit',
    env: Object.assign({}, process.env, { CRASH_ON_MIGRATION_ERROR: 'true' }),
    cwd
  });

  if (res.error) {
    console.error(`Failed to run ${script}:`, res.error);
    process.exit(1);
  }

  if (res.status !== 0) {
    console.error(`${script} exited with code ${res.status}`);
    process.exit(res.status || 1);
  }
};

try {
  run('applyMigrations.js');
  run('importDatabase.js');
  console.log('DB migrations/import completed successfully.');
} catch (err) {
  console.error('Migration wrapper failed:', err.message || err);
  process.exit(1);
}
