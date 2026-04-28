const sgMail = require('@sendgrid/mail');

const sendResetCode = async (email, code, fullName) => {
  const apiKey = process.env.SENDGRID_API_KEY;
  const fromEmail = process.env.EMAIL_FROM;

  console.log('SendGrid API Key exists:', !!apiKey);
  console.log('EMAIL_FROM:', fromEmail);
  console.log('Sending to:', email);

  if (!apiKey) {
    throw new Error('SENDGRID_API_KEY missing from environment');
  }
  if (!fromEmail) {
    throw new Error('EMAIL_FROM missing from environment');
  }

  sgMail.setApiKey(apiKey);

  const msg = {
    to: email,
    from: {
      email: fromEmail,
      name: 'Electric Bus Tracker'
    },
    subject: 'Your Password Reset Code',
    text: `Your password reset code is: ${code}. Valid for 10 minutes.`,
    html: `
      <div style="font-family:Arial,sans-serif;max-width:480px;
                  margin:0 auto;padding:24px;border:1px solid #eee;
                  border-radius:10px;">
        <h2 style="color:#2ECC71;text-align:center;">
          Electric Bus Tracker
        </h2>
        <p>Dear ${fullName},</p>
        <p>Your password reset code is:</p>
        <div style="text-align:center;margin:24px 0;">
          <span style="background:#2ECC71;color:#fff;
                       font-size:28px;font-weight:bold;
                       letter-spacing:6px;padding:16px 24px;
                       border-radius:8px;display:inline-block;">
            ${code}
          </span>
        </div>
        <p style="color:#888;font-size:12px;">
          This code expires in 10 minutes.
          If you didn't request this, ignore this email.
        </p>
      </div>
    `
  };

  try {
    const [response] = await sgMail.send(msg);
    console.log('✅ Email sent! Status:', response.statusCode);
    return true;
  } catch (error) {
    console.error('❌ SendGrid error:', error.message);
    if (error.response?.body?.errors) {
      error.response.body.errors.forEach(e => {
        console.error('  Error:', e.message);
      });
    }
    throw error;
  }
};

module.exports = { sendResetCode };