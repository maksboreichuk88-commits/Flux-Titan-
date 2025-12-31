require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const twilio = require('twilio');
const nodemailer = require('nodemailer');
const { google } = require('googleapis');
const fs = require('fs');

const app = express();
app.use(bodyParser.json());

const {
  PORT = 3000,
  PIPEDRIVE_API_TOKEN,
  PIPEDRIVE_BASE,
  TWILIO_ACCOUNT_SID,
  TWILIO_AUTH_TOKEN,
  TWILIO_FROM,
  SMTP_HOST,
  SMTP_PORT,
  SMTP_USER,
  SMTP_PASS,
  CALENDLY_LINK,
  GOOGLE_SERVICE_ACCOUNT_KEY_PATH,
  SHEETS_ID,
  TELEGRAM_BOT_TOKEN,
  TELEGRAM_CHAT_ID
} = process.env;

const twilioClient = TWILIO_ACCOUNT_SID && TWILIO_AUTH_TOKEN ? twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) : null;

async function createPipedrivePerson({ name, phone, email }) {
  if (!PIPEDRIVE_API_TOKEN || !PIPEDRIVE_BASE) return { id: null };
  const url = `${PIPEDRIVE_BASE}/persons?api_token=${PIPEDRIVE_API_TOKEN}`;
  const res = await axios.post(url, { name, phone, email });
  return res.data.data;
}

async function createPipedriveDeal({ title, person_id, value = 0 }) {
  if (!PIPEDRIVE_API_TOKEN || !PIPEDRIVE_BASE) return { id: null };
  const url = `${PIPEDRIVE_BASE}/deals?api_token=${PIPEDRIVE_API_TOKEN}`;
  const res = await axios.post(url, { title, person_id, value });
  return res.data.data;
}

async function createPipedriveActivity({ subject, due_date, deal_id, person_id }) {
  if (!PIPEDRIVE_API_TOKEN || !PIPEDRIVE_BASE) return { id: null };
  const url = `${PIPEDRIVE_BASE}/activities?api_token=${PIPEDRIVE_API_TOKEN}`;
  const res = await axios.post(url, { subject, due_date, done: 0, deal_id, person_id });
  return res.data.data;
}

async function sendWhatsApp(to, text) {
  if (!twilioClient || !TWILIO_FROM) return null;
  return twilioClient.messages.create({ from: TWILIO_FROM, to, body: text });
}

async function sendEmail({ to, subject, html }) {
  if (!SMTP_HOST) return null;
  const transporter = nodemailer.createTransport({
    host: SMTP_HOST, port: parseInt(SMTP_PORT || 587), secure: false,
    auth: { user: SMTP_USER, pass: SMTP_PASS }
  });
  return transporter.sendMail({ from: SMTP_USER, to, subject, html });
}

async function appendSheetRow(row) {
  if (!GOOGLE_SERVICE_ACCOUNT_KEY_PATH || !SHEETS_ID) return null;
  const keyData = JSON.parse(fs.readFileSync(GOOGLE_SERVICE_ACCOUNT_KEY_PATH, 'utf8'));
  const auth = new google.auth.GoogleAuth({
    credentials: keyData,
    scopes: ['https://www.googleapis.com/auth/spreadsheets']
  });
  const sheets = google.sheets({ version: 'v4', auth });
  return sheets.spreadsheets.values.append({
    spreadsheetId: SHEETS_ID,
    range: 'leads!A:Z',
    valueInputOption: 'RAW',
    requestBody: { values: [row] }
  });
}

async function notifyTelegram(text) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) return null;
  return axios.post(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
    chat_id: TELEGRAM_CHAT_ID, text, parse_mode: 'HTML'
  });
}

app.post('/lead', async (req, res) => {
  try {
    const { name, phone, email, source = 'web', property = '', message = '' } = req.body;
    if (!name || !phone) return res.status(400).json({ error: 'name and phone required' });

    // 1) Create person
    const person = await createPipedrivePerson({ name, phone, email });

    // 2) Create deal
    const dealTitle = `Lead: ${property || 'н/д'} — ${name}`;
    const deal = await createPipedriveDeal({ title: dealTitle, person_id: person.id });

    // 3) Create activity (task)
    const dueDate = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString().split('T')[0]; // today
    const activity = await createPipedriveActivity({ subject: 'Назначить показ / связаться', due_date: dueDate, deal_id: deal.id, person_id: person.id });

    // 4) Send WhatsApp/SMS
    const waTo = phone.startsWith('whatsapp:') ? phone : `whatsapp:${phone.replace(/\D/g,'')}`;
    const waText = `Здравствуйте, ${name}! Спасибо за заявку на объект "${property}". Записаться на показ можно здесь: ${CALENDLY_LINK || '[CALENDLY_LINK]'}`;
    await sendWhatsApp(waTo, waText);

    // 5) Send email
    if (email) {
      const subject = 'Подтверждение заявки — назначьте показ';
      const html = `<p>Здравствуйте, ${name}!</p><p>Спасибо за заявку на "${property}". <a href="${CALENDLY_LINK || '#'}">Записаться на показ</a></p>`;
      await sendEmail({ to: email, subject, html });
    }

    // 6) Append to Google Sheets
    const row = [new Date().toISOString(), name, phone, email || '', source, property || '', message || '', person.id, deal.id, activity.id];
    await appendSheetRow(row);

    // 7) Notify Telegram/Slack
    const note = `Новый лид: ${name} | ${phone} | ${property} | ${source}`;
    await notifyTelegram(note);

    res.json({ ok: true, person_id: person.id, deal_id: deal.id });
  } catch (err) {
    console.error(err.response ? err.response.data : err);
    res.status(500).json({ error: 'internal_error', details: err.message });
  }
});

app.listen(PORT, () => console.log(`Lead webhook running on port ${PORT}`));
