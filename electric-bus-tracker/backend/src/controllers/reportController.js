const path = require('path');
const fs = require('fs');
const Report = require('../models/Report');
const { generateReport } = require('../utils/reportGenerator');

const getReports = async (req, res) => {
  try {
    const reports = await Report.find()
      .sort({ generatedAt: -1 })
      .limit(30);

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

    const report = await generateReport(type);
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
    const report = await Report.findOne({
      reportId: req.params.reportId
    });

    if (!report || !report.pdfPath) {
      return res.status(404).json({
        message: 'Report not found'
      });
    }

    if (!fs.existsSync(report.pdfPath)) {
      return res.status(404).json({
        message: 'PDF file not found'
      });
    }

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="${report.reportId}.pdf"`
    );

    const fileStream = fs.createReadStream(report.pdfPath);
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