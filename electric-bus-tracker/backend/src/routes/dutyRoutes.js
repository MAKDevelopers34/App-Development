const express = require('express');
const {
  getTodayDuty,
  getUpcomingDuty,
  getMonthlyDuties,
  startDuty,
  completeDuty
} = require('../controllers/dutyController');
const { protect, driverOnly } = require('../middleware/auth');

const router = express.Router();

router.use(protect, driverOnly);

router.get('/today', getTodayDuty);
router.get('/upcoming', getUpcomingDuty);
router.get('/monthly', getMonthlyDuties);
router.post('/start', startDuty);
router.post('/complete', completeDuty);

module.exports = router;
