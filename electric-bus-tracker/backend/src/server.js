const express = require('express');
const dotenv = require('dotenv');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const { connectDB } = require('./config/database');

dotenv.config();

const app = express();

app.use(helmet());
app.use(cors());
app.use(morgan('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

const authRoutes = require('./routes/authRoutes');
const gpsRoutes = require('./routes/gpsRoutes');
const routeRoutes = require('./routes/routeRoutes');
const adminRoutes = require('./routes/adminRoutes');
const dutyRoutes = require('./routes/dutyRoutes');
const reportRoutes = require('./routes/reportRoutes');
const { startScheduler } = require('./utils/scheduler');

app.get('/', (req, res) => {
  res.json({
    message: 'Electric Bus Tracker API is running!',
    version: '1.0.0',
    status: 'ok'
  });
});

app.get('/api/health', (req, res) => {
  res.json({
    success: true,
    message: 'Electric Bus Tracker API is healthy',
    status: 'ok',
    uptime: process.uptime()
  });
});

app.use('/api/auth', authRoutes);
app.use('/api/routes', routeRoutes);
app.use('/api/gps', gpsRoutes);
app.use('/api/admin', adminRoutes);
app.use('/api/duty', dutyRoutes);
app.use('/api/reports', reportRoutes);

app.use((req, res) => {
  res.status(404).json({ message: 'Route not found' });
});

const PORT = process.env.PORT || 5000;

const start = async () => {
  try {
    await connectDB();

    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);
    });

    if (process.env.DISABLE_REPORT_SCHEDULER !== 'true') {
      startScheduler();
    }
  } catch (error) {
    console.error('Server startup failed:', error.message);
    process.exit(1);
  }
};

if (require.main === module) {
  start();
}

module.exports = app;
