// controllers/analysisController.js  (updated robust parser)
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

// ensure uploads and processed dirs exist
const UPLOADS_DIR = path.join(__dirname, '..', 'uploads');
const PROCESSED_DIR = path.join(__dirname, '..', 'processed');

if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR, { recursive: true });
if (!fs.existsSync(PROCESSED_DIR)) fs.mkdirSync(PROCESSED_DIR, { recursive: true });

function tryExtractJson(text) {
  if (!text) return null;
  const firstBrace = text.indexOf('{');
  const lastBrace = text.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
    const candidate = text.slice(firstBrace, lastBrace + 1);
    try {
      return JSON.parse(candidate);
    } catch (err) {
      return null;
    }
  }
  return null;
}

exports.analyzeVideo = (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No video uploaded (field name must be "video")' });
    }

    const inputPath = req.file.path;
    const outFilename = `annotated-${Date.now()}.avi`;
    const outputPath = path.join(PROCESSED_DIR, outFilename);

    const pythonScript = path.join(__dirname, '..', 'python', 'analyze_video.py');

    const pyCmd = process.platform === 'win32' ? 'python' : 'python3';
    const args = [pythonScript, '--input', inputPath, '--output', outputPath];

    const py = spawn(pyCmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });

    let stdoutData = '';
    let stderrData = '';

    py.stdout.on('data', (chunk) => {
      stdoutData += chunk.toString();
    });

    py.stderr.on('data', (chunk) => {
      stderrData += chunk.toString();
      // still log server-side so you can see messages
      console.error('[PY ERR]', chunk.toString());
    });

    py.on('close', (code) => {
      // Try to parse stdoutData as JSON
      let summary = null;
      let parseError = null;

      // First try direct parse
      try {
        const cleaned = stdoutData.trim();
        summary = cleaned ? JSON.parse(cleaned) : {};
      } catch (err) {
        parseError = err;
        // Attempt to extract JSON substring between first { and last }
        summary = tryExtractJson(stdoutData);
      }

      if (code !== 0 || !summary) {
        // Build helpful error response
        const annotatedVideoUrl = summary && summary.output ? `/processed/${path.basename(summary.output)}` : null;

        return res.status(500).json({
          error: 'Python analysis failed or returned invalid JSON',
          exit_code: code,
          parse_error: parseError ? parseError.message : undefined,
          stdout_raw: stdoutData ? stdoutData.slice(0, 5000) : undefined, // limit length
          stderr_raw: stderrData ? stderrData.slice(0, 5000) : undefined,
          annotatedVideoUrl // might be null
        });
      }

      // success
      const annotatedVideoUrl = `/processed/${outFilename}`;

      res.json({
        message: 'Analysis complete',
        annotatedVideoUrl,
        summary
      });
    });

    // safety: handle spawn errors
    py.on('error', (err) => {
      console.error('Failed to start python process:', err);
      return res.status(500).json({ error: 'Failed to start python process', details: err.message });
    });

  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Internal server error', details: err.message });
  }
};
