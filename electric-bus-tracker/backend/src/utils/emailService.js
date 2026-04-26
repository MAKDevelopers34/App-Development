const sgMail = require('@sendgrid/mail');

sgMail.setApiKey(process.env.SENDGRID_API_KEY);

const sendResetCode = async (email, code, fullName) => {
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
            🚌 Electric Bus Tracker
          </h2>
          <p style="color: #666;">
            Mianwali District, Pakistan
          </p>
        </div>

        <p style="color: #333;">
          Dear ${fullName || 'User'},
        </p>

        <p style="color: #333;">
          Your password reset code is:
        </p>

        <div style="text-align: center; margin: 30px 0;">
          <div style="background: #2ECC71; color: white;
                      font-size: 32px; font-weight: bold;
                      letter-spacing: 8px; padding: 20px;
                      border-radius: 10px;">
            ${code}
          </div>
        </div>

        <p style="color: #666; font-size: 13px;">
          This code expires in 
          <strong>10 minutes</strong>.
          Do not share it with anyone.
        </p>

        <p style="color: #666; font-size: 13px;">
          If you did not request this,
          please ignore this email.
        </p>

        <div style="margin-top: 30px; padding-top: 20px;
                    border-top: 1px solid #eee;
                    text-align: center; color: #aaa;
                    font-size: 12px;">
          Electric Bus Tracker — Mianwali District
        </div>
      </div>
    `,
  };

  await sgMail.send(msg);
  console.log(`Reset code sent to ${email}`);
};

module.exports = { sendResetCode };