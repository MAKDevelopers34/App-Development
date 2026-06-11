const {
  callProcedure,
  firstResultSet
} = require('../config/database');
const { formatLocation } = require('../utils/formatters');

const updateLocation = async (req, res) => {
  try {
    const {
      busId,
      routeId,
      dutyId,
      latitude,
      longitude,
      speed
    } = req.body;

    if (!busId || !routeId || latitude == null || longitude == null) {
      return res.status(400).json({
        message: 'busId, routeId, latitude and longitude are required'
      });
    }

    const result = await callProcedure('sp_update_bus_location', [
      req.user.userId,
      Number(busId),
      Number(routeId),
      dutyId ? Number(dutyId) : null,
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
    const result = await callProcedure('sp_get_active_buses');
    const buses = firstResultSet(result).map(formatLocation);

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
    const routeId = Number(req.params.routeId);
    const result = await callProcedure('sp_get_buses_by_route', [routeId]);
    const buses = firstResultSet(result).map(formatLocation);

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
