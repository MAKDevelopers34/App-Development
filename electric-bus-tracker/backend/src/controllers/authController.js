const jwt = require('jsonwebtoken');
const User = require('../models/User');

const generateToken = (id) => {
  return jwt.sign({ id }, process.env.JWT_SECRET, {
    expiresIn: '24h'
  });
};

const login = async (req, res) => {
  try {
    const { username, userId, password } = req.body;

    if (!username || !userId || !password) {
      return res.status(400).json({
        message: 'Username, User ID and password are required'
      });
    }

    // Find user by username only first
    const user = await User.findOne({ 
      username: username.trim().toLowerCase()
    });

    if (!user) {
      return res.status(401).json({
        message: 'Invalid credentials'
      });
    }

    // Then check userId matches
    if (user.userId !== userId.trim()) {
      return res.status(401).json({
        message: 'Invalid credentials'
      });
    }

    if (!user.isActive) {
      return res.status(401).json({
        message: 'Account is deactivated. Contact admin.'
      });
    }

    if (user.isLocked && user.isLocked()) {
      const minutesLeft = Math.ceil(
        (user.lockUntil - Date.now()) / 60000
      );
      return res.status(423).json({
        message: `Account locked. Try again in ${minutesLeft} minutes.`
      });
    }

    const isMatch = await user.matchPassword(password);

    if (!isMatch) {
      user.loginAttempts = (user.loginAttempts || 0) + 1;

      if (user.loginAttempts >= 5) {
        user.lockUntil = new Date(Date.now() + 30 * 60 * 1000);
        user.loginAttempts = 0;
        await user.save();
        return res.status(423).json({
          message: 'Account locked for 30 minutes.'
        });
      }

      await user.save();
      return res.status(401).json({
        message: `Invalid credentials. ${5 - user.loginAttempts} attempts remaining.`
      });
    }

    // Reset login attempts on success
    user.loginAttempts = 0;
    user.lockUntil = null;
    await user.save();

    res.json({
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
    console.error('Login error:', error.message);
    res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const logout = async (req, res) => {
  res.json({ success: true, message: 'Logged out successfully' });
};

const getProfile = async (req, res) => {
  try {
    const user = await User.findById(req.user._id).select('-password');
    res.json({ success: true, user });
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

const createFirstAdmin = async (req, res) => {
  try {
    const adminExists = await User.findOne({ role: 'admin' });
    if (adminExists) {
      return res.status(400).json({ 
        message: 'Admin already exists' 
      });
    }

    const { username, userId, password, email, fullName } = req.body;

    const admin = await User.create({
      username,
      userId,
      password,
      email,
      role: 'admin',
      profileInfo: { fullName }
    });

    res.status(201).json({
      success: true,
      message: 'Admin created successfully',
      token: generateToken(admin._id)
    });

  } catch (error) {
    res.status(500).json({ message: 'Server error', error: error.message });
  }
};

module.exports = { login, logout, getProfile, createFirstAdmin };

const changePassword = async (req, res) => {
  try {
    const { currentPassword, newPassword } = req.body;
    const user = await User.findById(req.user._id);

    const isMatch = await user.matchPassword(currentPassword);
    if (!isMatch) {
      return res.status(401).json({
        message: 'Current password is incorrect'
      });
    }

    user.password = newPassword;
    await user.save();

    res.json({
      success: true,
      message: 'Password changed successfully'
    });
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

const { sendResetCode } = require('../utils/emailService');

// Step 1 — User enters email, gets code
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
      // Still return success for security
      return res.json({
        success: true,
        message: 'If this email exists, a code was sent'
      });
    }

    const code = Math.floor(
      100000 + Math.random() * 900000
    ).toString();

    user.resetCode = code;
    user.resetCodeExpiry = new Date(Date.now() + 10 * 60 * 1000);
    await user.save();

    try {
      await sendResetCode(
        user.email,
        code,
        user.profileInfo?.fullName
      );
    } catch (emailError) {
      console.error('Email failed:', emailError.message);
      return res.status(500).json({
        message: 'Failed to send email. Check SendGrid configuration.',
        detail: emailError.message
      });
    }

    res.json({
      success: true,
      message: 'Reset code sent to your email'
    });

  } catch (error) {
    console.error('Forgot password error:', error.message);
    res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

// Step 2 — User enters code + new password
const resetPassword = async (req, res) => {
  try {
    const { email, code, newPassword } = req.body;

    if (!email || !code || !newPassword) {
      return res.status(400).json({
        message: 'Email, code and new password are required'
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

    // Check code is correct
    if (user.resetCode !== code) {
      return res.status(400).json({
        message: 'Invalid reset code'
      });
    }

    // Check code not expired
    if (!user.resetCodeExpiry ||
        user.resetCodeExpiry < new Date()) {
      return res.status(400).json({
        message: 'Reset code has expired. Request a new one.'
      });
    }

    if (newPassword.length < 6) {
      return res.status(400).json({
        message: 'Password must be at least 6 characters'
      });
    }

    // Set new password — bcrypt happens in pre-save hook
    user.password = newPassword;
    user.resetCode = null;
    user.resetCodeExpiry = null;
    await user.save();

    res.json({
      success: true,
      message: 'Password reset successfully! Please login.'
    });

  } catch (error) {
    res.status(500).json({
      message: 'Error resetting password',
      error: error.message
    });
  }
};

module.exports = {
  login, logout, getProfile,
  createFirstAdmin, changePassword,
  forgotPassword,
  resetPassword
};