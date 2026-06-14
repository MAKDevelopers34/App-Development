const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

const env = (name, fallback = '') => process.env[name] || fallback;

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

const executeScript = async (connection, sql) => {
  for (const statement of splitSql(sql)) {
    await connection.query(statement);
  }
};

const databaseStatus = async (connection, dbName) => {
  const [tables] = await connection.query(
    `SELECT COUNT(*) AS count
     FROM information_schema.tables
     WHERE table_schema = ?
       AND table_name = 'users'`,
    [dbName]
  );

  const hasUsersTable = Number(tables[0]?.count || 0) > 0;
  if (!hasUsersTable) {
    return {
      hasUsersTable: false,
      hasSeedData: false,
      hasRequiredRoutines: false
    };
  }

  const [rows] = await connection.query(
    `SELECT COUNT(*) AS count FROM \`${dbName}\`.users`
  );

  const requiredRoutines = [
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
  const [routines] = await connection.query(
    `SELECT routine_name
     FROM information_schema.routines
     WHERE routine_schema = ?
       AND routine_type = 'PROCEDURE'
       AND routine_name IN (?)`,
    [dbName, requiredRoutines]
  );

  return {
    hasUsersTable: true,
    hasSeedData: Number(rows[0]?.count || 0) > 0,
    hasRequiredRoutines: routines.length === requiredRoutines.length
  };
};

const main = async () => {
  const dbName = env('DB_NAME', 'electric_bus_tracker');
  const force = env('FORCE_DB_IMPORT', 'false') === 'true';
  const connection = await mysql.createConnection({
    host: env('DB_HOST', 'localhost'),
    port: Number(env('DB_PORT', 3306)),
    user: env('DB_USER', 'root'),
    password: env('DB_PASSWORD', ''),
    multipleStatements: false
  });

  try {
    const status = await databaseStatus(connection, dbName);

    if (!force && status.hasSeedData && status.hasRequiredRoutines) {
      console.log(`Database ${dbName} already contains data and required routines. Skipping import.`);
      return;
    }

    if (!force && status.hasSeedData && !status.hasRequiredRoutines) {
      throw new Error(
        `Database ${dbName} contains data but is missing required routines. ` +
        'Set FORCE_DB_IMPORT=true for a one-time rebuild, then set it back to false.'
      );
    }

    await executeScript(connection, readSqlFile('dbDDL.sql'));
    await executeScript(connection, readSqlFile('dbDML.sql'));
    console.log(`Database ${dbName} imported successfully.`);
  } finally {
    await connection.end();
  }
};

main().catch((error) => {
  console.error(`Database import failed: ${error.message}`);
  process.exit(1);
});
