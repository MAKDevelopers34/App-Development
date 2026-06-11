const { callProcedure, firstResultSet } = require('../config/database');
const { formatDuty } = require('../utils/formatters');

const getTodayDuty = async (req, res) => {
  try {
    const result = await callProcedure('sp_get_driver_today_duty', [
      req.user.userId
    ]);
    const duty = firstResultSet(result)[0];

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
    const result = await callProcedure('sp_get_driver_upcoming_duty', [
      req.user.userId
    ]);
    const duty = firstResultSet(result)[0];

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
