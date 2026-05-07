require('dotenv/config');
const express = require('express');
const cors = require('cors');
const { Resend } = require('resend');

const app = express();
const resend = new Resend(process.env.RESEND_API_KEY);

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));

function formatEmailBody(type, data) {
  const lines = [`Type: ${type}`, '---'];
  for (const [key, value] of Object.entries(data)) {
    lines.push(`${key}: ${value}`);
  }
  return lines.join('\n');
}

app.post('/api/send', async (req, res) => {
  try {
    const { type, ...data } = req.body;

    const { error } = await resend.emails.send({
      from: 'Dabilio <hello@dabil.io>',
      to: ['marketing@dabil.io'],
      subject: `[${type}] Nouveau message depuis dabil.io`,
      text: formatEmailBody(type, data),
    });

    if (error) {
      console.error('Resend error:', error);
      return res.status(500).json({ error: error.message });
    }

    res.json({ success: true });
  } catch (err) {
    console.error('Server error:', err);
    res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
