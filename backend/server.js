require('dotenv').config();
const express = require('express');
const path = require('path');
const cors = require('cors');

const analysisRoutes = require('./routes/analysis');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve frontend (one line)
app.use(express.static(path.join(__dirname, '..', 'frontend')));

// Serve processed folder for annotated files
app.use('/processed', express.static(path.join(__dirname, 'processed')));

// API routes
app.use('/api', analysisRoutes);

app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
