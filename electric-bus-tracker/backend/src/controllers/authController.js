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

    const user = await User.findOne({ username, userId });

    if (!user) {
      return res.status(401).json({ 
        message: 'Invalid credentials' 
      });
    }

    if (!user.isActive) {
      return res.status(401).json({ 
        message: 'Account is deactivated. Contact admin.' 
      });
    }

    if (user.isLocked()) {
      const minutesLeft = Math.ceil(
        (user.lockUntil - Date.now()) / 60000
      );
      return res.status(423).json({ 
        message: `Account locked. Try again in ${minutesLeft} minutes.` 
      });
    }

    const isMatch = await user.matchPassword(password);

    if (!isMatch) {
      user.loginAttempts += 1;

      if (user.loginAttempts >= 5) {
        user.lockUntil = new Date(Date.now() + 30 * 60 * 1000);
        user.loginAttempts = 0;
        await user.save();
        return res.status(423).json({ 
          message: 'Account locked for 30 minutes due to failed attempts.' 
        });
      }

      await user.save();
      return res.status(401).json({ 
        message: `Invalid credentials. ${5 - user.loginAttempts} attempts remaining.` 
      });
    }

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
    res.status(500).json({ message: 'Server error', error: error.message });
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