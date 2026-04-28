const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const User = require('../models/User');
const { sendResetCode } = require('../utils/emailService');

const generateToken = (id) => {
  return jwt.sign(
    { id },
    process.env.JWT_SECRET || 'fallback_secret_key',
    { expiresIn: '24h' }
  );
};

// ── LOGIN ─────────────────────────────────────────
const login = async (req, res) => {
  try {
    const { username, userId, password } = req.body;

    if (!username || !userId || !password) {
      return res.status(400).json({
        message: 'Username, User ID and password are required'
      });
    }

    // Find by username (lowercase)
    const user = await User.findOne({
      username: username.trim().toLowerCase()
    });

    if (!user) {
      return res.status(401).json({
        message: 'Invalid credentials'
      });
    }

    // Check userId
    if (user.userId.trim() !== userId.trim()) {
      return res.status(401).json({
        message: 'Invalid credentials'
      });
    }

    // Check active
    if (!user.isActive) {
      return res.status(401).json({
        message: 'Account deactivated. Contact administrator.'
      });
    }

    // Check lock
    if (user.isLocked()) {
      const minutesLeft = Math.ceil(
        (user.lockUntil - Date.now()) / 60000
      );
      return res.status(423).json({
        message: `Account locked. Try again in ${minutesLeft} minutes.`
      });
    }

    // Compare password directly with bcrypt
    const isMatch = await bcrypt.compare(
      password, user.password
    );

    if (!isMatch) {
      user.loginAttempts = (user.loginAttempts || 0) + 1;
      if (user.loginAttempts >= 5) {
        user.lockUntil = new Date(
          Date.now() + 30 * 60 * 1000
        );
        user.loginAttempts = 0;
        await User.updateOne(
          { _id: user._id },
          {
            loginAttempts: user.loginAttempts,
            lockUntil: user.lockUntil
          }
        );
        return res.status(423).json({
          message: 'Account locked for 30 minutes.'
        });
      }
      await User.updateOne(
        { _id: user._id },
        { loginAttempts: user.loginAttempts }
      );
      return res.status(401).json({
        message: `Invalid credentials. ${5 - user.loginAttempts} attempts left.`
      });
    }

    // Reset attempts on success
    await User.updateOne(
      { _id: user._id },
      { loginAttempts: 0, lockUntil: null }
    );

    return res.json({
      success: true,
      token: generateToken(user._id),
      user: {
        id: user._id,
        username: user.username,
        userId: user.userId,
        role: user.role,
        email: user.email,
        profileInfo: user.profileInfo
      }
    });

  } catch (error) {
    console.error('LOGIN ERROR:', error.message);
    console.error(error.stack);
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

// ── LOGOUT ────────────────────────────────────────
const logout = async (req, res) => {
  return res.json({
    success: true,
    message: 'Logged out successfully'
  });
};

// ── GET PROFILE ───────────────────────────────────
const getProfile = async (req, res) => {
  try {
    const user = await User.findById(
      req.user._id
    ).select('-password');
    return res.json({ success: true, user });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error'
    });
  }
};

// ── CREATE FIRST ADMIN ────────────────────────────
const createFirstAdmin = async (req, res) => {
  try {
    const adminExists = await User.findOne({
      role: 'admin'
    });
    if (adminExists) {
      return res.status(400).json({
        message: 'Admin already exists'
      });
    }

    const {
      username, userId, password,
      email, fullName
    } = req.body;

    const admin = await User.create({
      username,
      userId,
      password,
      email,
      role: 'admin',
      profileInfo: { fullName: fullName || 'Admin' }
    });

    return res.status(201).json({
      success: true,
      message: 'Admin created',
      token: generateToken(admin._id)
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

// ── CHANGE PASSWORD ───────────────────────────────
const changePassword = async (req, res) => {
  try {
    const { currentPassword, newPassword } = req.body;
    const user = await User.findById(req.user._id);

    const isMatch = await bcrypt.compare(
      currentPassword, user.password
    );
    if (!isMatch) {
      return res.status(401).json({
        message: 'Current password is incorrect'
      });
    }

    const salt = await bcrypt.genSalt(10);
    const hashed = await bcrypt.hash(newPassword, salt);

    await User.updateOne(
      { _id: user._id },
      { password: hashed }
    );

    return res.json({
      success: true,
      message: 'Password changed successfully'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error'
    });
  }
};

// ── FORGOT PASSWORD ───────────────────────────────
const forgotPassword = async (req, res) => {
  try {
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({
        message: 'Email is required'
      });
    }

    const user = await User.findOne({
      email: email.toLowerCase().trim()
    });

    if (!user) {
      return res.json({
        success: true,
        message: 'If this email exists, a code was sent'
      });
    }

    const code = Math.floor(
      100000 + Math.random() * 900000
    ).toString();

    await User.updateOne(
      { _id: user._id },
      {
        resetCode: code,
        resetCodeExpiry: new Date(
          Date.now() + 10 * 60 * 1000
        )
      }
    );

    await sendResetCode(
      user.email,
      code,
      user.profileInfo?.fullName || 'User'
    );

    return res.json({
      success: true,
      message: 'Reset code sent to your email'
    });

  } catch (error) {
    console.error('FORGOT PASSWORD ERROR:', error.message);
    return res.status(500).json({
      message: 'Failed to send reset code',
      error: error.message
    });
  }
};

// ── RESET PASSWORD ────────────────────────────────
const resetPassword = async (req, res) => {
  try {
    const { email, code, newPassword } = req.body;

    if (!email || !code || !newPassword) {
      return res.status(400).json({
        message: 'Email, code and new password required'
      });
    }

    const user = await User.findOne({
      email: email.toLowerCase().trim()
    });

    if (!user) {
      return res.status(404).json({
        message: 'User not found'
      });
    }

    if (user.resetCode !== code) {
      return res.status(400).json({
        message: 'Invalid reset code'
      });
    }

    if (!user.resetCodeExpiry ||
        user.resetCodeExpiry < new Date()) {
      return res.status(400).json({
        message: 'Code expired. Request a new one.'
      });
    }

    if (newPassword.length < 6) {
      return res.status(400).json({
        message: 'Password must be at least 6 characters'
      });
    }

    const salt = await bcrypt.genSalt(10);
    const hashed = await bcrypt.hash(newPassword, salt);

    await User.updateOne(
      { _id: user._id },
      {
        password: hashed,
        resetCode: null,
        resetCodeExpiry: null
      }
    );

    return res.json({
      success: true,
      message: 'Password reset successfully! Please login.'
    });

  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

module.exports = {
  login,
  logout,
  getProfile,
  createFirstAdmin,
  changePassword,
  forgotPassword,
  resetPassword
};