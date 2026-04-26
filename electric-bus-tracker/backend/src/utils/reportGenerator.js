const PDFDocument = require('pdfkit');
const fs = require('fs');
const path = require('path');
const Duty = require('../models/Duty');
const Bus = require('../models/Bus');
const User = require('../models/User');
const Report = require('../models/Report');

const generateReport = async (type) => {
  try {
    const now = new Date();
    let periodStart, periodEnd;

    if (type === 'daily') {
      periodStart = new Date(now);
      periodStart.setHours(0, 0, 0, 0);
      periodEnd = new Date(now);
      periodEnd.setHours(23, 59, 59, 999);
    } else if (type === 'weekly') {
      periodStart = new Date(now);
      periodStart.setDate(now.getDate() - 7);
      periodEnd = now;
    } else {
      periodStart = new Date(
        now.getFullYear(), now.getMonth(), 1
      );
      periodEnd = new Date(
        now.getFullYear(), now.getMonth() + 1, 0
      );
    }

    // Gather data
    const [
      totalDuties,
      completedDuties,
      skippedDuties,
      totalBuses,
      totalDrivers,
      activeDrivers,
      dutyDetails
    ] = await Promise.all([
      Duty.countDocuments({
        scheduledDate: {
          $gte: periodStart, $lte: periodEnd
        }
      }),
      Duty.countDocuments({
        scheduledDate: {
          $gte: periodStart, $lte: periodEnd
        },
        status: 'completed'
      }),
      Duty.countDocuments({
        scheduledDate: {
          $gte: periodStart, $lte: periodEnd
        },
        status: 'skipped'
      }),
      Bus.countDocuments(),
      User.countDocuments({ role: 'driver' }),
      User.countDocuments({
        role: 'driver', isActive: true
      }),
      Duty.find({
        scheduledDate: {
          $gte: periodStart, $lte: periodEnd
        }
      })
      .populate('driver', 'username profileInfo')
      .populate('bus', 'busNumber busId')
      .sort({ scheduledDate: -1 })
      .limit(50)
    ]);

    // Generate PDF
    const reportId = `RPT-${type.toUpperCase()}-${Date.now()}`;
    const fileName = `${reportId}.pdf`;
    const reportsDir = path.join(__dirname, '../../reports');

    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
    }

    const filePath = path.join(reportsDir, fileName);
    await createPDF(filePath, {
      type, reportId, periodStart, periodEnd,
      totalDuties, completedDuties, skippedDuties,
      totalBuses, totalDrivers, activeDrivers,
      dutyDetails
    });

    // Save report to database
    const report = await Report.create({
      reportId,
      type,
      periodStart,
      periodEnd,
      data: {
        totalDuties,
        completedDuties,
        skippedDuties,
        totalBuses,
        totalDrivers,
        activeDrivers
      },
      pdfPath: filePath
    });

    console.log(`${type} report generated: ${reportId}`);
    return report;

  } catch (error) {
    console.error('Report generation error:', error.message);
    throw error;
  }
};

const createPDF = (filePath, data) => {
  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({ margin: 50 });
    const stream = fs.createWriteStream(filePath);
    doc.pipe(stream);

    // Header
    doc
      .fillColor('#2ECC71')
      .fontSize(24)
      .font('Helvetica-Bold')
      .text('Electric Bus Tracker', { align: 'center' });

    doc
      .fillColor('#333333')
      .fontSize(16)
      .font('Helvetica-Bold')
      .text(
        `${data.type.toUpperCase()} OPERATIONAL REPORT`,
        { align: 'center' }
      );

    doc.moveDown(0.5);

    doc
      .fillColor('#666666')
      .fontSize(11)
      .font('Helvetica')
      .text(`Report ID: ${data.reportId}`, { align: 'center' })
      .text(
        `Period: ${data.periodStart.toDateString()} - `
        + `${data.periodEnd.toDateString()}`,
        { align: 'center' }
      )
      .text(
        `Generated: ${new Date().toLocaleString()}`,
        { align: 'center' }
      );

    doc.moveDown();

    // Divider
    doc
      .moveTo(50, doc.y)
      .lineTo(545, doc.y)
      .strokeColor('#2ECC71')
      .lineWidth(2)
      .stroke();

    doc.moveDown();

    // Summary section
    doc
      .fillColor('#2ECC71')
      .fontSize(14)
      .font('Helvetica-Bold')
      .text('SUMMARY');

    doc.moveDown(0.5);

    const summaryItems = [
      ['Total Duties', data.totalDuties],
      ['Completed Duties', data.completedDuties],
      ['Skipped Duties', data.skippedDuties],
      ['Total Buses', data.totalBuses],
      ['Total Drivers', data.totalDrivers],
      ['Active Drivers', data.activeDrivers],
      [
        'Completion Rate',
        data.totalDuties > 0
          ? `${Math.round(
              (data.completedDuties / data.totalDuties) * 100
            )}%`
          : '0%'
      ],
    ];

    summaryItems.forEach(([label, value]) => {
      doc
        .fillColor('#333333')
        .fontSize(11)
        .font('Helvetica-Bold')
        .text(`${label}: `, { continued: true })
        .font('Helvetica')
        .text(String(value));
    });

    doc.moveDown();

    // Divider
    doc
      .moveTo(50, doc.y)
      .lineTo(545, doc.y)
      .strokeColor('#EEEEEE')
      .lineWidth(1)
      .stroke();

    doc.moveDown();

    // Duty Details
    doc
      .fillColor('#2ECC71')
      .fontSize(14)
      .font('Helvetica-Bold')
      .text('DUTY DETAILS');

    doc.moveDown(0.5);

    if (data.dutyDetails.length === 0) {
      doc
        .fillColor('#666666')
        .fontSize(11)
        .text('No duties recorded for this period.');
    } else {
      // Table header
      const tableTop = doc.y;
      doc
        .fillColor('#2ECC71')
        .rect(50, tableTop, 495, 22)
        .fill();

      doc
        .fillColor('#FFFFFF')
        .fontSize(10)
        .font('Helvetica-Bold')
        .text('Driver', 55, tableTop + 6)
        .text('Route', 180, tableTop + 6)
        .text('Bus', 330, tableTop + 6)
        .text('Status', 420, tableTop + 6)
        .text('Date', 470, tableTop + 6);

      let rowY = tableTop + 24;

      data.dutyDetails.forEach((duty, index) => {
        if (rowY > 700) {
          doc.addPage();
          rowY = 50;
        }

        const bgColor = index % 2 === 0
          ? '#F9F9F9' : '#FFFFFF';
        doc
          .fillColor(bgColor)
          .rect(50, rowY, 495, 20)
          .fill();

        const statusColor =
          duty.status === 'completed' ? '#2ECC71'
          : duty.status === 'skipped' ? '#E74C3C'
          : '#F39C12';

        doc
          .fillColor('#333333')
          .fontSize(9)
          .font('Helvetica')
          .text(
            duty.driver?.profileInfo?.fullName
            || duty.driver?.username || 'N/A',
            55, rowY + 6, { width: 120, ellipsis: true }
          )
          .text(
            duty.route || 'N/A',
            180, rowY + 6, { width: 140, ellipsis: true }
          )
          .text(
            duty.bus?.busNumber || 'N/A',
            330, rowY + 6, { width: 80 }
          );

        doc
          .fillColor(statusColor)
          .text(
            duty.status?.toUpperCase() || 'N/A',
            420, rowY + 6, { width: 60 }
          );

        doc
          .fillColor('#333333')
          .text(
            new Date(duty.scheduledDate)
              .toLocaleDateString(),
            470, rowY + 6
          );

        rowY += 20;
      });
    }

    doc.moveDown(2);

    // Footer
    doc
      .fillColor('#AAAAAA')
      .fontSize(9)
      .text(
        'Electric Bus Tracker — Mianwali District, Pakistan',
        { align: 'center' }
      )
      .text(
        'This report was auto-generated by the system.',
        { align: 'center' }
      );

    doc.end();
    stream.on('finish', resolve);
    stream.on('error', reject);
  });
};

module.exports = { generateReport };