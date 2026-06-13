const {
  callProcedure,
  firstResultSet,
  getPool,
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

const codeFromName = (name) => String(name || 'STOP')
  .toUpperCase()
  .replace(/[^A-Z0-9]+/g, '-')
  .replace(/^-+|-+$/g, '')
  .slice(0, 12) || 'STOP';

const getStops = async (req, res) => {
  try {
    const stops = await query(
      `SELECT
         stop_id,
         stop_code,
         name,
         latitude,
         longitude,
         creation_date,
         status
       FROM stops
       WHERE status = 'Active'
         AND deletion_date IS NULL
       ORDER BY name`
    );

    return res.json({
      success: true,
      count: stops.length,
      stops: stops.map(formatStop)
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const findOrCreateStop = async (runQuery, point, routeId, index) => {
  if (point.stopId) {
    const existingById = await runQuery(
      `SELECT stop_id
       FROM stops
       WHERE stop_id = ?
         AND deletion_date IS NULL
       LIMIT 1`,
      [Number(point.stopId)]
    );
    if (existingById[0]) return existingById[0].stop_id;
  }

  const existingByName = await runQuery(
    `SELECT stop_id
     FROM stops
     WHERE LOWER(name) = LOWER(?)
       AND deletion_date IS NULL
     LIMIT 1`,
    [point.name]
  );
  if (existingByName[0]) return existingByName[0].stop_id;

  const createdStop = await runQuery(
    `INSERT INTO stops(stop_code, name, latitude, longitude)
     VALUES (?, ?, ?, ?)`,
    [
      `${codeFromName(point.name)}-${routeId}-${index}`,
      point.name,
      point.latitude,
      point.longitude
    ]
  );

  return createdStop.insertId;
};

const saveRouteStops = async ({
  runQuery = query,
  routeId,
  startPoint,
  endPoint,
  stops,
  totalDistance,
  estimatedTotalTime
}) => {
  const orderedPoints = [startPoint, ...stops, endPoint].filter((point) => {
    return point?.name && point.latitude != null && point.longitude != null;
  });
  const linkedStops = new Set();

  for (let index = 0; index < orderedPoints.length; index += 1) {
    const point = orderedPoints[index];
    const stopId = await findOrCreateStop(runQuery, point, routeId, index + 1);
    if (linkedStops.has(stopId)) continue;
    linkedStops.add(stopId);

    const stopDistance = index === 0
      ? 0
      : distanceKm(
        Number(startPoint.latitude),
        Number(startPoint.longitude),
        Number(point.latitude),
        Number(point.longitude)
      );
    const totalKm = Number(totalDistance || 0);
    const totalMinutes = Number(estimatedTotalTime || 0);
    const estimatedMinutes = index === 0
      ? 0
      : totalKm > 0 && totalMinutes > 0
        ? Math.round((stopDistance / totalKm) * totalMinutes)
        : 0;

    await runQuery(
      `INSERT INTO route_stop_details(
         route_id,
         stop_id,
         stop_order,
         distance_from_start,
         estimated_minutes_from_start
       )
       VALUES (?, ?, ?, ?, ?)`,
      [
        routeId,
        stopId,
        linkedStops.size,
        Number(stopDistance.toFixed(2)),
        estimatedMinutes
      ]
    );
  }
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
  let connection;

  try {
    const {
      routeCode,
      routeName,
      startPoint,
      endPoint,
      totalDistance,
      estimatedTotalTime,
      stops = []
    } = req.body;

    if (!routeCode || !routeName || !startPoint || !endPoint) {
      return res.status(400).json({
        message: 'routeCode, routeName, startPoint and endPoint are required'
      });
    }

    connection = await getPool().getConnection();
    await connection.beginTransaction();

    const [result] = await connection.query('CALL sp_create_route(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [
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
    const routeId = route?.route_id;

    if (!routeId) {
      throw new Error('Route was not created');
    }

    const runQuery = async (sql, params = []) => {
      const [rows] = await connection.execute(sql, params);
      return rows;
    };

    await saveRouteStops({
      runQuery,
      routeId,
      startPoint,
      endPoint,
      stops: Array.isArray(stops) ? stops : [],
      totalDistance,
      estimatedTotalTime
    });

    await connection.commit();

    return res.status(201).json({
      success: true,
      message: 'Route created',
      routeId
    });
  } catch (error) {
    if (connection) {
      await connection.rollback();
    }

    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  } finally {
    if (connection) connection.release();
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
  getStops,
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
