const express = require('express');
const router = express.Router();
const {
  login,
  logout,
  getProfile,
  createFirstAdmin,
  changePassword,
  forgotPassword,
  resetPassword
} = require('../controllers/authController');
const { protect } = require('../middleware/auth');

router.post('/login', login);
router.post('/logout', protect, logout);
router.get('/profile', protect, getProfile);
router.post('/setup-admin', createFirstAdmin);
router.post('/change-password', protect, changePassword);
router.post('/forgot-password', forgotPassword);
router.post('/reset-password', resetPassword);

module.exports = router;