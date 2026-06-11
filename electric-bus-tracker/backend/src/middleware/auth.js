const jwt = require('jsonwebtoken');

const protect = async (req, res, next) => {
  const header = req.headers.authorization;

  if (!header || !header.startsWith('Bearer ')) {
    return res.status(401).json({ message: 'Not authorized, no token' });
  }

  try {
    const token = header.split(' ')[1];
    const decoded = jwt.verify(token, process.env.JWT_SECRET);

    req.user = {
      userId: decoded.userId,
      username: decoded.username,
      role: decoded.role,
      driverId: decoded.driverId || null,
      adminId: decoded.adminId || null
    };

    return next();
  } catch (error) {
    return res.status(401).json({ message: 'Not authorized, token failed' });
  }
};

const adminOnly = (req, res, next) => {
  if (req.user && req.user.role === 'Admin') {
    return next();
  }

  return res.status(403).json({ message: 'Admin access only' });
};

const driverOnly = (req, res, next) => {
  if (req.user && req.user.role === 'Driver') {
    return next();
  }

  return res.status(403).json({ message: 'Driver access only' });
};

module.exports = { protect, adminOnly, driverOnly };
