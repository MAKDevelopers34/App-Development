const express = require('express');
const {
  dashboard,
  getDrivers,
  createDriver,
  updateDriver,
  deleteDriver,
  setDriverStatus,
  getBuses,
  getDuties,
  createDuty,
  updateDuty,
  deleteDuty
} = require('../controllers/adminController');
const { protect, adminOnly } = require('../middleware/auth');

const router = express.Router();

router.use(protect, adminOnly);

router.get('/dashboard', dashboard);

router.get('/drivers', getDrivers);
router.post('/drivers', createDriver);
router.put('/drivers/:driverId', updateDriver);
router.delete('/drivers/:driverId', deleteDriver);
router.post('/drivers/:driverId/activate', (req, res, next) => {
  req.params.action = 'activate';
  return setDriverStatus(req, res, next);
});
router.post('/drivers/:driverId/deactivate', (req, res, next) => {
  req.params.action = 'deactivate';
  return setDriverStatus(req, res, next);
});

router.get('/buses', getBuses);

router.get('/duties', getDuties);
router.post('/duties', createDuty);
router.put('/duties/:dutyId', updateDuty);
router.delete('/duties/:dutyId', deleteDuty);

module.exports = router;
