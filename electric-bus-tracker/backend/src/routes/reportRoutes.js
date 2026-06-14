const express = require('express');
const router = express.Router();
const {
  getReports,
  generateManualReport,
  downloadReport,
  downloadGeneratedReport
} = require('../controllers/reportController');
const { protect, adminOnly } = require('../middleware/auth');

router.use(protect, adminOnly);

router.get('/', getReports);
router.post('/generate/:type', generateManualReport);
router.get('/generate-download/:type', downloadGeneratedReport);
router.get('/download/:reportId', downloadReport);

module.exports = router;
