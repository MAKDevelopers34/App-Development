const fs = require('fs');
const {
  callProcedure,
  firstResultSet,
  query
} = require('../config/database');
const { formatReport } = require('../utils/formatters');
const { generateReport } = require('../utils/reportGenerator');

const getReports = async (req, res) => {
  try {
    const result = await callProcedure('sp_get_reports');
    const reports = firstResultSet(result).map(formatReport);

    res.json({
      success: true,
      count: reports.length,
      reports
    });
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

const generateManualReport = async (req, res) => {
  try {
    const { type } = req.params;

    if (!['daily', 'weekly', 'monthly'].includes(type)) {
      return res.status(400).json({
        message: 'Invalid type. Use daily, weekly or monthly'
      });
    }

    const report = await generateReport(type, req.user.adminId);
    res.json({
      success: true,
      message: `${type} report generated successfully`,
      report
    });
  } catch (error) {
    res.status(500).json({
      message: 'Error generating report',
      error: error.message
    });
  }
};

const downloadReport = async (req, res) => {
  try {
    const reports = await query(
      'SELECT * FROM reports WHERE report_code = ? LIMIT 1',
      [req.params.reportId]
    );
    const report = reports[0];

    if (!report || !report.pdf_path) {
      return res.status(404).json({
        message: 'Report not found'
      });
    }

    if (!fs.existsSync(report.pdf_path)) {
      return res.status(404).json({
        message: 'PDF file not found'
      });
    }

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="${report.report_code}.pdf"`
    );

    const fileStream = fs.createReadStream(report.pdf_path);
    fileStream.pipe(res);

  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

module.exports = {
  getReports,
  generateManualReport,
  downloadReport
};
