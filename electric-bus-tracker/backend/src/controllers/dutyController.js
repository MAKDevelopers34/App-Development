const { callProcedure, firstResultSet, query } = require('../config/database');
const { formatDuty } = require('../utils/formatters');
const { refreshDutyStatuses } = require('../utils/dutyMaintenance');

const driverDutySelect = `
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
`;

const getTodayDuty = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const rows = await query(
      `${driverDutySelect}
       WHERE d.user_id = ?
         AND da.scheduled_date = CURDATE()
         AND da.status IN ('In-Progress', 'Scheduled')
       ORDER BY
         CASE da.status
           WHEN 'In-Progress' THEN 0
           ELSE 1
         END,
         da.scheduled_start_time
       LIMIT 1`,
      [req.user.userId]
    );
    const duty = rows[0];

    return res.json({
      success: true,
      duty: duty ? formatDuty(duty) : null
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const getUpcomingDuty = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const rows = await query(
      `${driverDutySelect}
       WHERE d.user_id = ?
         AND da.status = 'Scheduled'
         AND TIMESTAMP(da.scheduled_date, da.scheduled_start_time) > NOW()
       ORDER BY da.scheduled_date, da.scheduled_start_time
       LIMIT 1`,
      [req.user.userId]
    );
    const duty = rows[0];

    return res.json({
      success: true,
      duty: duty ? formatDuty(duty) : null
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const getMonthlyDuties = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const month = Number(req.query.month || new Date().getMonth() + 1);
    const year = Number(req.query.year || new Date().getFullYear());

    const result = await callProcedure('sp_get_driver_monthly_duties', [
      req.user.userId,
      month,
      year
    ]);

    const duties = (result[0] || []).map(formatDuty);
    const rawSummary = (result[1] || [])[0] || {};

    return res.json({
      success: true,
      duties,
      summary: {
        total: Number(rawSummary.total || 0),
        completed: Number(rawSummary.completed || 0),
        skipped: Number(rawSummary.skipped || 0),
        assigned: Number(rawSummary.assigned || 0),
        inProgress: Number(rawSummary.in_progress || 0)
      }
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

    if (!dutyId) {
      return res.status(400).json({ message: 'dutyId is required' });
    }

    const result = await callProcedure('sp_start_duty', [
      req.user.userId,
      Number(dutyId)
    ]);
    const affected = firstResultSet(result)[0]?.affected_rows || 0;

    if (affected === 0) {
      return res.status(400).json({
        message: 'Duty could not be started'
      });
    }

    return res.json({
      success: true,
      message: 'Duty started successfully'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const completeDuty = async (req, res) => {
  try {
    await refreshDutyStatuses();

    const { dutyId, note } = req.body;

    if (!dutyId) {
      return res.status(400).json({ message: 'dutyId is required' });
    }

    const result = await callProcedure('sp_complete_duty', [
      req.user.userId,
      Number(dutyId),
      note || 'Completed from driver app'
    ]);
    const affected = firstResultSet(result)[0]?.affected_rows || 0;

    if (affected === 0) {
      return res.status(400).json({
        message: 'Duty could not be completed'
      });
    }

    return res.json({
      success: true,
      message: 'Duty completed successfully'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

module.exports = {
  getTodayDuty,
  getUpcomingDuty,
  getMonthlyDuties,
  startDuty,
  completeDuty
};
