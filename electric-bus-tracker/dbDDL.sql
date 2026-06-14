DROP DATABASE IF EXISTS electric_bus_tracker;
CREATE DATABASE electric_bus_tracker
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE electric_bus_tracker;

CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  user_code VARCHAR(30) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  contact VARCHAR(20) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('Driver', 'Admin') NOT NULL,
  account_status ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active',
  login_attempts INT NOT NULL DEFAULT 0,
  lock_until DATETIME NULL,
  reset_code VARCHAR(10) NULL,
  reset_code_expiry DATETIME NULL,
  creation_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deletion_date DATETIME NULL,
  INDEX idx_users_role_status (role, account_status),
  INDEX idx_users_login (username, user_code)
);

CREATE TABLE drivers (
  driver_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  license_no VARCHAR(50) NOT NULL UNIQUE,
  hire_date DATE NOT NULL,
  address VARCHAR(255) NULL,
  status ENUM('Available', 'On-Duty', 'Off-Duty', 'On-Leave') NOT NULL DEFAULT 'Available',
  CONSTRAINT fk_drivers_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE TABLE admins (
  admin_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  CONSTRAINT fk_admins_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE TABLE buses (
  bus_id INT AUTO_INCREMENT PRIMARY KEY,
  bus_number VARCHAR(20) NOT NULL UNIQUE,
  capacity INT NOT NULL DEFAULT 40,
  model VARCHAR(80) NOT NULL DEFAULT 'Electric Bus',
  status ENUM('Active', 'Maintenance', 'Inactive') NOT NULL DEFAULT 'Active',
  registration_date DATE NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_buses_status (status)
);

CREATE TABLE routes (
  route_id INT AUTO_INCREMENT PRIMARY KEY,
  route_code VARCHAR(30) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  starting_point VARCHAR(100) NOT NULL,
  start_latitude DECIMAL(10,7) NOT NULL,
  start_longitude DECIMAL(10,7) NOT NULL,
  destination_point VARCHAR(100) NOT NULL,
  destination_latitude DECIMAL(10,7) NOT NULL,
  destination_longitude DECIMAL(10,7) NOT NULL,
  distance DECIMAL(10,2) NOT NULL,
  estimated_duration INT NOT NULL,
  status ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_routes_status (status),
  INDEX idx_routes_name (name)
);

CREATE TABLE stops (
  stop_id INT AUTO_INCREMENT PRIMARY KEY,
  stop_code VARCHAR(30) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  latitude DECIMAL(10,7) NOT NULL,
  longitude DECIMAL(10,7) NOT NULL,
  creation_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deletion_date DATETIME NULL,
  status ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active',
  INDEX idx_stops_name (name),
  INDEX idx_stops_status (status)
);

CREATE TABLE route_stop_details (
  route_id INT NOT NULL,
  stop_id INT NOT NULL,
  stop_order INT NOT NULL,
  distance_from_start DECIMAL(10,2) NOT NULL DEFAULT 0,
  estimated_minutes_from_start INT NOT NULL DEFAULT 0,
  PRIMARY KEY (route_id, stop_id),
  UNIQUE KEY uq_route_stop_order (route_id, stop_order),
  CONSTRAINT fk_route_stop_route
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_route_stop_stop
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE TABLE schedules (
  schedule_id INT AUTO_INCREMENT PRIMARY KEY,
  route_id INT NOT NULL,
  bus_id INT NOT NULL,
  departure_time TIME NOT NULL,
  arrival_time TIME NOT NULL,
  service_date DATE NOT NULL,
  status ENUM('Scheduled', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Scheduled',
  CONSTRAINT fk_schedules_route
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_schedules_bus
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  UNIQUE KEY uq_schedule_trip (route_id, bus_id, departure_time, service_date),
  INDEX idx_schedules_date (service_date),
  INDEX idx_schedules_route_date (route_id, service_date)
);

CREATE TABLE duty_assignments (
  duty_id INT AUTO_INCREMENT PRIMARY KEY,
  driver_id INT NOT NULL,
  bus_id INT NOT NULL,
  schedule_id INT NOT NULL,
  scheduled_date DATE NOT NULL,
  scheduled_start_time TIME NOT NULL,
  scheduled_end_time TIME NOT NULL,
  actual_start_time DATETIME NULL,
  actual_end_time DATETIME NULL,
  status ENUM('Scheduled', 'In-Progress', 'Completed', 'Skipped') NOT NULL DEFAULT 'Scheduled',
  completion_note TEXT NULL,
  admin_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_duties_driver
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_duties_bus
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_duties_schedule
    FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_duties_admin
    FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  INDEX idx_duties_driver_date (driver_id, scheduled_date),
  INDEX idx_duties_bus_date (bus_id, scheduled_date),
  INDEX idx_duties_status (status)
);

CREATE TABLE bus_locations (
  location_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  bus_id INT NOT NULL,
  driver_id INT NOT NULL,
  route_id INT NOT NULL,
  duty_id INT NULL,
  latitude DECIMAL(10,7) NOT NULL,
  longitude DECIMAL(10,7) NOT NULL,
  speed DECIMAL(7,2) NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_locations_bus
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_locations_driver
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_locations_route
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_locations_duty
    FOREIGN KEY (duty_id) REFERENCES duty_assignments(duty_id)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  INDEX idx_locations_active_time (is_active, recorded_at),
  INDEX idx_locations_bus_time (bus_id, recorded_at),
  INDEX idx_locations_route_time (route_id, recorded_at)
);

CREATE TABLE reports (
  report_id INT AUTO_INCREMENT PRIMARY KEY,
  report_code VARCHAR(60) NOT NULL UNIQUE,
  admin_id INT NOT NULL,
  type ENUM('daily', 'weekly', 'monthly') NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  total_duties INT NOT NULL DEFAULT 0,
  completed_duties INT NOT NULL DEFAULT 0,
  skipped_duties INT NOT NULL DEFAULT 0,
  total_buses INT NOT NULL DEFAULT 0,
  total_drivers INT NOT NULL DEFAULT 0,
  active_drivers INT NOT NULL DEFAULT 0,
  pdf_path VARCHAR(255) NULL,
  description TEXT NULL,
  CONSTRAINT fk_reports_admin
    FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  INDEX idx_reports_type_generated (type, generated_at)
);

CREATE TABLE audit_logs (
  audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  action VARCHAR(80) NOT NULL,
  entity_name VARCHAR(80) NULL,
  entity_id VARCHAR(80) NULL,
  details TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  INDEX idx_audit_created (created_at),
  INDEX idx_audit_action (action)
);

CREATE OR REPLACE VIEW view_admin_dashboard_stats AS
SELECT
  (SELECT COUNT(*) FROM buses WHERE status = 'Active') AS active_buses,
  (SELECT COUNT(*) FROM buses) AS total_buses,
  (SELECT COUNT(*) FROM drivers) AS total_drivers,
  (SELECT COUNT(*) FROM drivers WHERE status <> 'Off-Duty') AS available_drivers,
  (SELECT COUNT(*) FROM duty_assignments WHERE scheduled_date = CURDATE()) AS today_duties,
  (SELECT COUNT(*) FROM duty_assignments WHERE scheduled_date = CURDATE() AND status = 'Completed') AS completed_duties,
  (SELECT COUNT(*) FROM routes WHERE status = 'Active') AS active_routes;

DELIMITER $$

CREATE TRIGGER trg_duty_before_insert
BEFORE INSERT ON duty_assignments
FOR EACH ROW
BEGIN
  IF NEW.scheduled_end_time <= NEW.scheduled_start_time THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Duty end time must be after start time';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM duty_assignments
    WHERE driver_id = NEW.driver_id
      AND scheduled_date = NEW.scheduled_date
      AND status IN ('Scheduled', 'In-Progress')
      AND NEW.scheduled_start_time < scheduled_end_time
      AND NEW.scheduled_end_time > scheduled_start_time
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Driver already has an overlapping duty';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM duty_assignments
    WHERE bus_id = NEW.bus_id
      AND scheduled_date = NEW.scheduled_date
      AND status IN ('Scheduled', 'In-Progress')
      AND NEW.scheduled_start_time < scheduled_end_time
      AND NEW.scheduled_end_time > scheduled_start_time
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Bus already has an overlapping duty';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM drivers d
    JOIN users u ON u.user_id = d.user_id
    WHERE d.driver_id = NEW.driver_id
      AND u.account_status = 'Active'
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Driver account must be active';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM buses
    WHERE bus_id = NEW.bus_id
      AND status = 'Active'
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Bus must be active';
  END IF;
END$$

CREATE TRIGGER trg_duty_after_insert
AFTER INSERT ON duty_assignments
FOR EACH ROW
BEGIN
  IF NEW.status = 'In-Progress' THEN
    UPDATE drivers SET status = 'On-Duty' WHERE driver_id = NEW.driver_id;
  END IF;
END$$

CREATE TRIGGER trg_duty_before_update
BEFORE UPDATE ON duty_assignments
FOR EACH ROW
BEGIN
  IF NEW.scheduled_end_time <= NEW.scheduled_start_time THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Duty end time must be after start time';
  END IF;

  IF NEW.status = 'Scheduled' AND OLD.status = 'Completed' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Completed duty cannot return to scheduled status';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM duty_assignments
    WHERE duty_id <> NEW.duty_id
      AND driver_id = NEW.driver_id
      AND scheduled_date = NEW.scheduled_date
      AND status IN ('Scheduled', 'In-Progress')
      AND NEW.status IN ('Scheduled', 'In-Progress')
      AND NEW.scheduled_start_time < scheduled_end_time
      AND NEW.scheduled_end_time > scheduled_start_time
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Driver already has an overlapping duty';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM duty_assignments
    WHERE duty_id <> NEW.duty_id
      AND bus_id = NEW.bus_id
      AND scheduled_date = NEW.scheduled_date
      AND status IN ('Scheduled', 'In-Progress')
      AND NEW.status IN ('Scheduled', 'In-Progress')
      AND NEW.scheduled_start_time < scheduled_end_time
      AND NEW.scheduled_end_time > scheduled_start_time
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Bus already has an overlapping duty';
  END IF;
END$$

CREATE TRIGGER trg_duty_after_update
AFTER UPDATE ON duty_assignments
FOR EACH ROW
BEGIN
  IF NEW.status = 'In-Progress' THEN
    UPDATE drivers SET status = 'On-Duty' WHERE driver_id = NEW.driver_id;
  ELSEIF NEW.status IN ('Completed', 'Skipped') THEN
    UPDATE drivers SET status = 'Available' WHERE driver_id = NEW.driver_id;
  END IF;
END$$

CREATE PROCEDURE sp_get_user_for_login(
  IN p_username VARCHAR(100),
  IN p_user_code VARCHAR(30)
)
BEGIN
  SELECT
    u.user_id,
    u.username,
    u.user_code,
    u.name,
    u.email,
    u.contact,
    u.password_hash,
    u.role,
    u.account_status,
    u.login_attempts,
    u.lock_until,
    d.driver_id,
    a.admin_id
  FROM users u
  LEFT JOIN drivers d ON d.user_id = u.user_id
  LEFT JOIN admins a ON a.user_id = u.user_id
  WHERE LOWER(u.username) = LOWER(p_username)
    AND u.user_code = p_user_code
    AND u.deletion_date IS NULL
  LIMIT 1;
END$$

CREATE PROCEDURE sp_record_login_failure(IN p_user_id INT)
BEGIN
  UPDATE users
  SET
    login_attempts = CASE WHEN login_attempts + 1 >= 5 THEN 0 ELSE login_attempts + 1 END,
    lock_until = CASE WHEN login_attempts + 1 >= 5 THEN DATE_ADD(NOW(), INTERVAL 30 MINUTE) ELSE lock_until END
  WHERE user_id = p_user_id;

  INSERT INTO audit_logs(user_id, action, entity_name, entity_id, details)
  VALUES (p_user_id, 'LOGIN_FAILED', 'users', p_user_id, 'Failed login attempt');
END$$

CREATE PROCEDURE sp_record_login_success(IN p_user_id INT)
BEGIN
  UPDATE users
  SET login_attempts = 0,
      lock_until = NULL
  WHERE user_id = p_user_id;

  INSERT INTO audit_logs(user_id, action, entity_name, entity_id, details)
  VALUES (p_user_id, 'LOGIN_SUCCESS', 'users', p_user_id, 'Successful login');
END$$

CREATE PROCEDURE sp_get_user_profile(IN p_user_id INT)
BEGIN
  SELECT
    u.user_id,
    u.username,
    u.user_code,
    u.name,
    u.email,
    u.contact,
    u.role,
    u.account_status,
    d.driver_id,
    d.license_no,
    d.hire_date,
    d.status AS driver_status,
    a.admin_id
  FROM users u
  LEFT JOIN drivers d ON d.user_id = u.user_id
  LEFT JOIN admins a ON a.user_id = u.user_id
  WHERE u.user_id = p_user_id;
END$$

CREATE PROCEDURE sp_change_password(
  IN p_user_id INT,
  IN p_password_hash VARCHAR(255)
)
BEGIN
  UPDATE users
  SET password_hash = p_password_hash,
      reset_code = NULL,
      reset_code_expiry = NULL
  WHERE user_id = p_user_id;
END$$

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
END$$

CREATE PROCEDURE sp_reset_password(
  IN p_email VARCHAR(100),
  IN p_reset_code VARCHAR(10),
  IN p_password_hash VARCHAR(255)
)
BEGIN
  UPDATE users
  SET password_hash = p_password_hash,
      reset_code = NULL,
      reset_code_expiry = NULL,
      login_attempts = 0,
      lock_until = NULL
  WHERE LOWER(email) = LOWER(p_email)
    AND reset_code = p_reset_code
    AND reset_code_expiry >= NOW()
    AND deletion_date IS NULL;

  SELECT ROW_COUNT() AS affected_rows;
END$$

CREATE PROCEDURE sp_get_routes()
BEGIN
  SELECT
    r.route_id,
    r.route_code,
    r.name,
    r.starting_point,
    r.start_latitude,
    r.start_longitude,
    r.destination_point,
    r.destination_latitude,
    r.destination_longitude,
    r.distance,
    r.estimated_duration,
    r.status,
    COUNT(s.stop_id) AS stop_count
  FROM routes r
  LEFT JOIN route_stop_details rsd ON rsd.route_id = r.route_id
  LEFT JOIN stops s ON s.stop_id = rsd.stop_id
    AND s.status = 'Active'
    AND s.deletion_date IS NULL
  WHERE r.status = 'Active'
  GROUP BY r.route_id
  ORDER BY r.name;
END$$

CREATE PROCEDURE sp_create_route(
  IN p_route_code VARCHAR(30),
  IN p_name VARCHAR(100),
  IN p_starting_point VARCHAR(100),
  IN p_start_latitude DECIMAL(10,7),
  IN p_start_longitude DECIMAL(10,7),
  IN p_destination_point VARCHAR(100),
  IN p_destination_latitude DECIMAL(10,7),
  IN p_destination_longitude DECIMAL(10,7),
  IN p_distance DECIMAL(10,2),
  IN p_estimated_duration INT
)
BEGIN
  INSERT INTO routes(
    route_code,
    name,
    starting_point,
    start_latitude,
    start_longitude,
    destination_point,
    destination_latitude,
    destination_longitude,
    distance,
    estimated_duration
  )
  VALUES (
    p_route_code,
    p_name,
    p_starting_point,
    p_start_latitude,
    p_start_longitude,
    p_destination_point,
    p_destination_latitude,
    p_destination_longitude,
    p_distance,
    p_estimated_duration
  );

  SELECT LAST_INSERT_ID() AS route_id;
END$$

CREATE PROCEDURE sp_get_drivers()
BEGIN
  SELECT
    d.driver_id,
    d.license_no,
    d.hire_date,
    d.status AS driver_status,
    u.user_id,
    u.username,
    u.user_code,
    u.name,
    u.email,
    u.contact,
    u.account_status,
    d.address
  FROM drivers d
  JOIN users u ON u.user_id = d.user_id
  WHERE u.deletion_date IS NULL
  ORDER BY u.name;
END$$

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
      d.address = p_address,
      d.status = p_driver_status
  WHERE d.driver_id = p_driver_id;
END$$

CREATE PROCEDURE sp_set_driver_account_status(
  IN p_driver_id INT,
  IN p_account_status VARCHAR(20)
)
BEGIN
  UPDATE users u
  JOIN drivers d ON d.user_id = u.user_id
  SET u.account_status = p_account_status
  WHERE d.driver_id = p_driver_id;
END$$

CREATE PROCEDURE sp_create_duty(
  IN p_driver_id INT,
  IN p_bus_id INT,
  IN p_route_id INT,
  IN p_scheduled_date DATE,
  IN p_scheduled_start_time TIME,
  IN p_scheduled_end_time TIME,
  IN p_admin_id INT
)
BEGIN
  DECLARE v_schedule_id INT;

  SET v_schedule_id = (
    SELECT schedule_id
    FROM schedules
    WHERE route_id = p_route_id
      AND bus_id = p_bus_id
      AND service_date = p_scheduled_date
      AND departure_time = p_scheduled_start_time
    LIMIT 1
  );

  IF v_schedule_id IS NULL THEN
    INSERT INTO schedules(route_id, bus_id, departure_time, arrival_time, service_date)
    VALUES (p_route_id, p_bus_id, p_scheduled_start_time, p_scheduled_end_time, p_scheduled_date);
    SET v_schedule_id = LAST_INSERT_ID();
  END IF;

  INSERT INTO duty_assignments(
    driver_id,
    bus_id,
    schedule_id,
    scheduled_date,
    scheduled_start_time,
    scheduled_end_time,
    admin_id
  )
  VALUES (
    p_driver_id,
    p_bus_id,
    v_schedule_id,
    p_scheduled_date,
    p_scheduled_start_time,
    p_scheduled_end_time,
    p_admin_id
  );

  SELECT LAST_INSERT_ID() AS duty_id;
END$$

CREATE PROCEDURE sp_get_admin_duties()
BEGIN
  SELECT
    da.*,
    u.name AS driver_name,
    u.username AS driver_username,
    b.bus_number,
    r.route_id,
    r.name AS route_name
  FROM duty_assignments da
  JOIN drivers d ON d.driver_id = da.driver_id
  JOIN users u ON u.user_id = d.user_id
  JOIN buses b ON b.bus_id = da.bus_id
  JOIN schedules s ON s.schedule_id = da.schedule_id
  JOIN routes r ON r.route_id = s.route_id
  ORDER BY da.scheduled_date DESC, da.scheduled_start_time DESC;
END$$

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
END$$

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
END$$

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
END$$

CREATE PROCEDURE sp_update_bus_location(
  IN p_user_id INT,
  IN p_bus_id INT,
  IN p_route_id INT,
  IN p_duty_id INT,
  IN p_latitude DECIMAL(10,7),
  IN p_longitude DECIMAL(10,7),
  IN p_speed DECIMAL(7,2)
)
BEGIN
  DECLARE v_driver_id INT;

  SET v_driver_id = (
    SELECT driver_id FROM drivers WHERE user_id = p_user_id LIMIT 1
  );

  INSERT INTO bus_locations(
    bus_id,
    driver_id,
    route_id,
    duty_id,
    latitude,
    longitude,
    speed,
    is_active
  )
  VALUES (
    p_bus_id,
    v_driver_id,
    p_route_id,
    p_duty_id,
    p_latitude,
    p_longitude,
    p_speed,
    TRUE
  );

  SELECT LAST_INSERT_ID() AS location_id;
END$$

CREATE PROCEDURE sp_get_reports()
BEGIN
  SELECT
    r.*,
    u.name AS admin_name
  FROM reports r
  JOIN admins a ON a.admin_id = r.admin_id
  JOIN users u ON u.user_id = a.user_id
  ORDER BY r.generated_at DESC
  LIMIT 50;
END$$

CREATE PROCEDURE sp_create_report(
  IN p_admin_id INT,
  IN p_report_code VARCHAR(60),
  IN p_type VARCHAR(20),
  IN p_period_start DATE,
  IN p_period_end DATE,
  IN p_total_duties INT,
  IN p_completed_duties INT,
  IN p_skipped_duties INT,
  IN p_total_buses INT,
  IN p_total_drivers INT,
  IN p_active_drivers INT,
  IN p_pdf_path VARCHAR(255),
  IN p_description TEXT
)
BEGIN
  INSERT INTO reports(
    report_code,
    admin_id,
    type,
    period_start,
    period_end,
    total_duties,
    completed_duties,
    skipped_duties,
    total_buses,
    total_drivers,
    active_drivers,
    pdf_path,
    description
  )
  VALUES (
    p_report_code,
    p_admin_id,
    p_type,
    p_period_start,
    p_period_end,
    p_total_duties,
    p_completed_duties,
    p_skipped_duties,
    p_total_buses,
    p_total_drivers,
    p_active_drivers,
    p_pdf_path,
    p_description
  );

  SELECT
    r.*,
    u.name AS admin_name
  FROM reports r
  JOIN admins a ON a.admin_id = r.admin_id
  JOIN users u ON u.user_id = a.user_id
  WHERE r.report_id = LAST_INSERT_ID();
END$$

DELIMITER ;
