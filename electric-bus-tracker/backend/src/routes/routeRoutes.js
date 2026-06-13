const express = require('express');
const {
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
} = require('../controllers/routeController');
const { protect, adminOnly } = require('../middleware/auth');

const router = express.Router();

router.get('/', getRoutes);
router.get('/search', searchRoutes);
router.get('/stops', getStops);
router.get('/favorites', getFavoriteRoutes);
router.post('/favorites', saveFavoriteRoute);
router.delete('/favorites/:routeId', removeFavoriteRoute);
router.get('/:routeId', getRouteById);
router.get('/:routeId/eat/:stopId', getRouteEat);
router.post('/', protect, adminOnly, createRoute);
router.delete('/:routeId', protect, adminOnly, deleteRoute);

module.exports = router;
