const form = document.getElementById('uploadForm');
const statusDiv = document.getElementById('status');
const backend = 'http://localhost:3000'; // change if deployed

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('videoInput');
  if (!fileInput.files[0]) return;

  // preview original
  const originalVideo = document.getElementById('originalVideo');
  originalVideo.src = URL.createObjectURL(fileInput.files[0]);

  const formData = new FormData();
  formData.append('video', fileInput.files[0]);

  statusDiv.innerText = 'Uploading and analyzing...';

  try {
    const res = await fetch(`${backend}/api/analyze-video`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const text = await res.text();
      statusDiv.innerText = `Server error: ${res.status} ${res.statusText}`;
      console.error('Server response (non-ok):', text);
      return;
    }

    const data = await res.json();
    statusDiv.innerText = data.message || 'Analysis complete';

    // annotated URL from backend (already starts with /processed/...)
    const annotatedUrl = backend + data.annotatedVideoUrl;
    console.log('Annotated URL:', annotatedUrl);
    console.log('Summary:', data.summary);

    // show download button and set href
    const downloadLink = document.getElementById('downloadLink');
    const downloadBtn = document.getElementById('downloadBtn');

    // If backend returned an AVI or MP4, leave as-is. Otherwise, attempt .avi fallback
    downloadLink.href = annotatedUrl;
    downloadLink.style.display = 'inline-block';
    downloadBtn.style.display = 'inline-block';

    // render summary friendly
    renderSummary(data.summary);
  } catch (err) {
    console.error('Upload/analysis failed:', err);
    statusDiv.innerText = 'Upload/analysis failed. See console.';
  }
});

function renderSummary(summary) {
  const friendly = document.getElementById('summaryFriendly');
  const raw = document.getElementById('summary');
  raw.style.display = 'none';

  if (!summary) {
    friendly.innerText = 'No summary returned.';
    return;
  }

  const rows = [
    ['Frames processed', summary.frame_count_processed ?? summary.frame_count ?? '?'],
    ['FPS used', summary.fps_used ?? summary.fps ?? '?'],
    ['Resolution', (summary.resolution && (summary.resolution.width + '×' + summary.resolution.height)) || '?'],
    ['Total vehicle detections', summary.vehicle_detections_total ?? '?'],
    ['Illegal parking events', summary.illegal_parking_count ?? (summary.issues ? summary.issues.filter(i=>i.type==='illegal_parking').length : 0)]
  ];

  let html = '<table id="summaryTable"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>';
  for (const r of rows) html += `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`;
  html += '</tbody></table>';

  if (summary.issues && summary.issues.length) {
    html += '<h3>Detected issues</h3><ul>';
    for (const it of summary.issues) {
      html += `<li><strong>${it.type}</strong> — frame ${it.frame} — ${it.message || JSON.stringify(it)}</li>`;
    }
    html += '</ul>';
  } else {
    html += '<p>No issues detected (based on current heuristic).</p>';
  }

  friendly.innerHTML = html;
  raw.innerText = JSON.stringify(summary, null, 2);
}
