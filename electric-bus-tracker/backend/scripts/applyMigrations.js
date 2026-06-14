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

const spCreateDriver = `
CREATE PROCEDURE sp_create_driver(
  IN p_username VARCHAR(50),
  IN p_user_code VARCHAR(30),
  IN p_name VARCHAR(100),
  IN p_email VARCHAR(100),
  IN p_contact VARCHAR(20),
  IN p_password_hash VARCHAR(255),
  IN p_license_no VARCHAR(50),
  IN p_hire_date DATE,
  IN p_address VARCHAR(255)
)
BEGIN
  DECLARE v_user_id INT;

  INSERT INTO users(username, user_code, name, email, contact, password_hash, role)
  VALUES (LOWER(p_username), p_user_code, p_name, LOWER(p_email), p_contact, p_password_hash, 'Driver');

  SET v_user_id = LAST_INSERT_ID();

  INSERT INTO drivers(user_id, license_no, hire_date, address)
  VALUES (v_user_id, p_license_no, p_hire_date, p_address);

  SELECT LAST_INSERT_ID() AS driver_id, v_user_id AS user_id;
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

const spGetDriverTodayDuty = `
CREATE PROCEDURE sp_get_driver_today_duty(IN p_user_id INT)
BEGIN
  SELECT
    da.*,
    b.bus_number,
    b.bus_id,
    r.route_id,
    r.name AS route_name,
    r.starting_point,
    r.destination_point
  FROM duty_assignments da
  JOIN drivers d ON d.driver_id = da.driver_id
  JOIN buses b ON b.bus_id = da.bus_id
  JOIN schedules s ON s.schedule_id = da.schedule_id
  JOIN routes r ON r.route_id = s.route_id
  WHERE d.user_id = p_user_id
    AND da.scheduled_date = CURDATE()
    AND da.status IN ('In-Progress', 'Scheduled')
  ORDER BY
    CASE da.status
      WHEN 'In-Progress' THEN 0
      ELSE 1
    END,
    da.scheduled_start_time
  LIMIT 1;
END`;

const spGetDriverUpcomingDuty = `
CREATE PROCEDURE sp_get_driver_upcoming_duty(IN p_user_id INT)
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
    AND da.status = 'Scheduled'
    AND TIMESTAMP(da.scheduled_date, da.scheduled_start_time) > NOW()
  ORDER BY da.scheduled_date, da.scheduled_start_time
  LIMIT 1;
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

const viewActiveBuses = `
CREATE OR REPLACE VIEW view_active_buses AS
SELECT
  latest.location_id,
  latest.bus_id,
  b.bus_number,
  latest.driver_id,
  u.name AS driver_name,
  latest.route_id,
  r.name AS route_name,
  latest.duty_id,
  latest.latitude,
  latest.longitude,
  latest.speed,
  latest.recorded_at
FROM bus_locations latest
JOIN (
  SELECT bus_id, MAX(recorded_at) AS max_recorded_at
  FROM bus_locations
  WHERE is_active = TRUE
  GROUP BY bus_id
) pick
  ON pick.bus_id = latest.bus_id
  AND pick.max_recorded_at = latest.recorded_at
JOIN buses b
  ON b.bus_id = latest.bus_id
  AND b.status = 'Active'
JOIN drivers d ON d.driver_id = latest.driver_id
JOIN users u ON u.user_id = d.user_id
JOIN routes r ON r.route_id = latest.route_id
JOIN duty_assignments da ON da.duty_id = latest.duty_id
WHERE latest.is_active = TRUE
  AND da.status = 'In-Progress'
  AND latest.recorded_at >= DATE_SUB(NOW(), INTERVAL 10 MINUTE)`;

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
      spCreateDriver,
      'DROP PROCEDURE IF EXISTS sp_update_driver',
      spUpdateDriver,
      'DROP PROCEDURE IF EXISTS sp_get_driver_monthly_duties',
      spGetDriverMonthlyDuties,
      'DROP PROCEDURE IF EXISTS sp_get_driver_today_duty',
      spGetDriverTodayDuty,
      'DROP PROCEDURE IF EXISTS sp_get_driver_upcoming_duty',
      spGetDriverUpcomingDuty,
      'DROP PROCEDURE IF EXISTS sp_start_duty',
      spStartDuty,
      'DROP PROCEDURE IF EXISTS sp_complete_duty',
      spCompleteDuty,
      'DROP PROCEDURE IF EXISTS sp_save_reset_code',
      spSaveResetCode,
      viewActiveBuses
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
