const sgMail = require('@sendgrid/mail');
const { SESv2Client, SendEmailCommand } = require('@aws-sdk/client-sesv2');

const emailProvider = () => {
  const configured = String(process.env.EMAIL_PROVIDER || '').toLowerCase();
  if (configured) return configured;
  return process.env.SENDGRID_API_KEY ? 'sendgrid' : 'ses';
};

const fromAddress = () => {
  const email = process.env.EMAIL_FROM;
  if (!email) {
    throw new Error('EMAIL_FROM missing from environment');
  }
  return email;
};

const resetEmail = (code, fullName) => ({
  subject: 'Your Password Reset Code',
  text: `Dear ${fullName}, your Electric Bus Tracker password reset code is ${code}. It is valid for 5 minutes.`,
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
        This code expires in 5 minutes.
        If you did not request this, ignore this email.
      </p>
    </div>
  `
});

const sendWithSes = async ({ to, from, subject, text, html }) => {
  const region =
    process.env.AWS_SES_REGION ||
    process.env.AWS_REGION ||
    process.env.AWS_DEFAULT_REGION ||
    'ap-south-1';

  const client = new SESv2Client({ region });
  await client.send(
    new SendEmailCommand({
      FromEmailAddress: from,
      Destination: {
        ToAddresses: [to]
      },
      Content: {
        Simple: {
          Subject: {
            Data: subject,
            Charset: 'UTF-8'
          },
          Body: {
            Text: {
              Data: text,
              Charset: 'UTF-8'
            },
            Html: {
              Data: html,
              Charset: 'UTF-8'
            }
          }
        }
      }
    })
  );
};

const sendWithSendGrid = async ({ to, from, subject, text, html }) => {
  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) {
    throw new Error('SENDGRID_API_KEY missing from environment');
  }

  sgMail.setApiKey(apiKey);
  await sgMail.send({
    to,
    from: {
      email: from,
      name: 'Electric Bus Tracker'
    },
    subject,
    text,
    html
  });
};

const sendResetCode = async (email, code, fullName) => {
  const provider = emailProvider();
  const from = fromAddress();
  const message = resetEmail(code, fullName);

  if (provider === 'ses') {
    await sendWithSes({ to: email, from, ...message });
    return true;
  }

  if (provider === 'sendgrid') {
    await sendWithSendGrid({ to: email, from, ...message });
    return true;
  }

  throw new Error(`Unsupported EMAIL_PROVIDER: ${provider}`);
};

module.exports = { sendResetCode };
