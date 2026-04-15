const express = require('express');
const router = express.Router();
const { 
  login, 
  logout, 
  getProfile,
  createFirstAdmin 
} = require('../controllers/authController');
const { protect } = require('../middleware/auth');

router.post('/login', login);
router.post('/logout', protect, logout);
router.get('/profile', protect, getProfile);
router.post('/setup-admin', createFirstAdmin);

module.exports = router;