const mongoose = require('mongoose');

const reportSchema = new mongoose.Schema({
  reportId: {
    type: String,
    required: true,
    unique: true
  },
  type: {
    type: String,
    enum: ['daily', 'weekly', 'monthly'],
    required: true
  },
  generatedAt: {
    type: Date,
    default: Date.now
  },
  periodStart: {
    type: Date,
    required: true
  },
  periodEnd: {
    type: Date,
    required: true
  },
  data: {
    totalDuties: { type: Number, default: 0 },
    completedDuties: { type: Number, default: 0 },
    skippedDuties: { type: Number, default: 0 },
    totalBuses: { type: Number, default: 0 },
    activeBuses: { type: Number, default: 0 },
    totalDrivers: { type: Number, default: 0 },
    activeDrivers: { type: Number, default: 0 },
  },
  pdfPath: {
    type: String,
    default: null
  }
});

module.exports = mongoose.model('Report', reportSchema);