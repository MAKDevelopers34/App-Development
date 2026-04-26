const mongoose = require('mongoose');

const dutySchema = new mongoose.Schema({
  dutyId: {
    type: String,
    required: true,
    unique: true
  },
  driver: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  bus: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Bus',
    required: true
  },
  route: {
    type: String,
    required: true
  },
  scheduledDate: {
    type: Date,
    required: true
  },
  scheduledStartTime: {
    type: String,
    required: true
  },
  scheduledEndTime: {
    type: String,
    required: true
  },
  actualStartTime: {
    type: Date,
    default: null
  },
  actualEndTime: {
    type: Date,
    default: null
  },
  status: {
    type: String,
    enum: ['assigned', 'started', 'completed', 'skipped'],
    default: 'assigned'
  },
  completionNote: {
    type: String,
    default: null
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('Duty', dutySchema);