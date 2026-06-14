const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

const env = (name, fallback = '') => process.env[name] || fallback;

const requiredProcedures = [
  'sp_get_user_for_login',
  'sp_record_login_failure',
  'sp_record_login_success',
  'sp_get_user_profile',
  'sp_change_password',
  'sp_save_reset_code',
  'sp_reset_password',
  'sp_get_routes',
  'sp_create_route',
  'sp_get_drivers',
  'sp_update_driver',
  'sp_set_driver_account_status',
  'sp_create_duty',
  'sp_get_admin_duties',
  'sp_get_driver_monthly_duties',
  'sp_start_duty',
  'sp_complete_duty',
  'sp_update_bus_location',
  'sp_get_reports',
  'sp_create_report'
];

const assertSafeDatabaseName = (dbName) => {
  if (!/^[A-Za-z0-9_]+$/.test(dbName)) {
    throw new Error(`Unsafe database name: ${dbName}`);
  }
};

const readSqlFile = (fileName) => {
  const candidates = [
    path.join(__dirname, '..', fileName),
    path.join(__dirname, '..', '..', fileName),
    path.join(process.cwd(), fileName)
  ];
  const filePath = candidates.find((candidate) => fs.existsSync(candidate));

  if (!filePath) {
    throw new Error(`${fileName} was not found in deployment bundle`);
  }

  return fs.readFileSync(filePath, 'utf8');
};

const splitSql = (sql) => {
  const statements = [];
  let delimiter = ';';
  let buffer = '';

  for (const rawLine of sql.split(/\r?\n/)) {
    const line = rawLine.trim();
    const delimiterMatch = line.match(/^DELIMITER\s+(.+)$/i);

    if (delimiterMatch) {
      if (buffer.trim()) {
        statements.push(buffer.trim());
        buffer = '';
      }
      delimiter = delimiterMatch[1];
      continue;
    }

    buffer += `${rawLine}\n`;

    if (buffer.trimEnd().endsWith(delimiter)) {
      const endIndex = buffer.lastIndexOf(delimiter);
      const statement = buffer.slice(0, endIndex).trim();
      if (statement) statements.push(statement);
      buffer = '';
    }
  }

  if (buffer.trim()) {
    statements.push(buffer.trim());
  }

  return statements;
};

const getTableStatus = async (connection, dbName) => {
  const [rows] = await connection.query(
    `SELECT COUNT(*) AS count
     FROM information_schema.tables
     WHERE table_schema = ?
       AND table_name = 'duty_assignments'`,
    [dbName]
  );

  return Number(rows[0]?.count || 0) > 0;
};

const hasColumn = async (connection, dbName, tableName, columnName) => {
  const [rows] = await connection.query(
    `SELECT COUNT(*) AS count
     FROM information_schema.columns
     WHERE table_schema = ?
       AND table_name = ?
       AND column_name = ?`,
    [dbName, tableName, columnName]
  );

  return Number(rows[0]?.count || 0) > 0;
};

const ensureDriverAddressColumn = async (connection, dbName) => {
  if (!await hasColumn(connection, dbName, 'drivers', 'address')) {
    await connection.query(
      `ALTER TABLE \`${dbName}\`.drivers
       ADD COLUMN address VARCHAR(255) NULL AFTER hire_date`
    );
  }
};

const ensureBusColumns = async (connection, dbName) => {
  if (!await hasColumn(connection, dbName, 'buses', 'capacity')) {
    await connection.query(
      `ALTER TABLE \`${dbName}\`.buses
       ADD COLUMN capacity INT NOT NULL DEFAULT 40 AFTER bus_number`
    );
  }

  if (!await hasColumn(connection, dbName, 'buses', 'model')) {
    await connection.query(
      `ALTER TABLE \`${dbName}\`.buses
       ADD COLUMN model VARCHAR(80) NOT NULL DEFAULT 'Electric Bus' AFTER capacity`
    );
  }

  if (!await hasColumn(connection, dbName, 'buses', 'created_at')) {
    await connection.query(
      `ALTER TABLE \`${dbName}\`.buses
       ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`
    );
  }
};

const getRoutineStatements = () => {
  const statements = splitSql(readSqlFile('dbDDL.sql'));

  return statements.filter((statement) => {
    const procedureMatch = statement.match(/^CREATE\s+PROCEDURE\s+`?([A-Za-z0-9_]+)`?/i);
    if (procedureMatch) {
      return requiredProcedures.includes(procedureMatch[1]);
    }

    return /^CREATE\s+OR\s+REPLACE\s+VIEW\s+view_admin_dashboard_stats/i.test(statement);
  });
};

const applyRoutineStatements = async (connection, statements) => {
  for (const statement of statements) {
    const procedureMatch = statement.match(/^CREATE\s+PROCEDURE\s+`?([A-Za-z0-9_]+)`?/i);

    if (procedureMatch) {
      await connection.query(`DROP PROCEDURE IF EXISTS \`${procedureMatch[1]}\``);
    }

    await connection.query(statement);
  }
};

const main = async () => {
  const dbName = env('DB_NAME', 'electric_bus_tracker');
  assertSafeDatabaseName(dbName);

  const connection = await mysql.createConnection({
    host: env('DB_HOST', 'localhost'),
    port: Number(env('DB_PORT', 3306)),
    user: env('DB_USER', 'root'),
    password: env('DB_PASSWORD', ''),
    multipleStatements: false
  });

  try {
    const hasDutyAssignments = await getTableStatus(connection, dbName);
    if (!hasDutyAssignments) {
      console.log(`Database ${dbName} is not initialized yet. Skipping migrations.`);
      return;
    }

    await connection.query(`USE \`${dbName}\``);
    await ensureDriverAddressColumn(connection, dbName);
    await ensureBusColumns(connection, dbName);
    await applyRoutineStatements(connection, getRoutineStatements());

    console.log(`Database ${dbName} migrations applied successfully.`);
  } finally {
    await connection.end();
  }
};

main().catch((error) => {
  console.error(`Database migration failed: ${error.message}`);
  if (process.env.CRASH_ON_MIGRATION_ERROR === 'true') {
    process.exit(1);
  }

  // Non-fatal in normal deployments: log and continue so the app can start.
  console.warn('Continuing startup despite migration failure (CRASH_ON_MIGRATION_ERROR not set).');
});
