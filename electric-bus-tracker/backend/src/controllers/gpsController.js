const {
  callProcedure,
  firstResultSet,
  query
} = require('../config/database');
const { formatLocation } = require('../utils/formatters');
const { refreshDutyStatuses } = require('../utils/dutyMaintenance');

const activeBusRows = async (routeId = null) => {
  const params = [];
  let routeFilter = '';
  if (routeId != null) {
    routeFilter = 'AND latest.route_id = ?';
    params.push(Number(routeId));
  }

  return query(
    `SELECT
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
     JOIN duty_assignments da
       ON da.duty_id = latest.duty_id
      AND da.status = 'In-Progress'
     JOIN buses b ON b.bus_id = latest.bus_id
     JOIN drivers d ON d.driver_id = latest.driver_id
     JOIN users u ON u.user_id = d.user_id
     JOIN routes r ON r.route_id = latest.route_id
     WHERE latest.is_active = TRUE
       AND latest.recorded_at >= DATE_SUB(NOW(), INTERVAL 10 MINUTE)
       ${routeFilter}
     ORDER BY latest.recorded_at DESC`,
    params
  );
};

const updateLocation = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const {
      busId,
      routeId,
      dutyId,
      latitude,
      longitude,
      speed
    } = req.body;

    if (!busId || !routeId || !dutyId || latitude == null || longitude == null) {
      return res.status(400).json({
        message: 'busId, routeId, dutyId, latitude and longitude are required'
      });
    }

    const activeDuty = await query(
      `SELECT da.duty_id
       FROM duty_assignments da
       JOIN drivers d ON d.driver_id = da.driver_id
       JOIN schedules s ON s.schedule_id = da.schedule_id
       WHERE da.duty_id = ?
         AND d.user_id = ?
         AND da.bus_id = ?
         AND s.route_id = ?
         AND da.status = 'In-Progress'
       LIMIT 1`,
      [Number(dutyId), req.user.userId, Number(busId), Number(routeId)]
    );

    if (!activeDuty[0]) {
      return res.status(400).json({
        message: 'Location can only be shared for an in-progress duty'
      });
    }

    const result = await callProcedure('sp_update_bus_location', [
      req.user.userId,
      Number(busId),
      Number(routeId),
      Number(dutyId),
      Number(latitude),
      Number(longitude),
      Number(speed || 0)
    ]);
    const created = firstResultSet(result)[0];

    return res.json({
      success: true,
      message: 'Location updated',
      locationId: created?.location_id
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const getActiveBuses = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const buses = (await activeBusRows()).map(formatLocation);

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

const getBusesByRoute = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const routeId = Number(req.params.routeId);
    const buses = (await activeBusRows(routeId)).map(formatLocation);

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

const startDuty = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const { dutyId } = req.body;
    const result = await callProcedure('sp_start_duty', [
      req.user.userId,
      Number(dutyId)
    ]);
    const affected = firstResultSet(result)[0]?.affected_rows || 0;

    return res.json({
      success: affected > 0,
      message: affected > 0
        ? 'Duty started successfully'
        : 'Duty could not be started'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const endDuty = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const { dutyId } = req.body;
    const result = await callProcedure('sp_complete_duty', [
      req.user.userId,
      Number(dutyId),
      'Completed from GPS endpoint'
    ]);
    const affected = firstResultSet(result)[0]?.affected_rows || 0;

    return res.json({
      success: affected > 0,
      message: affected > 0
        ? 'Duty ended successfully'
        : 'Duty could not be ended'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

module.exports = {
  updateLocation,
  getActiveBuses,
  getBusesByRoute,
  startDuty,
  endDuty
};
