const bcrypt = require('bcryptjs');
const {
  getPool,
  query,
  callProcedure,
  firstResultSet
} = require('../config/database');
const {
  formatDriver,
  formatBus,
  formatDuty,
  formatRoute
} = require('../utils/formatters');
const { refreshDutyStatuses } = require('../utils/dutyMaintenance');

const normalizeUsername = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, '_')
  .replace(/^_+|_+$/g, '');

const generateDriverUsername = async (fullName) => {
  const baseName = normalizeUsername(fullName) || 'driver';
  const base = baseName.startsWith('driver_') ? baseName : `driver_${baseName}`;

  for (let suffix = 0; suffix < 100; suffix += 1) {
    const candidate = suffix === 0 ? base : `${base}_${suffix + 1}`;
    const rows = await query(
      'SELECT COUNT(*) AS count FROM users WHERE username = ?',
      [candidate]
    );
    if (Number(rows[0]?.count || 0) === 0) return candidate;
  }

  return `driver_${Date.now()}`;
};

const generateDriverUserCode = async () => {
  const rows = await query(
    `SELECT MAX(CAST(SUBSTRING(user_code, 5) AS UNSIGNED)) AS max_code
     FROM users
     WHERE role = 'Driver'
       AND user_code REGEXP '^DRV-[0-9]+$'`
  );
  const next = Number(rows[0]?.max_code || 0) + 1;
  return `DRV-${String(next).padStart(3, '0')}`;
};

const sqlDate = (value) => {
  if (!value) return null;
  return value instanceof Date ? value.toISOString().slice(0, 10) : String(value).slice(0, 10);
};

const sqlTime = (value) => String(value || '').slice(0, 5);

const normalizeBusStatus = (value, fallback = 'Active') => {
  const status = String(value || fallback).trim().toLowerCase();
  if (status === 'maintenance') return 'Maintenance';
  if (status === 'active') return 'Active';
  return fallback;
};

const busRegistrationDate = (value) => (
  value ? sqlDate(value) : new Date().toISOString().slice(0, 10)
);

const assertActiveBus = async (busId) => {
  const rows = await query(
    `SELECT bus_id
     FROM buses
     WHERE bus_id = ?
       AND status = 'Active'
     LIMIT 1`,
    [Number(busId)]
  );
  return Boolean(rows[0]);
};

const hasColumn = async (connection, tableName, columnName) => {
  const [rows] = await connection.execute(
    `SELECT COUNT(*) AS count
     FROM information_schema.columns
     WHERE table_schema = DATABASE()
       AND table_name = ?
       AND column_name = ?`,
    [tableName, columnName]
  );
  return Number(rows[0]?.count || 0) > 0;
};

const dashboard = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const statsRows = await query('SELECT * FROM view_admin_dashboard_stats');
    const routesResult = await callProcedure('sp_get_routes');

    return res.json({
      success: true,
      stats: statsRows[0] || {},
      routes: firstResultSet(routesResult).map((row) => formatRoute(row))
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const getDrivers = async (req, res) => {
  try {
    const result = await callProcedure('sp_get_drivers');
    const drivers = firstResultSet(result).map(formatDriver);

    return res.json({
      success: true,
      count: drivers.length,
      drivers
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const createDriver = async (req, res) => {
  let connection;

  try {
    const {
      username,
      userId,
      password,
      email,
      fullName,
      phone,
      licenseNo,
      cnic,
      address,
      hireDate
    } = req.body;

    if (!email || !fullName) {
      return res.status(400).json({
        message: 'email and fullName are required'
      });
    }

    const driverUsername = username || await generateDriverUsername(fullName);
    const driverUserCode = userId || await generateDriverUserCode();
    const defaultPassword = password || 'driver123';
    const passwordHash = await bcrypt.hash(defaultPassword, 10);
    const normalizedEmail = String(email).trim().toLowerCase();
    const normalizedUsername = String(driverUsername).trim().toLowerCase();

    const existing = await query(
      `SELECT username, user_code, email
       FROM users
       WHERE username = ?
          OR user_code = ?
          OR LOWER(email) = ?
       LIMIT 1`,
      [normalizedUsername, driverUserCode, normalizedEmail]
    );

    if (existing[0]) {
      return res.status(409).json({
        message: 'A driver with this username, user ID, or email already exists'
      });
    }

    connection = await getPool().getConnection();
    await connection.beginTransaction();

    const [userResult] = await connection.execute(
      `INSERT INTO users(
         username,
         user_code,
         name,
         email,
         contact,
         password_hash,
         role
       )
       VALUES (?, ?, ?, ?, ?, ?, 'Driver')`,
      [
        normalizedUsername,
        driverUserCode,
        fullName,
        normalizedEmail,
        phone || 'N/A',
        passwordHash
      ]
    );
    const userDbId = userResult.insertId;
    const driverAddressExists = await hasColumn(
      connection,
      'drivers',
      'address'
    );
    const driverValues = [
      userDbId,
      licenseNo || cnic || `DL-${driverUserCode}`,
      hireDate || new Date().toISOString().slice(0, 10)
    ];
    const driverSql = driverAddressExists
      ? `INSERT INTO drivers(user_id, license_no, hire_date, address)
         VALUES (?, ?, ?, ?)`
      : `INSERT INTO drivers(user_id, license_no, hire_date)
         VALUES (?, ?, ?)`;
    if (driverAddressExists) driverValues.push(address || '');

    const [driverResult] = await connection.execute(driverSql, driverValues);
    await connection.commit();

    return res.status(201).json({
      success: true,
      message: 'Driver registered successfully',
      driverId: driverResult.insertId,
      userDbId,
      credentials: {
        username: normalizedUsername,
        userId: driverUserCode,
        temporaryPassword: password ? null : defaultPassword
      }
    });
  } catch (error) {
    if (connection) await connection.rollback();

    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  } finally {
    if (connection) connection.release();
  }
};

const updateDriver = async (req, res) => {
  try {
    const driverId = Number(req.params.driverId);
    const existing = await query(
      `SELECT d.*, u.name, u.email, u.contact
       FROM drivers d
       JOIN users u ON u.user_id = d.user_id
       WHERE d.driver_id = ?`,
      [driverId]
    );

    if (!existing[0]) {
      return res.status(404).json({ message: 'Driver not found' });
    }

    const info = req.body.profileInfo || {};
    const current = existing[0];

    await callProcedure('sp_update_driver', [
      driverId,
      info.fullName || req.body.fullName || current.name,
      info.email || req.body.email || current.email,
      info.phone || req.body.phone || current.contact,
      req.body.licenseNo || req.body.cnic || info.licenseNo || info.cnic || current.license_no,
      req.body.status || info.status || current.status,
      req.body.address || info.address || current.address || ''
    ]);

    return res.json({
      success: true,
      message: 'Driver updated successfully'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const deleteDriver = async (req, res) => {
  try {
    const driverId = Number(req.params.driverId);
    const existing = await query(
      `SELECT d.driver_id
       FROM drivers d
       JOIN users u ON u.user_id = d.user_id
       WHERE d.driver_id = ?
         AND u.deletion_date IS NULL`,
      [driverId]
    );

    if (!existing[0]) {
      return res.status(404).json({ message: 'Driver not found' });
    }

    await query(
      `UPDATE users u
       JOIN drivers d ON d.user_id = u.user_id
       SET u.account_status = 'Inactive',
           u.deletion_date = NOW(),
           d.status = 'Off-Duty'
       WHERE d.driver_id = ?`,
      [driverId]
    );

    return res.json({
      success: true,
      message: 'Driver removed successfully'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const setDriverStatus = async (req, res) => {
  try {
    const driverId = Number(req.params.driverId);
    const accountStatus = req.params.action === 'activate'
      ? 'Active'
      : 'Inactive';

    await callProcedure('sp_set_driver_account_status', [
      driverId,
      accountStatus
    ]);

    return res.json({
      success: true,
      message: `Driver ${accountStatus.toLowerCase()}`
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const getBuses = async (req, res) => {
  try {
    const rows = await query(
      `SELECT *
       FROM buses
       WHERE status <> 'Inactive'
       ORDER BY bus_number`
    );
    const buses = rows.map(formatBus);

    return res.json({
      success: true,
      count: buses.length,
      buses
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const createBus = async (req, res) => {
  try {
    const busNumber = String(req.body.busNumber || req.body.bus_number || '').trim();
    const capacity = Number(req.body.capacity || 40);
    const model = String(req.body.model || 'Electric Bus').trim();
    const status = normalizeBusStatus(req.body.status);
    const registrationDate = busRegistrationDate(req.body.registrationDate);

    if (!busNumber) {
      return res.status(400).json({ message: 'Bus number is required' });
    }
    if (!Number.isInteger(capacity) || capacity <= 0) {
      return res.status(400).json({ message: 'Capacity must be a positive number' });
    }

    const duplicate = await query(
      `SELECT bus_id
       FROM buses
       WHERE bus_number = ?
       LIMIT 1`,
      [busNumber]
    );

    if (duplicate[0]) {
      return res.status(409).json({ message: 'Bus number already exists' });
    }

    const result = await query(
      `INSERT INTO buses(bus_number, capacity, model, status, registration_date)
       VALUES (?, ?, ?, ?, ?)`,
      [busNumber, capacity, model || 'Electric Bus', status, registrationDate]
    );

    return res.status(201).json({
      success: true,
      message: 'Bus added successfully',
      busId: result.insertId
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const updateBus = async (req, res) => {
  try {
    const busId = Number(req.params.busId);
    const existingRows = await query(
      `SELECT *
       FROM buses
       WHERE bus_id = ?
         AND status <> 'Inactive'
       LIMIT 1`,
      [busId]
    );
    const existing = existingRows[0];

    if (!existing) {
      return res.status(404).json({ message: 'Bus not found' });
    }

    const busNumber = String(req.body.busNumber || existing.bus_number).trim();
    const capacity = Number(req.body.capacity || existing.capacity);
    const model = String(req.body.model || existing.model || 'Electric Bus').trim();
    const status = normalizeBusStatus(req.body.status, existing.status);
    const registrationDate = busRegistrationDate(
      req.body.registrationDate || existing.registration_date
    );

    if (!busNumber) {
      return res.status(400).json({ message: 'Bus number is required' });
    }
    if (!Number.isInteger(capacity) || capacity <= 0) {
      return res.status(400).json({ message: 'Capacity must be a positive number' });
    }

    const duplicate = await query(
      `SELECT bus_id
       FROM buses
       WHERE bus_number = ?
         AND bus_id <> ?
       LIMIT 1`,
      [busNumber, busId]
    );

    if (duplicate[0]) {
      return res.status(409).json({ message: 'Bus number already exists' });
    }

    await query(
      `UPDATE buses
       SET bus_number = ?,
           capacity = ?,
           model = ?,
           status = ?,
           registration_date = ?
       WHERE bus_id = ?`,
      [busNumber, capacity, model || 'Electric Bus', status, registrationDate, busId]
    );

    return res.json({
      success: true,
      message: 'Bus updated successfully'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const deleteBus = async (req, res) => {
  try {
    const busId = Number(req.params.busId);
    const result = await query(
      `UPDATE buses
       SET status = 'Inactive'
       WHERE bus_id = ?
         AND status <> 'Inactive'`,
      [busId]
    );

    if (result.affectedRows === 0) {
      return res.status(404).json({ message: 'Bus not found' });
    }

    await query(
      `UPDATE bus_locations
       SET is_active = FALSE
       WHERE bus_id = ?`,
      [busId]
    );

    return res.json({
      success: true,
      message: 'Bus removed from active list'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const getDuties = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const result = await callProcedure('sp_get_admin_duties');
    const duties = firstResultSet(result).map(formatDuty);

    return res.json({
      success: true,
      count: duties.length,
      duties
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const createDuty = async (req, res) => {
  try {
    const {
      driverId,
      busId,
      routeId,
      scheduledDate,
      scheduledStartTime,
      scheduledEndTime
    } = req.body;

    if (!driverId || !busId || !routeId || !scheduledDate ||
        !scheduledStartTime || !scheduledEndTime) {
      return res.status(400).json({
        message: 'driverId, busId, routeId, date and times are required'
      });
    }

    if (!await assertActiveBus(busId)) {
      return res.status(400).json({
        message: 'Only active buses can be assigned to duties'
      });
    }

    const result = await callProcedure('sp_create_duty', [
      Number(driverId),
      Number(busId),
      Number(routeId),
      scheduledDate,
      scheduledStartTime,
      scheduledEndTime,
      req.user.adminId
    ]);
    const created = firstResultSet(result)[0];

    return res.status(201).json({
      success: true,
      message: 'Duty assigned successfully',
      dutyId: created?.duty_id
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Error assigning duty',
      error: error.message
    });
  }
};

const updateDuty = async (req, res) => {
  try {
    const dutyId = Number(req.params.dutyId);
    const existingRows = await query(
      `SELECT
         da.*,
         s.route_id
       FROM duty_assignments da
       JOIN schedules s ON s.schedule_id = da.schedule_id
       WHERE da.duty_id = ?`,
      [dutyId]
    );

    const existing = existingRows[0];
    if (!existing) {
      return res.status(404).json({ message: 'Duty not found' });
    }

    const driverId = Number(req.body.driverId || existing.driver_id);
    const busId = Number(req.body.busId || existing.bus_id);
    const routeId = Number(req.body.routeId || existing.route_id);
    const scheduledDate = req.body.scheduledDate || sqlDate(existing.scheduled_date);
    const scheduledStartTime = req.body.scheduledStartTime || sqlTime(existing.scheduled_start_time);
    const scheduledEndTime = req.body.scheduledEndTime || sqlTime(existing.scheduled_end_time);

    if (!driverId || !busId || !routeId || !scheduledDate ||
        !scheduledStartTime || !scheduledEndTime) {
      return res.status(400).json({
        message: 'driverId, busId, routeId, date and times are required'
      });
    }

    if (existing.status !== 'Scheduled') {
      return res.status(400).json({
        message: 'Only scheduled duties can be edited'
      });
    }

    if (!await assertActiveBus(busId)) {
      return res.status(400).json({
        message: 'Only active buses can be assigned to duties'
      });
    }

    let scheduleId;
    const schedules = await query(
      `SELECT schedule_id
       FROM schedules
       WHERE route_id = ?
         AND bus_id = ?
         AND service_date = ?
         AND departure_time = ?
       LIMIT 1`,
      [routeId, busId, scheduledDate, scheduledStartTime]
    );

    if (schedules[0]) {
      scheduleId = schedules[0].schedule_id;
      await query(
        `UPDATE schedules
         SET arrival_time = ?,
             status = 'Scheduled'
         WHERE schedule_id = ?`,
        [scheduledEndTime, scheduleId]
      );
    } else {
      const insert = await query(
        `INSERT INTO schedules(route_id, bus_id, departure_time, arrival_time, service_date)
         VALUES (?, ?, ?, ?, ?)`,
        [routeId, busId, scheduledStartTime, scheduledEndTime, scheduledDate]
      );
      scheduleId = insert.insertId;
    }

    await query(
      `UPDATE duty_assignments
       SET driver_id = ?,
           bus_id = ?,
           schedule_id = ?,
           scheduled_date = ?,
           scheduled_start_time = ?,
           scheduled_end_time = ?
       WHERE duty_id = ?`,
      [
        driverId,
        busId,
        scheduleId,
        scheduledDate,
        scheduledStartTime,
        scheduledEndTime,
        dutyId
      ]
    );

    return res.json({
      success: true,
      message: 'Duty updated successfully'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Error updating duty',
      error: error.message
    });
  }
};

const deleteDuty = async (req, res) => {
  try {
    const dutyId = Number(req.params.dutyId);

    await query(
      `UPDATE duty_assignments
       SET status = 'Skipped',
           completion_note = COALESCE(completion_note, 'Removed by admin')
       WHERE duty_id = ?
         AND status IN ('Scheduled', 'Skipped')`,
      [dutyId]
    );

    return res.json({
      success: true,
      message: 'Duty removed from active schedule'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Error removing duty',
      error: error.message
    });
  }
};

module.exports = {
  dashboard,
  getDrivers,
  createDriver,
  updateDriver,
  deleteDriver,
  setDriverStatus,
  getBuses,
  createBus,
  updateBus,
  deleteBus,
  getDuties,
  createDuty,
  updateDuty,
  deleteDuty
};
