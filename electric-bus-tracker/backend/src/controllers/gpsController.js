const BusLocation = require('../models/BusLocation');
const { publishLocation } = require('../config/ably');

const updateLocation = async (req, res) => {
  try {
    const { busId, routeId, latitude, longitude, speed } = req.body;
    const driverId = req.user._id;

    if (!busId || !routeId || !latitude || !longitude) {
      return res.status(400).json({ 
        message: 'busId, routeId, latitude and longitude are required' 
      });
    }

    const locationData = {
      busId,
      driverId,
      routeId,
      location: { latitude, longitude },
      speed: speed || 0,
      timestamp: new Date()
    };

    await BusLocation.findOneAndUpdate(
      { busId },
      locationData,
      { upsert: true, new: true }
    );

    await publishLocation(routeId, {
      busId,
      driverId: driverId.toString(),
      routeId,
      latitude,
      longitude,
      speed: speed || 0,
      timestamp: new Date()
    });

    res.json({
      success: true,
      message: 'Location updated and published',
      data: locationData
    });

  } catch (error) {
    res.status(500).json({ 
      message: 'Server error', 
      error: error.message 
    });
  }
};

const getActiveBuses = async (req, res) => {
  try {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);

    const activeBuses = await BusLocation.find({
      isActive: true,
      timestamp: { $gte: fiveMinutesAgo }
    }).populate('driverId', 'username profileInfo');

    res.json({
      success: true,
      count: activeBuses.length,
      buses: activeBuses
    });

  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

const getBusesByRoute = async (req, res) => {
  try {
    const { routeId } = req.params;
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);

    const buses = await BusLocation.find({
      routeId,
      isActive: true,
      timestamp: { $gte: fiveMinutesAgo }
    });

    res.json({
      success: true,
      count: buses.length,
      buses
    });

  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

const startDuty = async (req, res) => {
  try {
    const { busId, routeId } = req.body;
    const driverId = req.user._id;

    await BusLocation.findOneAndUpdate(
      { busId },
      {
        busId,
        driverId,
        routeId,
        isActive: true,
        location: { latitude: 0, longitude: 0 },
        timestamp: new Date()
      },
      { upsert: true, new: true }
    );

    await publishLocation(routeId, {
      busId,
      driverId: driverId.toString(),
      routeId,
      status: 'duty-started',
      timestamp: new Date()
    });

    res.json({
      success: true,
      message: 'Duty started successfully'
    });

  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

const endDuty = async (req, res) => {
  try {
    const { busId, routeId } = req.body;

    await BusLocation.findOneAndUpdate(
      { busId },
      { isActive: false, timestamp: new Date() }
    );

    await publishLocation(routeId, {
      busId,
      status: 'duty-ended',
      timestamp: new Date()
    });

    res.json({
      success: true,
      message: 'Duty ended successfully'
    });

  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

const getAblyToken = async (req, res) => {
  try {
    const Ably = require('ably');
    const client = new Ably.Rest(process.env.ABLY_API_KEY);

    const tokenParams = {
      clientId: req.user._id.toString()
    };

    client.auth.createTokenRequest(tokenParams, (err, tokenRequest) => {
      if (err) {
        return res.status(500).json({ 
          message: 'Error creating Ably token' 
        });
      }
      res.json({ success: true, tokenRequest });
    });

  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

module.exports = {
  updateLocation,
  getActiveBuses,
  getBusesByRoute,
  startDuty,
  endDuty,
  getAblyToken
};