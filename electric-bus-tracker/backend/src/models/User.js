const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true,
    trim: true,
    lowercase: true
  },
  userId: {
    type: String,
    required: true,
    unique: true,
    trim: true
  },
  password: {
    type: String,
    required: true
  },
  role: {
    type: String,
    enum: ['driver', 'admin'],
    required: true
  },
  email: {
    type: String,
    required: true,
    unique: true,
    trim: true,
    lowercase: true
  },
  isActive: {
    type: Boolean,
    default: true
  },
  loginAttempts: {
    type: Number,
    default: 0
  },
  lockUntil: {
    type: Date,
    default: null
  },
  profileInfo: {
    fullName: { type: String, default: '' },
    phone: { type: String, default: '' },
    address: { type: String, default: '' }
  },
  favoriteRoutes: [{
    type: String
  }],
  resetCode: {
    type: String,
    default: null
  },
  resetCodeExpiry: {
    type: Date,
    default: null
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

// Hash password before save
userSchema.pre('save', async function(next) {
  try {
    if (!this.isModified('password')) {
      return next();
    }
    const salt = await bcrypt.genSalt(10);
    this.password = await bcrypt.hash(this.password, salt);
    return next();
  } catch (err) {
    return next(err);
  }
});

// Compare password method
userSchema.methods.matchPassword = async function(enteredPassword) {
  try {
    return await bcrypt.compare(enteredPassword, this.password);
  } catch (err) {
    return false;
  }
};

// Check if account is locked
userSchema.methods.isLocked = function() {
  if (!this.lockUntil) return false;
  return this.lockUntil > Date.now();
};

module.exports = mongoose.model('User', userSchema);