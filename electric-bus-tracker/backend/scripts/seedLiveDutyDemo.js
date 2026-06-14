const dotenv = require('dotenv');
const mysql = require('mysql2/promise');

dotenv.config();

const env = (name, fallback = '') => process.env[name] || fallback;

const addMinutes = (date, minutes) => new Date(date.getTime() + minutes * 60000);
const dateOnly = (date) => date.toISOString().slice(0, 10);
const timeOnly = (date) => date.toISOString().slice(11, 19);

const main = async () => {
  const dbName = env('DB_NAME', 'electric_bus_tracker');
  const connection = await mysql.createConnection({
    host: env('DB_HOST', 'localhost'),
    port: Number(env('DB_PORT', 3306)),
    user: env('DB_USER', 'root'),
    password: env('DB_PASSWORD', ''),
    database: dbName
  });

  try {
    const [[route]] = await connection.query(
      `SELECT *
       FROM routes
       WHERE status = 'Active'
       ORDER BY route_id
       LIMIT 1`
    );
    const [[driver]] = await connection.query(
      `SELECT d.driver_id, u.name
       FROM drivers d
       JOIN users u ON u.user_id = d.user_id
       WHERE d.status <> 'Inactive'
         AND u.account_status = 'Active'
         AND u.deletion_date IS NULL
       ORDER BY d.driver_id
       LIMIT 1`
    );
    const [[bus]] = await connection.query(
      `SELECT bus_id, bus_number
       FROM buses
       WHERE status = 'Active'
       ORDER BY bus_id
       LIMIT 1`
    );

    if (!route || !driver || !bus) {
      throw new Error('Need at least one active route, driver, and bus before seeding demo live duty.');
    }

    const now = new Date();
    const start = addMinutes(now, -5);
    const end = addMinutes(start, Number(route.estimated_duration || 60));
    const serviceDate = dateOnly(now);
    const departure = timeOnly(start);
    const arrival = timeOnly(end);

    await connection.query(
      `INSERT INTO schedules(route_id, bus_id, departure_time, arrival_time, service_date, status)
       VALUES (?, ?, ?, ?, ?, 'Scheduled')
       ON DUPLICATE KEY UPDATE
         arrival_time = VALUES(arrival_time),
         status = 'Scheduled'`,
      [route.route_id, bus.bus_id, departure, arrival, serviceDate]
    );

    const [[schedule]] = await connection.query(
      `SELECT schedule_id
       FROM schedules
       WHERE route_id = ?
         AND bus_id = ?
         AND departure_time = ?
         AND service_date = ?
       LIMIT 1`,
      [route.route_id, bus.bus_id, departure, serviceDate]
    );

    const [[existingDuty]] = await connection.query(
      `SELECT duty_id
       FROM duty_assignments
       WHERE driver_id = ?
         AND bus_id = ?
         AND scheduled_date = ?
         AND status IN ('Scheduled', 'In-Progress')
       ORDER BY duty_id DESC
       LIMIT 1`,
      [driver.driver_id, bus.bus_id, serviceDate]
    );

    let dutyId = existingDuty?.duty_id;
    if (!dutyId) {
      const [[admin]] = await connection.query(
        `SELECT admin_id FROM admins ORDER BY admin_id LIMIT 1`
      );
      if (!admin) throw new Error('Need at least one admin before creating a demo duty.');

      const [insert] = await connection.query(
        `INSERT INTO duty_assignments(
           driver_id,
           bus_id,
           schedule_id,
           scheduled_date,
           scheduled_start_time,
           scheduled_end_time,
           actual_start_time,
           status,
           admin_id
         )
         VALUES (?, ?, ?, ?, ?, ?, NOW(), 'In-Progress', ?)`,
        [
          driver.driver_id,
          bus.bus_id,
          schedule.schedule_id,
          serviceDate,
          departure,
          arrival,
          admin.admin_id
        ]
      );
      dutyId = insert.insertId;
    } else {
      await connection.query(
        `UPDATE duty_assignments
         SET schedule_id = ?,
             scheduled_start_time = ?,
             scheduled_end_time = ?,
             actual_start_time = COALESCE(actual_start_time, NOW()),
             status = 'In-Progress'
         WHERE duty_id = ?`,
        [schedule.schedule_id, departure, arrival, dutyId]
      );
    }

    await connection.query(
      `UPDATE bus_locations
       SET is_active = FALSE
       WHERE bus_id = ?`,
      [bus.bus_id]
    );

    const midpointLat = (
      Number(route.start_latitude) + Number(route.destination_latitude)
    ) / 2;
    const midpointLng = (
      Number(route.start_longitude) + Number(route.destination_longitude)
    ) / 2;

    await connection.query(
      `INSERT INTO bus_locations(
         bus_id,
         driver_id,
         route_id,
         duty_id,
         latitude,
         longitude,
         speed,
         is_active
       )
       VALUES (?, ?, ?, ?, ?, ?, 28, TRUE)`,
      [
        bus.bus_id,
        driver.driver_id,
        route.route_id,
        dutyId,
        midpointLat,
        midpointLng
      ]
    );

    console.log(
      `Demo live duty ready: ${bus.bus_number} on ${route.name}, driver ${driver.name}, duty ${dutyId}.`
    );
  } finally {
    await connection.end();
  }
};

main().catch((error) => {
  console.error(`Demo seed failed: ${error.message}`);
  process.exit(1);
});
