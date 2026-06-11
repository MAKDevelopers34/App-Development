const express = require('express');
const router = express.Router();
const {
  updateLocation,
  getActiveBuses,
  getBusesByRoute,
  startDuty,
  endDuty
} = require('../controllers/gpsController');
const { protect, driverOnly } = require('../middleware/auth');

router.get('/active-buses', getActiveBuses);
router.get('/route/:routeId', getBusesByRoute);
router.post('/update-location', protect, driverOnly, updateLocation);
router.post('/start-duty', protect, driverOnly, startDuty);
router.post('/end-duty', protect, driverOnly, endDuty);

module.exports = router;
