const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const {
  query,
  callProcedure,
  firstResultSet
} = require('../config/database');
const { sendResetCode } = require('../utils/emailService');

const jwtSecret = () => {
  if (!process.env.JWT_SECRET && process.env.NODE_ENV === 'production') {
    throw new Error('JWT_SECRET missing from environment');
  }

  return process.env.JWT_SECRET || 'development_secret_change_me';
};

const normalizeRole = (role) => String(role || '').toLowerCase();

const generateToken = (user) => jwt.sign(
  {
    userId: user.user_id,
    username: user.username,
    role: user.role,
    driverId: user.driver_id || null,
    adminId: user.admin_id || null
  },
  jwtSecret(),
  { expiresIn: '24h' }
);

const publicUser = (user) => ({
  id: user.user_id,
  username: user.username,
  userId: user.user_code,
  role: normalizeRole(user.role),
  email: user.email,
  profileInfo: {
    fullName: user.name,
    phone: user.contact,
    licenseNo: user.license_no || null,
    driverStatus: user.driver_status || null
  }
});

const login = async (req, res) => {
  try {
    const { username, userId, password } = req.body;

    if (!username || !userId || !password) {
      return res.status(400).json({
        message: 'Username, User ID and password are required'
      });
    }

    const result = await callProcedure('sp_get_user_for_login', [
      username.trim().toLowerCase(),
      userId.trim()
    ]);
    const user = firstResultSet(result)[0];

    if (!user) {
      return res.status(401).json({ message: 'Invalid credentials' });
    }

    if (user.account_status !== 'Active') {
      return res.status(401).json({
        message: 'Account deactivated. Contact administrator.'
      });
    }

    if (user.lock_until && new Date(user.lock_until) > new Date()) {
      const minutesLeft = Math.ceil(
        (new Date(user.lock_until).getTime() - Date.now()) / 60000
      );
      return res.status(423).json({
        message: `Account locked. Try again in ${minutesLeft} minutes.`
      });
    }

    const isMatch = await bcrypt.compare(password, user.password_hash);

    if (!isMatch) {
      await callProcedure('sp_record_login_failure', [user.user_id]);
      const attemptsLeft = Math.max(0, 4 - Number(user.login_attempts || 0));
      return res.status(attemptsLeft === 0 ? 423 : 401).json({
        message: attemptsLeft === 0
          ? 'Account locked for 30 minutes.'
          : `Invalid credentials. ${attemptsLeft} attempts left.`
      });
    }

    await callProcedure('sp_record_login_success', [user.user_id]);

    return res.json({
      success: true,
      token: generateToken(user),
      user: publicUser(user)
    });
  } catch (error) {
    console.error('LOGIN ERROR:', error.message);
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const logout = async (req, res) => res.json({
  success: true,
  message: 'Logged out successfully'
});

const getProfile = async (req, res) => {
  try {
    const result = await callProcedure('sp_get_user_profile', [
      req.user.userId
    ]);
    const user = firstResultSet(result)[0];

    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }

    return res.json({ success: true, user: publicUser(user) });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const createFirstAdmin = async (req, res) => {
  const connection = await require('../config/database').getPool()
    .getConnection();

  try {
    const [existing] = await connection.execute(
      "SELECT user_id FROM users WHERE role = 'Admin' LIMIT 1"
    );

    if (existing.length > 0) {
      return res.status(400).json({ message: 'Admin already exists' });
    }

    const {
      username,
      userId,
      password,
      email,
      fullName,
      phone
    } = req.body;

    if (!username || !userId || !password || !email) {
      return res.status(400).json({
        message: 'username, userId, password and email are required'
      });
    }

    await connection.beginTransaction();
    const passwordHash = await bcrypt.hash(password, 10);

    const [userResult] = await connection.execute(
      `INSERT INTO users
        (username, user_code, name, email, contact, password_hash, role)
       VALUES (?, ?, ?, ?, ?, ?, 'Admin')`,
      [
        username.trim().toLowerCase(),
        userId.trim(),
        fullName || 'Admin',
        email.trim().toLowerCase(),
        phone || 'N/A',
        passwordHash
      ]
    );

    await connection.execute(
      'INSERT INTO admins(user_id) VALUES (?)',
      [userResult.insertId]
    );

    await connection.commit();

    return res.status(201).json({
      success: true,
      message: 'Admin created'
    });
  } catch (error) {
    await connection.rollback();
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  } finally {
    connection.release();
  }
};

const changePassword = async (req, res) => {
  try {
    const { currentPassword, newPassword } = req.body;

    if (!currentPassword || !newPassword) {
      return res.status(400).json({
        message: 'Current password and new password are required'
      });
    }

    const rows = await query(
      'SELECT password_hash FROM users WHERE user_id = ?',
      [req.user.userId]
    );
    const user = rows[0];

    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }

    const isMatch = await bcrypt.compare(
      currentPassword,
      user.password_hash
    );

    if (!isMatch) {
      return res.status(401).json({
        message: 'Current password is incorrect'
      });
    }

    const hashed = await bcrypt.hash(newPassword, 10);
    await callProcedure('sp_change_password', [req.user.userId, hashed]);

    return res.json({
      success: true,
      message: 'Password changed successfully'
    });
  } catch (error) {
    return res.status(500).json({
      message: 'Server error',
      error: error.message
    });
  }
};

const forgotPassword = async (req, res) => {
  try {
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({ message: 'Email is required' });
    }

    const code = Math.floor(100000 + Math.random() * 900000).toString();
    const result = await callProcedure('sp_save_reset_code', [
      email.trim().toLowerCase(),
      code
    ]);
    const user = firstResultSet(result)[0];

    if (user) {
      await sendResetCode(user.email, code, user.name || 'User');
    }

    return res.json({
      success: true,
      message: 'If this email exists, a code was sent'
    });
  } catch (error) {
    console.error('FORGOT PASSWORD ERROR:', error.message);
    return res.status(500).json({
      message: 'Failed to send reset code',
      error: error.message
    });
  }
};

const resetPassword = async (req, res) => {
  try {
    const { email, code, newPassword } = req.body;

    if (!email || !code || !newPassword) {
      return res.status(400).json({
        message: 'Email, code and new password required'
      });
    }

    if (newPassword.length < 6) {
      return res.status(400).json({
        message: 'Password must be at least 6 characters'
      });
    }

    const hashed = await bcrypt.hash(newPassword, 10);
    const result = await callProcedure('sp_reset_password', [
      email.trim().toLowerCase(),
      code.trim(),
      hashed
    ]);
    const affected = firstResultSet(result)[0]?.affected_rows || 0;

    if (affected === 0) {
      return res.status(400).json({
        message: 'Invalid or expired reset code'
      });
    }

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
