const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const dotenv = require('dotenv');
dotenv.config();

const connectDB = async () => {
  await mongoose.connect(process.env.MONGODB_URI);
  console.log('Connected to MongoDB');
};

const seedDatabase = async () => {
  try {
    await connectDB();

    // Import models AFTER connection
    const User = require('../models/User');
    const Bus = require('../models/Bus');
    const Route = require('../models/Route');

    // ── CREATE ADMIN ──────────────────────────────
    const adminExists = await User.findOne({ role: 'admin' });
    if (!adminExists) {
      const salt = await bcrypt.genSalt(10);
      const hashedPassword = await bcrypt.hash('admin1', salt);

      await User.collection.insertOne({
        username: 'admin',
        userId: 'ADMIN1',
        password: hashedPassword,
        email: 'mehrozalikhan034@gmail.com',
        role: 'admin',
        isActive: true,
        loginAttempts: 0,
        lockUntil: null,
        favoriteRoutes: [],
        profileInfo: {
          fullName: 'Administrator',
          phone: '03081637707'
        },
        createdAt: new Date()
      });
      console.log('✅ Admin created');
      console.log('   Username: admin');
      console.log('   UserID:   ADMIN-001');
      console.log('   Password: admin123456');
    } else {
      console.log('⚠️  Admin already exists');
    }

    // ── CREATE TEST DRIVER ────────────────────────
    const driverExists = await User.findOne({ userId: 'DRV-001' });
    if (!driverExists) {
      const salt = await bcrypt.genSalt(10);
      const hashedPassword = await bcrypt.hash('driver123', salt);

      await User.collection.insertOne({
        username: 'driver_ahmed',
        userId: 'DRV-001',
        password: hashedPassword,
        email: 'ahmed@electricbus.pk',
        role: 'driver',
        isActive: true,
        loginAttempts: 0,
        lockUntil: null,
        favoriteRoutes: [],
        profileInfo: {
          fullName: 'Ahmed Khan',
          phone: '03111234567'
        },
        createdAt: new Date()
      });
      console.log('✅ Test driver created');
      console.log('   Username: driver_ahmed');
      console.log('   UserID:   DRV-001');
      console.log('   Password: driver123');
    } else {
      console.log('⚠️  Driver already exists');
    }

    // ── CREATE BUSES ──────────────────────────────
    const busCount = await Bus.countDocuments();
    if (busCount === 0) {
      await Bus.insertMany([
        {
          busId: 'BUS-001',
          busNumber: 'MWL-001',
          capacity: 40,
          model: 'Yutong Electric',
          status: 'inactive'
        },
        {
          busId: 'BUS-002',
          busNumber: 'MWL-002',
          capacity: 40,
          model: 'Yutong Electric',
          status: 'inactive'
        },
        {
          busId: 'BUS-003',
          busNumber: 'MWL-003',
          capacity: 35,
          model: 'BYD Electric',
          status: 'inactive'
        }
      ]);
      console.log('✅ 3 Buses created');
    } else {
      console.log('⚠️  Buses already exist');
    }

    // ── CREATE ROUTES ─────────────────────────────
    const routeCount = await Route.countDocuments();
    if (routeCount === 0) {
      await Route.insertMany([
        {
          routeId: 'ROUTE-001',
          routeName: 'Barnala - Mianwali',
          startPoint: {
            name: 'Barnala',
            latitude: 32.4761,
            longitude: 71.4489
          },
          endPoint: {
            name: 'Mianwali City',
            latitude: 32.5838,
            longitude: 71.5436
          },
          stops: [
            {
              stopId: 'STOP-001',
              name: 'Barnala',
              latitude: 32.4761,
              longitude: 71.4489,
              order: 1,
              arrivalTimes: ['08:00', '10:00', '14:00', '17:00']
            },
            {
              stopId: 'STOP-002',
              name: 'Namal',
              latitude: 32.5200,
              longitude: 71.4800,
              order: 2,
              arrivalTimes: ['08:15', '10:15', '14:15', '17:15']
            },
            {
              stopId: 'STOP-003',
              name: 'Mianwali City',
              latitude: 32.5838,
              longitude: 71.5436,
              order: 3,
              arrivalTimes: ['08:40', '10:40', '14:40', '17:40']
            }
          ],
          totalDistance: 18.5,
          estimatedTotalTime: 40,
          schedule: [
            {
              departureTime: '08:00',
              days: ['Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday']
            }
          ],
          isActive: true
        },
        {
          routeId: 'ROUTE-002',
          routeName: 'Mianwali - Daudkhel',
          startPoint: {
            name: 'Mianwali City',
            latitude: 32.5838,
            longitude: 71.5436
          },
          endPoint: {
            name: 'Daudkhel',
            latitude: 32.8833,
            longitude: 71.5667
          },
          stops: [
            {
              stopId: 'STOP-004',
              name: 'Mianwali City',
              latitude: 32.5838,
              longitude: 71.5436,
              order: 1,
              arrivalTimes: ['09:00', '13:00', '16:00']
            },
            {
              stopId: 'STOP-005',
              name: 'Khairabad',
              latitude: 32.7000,
              longitude: 71.5500,
              order: 2,
              arrivalTimes: ['09:20', '13:20', '16:20']
            },
            {
              stopId: 'STOP-006',
              name: 'Daudkhel',
              latitude: 32.8833,
              longitude: 71.5667,
              order: 3,
              arrivalTimes: ['09:50', '13:50', '16:50']
            }
          ],
          totalDistance: 32.0,
          estimatedTotalTime: 50,
          schedule: [
            {
              departureTime: '09:00',
              days: ['Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday', 'Saturday']
            }
          ],
          isActive: true
        },
        {
          routeId: 'ROUTE-003',
          routeName: 'Mianwali - Wan Bachran',
          startPoint: {
            name: 'Mianwali City',
            latitude: 32.5838,
            longitude: 71.5436
          },
          endPoint: {
            name: 'Wan Bachran',
            latitude: 32.3500,
            longitude: 71.7000
          },
          stops: [
            {
              stopId: 'STOP-007',
              name: 'Mianwali City',
              latitude: 32.5838,
              longitude: 71.5436,
              order: 1,
              arrivalTimes: ['07:30', '12:00', '15:30']
            },
            {
              stopId: 'STOP-008',
              name: 'Piplan',
              latitude: 32.4500,
              longitude: 71.6500,
              order: 2,
              arrivalTimes: ['07:55', '12:25', '15:55']
            },
            {
              stopId: 'STOP-009',
              name: 'Wan Bachran',
              latitude: 32.3500,
              longitude: 71.7000,
              order: 3,
              arrivalTimes: ['08:30', '13:00', '16:30']
            }
          ],
          totalDistance: 28.0,
          estimatedTotalTime: 60,
          schedule: [
            {
              departureTime: '07:30',
              days: ['Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday']
            }
          ],
          isActive: true
        }
      ]);
      console.log('✅ 3 Routes created');
    } else {
      console.log('⚠️  Routes already exist');
    }

    console.log('\n🎉 Database seeded successfully!');
    console.log('─────────────────────────────────');
    console.log('Admin:  admin / ADMIN-001 / admin123456');
    console.log('Driver: driver_ahmed / DRV-001 / driver123');
    console.log('─────────────────────────────────');
    process.exit(0);

  } catch (error) {
    console.error('❌ Seed error:', error.message);
    process.exit(1);
  }
};

seedDatabase();