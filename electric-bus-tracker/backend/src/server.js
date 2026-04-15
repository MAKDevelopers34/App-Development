const express = require('express');
const dotenv = require('dotenv');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const connectDB = require('./config/database');

dotenv.config();
connectDB();

const app = express();

app.use(helmet());
app.use(cors());
app.use(morgan('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

const authRoutes = require('./routes/authRoutes');
app.use('/api/auth', authRoutes);

app.get('/', (req, res) => {
  res.json({
    message: 'Electric Bus Tracker API is running!',
    version: '1.0.0',
    status: 'ok'
  });
});

app.use((req, res) => {
  res.status(404).json({ message: 'Route not found' });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});