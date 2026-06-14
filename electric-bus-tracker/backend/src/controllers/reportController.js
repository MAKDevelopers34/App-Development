const fs = require('fs');
const {
  callProcedure,
  firstResultSet,
  query
} = require('../config/database');
const { formatReport } = require('../utils/formatters');
const { generateReport } = require('../utils/reportGenerator');

const enrichReport = async (report) => {
  const [periodRows, totalRows] = await Promise.all([
    query(
      `SELECT
        COUNT(DISTINCT driver_id) AS drivers_performed_duties,
        COUNT(DISTINCT bus_id) AS buses_performed_duties
       FROM duty_assignments
       WHERE scheduled_date BETWEEN ? AND ?`,
      [report.periodStart, report.periodEnd]
    ),
    query(
      `SELECT
        (SELECT COUNT(*)
         FROM stops
         WHERE status = 'Active'
           AND deletion_date IS NULL) AS total_stops,
        (SELECT COUNT(*)
         FROM routes
         WHERE status = 'Active') AS total_routes`
    )
  ]);

  return {
    ...report,
    data: {
      ...report.data,
      driversPerformedDuties: Number(
        periodRows[0]?.drivers_performed_duties || 0
      ),
      busesPerformedDuties: Number(periodRows[0]?.buses_performed_duties || 0),
      totalStops: Number(totalRows[0]?.total_stops || 0),
      totalRoutes: Number(totalRows[0]?.total_routes || 0)
    }
  };
};

const getReports = async (req, res) => {
  try {
    const result = await callProcedure('sp_get_reports');
    const reports = await Promise.all(
      firstResultSet(result).map((row) => enrichReport(formatReport(row)))
    );

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

const downloadGeneratedReport = async (req, res) => {
  try {
    const { type } = req.params;

    if (!['daily', 'weekly', 'monthly'].includes(type)) {
      return res.status(400).json({
        message: 'Invalid type. Use daily, weekly or monthly'
      });
    }

    const report = await generateReport(type, req.user.adminId);

    if (!report || !report.pdfPath || !fs.existsSync(report.pdfPath)) {
      return res.status(500).json({
        message: 'PDF file could not be generated'
      });
    }

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="${report.reportId}.pdf"`
    );

    fs.createReadStream(report.pdfPath).pipe(res);
  } catch (error) {
    res.status(500).json({
      message: 'Error generating report',
      error: error.message
    });
  }
};

module.exports = {
  getReports,
  generateManualReport,
  downloadReport,
  downloadGeneratedReport
};
