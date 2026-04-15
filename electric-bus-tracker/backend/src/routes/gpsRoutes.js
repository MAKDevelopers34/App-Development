const express = require('express');
const router = express.Router();
const {
  updateLocation,
  getActiveBuses,
  getBusesByRoute,
  startDuty,
  endDuty,
  getAblyToken
} = require('../controllers/gpsController');
const { protect, driverOnly } = require('../middleware/auth');

router.post('/update-location', protect, driverOnly, updateLocation);
router.get('/active-buses', protect, getActiveBuses);
router.get('/route/:routeId', protect, getBusesByRoute);
router.post('/start-duty', protect, driverOnly, startDuty);
router.post('/end-duty', protect, driverOnly, endDuty);
router.get('/ably-token', protect, getAblyToken);

module.exports = router;