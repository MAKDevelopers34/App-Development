const {
  callProcedure,
  firstResultSet,
  query
} = require('../config/database');
const {
  formatRoute,
  formatStop,
  formatSchedule,
  formatLocation
} = require('../utils/formatters');

const toNumberId = (value) => {
  const id = Number(value);
  return Number.isFinite(id) ? id : null;
};

const distanceKm = (aLat, aLng, bLat, bLng) => {
  const radius = 6371;
  const dLat = (bLat - aLat) * Math.PI / 180;
  const dLng = (bLng - aLng) * Math.PI / 180;
  const lat1 = aLat * Math.PI / 180;
  const lat2 = bLat * Math.PI / 180;

  const h =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);

  return radius * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
};

const getRoutes = async (req, res) => {
  try {
    const result = await callProcedure('sp_get_routes');
    const routes = firstResultSet(result).map((row) => formatRoute(row));

    return res.json({
      success: true,
      count: routes.length,
      routes
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const getRouteById = async (req, res) => {
  try {
    const routeId = toNumberId(req.params.routeId);
    if (!routeId) {
      return res.status(400).json({ message: 'Invalid route id' });
    }

    const result = await callProcedure('sp_get_route_by_id', [routeId]);
    const routeRow = Array.isArray(result[0]) ? result[0][0] : null;

    if (!routeRow) {
      return res.status(404).json({ message: 'Route not found' });
    }

    const stops = (result[1] || []).map(formatStop);
    const schedules = (result[2] || []).map(formatSchedule);

    return res.json({
      success: true,
      route: formatRoute(routeRow, stops, schedules)
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const searchRoutes = async (req, res) => {
  try {
    const term = String(req.query.query || '').trim();

    if (!term) {
      return getRoutes(req, res);
    }

    const result = await callProcedure('sp_search_routes', [term]);
    const routes = firstResultSet(result).map((row) => formatRoute(row));

    return res.json({
      success: true,
      count: routes.length,
      routes
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const deleteRoute = async (req, res) => {
  try {
    const routeId = toNumberId(req.params.routeId);
    if (!routeId) {
      return res.status(400).json({ message: 'Invalid route id' });
    }

    await callProcedure('sp_delete_route', [routeId]);
    return res.json({ success: true, message: 'Route deactivated' });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const createRoute = async (req, res) => {
  try {
    const {
      routeCode,
      routeName,
      startPoint,
      endPoint,
      totalDistance,
      estimatedTotalTime
    } = req.body;

    if (!routeCode || !routeName || !startPoint || !endPoint) {
      return res.status(400).json({
        message: 'routeCode, routeName, startPoint and endPoint are required'
      });
    }

    const result = await callProcedure('sp_create_route', [
      routeCode,
      routeName,
      startPoint.name,
      startPoint.latitude,
      startPoint.longitude,
      endPoint.name,
      endPoint.latitude,
      endPoint.longitude,
      totalDistance || 0,
      estimatedTotalTime || 0
    ]);
    const route = firstResultSet(result)[0];

    return res.status(201).json({
      success: true,
      message: 'Route created',
      routeId: route?.route_id
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const getRouteEat = async (req, res) => {
  try {
    const routeId = toNumberId(req.params.routeId);
    const stopId = toNumberId(req.params.stopId);

    if (!routeId || !stopId) {
      return res.status(400).json({ message: 'Invalid route or stop id' });
    }

    const stops = await query(
      `SELECT s.*, rsd.stop_order
       FROM route_stop_details rsd
       JOIN stops s ON s.stop_id = rsd.stop_id
       WHERE rsd.route_id = ? AND s.stop_id = ?
       LIMIT 1`,
      [routeId, stopId]
    );
    const targetStop = stops[0];

    if (!targetStop) {
      return res.status(404).json({ message: 'Stop not found on route' });
    }

    const active = await callProcedure('sp_get_buses_by_route', [routeId]);
    const buses = firstResultSet(active).map(formatLocation);

    const estimates = buses.map((bus) => {
      const km = distanceKm(
        bus.location.latitude,
        bus.location.longitude,
        Number(targetStop.latitude),
        Number(targetStop.longitude)
      );
      const speed = Math.max(Number(bus.speed || 0), 18);
      const minutes = Math.max(1, Math.round((km / speed) * 60));

      return {
        busId: bus.busNumber || bus.busId,
        routeId: bus.routeId,
        stopId: String(targetStop.stop_id),
        stopName: targetStop.name,
        distanceKm: Number(km.toFixed(2)),
        durationMinutes: minutes,
        durationText: minutes >= 60
          ? `${Math.floor(minutes / 60)}h ${minutes % 60}m`
          : `${minutes} min`
      };
    });

    return res.json({
      success: true,
      stop: formatStop(targetStop),
      estimates
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const getFavoriteRoutes = async (req, res) => res.json({
  success: true,
  routes: [],
  message: 'Passenger favorites are stored locally on the device.'
});

const saveFavoriteRoute = async (req, res) => res.json({
  success: true,
  message: 'Favorite route should be stored locally on the device.'
});

const removeFavoriteRoute = async (req, res) => res.json({
  success: true,
  message: 'Favorite route should be removed locally on the device.'
});

module.exports = {
  getRoutes,
  getRouteById,
  searchRoutes,
  createRoute,
  deleteRoute,
  getRouteEat,
  getFavoriteRoutes,
  saveFavoriteRoute,
  removeFavoriteRoute
};
