const mysql = require('mysql2/promise');

const env = (name, fallback = '') => process.env[name] || fallback;

const assertSafeDatabaseName = (dbName) => {
  if (!/^[A-Za-z0-9_]+$/.test(dbName)) {
    throw new Error(`Unsafe database name: ${dbName}`);
  }
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

const runStatements = async (connection, statements) => {
  for (const statement of statements) {
    await connection.query(statement);
  }
};

const spGetDriverMonthlyDuties = `
CREATE PROCEDURE sp_get_driver_monthly_duties(
  IN p_user_id INT,
  IN p_month INT,
  IN p_year INT
)
BEGIN
  SELECT
    da.*,
    b.bus_number,
    r.route_id,
    r.name AS route_name
  FROM duty_assignments da
  JOIN drivers d ON d.driver_id = da.driver_id
  JOIN buses b ON b.bus_id = da.bus_id
  JOIN schedules s ON s.schedule_id = da.schedule_id
  JOIN routes r ON r.route_id = s.route_id
  WHERE d.user_id = p_user_id
    AND MONTH(da.scheduled_date) = p_month
    AND YEAR(da.scheduled_date) = p_year
  ORDER BY da.scheduled_date, da.scheduled_start_time;

  SELECT
    COUNT(*) AS total,
    COALESCE(SUM(da.status = 'Completed'), 0) AS completed,
    COALESCE(SUM(da.status = 'Skipped'), 0) AS skipped,
    COALESCE(SUM(da.status = 'Scheduled'), 0) AS assigned,
    COALESCE(SUM(da.status = 'In-Progress'), 0) AS in_progress
  FROM duty_assignments da
  JOIN drivers d ON d.driver_id = da.driver_id
  WHERE d.user_id = p_user_id
    AND MONTH(da.scheduled_date) = p_month
    AND YEAR(da.scheduled_date) = p_year;
END`;

const spStartDuty = `
CREATE PROCEDURE sp_start_duty(
  IN p_user_id INT,
  IN p_duty_id INT
)
BEGIN
  DECLARE v_driver_id INT DEFAULT NULL;

  SELECT driver_id
  INTO v_driver_id
  FROM drivers
  WHERE user_id = p_user_id
  LIMIT 1;

  UPDATE duty_assignments
  SET status = 'In-Progress',
      actual_start_time = NOW()
  WHERE duty_id = p_duty_id
    AND driver_id = v_driver_id
    AND status = 'Scheduled';

  SELECT ROW_COUNT() AS affected_rows;
END`;

const spCompleteDuty = `
CREATE PROCEDURE sp_complete_duty(
  IN p_user_id INT,
  IN p_duty_id INT,
  IN p_note TEXT
)
BEGIN
  DECLARE v_affected_rows INT DEFAULT 0;
  DECLARE v_driver_id INT DEFAULT NULL;

  SELECT driver_id
  INTO v_driver_id
  FROM drivers
  WHERE user_id = p_user_id
  LIMIT 1;

  UPDATE duty_assignments
  SET status = 'Completed',
      actual_end_time = NOW(),
      completion_note = p_note
  WHERE duty_id = p_duty_id
    AND driver_id = v_driver_id
    AND status = 'In-Progress';

  SET v_affected_rows = ROW_COUNT();

  UPDATE bus_locations
  SET is_active = FALSE
  WHERE duty_id = p_duty_id;

  SELECT v_affected_rows AS affected_rows;
END`;

const spSaveResetCode = `
CREATE PROCEDURE sp_save_reset_code(
  IN p_email VARCHAR(100),
  IN p_reset_code VARCHAR(10)
)
BEGIN
  UPDATE users
  SET reset_code = p_reset_code,
      reset_code_expiry = DATE_ADD(NOW(), INTERVAL 5 MINUTE)
  WHERE LOWER(email) = LOWER(p_email)
    AND deletion_date IS NULL;

  SELECT user_id, name, email
  FROM users
  WHERE LOWER(email) = LOWER(p_email)
    AND deletion_date IS NULL
  LIMIT 1;
END`;

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
    await runStatements(connection, [
      'DROP PROCEDURE IF EXISTS sp_get_driver_monthly_duties',
      spGetDriverMonthlyDuties,
      'DROP PROCEDURE IF EXISTS sp_start_duty',
      spStartDuty,
      'DROP PROCEDURE IF EXISTS sp_complete_duty',
      spCompleteDuty,
      'DROP PROCEDURE IF EXISTS sp_save_reset_code',
      spSaveResetCode
    ]);

    console.log(`Database ${dbName} migrations applied successfully.`);
  } finally {
    await connection.end();
  }
};

main().catch((error) => {
  console.error(`Database migration failed: ${error.message}`);
  process.exit(1);
});
