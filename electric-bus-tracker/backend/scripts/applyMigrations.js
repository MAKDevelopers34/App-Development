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

const ensureDriverAddressColumn = async (connection, dbName) => {
  const [rows] = await connection.query(
    `SELECT COUNT(*) AS count
     FROM information_schema.columns
     WHERE table_schema = ?
       AND table_name = 'drivers'
       AND column_name = 'address'`,
    [dbName]
  );

  if (Number(rows[0]?.count || 0) === 0) {
    await connection.query(
      `ALTER TABLE \`${dbName}\`.drivers
       ADD COLUMN address VARCHAR(255) NULL AFTER hire_date`
    );
  }
};

const spGetDrivers = `
CREATE PROCEDURE sp_get_drivers()
BEGIN
  SELECT
    d.driver_id,
    d.license_no,
    d.hire_date,
    d.status AS driver_status,
    d.address,
    u.user_id,
    u.username,
    u.user_code,
    u.name,
    u.email,
    u.contact,
    u.account_status
  FROM drivers d
  JOIN users u ON u.user_id = d.user_id
  WHERE u.deletion_date IS NULL
  ORDER BY u.name;
END`;

const spUpdateDriver = `
CREATE PROCEDURE sp_update_driver(
  IN p_driver_id INT,
  IN p_name VARCHAR(100),
  IN p_email VARCHAR(100),
  IN p_contact VARCHAR(20),
  IN p_license_no VARCHAR(50),
  IN p_driver_status VARCHAR(20),
  IN p_address VARCHAR(255)
)
BEGIN
  UPDATE users u
  JOIN drivers d ON d.user_id = u.user_id
  SET u.name = p_name,
      u.email = LOWER(p_email),
      u.contact = p_contact,
      d.license_no = p_license_no,
      d.status = p_driver_status,
      d.address = p_address
  WHERE d.driver_id = p_driver_id;
END`;

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
    AND status = 'Scheduled'
    AND NOW() < DATE_ADD(
      TIMESTAMP(scheduled_date, scheduled_start_time),
      INTERVAL 25 MINUTE
    );

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
    await ensureDriverAddressColumn(connection, dbName);
    await runStatements(connection, [
      'DROP PROCEDURE IF EXISTS sp_get_drivers',
      spGetDrivers,
      'DROP PROCEDURE IF EXISTS sp_create_driver',
      'DROP PROCEDURE IF EXISTS sp_get_route_by_id',
      'DROP PROCEDURE IF EXISTS sp_search_routes',
      'DROP PROCEDURE IF EXISTS sp_delete_route',
      'DROP PROCEDURE IF EXISTS sp_get_buses',
      'DROP PROCEDURE IF EXISTS sp_update_duty_times',
      'DROP PROCEDURE IF EXISTS sp_get_active_buses',
      'DROP PROCEDURE IF EXISTS sp_get_buses_by_route',
      'DROP PROCEDURE IF EXISTS sp_update_driver',
      spUpdateDriver,
      'DROP PROCEDURE IF EXISTS sp_get_driver_monthly_duties',
      spGetDriverMonthlyDuties,
      'DROP PROCEDURE IF EXISTS sp_get_driver_today_duty',
      'DROP PROCEDURE IF EXISTS sp_get_driver_upcoming_duty',
      'DROP PROCEDURE IF EXISTS sp_start_duty',
      spStartDuty,
      'DROP PROCEDURE IF EXISTS sp_complete_duty',
      spCompleteDuty,
      'DROP PROCEDURE IF EXISTS sp_save_reset_code',
      spSaveResetCode,
      'DROP VIEW IF EXISTS view_active_buses'
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
