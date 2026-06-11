const PDFDocument = require('pdfkit');
const fs = require('fs');
const path = require('path');
const {
  callProcedure,
  firstResultSet,
  query
} = require('../config/database');
const { formatReport } = require('./formatters');

const pad = (value) => String(value).padStart(2, '0');

const toDateOnly = (date) => (
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
);

const getPeriod = (type) => {
  const now = new Date();

  if (type === 'daily') {
    return {
      periodStart: toDateOnly(now),
      periodEnd: toDateOnly(now)
    };
  }

  if (type === 'weekly') {
    const start = new Date(now);
    start.setDate(now.getDate() - 6);

    return {
      periodStart: toDateOnly(start),
      periodEnd: toDateOnly(now)
    };
  }

  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);

  return {
    periodStart: toDateOnly(start),
    periodEnd: toDateOnly(end)
  };
};

const generateReport = async (type, adminId = 1) => {
  try {
    const { periodStart, periodEnd } = getPeriod(type);

    const [summaryRows, dutyDetails] = await Promise.all([
      query(
        `SELECT
          COUNT(da.duty_id) AS total_duties,
          COALESCE(SUM(da.status = 'Completed'), 0) AS completed_duties,
          COALESCE(SUM(da.status = 'Skipped'), 0) AS skipped_duties,
          (SELECT COUNT(*) FROM buses WHERE deletion_date IS NULL) AS total_buses,
          (
            SELECT COUNT(*)
            FROM drivers d
            JOIN users u ON u.user_id = d.user_id
            WHERE u.deletion_date IS NULL
          ) AS total_drivers,
          (
            SELECT COUNT(*)
            FROM drivers d
            JOIN users u ON u.user_id = d.user_id
            WHERE u.account_status = 'Active'
              AND u.deletion_date IS NULL
          ) AS active_drivers
        FROM duty_assignments da
        WHERE da.scheduled_date BETWEEN ? AND ?`,
        [periodStart, periodEnd]
      ),
      query(
        `SELECT
          da.duty_id,
          da.scheduled_date,
          da.scheduled_start_time,
          da.scheduled_end_time,
          da.status,
          u.name AS driver_name,
          u.username AS driver_username,
          b.bus_number,
          r.name AS route_name
        FROM duty_assignments da
        JOIN drivers d ON d.driver_id = da.driver_id
        JOIN users u ON u.user_id = d.user_id
        JOIN buses b ON b.bus_id = da.bus_id
        JOIN schedules s ON s.schedule_id = da.schedule_id
        JOIN routes r ON r.route_id = s.route_id
        WHERE da.scheduled_date BETWEEN ? AND ?
        ORDER BY da.scheduled_date DESC, da.scheduled_start_time DESC
        LIMIT 50`,
        [periodStart, periodEnd]
      )
    ]);

    const summary = summaryRows[0] || {};
    const data = {
      type,
      reportId: `RPT-${type.toUpperCase()}-${Date.now()}`,
      periodStart,
      periodEnd,
      totalDuties: Number(summary.total_duties || 0),
      completedDuties: Number(summary.completed_duties || 0),
      skippedDuties: Number(summary.skipped_duties || 0),
      totalBuses: Number(summary.total_buses || 0),
      totalDrivers: Number(summary.total_drivers || 0),
      activeDrivers: Number(summary.active_drivers || 0),
      dutyDetails
    };

    const reportsDir = path.join(__dirname, '../../reports');
    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
    }

    const filePath = path.join(reportsDir, `${data.reportId}.pdf`);
    await createPDF(filePath, data);

    const result = await callProcedure('sp_create_report', [
      adminId,
      data.reportId,
      type,
      periodStart,
      periodEnd,
      data.totalDuties,
      data.completedDuties,
      data.skippedDuties,
      data.totalBuses,
      data.totalDrivers,
      data.activeDrivers,
      filePath,
      `${type} operational report`
    ]);

    const saved = firstResultSet(result)[0];
    console.log(`${type} report generated: ${data.reportId}`);

    return saved ? formatReport(saved) : {
      reportId: data.reportId,
      type,
      pdfPath: filePath
    };
  } catch (error) {
    console.error('Report generation error:', error.message);
    throw error;
  }
};

const createPDF = (filePath, data) => {
  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({ margin: 50 });
    const stream = fs.createWriteStream(filePath);

    stream.on('finish', resolve);
    stream.on('error', reject);
    doc.on('error', reject);
    doc.pipe(stream);

    doc
      .fillColor('#00A63E')
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
        `Period: ${data.periodStart} - ${data.periodEnd}`,
        { align: 'center' }
      )
      .text(
        `Generated: ${new Date().toLocaleString()}`,
        { align: 'center' }
      );

    doc.moveDown();

    doc
      .moveTo(50, doc.y)
      .lineTo(545, doc.y)
      .strokeColor('#00A63E')
      .lineWidth(2)
      .stroke();

    doc.moveDown();

    doc
      .fillColor('#00A63E')
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
          ? `${Math.round((data.completedDuties / data.totalDuties) * 100)}%`
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

    doc
      .moveTo(50, doc.y)
      .lineTo(545, doc.y)
      .strokeColor('#EEEEEE')
      .lineWidth(1)
      .stroke();

    doc.moveDown();

    doc
      .fillColor('#00A63E')
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
      const tableTop = doc.y;
      doc
        .fillColor('#00A63E')
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

        const bgColor = index % 2 === 0 ? '#F9F9F9' : '#FFFFFF';
        doc
          .fillColor(bgColor)
          .rect(50, rowY, 495, 20)
          .fill();

        const statusColor =
          duty.status === 'Completed' ? '#00A63E'
          : duty.status === 'Skipped' ? '#E7000B'
          : '#F0B100';

        doc
          .fillColor('#333333')
          .fontSize(9)
          .font('Helvetica')
          .text(
            duty.driver_name || duty.driver_username || 'N/A',
            55, rowY + 6, { width: 120, ellipsis: true }
          )
          .text(
            duty.route_name || 'N/A',
            180, rowY + 6, { width: 140, ellipsis: true }
          )
          .text(
            duty.bus_number || 'N/A',
            330, rowY + 6, { width: 80 }
          );

        doc
          .fillColor(statusColor)
          .text(
            String(duty.status || 'N/A').toUpperCase(),
            420, rowY + 6, { width: 60 }
          );

        doc
          .fillColor('#333333')
          .text(String(duty.scheduled_date || ''), 470, rowY + 6);

        rowY += 20;
      });
    }

    doc.moveDown(2);

    doc
      .fillColor('#AAAAAA')
      .fontSize(9)
      .text(
        'Electric Bus Tracker - Mianwali District, Pakistan',
        { align: 'center' }
      )
      .text(
        'This report was auto-generated by the system.',
        { align: 'center' }
      );

    doc.end();
  });
};

module.exports = { generateReport };
