const sgMail = require('@sendgrid/mail');

sgMail.setApiKey(process.env.SENDGRID_API_KEY);

const sendResetCode = async (email, code, fullName) => {
  try {
    if (!process.env.SENDGRID_API_KEY) {
      throw new Error('SENDGRID_API_KEY is not set in environment');
    }

    if (!process.env.EMAIL_FROM) {
      throw new Error('EMAIL_FROM is not set in environment');
    }

    const msg = {
      to: email,
      from: {
        email: process.env.EMAIL_FROM,
        name: 'Electric Bus Tracker'
      },
      subject: 'Password Reset Code — Electric Bus Tracker',
      html: `
        <div style="font-family: Arial, sans-serif;
                    max-width: 500px; margin: 0 auto;
                    padding: 30px; border-radius: 10px;
                    border: 1px solid #eee;">
          <div style="text-align: center; margin-bottom: 30px;">
            <h2 style="color: #2ECC71;">
              Electric Bus Tracker
            </h2>
            <p style="color: #666;">Mianwali District, Pakistan</p>
          </div>
          <p style="color: #333;">Dear ${fullName || 'User'},</p>
          <p style="color: #333;">Your password reset code is:</p>
          <div style="text-align: center; margin: 30px 0;">
            <div style="background: #2ECC71; color: white;
                        font-size: 32px; font-weight: bold;
                        letter-spacing: 8px; padding: 20px;
                        border-radius: 10px;">
              ${code}
            </div>
          </div>
          <p style="color: #666; font-size: 13px;">
            This code expires in <strong>10 minutes</strong>.
          </p>
          <p style="color: #666; font-size: 13px;">
            If you did not request this, ignore this email.
          </p>
        </div>
      `,
    };

    const response = await sgMail.send(msg);
    console.log(`✅ Reset code sent to ${email}`);
    console.log(`   SendGrid status: ${response[0].statusCode}`);
    return true;

  } catch (error) {
    console.error('❌ SendGrid error:', error.message);
    if (error.response) {
      console.error('   SendGrid body:', 
        JSON.stringify(error.response.body)
      );
    }
    throw error;
  }
};

module.exports = { sendResetCode };