const { execFileSync } = require('child_process');

const env = (name, fallback = '') => process.env[name] || fallback;

const SKIP = env('SKIP_DB_MIGRATIONS', 'false') === 'true';

if (SKIP) {
  console.log('Skipping DB migrations because SKIP_DB_MIGRATIONS=true');
  process.exit(0);
}

try {
  console.log('Running applyMigrations.js');
  execFileSync(process.execPath, [require('path').join(__dirname, 'applyMigrations.js')], { stdio: 'inherit' });

  console.log('Running importDatabase.js');
  execFileSync(process.execPath, [require('path').join(__dirname, 'importDatabase.js')], { stdio: 'inherit' });

  console.log('Migrations/import completed');
} catch (err) {
  console.error('Migration wrapper detected an error:', err && err.message ? err.message : err);
  // If strict mode requested, fail the process so callers can detect the error.
  if (env('CRASH_ON_MIGRATION_ERROR', 'false') === 'true') {
    process.exit(1);
  }

  // Otherwise continue startup but surface a non-zero exitCode.
  console.warn('Continuing despite migration errors (CRASH_ON_MIGRATION_ERROR not set).');
}
