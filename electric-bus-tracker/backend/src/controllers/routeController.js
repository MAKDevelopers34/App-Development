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
const { refreshDutyStatuses } = require('../utils/dutyMaintenance');

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

const durationText = (minutes) => {
  const safeMinutes = Math.max(1, Math.round(Number(minutes || 0)));
  if (safeMinutes < 60) return `${safeMinutes} min`;
  const hours = Math.floor(safeMinutes / 60);
  const remainder = safeMinutes % 60;
  return remainder === 0 ? `${hours}h` : `${hours}h ${remainder}m`;
};

const projectToSegment = (start, end, target) => {
  const latScale = Math.cos(start.latitude * Math.PI / 180);
  const ax = start.longitude * latScale;
  const ay = start.latitude;
  const bx = end.longitude * latScale;
  const by = end.latitude;
  const px = target.longitude * latScale;
  const py = target.latitude;
  const dx = bx - ax;
  const dy = by - ay;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return 0;
  return Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lengthSquared));
};

const interpolatePoint = (start, end, amount) => ({
  latitude: start.latitude + ((end.latitude - start.latitude) * amount),
  longitude: start.longitude + ((end.longitude - start.longitude) * amount)
});

const progressAlongRouteMeters = (points, target) => {
  if (points.length < 2) return null;

  let bestDistance = Infinity;
  let bestProgress = 0;
  let cumulative = 0;

  for (let index = 0; index < points.length - 1; index += 1) {
    const start = points[index];
    const end = points[index + 1];
    const segmentMeters = distanceKm(
      start.latitude,
      start.longitude,
      end.latitude,
      end.longitude
    ) * 1000;
    if (segmentMeters <= 0) continue;

    const amount = projectToSegment(start, end, target);
    const projected = interpolatePoint(start, end, amount);
    const distanceToSegment = distanceKm(
      target.latitude,
      target.longitude,
      projected.latitude,
      projected.longitude
    ) * 1000;

    if (distanceToSegment < bestDistance) {
      bestDistance = distanceToSegment;
      bestProgress = cumulative + (segmentMeters * amount);
    }

    cumulative += segmentMeters;
  }

  return bestProgress;
};

const averageRouteSpeed = (route) => {
  const distance = Number(route.distance || 0);
  const minutes = Number(route.estimated_duration || 0);
  if (distance > 0 && minutes > 0) return Math.max(12, distance / (minutes / 60));
  return 24;
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
         AND status = 'Active'
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
       AND status = 'Active'
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
    const rows = await query(
      `SELECT
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
       ORDER BY r.name`
    );
    const routes = rows.map((row) => formatRoute(row));

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

    const routeRows = await query(
      `SELECT *
       FROM routes
       WHERE route_id = ?
         AND status = 'Active'
       LIMIT 1`,
      [routeId]
    );
    const routeRow = routeRows[0];

    if (!routeRow) {
      return res.status(404).json({ message: 'Route not found' });
    }

    const stopRows = await query(
      `SELECT
         s.stop_id,
         s.stop_code,
         s.name,
         s.latitude,
         s.longitude,
         rsd.stop_order,
         rsd.distance_from_start,
         rsd.estimated_minutes_from_start
       FROM route_stop_details rsd
       JOIN stops s ON s.stop_id = rsd.stop_id
       WHERE rsd.route_id = ?
         AND s.status = 'Active'
         AND s.deletion_date IS NULL
       ORDER BY rsd.stop_order`,
      [routeId]
    );
    const scheduleRows = await query(
      `SELECT
         schedule_id,
         bus_id,
         departure_time,
         arrival_time,
         service_date,
         status
       FROM schedules
       WHERE route_id = ?
       ORDER BY service_date, departure_time`,
      [routeId]
    );
    const stops = stopRows.map(formatStop);
    const schedules = scheduleRows.map(formatSchedule);

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

    const rows = await query(
      `SELECT DISTINCT
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
         r.status
       FROM routes r
       LEFT JOIN route_stop_details rsd ON rsd.route_id = r.route_id
       LEFT JOIN stops s ON s.stop_id = rsd.stop_id
        AND s.status = 'Active'
        AND s.deletion_date IS NULL
       WHERE r.status = 'Active'
         AND (
           LOWER(r.name) LIKE CONCAT('%', LOWER(?), '%')
           OR LOWER(r.starting_point) LIKE CONCAT('%', LOWER(?), '%')
           OR LOWER(r.destination_point) LIKE CONCAT('%', LOWER(?), '%')
           OR LOWER(s.name) LIKE CONCAT('%', LOWER(?), '%')
         )
       ORDER BY r.name`,
      [term, term, term, term]
    );
    const routes = rows.map((row) => formatRoute(row));

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

    const result = await query(
      `UPDATE routes
       SET status = 'Inactive'
       WHERE route_id = ?
         AND status = 'Active'`,
      [routeId]
    );
    if (result.affectedRows === 0) {
      return res.status(404).json({ message: 'Route not found' });
    }

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
    await refreshDutyStatuses();

    const routeId = toNumberId(req.params.routeId);
    const stopId = toNumberId(req.params.stopId);

    if (!routeId || !stopId) {
      return res.status(400).json({ message: 'Invalid route or stop id' });
    }

    const routeRows = await query(
      `SELECT *
       FROM routes
       WHERE route_id = ?
         AND status = 'Active'
       LIMIT 1`,
      [routeId]
    );
    const route = routeRows[0];
    if (!route) {
      return res.status(404).json({ message: 'Route not found' });
    }

    const stops = await query(
      `SELECT
         s.*,
         rsd.stop_order,
         rsd.distance_from_start,
         rsd.estimated_minutes_from_start
       FROM route_stop_details rsd
       JOIN stops s ON s.stop_id = rsd.stop_id
       WHERE rsd.route_id = ?
         AND s.status = 'Active'
         AND s.deletion_date IS NULL
       ORDER BY rsd.stop_order`,
      [routeId]
    );
    const targetStop = stops.find((stop) => Number(stop.stop_id) === stopId);

    if (!targetStop) {
      return res.status(404).json({ message: 'Stop not found on route' });
    }

    const routePoints = [
      {
        latitude: Number(route.start_latitude),
        longitude: Number(route.start_longitude)
      },
      ...stops.map((stop) => ({
        latitude: Number(stop.latitude),
        longitude: Number(stop.longitude)
      })),
      {
        latitude: Number(route.destination_latitude),
        longitude: Number(route.destination_longitude)
      }
    ];
    const targetPoint = {
      latitude: Number(targetStop.latitude),
      longitude: Number(targetStop.longitude)
    };
    const targetProgress = progressAlongRouteMeters(routePoints, targetPoint);
    const routeSpeed = averageRouteSpeed(route);

    const busRows = await query(
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
       JOIN buses b
         ON b.bus_id = latest.bus_id
        AND b.status = 'Active'
       JOIN drivers d ON d.driver_id = latest.driver_id
       JOIN users u ON u.user_id = d.user_id
       JOIN routes r ON r.route_id = latest.route_id
       WHERE latest.is_active = TRUE
         AND latest.route_id = ?
         AND latest.recorded_at >= DATE_SUB(NOW(), INTERVAL 10 MINUTE)
       ORDER BY latest.recorded_at DESC`,
      [routeId]
    );
    const buses = busRows.map(formatLocation);

    const estimates = buses.map((bus) => {
      const busPoint = {
        latitude: bus.location.latitude,
        longitude: bus.location.longitude
      };
      const busProgress = progressAlongRouteMeters(routePoints, busPoint);
      if (targetProgress == null || busProgress == null) return null;

      const remainingMeters = targetProgress - busProgress;
      if (remainingMeters <= 35) return null;

      const speed = Math.max(Number(bus.speed || 0), routeSpeed);
      const km = remainingMeters / 1000;
      const minutes = Math.max(1, Math.round((km / speed) * 60));

      return {
        busId: bus.busNumber || `Bus ${bus.busId}`,
        busNumber: bus.busNumber,
        driverName: bus.driverName,
        routeId: bus.routeId,
        stopId: String(targetStop.stop_id),
        stopName: targetStop.name,
        distanceKm: Number(km.toFixed(2)),
        durationMinutes: minutes,
        durationText: durationText(minutes),
        source: 'live'
      };
    }).filter(Boolean);

    if (estimates.length === 0) {
      const scheduled = await query(
        `SELECT
           da.duty_id,
           b.bus_number,
           u.name AS driver_name,
           TIMESTAMPDIFF(
             MINUTE,
             NOW(),
             TIMESTAMP(da.scheduled_date, da.scheduled_start_time)
           ) AS minutes_until_start
         FROM duty_assignments da
         JOIN schedules s ON s.schedule_id = da.schedule_id
         JOIN buses b
           ON b.bus_id = da.bus_id
          AND b.status = 'Active'
         JOIN drivers d ON d.driver_id = da.driver_id
         JOIN users u ON u.user_id = d.user_id
         WHERE s.route_id = ?
           AND da.status = 'Scheduled'
           AND TIMESTAMP(da.scheduled_date, da.scheduled_start_time)
             >= DATE_SUB(NOW(), INTERVAL 25 MINUTE)
         ORDER BY da.scheduled_date, da.scheduled_start_time
         LIMIT 3`,
        [routeId]
      );
      const averageMinutesToStop = Math.max(
        1,
        Number(targetStop.estimated_minutes_from_start || 0) ||
          Math.round(((targetProgress || 0) / 1000 / routeSpeed) * 60)
      );

      for (const duty of scheduled) {
        const minutes = Math.max(
          1,
          Number(duty.minutes_until_start || 0) + averageMinutesToStop
        );
        estimates.push({
          busId: duty.bus_number || `Duty ${duty.duty_id}`,
          busNumber: duty.bus_number,
          driverName: duty.driver_name,
          routeId: String(routeId),
          stopId: String(targetStop.stop_id),
          stopName: targetStop.name,
          distanceKm: Number(((targetProgress || 0) / 1000).toFixed(2)),
          durationMinutes: minutes,
          durationText: durationText(minutes),
          source: 'scheduled'
        });
      }

      if (estimates.length === 0) {
        estimates.push({
          busId: 'Average ETA',
          routeId: String(routeId),
          stopId: String(targetStop.stop_id),
          stopName: targetStop.name,
          distanceKm: Number(((targetProgress || 0) / 1000).toFixed(2)),
          durationMinutes: averageMinutesToStop,
          durationText: durationText(averageMinutesToStop),
          source: 'average'
        });
      }
    }

    estimates.sort((a, b) => a.durationMinutes - b.durationMinutes);

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
