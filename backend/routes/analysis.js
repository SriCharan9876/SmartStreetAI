// routes/analysis.js
const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const analysisController = require('../controllers/analysisController');

// multer storage config
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, path.join(__dirname, '..', 'uploads'));
  },
  filename: function (req, file, cb) {
    const ts = Date.now();
    // keep original extension
    const ext = path.extname(file.originalname) || '.mp4';
    cb(null, `video-${ts}${ext}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 200 * 1024 * 1024 } // 200MB limit
});

// POST /api/analyze-video
router.post('/analyze-video', upload.single('video'), analysisController.analyzeVideo);

module.exports = router;
