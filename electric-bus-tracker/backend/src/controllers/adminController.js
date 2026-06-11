const bcrypt = require('bcryptjs');
const {
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

const dashboard = async (req, res) => {
  try {
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
  try {
    const {
      username,
      userId,
      password,
      email,
      fullName,
      phone,
      licenseNo,
      hireDate
    } = req.body;

    if (!username || !userId || !password || !email || !fullName) {
      return res.status(400).json({
        message: 'username, userId, password, email and fullName are required'
      });
    }

    const passwordHash = await bcrypt.hash(password, 10);
    const result = await callProcedure('sp_create_driver', [
      username,
      userId,
      fullName,
      email,
      phone || 'N/A',
      passwordHash,
      licenseNo || `DL-${userId}`,
      hireDate || new Date().toISOString().slice(0, 10)
    ]);
    const created = firstResultSet(result)[0];

    return res.status(201).json({
      success: true,
      message: 'Driver registered successfully',
      driverId: created?.driver_id,
      userDbId: created?.user_id
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
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
      req.body.email || current.email,
      info.phone || req.body.phone || current.contact,
      req.body.licenseNo || info.licenseNo || current.license_no,
      req.body.status || current.status
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
    const result = await callProcedure('sp_get_buses');
    const buses = firstResultSet(result).map(formatBus);

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

const getDuties = async (req, res) => {
  try {
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
    const { scheduledStartTime, scheduledEndTime } = req.body;

    if (!scheduledStartTime || !scheduledEndTime) {
      return res.status(400).json({
        message: 'scheduledStartTime and scheduledEndTime are required'
      });
    }

    await callProcedure('sp_update_duty_times', [
      dutyId,
      scheduledStartTime,
      scheduledEndTime
    ]);

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

module.exports = {
  dashboard,
  getDrivers,
  createDriver,
  updateDriver,
  setDriverStatus,
  getBuses,
  getDuties,
  createDuty,
  updateDuty
};
