const cron = require('node-cron');
const { generateReport } = require('./reportGenerator');

const startScheduler = () => {
  cron.schedule('0 23 * * *', async () => {
    console.log('Generating daily report...');
    try {
      await generateReport('daily');
      console.log('Daily report done!');
    } catch (error) {
      console.error('Daily report error:', error.message);
    }
  });

  cron.schedule('30 23 * * 0', async () => {
    console.log('Generating weekly report...');
    try {
      await generateReport('weekly');
      console.log('Weekly report done!');
    } catch (error) {
      console.error('Weekly report error:', error.message);
    }
  });

  cron.schedule('55 23 28-31 * *', async () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (tomorrow.getDate() !== 1) {
      return;
    }

    console.log('Generating monthly report...');
    try {
      await generateReport('monthly');
      console.log('Monthly report done!');
    } catch (error) {
      console.error('Monthly report error:', error.message);
    }
  });

  console.log('Report scheduler started!');
};

module.exports = { startScheduler };
