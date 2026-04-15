const Ably = require('ably');

let ablyClient = null;

const getAblyClient = () => {
  if (!ablyClient) {
    ablyClient = new Ably.Rest(process.env.ABLY_API_KEY);
  }
  return ablyClient;
};

const publishLocation = async (routeId, locationData) => {
  try {
    const client = getAblyClient();
    const channel = client.channels.get(`bus-route-${routeId}`);
    await channel.publish('location-update', locationData);
    console.log(`Location published to channel: bus-route-${routeId}`);
  } catch (error) {
    console.error('Ably publish error:', error.message);
  }
};

module.exports = { getAblyClient, publishLocation };