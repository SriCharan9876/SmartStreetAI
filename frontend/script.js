const form = document.getElementById('uploadForm');
const statusDiv = document.getElementById('status');
const backend = 'http://localhost:3000'; // change if deployed

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const fileInput = document.getElementById('videoInput');
  if (!fileInput.files[0]) return;

  // Preview original video
  const originalVideo = document.getElementById('originalVideo');
  originalVideo.src = URL.createObjectURL(fileInput.files[0]);

  const formData = new FormData();
  formData.append('video', fileInput.files[0]);

  statusDiv.innerText = 'Uploading & analyzing…';

  try {
    const res = await fetch(`${backend}/api/analyze-video`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      statusDiv.innerText = `Server error (${res.status})`;
      console.error(await res.text());
      return;
    }

    const data = await res.json();
    console.log(data.summary);
    statusDiv.innerText = 'Analysis complete';

    // Download link
    const downloadLink = document.getElementById('downloadLink');
    const downloadBtn = document.getElementById('downloadBtn');
    downloadLink.href = backend + data.annotatedVideoUrl;
    downloadBtn.style.display = 'inline-block';
    
    renderSummary(data.summary);
  } catch (err) {
    console.error(err);
    statusDiv.innerText = 'Upload / analysis failed';
  }
});

function renderSummary(summary) {
  const friendly = document.getElementById('summaryFriendly');
  const raw = document.getElementById('summary');
  raw.style.display = 'none';

  if (!summary) {
    friendly.innerHTML = '<p>No summary returned.</p>';
    return;
  }

  const vehicles = summary.vehicles || {};
  const crowd = summary.crowd || {};
  const issues = summary.issues || [];

  let html = '';

  // ---- Vehicles ----
  html += `
    <div class="section">
      <h3>🚗 Vehicles</h3>
      <ul>
        <li>Total detections: <b>${vehicles.total_detections ?? 0}</b></li>
        <li>Illegal parked vehicles: <b>${vehicles.illegal_parked ?? 0}</b></li>
      </ul>
    </div>
  `;

  // ---- Crowd ----
  html += `
    <div class="section">
      <h3>👥 Crowd</h3>
      <ul>
        <li>Max people detected in ROI: <b>${crowd.max_people_detected ?? 0}</b></li>
      </ul>
    </div>
  `;

  // ---- Issues ----
  html += `<div class="section"><h3>⚠️ Detected Issues</h3>`;
  if (issues.length === 0) {
    html += `<p class="muted">No civic issues detected.</p>`;
  } else {
    html += `<ul class="issues">`;
    issues.forEach((i, idx) => {
      html += `<li>
        <span class="badge ${i.type}">${i.type}</span>
        <span class="issue-text">#${idx + 1}</span>
      </li>`;
    });
    html += `</ul>`;
  }
  html += `</div>`;

  friendly.innerHTML = html;
  raw.innerText = JSON.stringify(summary, null, 2);
}
