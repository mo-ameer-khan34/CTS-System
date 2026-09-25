// TRACE — Captain Dashboard JavaScript

let currentDocketId = null;
let currentDocketNumber = null;
let currentTab = 'dashboard';
let chartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
  loadCaptainProfile();
  loadStats();
});

// ── Stats & Chart ─────────────────────────────────────────────────────────────
function loadStats() {
  fetch('/captain/api/stats')
    .then(r => r.json())
    .then(d => {
      setText('statClosed', d.closed);
      setText('statEscalated', d.escalated);
      setText('statFlagged', d.flagged);
      buildChart(d.closed, d.escalated, d.flagged);
    });
}

function buildChart(closed, escalated, flagged) {
  const ctx = document.getElementById('activityChart');
  if (!ctx) return;
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Cases Closed', 'Cases Escalated', 'Cases Flagged'],
      datasets: [{
        label: 'This Month',
        data: [closed, escalated, flagged],
        backgroundColor: ['#0052CC', '#F0B429', '#001A57'],
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
    }
  });
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Tab handling ──────────────────────────────────────────────────────────────
const origShowTab = window.showTab;
window.showTab = function(tabName, el) {
  origShowTab(tabName, el);
  currentTab = tabName;
  if (tabName === 'cases-to-close') loadCasesToClose();
  if (tabName === 'escalated') loadEscalated();
  if (tabName === 'flagged') loadFlagged();
  if (tabName === 'profile') loadCaptainProfile();
  if (tabName === 'dashboard') loadStats();
  return false;
};

// ── Cases to close ────────────────────────────────────────────────────────────
function loadCasesToClose() {
  const wrap = document.getElementById('closeCasesTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch('/captain/api/cases-to-close')
    .then(r => r.json())
    .then(cases => {
      if (!cases.length) { wrap.innerHTML = '<div class="loading-state"><p>No cases ready for closure.</p></div>'; return; }
      let html = `<table class="cases-table"><thead><tr>
        <th>Case Number</th><th>Case Type</th><th>Complainant</th><th>Officer</th><th>Date</th><th>Actions</th>
      </tr></thead><tbody>`;
      cases.forEach(c => {
        html += `<tr>
          <td>${escHtml(c.case_number)}</td>
          <td>${escHtml(c.case_type)}</td>
          <td>${escHtml(c.complainant_full_name)}</td>
          <td>${escHtml(c.officer_name)}</td>
          <td>${formatDateOnly(c.date_reported)}</td>
          <td>
            <button class="btn btn-sm btn-outline" onclick="requestViewCaptainDocket(${c.id},'${escHtml(c.case_number)}','close')">View / Close</button>
            <button class="btn btn-sm btn-danger" onclick="openFlagModal(${c.id},'${escHtml(c.case_number)}')">Flag</button>
          </td>
        </tr>`;
      });
      html += '</tbody></table>';
      wrap.innerHTML = html;
    })
    .catch(() => { wrap.innerHTML = '<div class="loading-state"><p>Failed to load.</p></div>'; });
}

// ── Escalated cases ───────────────────────────────────────────────────────────
function loadEscalated() {
  const wrap = document.getElementById('escalatedTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch('/captain/api/escalated-cases')
    .then(r => r.json())
    .then(cases => {
      if (!cases.length) { wrap.innerHTML = '<div class="loading-state"><p>No escalated cases.</p></div>'; return; }
      let html = `<table class="cases-table"><thead><tr>
        <th>Case Number</th><th>Case Type</th><th>Complainant</th><th>Officer</th><th>Date</th><th>Actions</th>
      </tr></thead><tbody>`;
      cases.forEach(c => {
        html += `<tr>
          <td>${escHtml(c.case_number)}</td>
          <td>${escHtml(c.case_type)}</td>
          <td>${escHtml(c.complainant_full_name)}</td>
          <td>${escHtml(c.officer_name)}</td>
          <td>${formatDateOnly(c.date_reported)}</td>
          <td><button class="btn btn-sm btn-outline" onclick="requestViewCaptainDocket(${c.id},'${escHtml(c.case_number)}','escalated')">View / Update</button></td>
        </tr>`;
      });
      html += '</tbody></table>';
      wrap.innerHTML = html;
    })
    .catch(() => { wrap.innerHTML = '<div class="loading-state"><p>Failed to load.</p></div>'; });
}

// ── Flagged cases ─────────────────────────────────────────────────────────────
function loadFlagged() {
  const wrap = document.getElementById('flaggedTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch('/captain/api/flagged-cases')
    .then(r => r.json())
    .then(cases => {
      if (!cases.length) { wrap.innerHTML = '<div class="loading-state"><p>No flagged cases.</p></div>'; return; }
      let html = `<table class="cases-table"><thead><tr>
        <th>Case Number</th><th>Case Type</th><th>Flagged At</th><th>Reason</th><th>Actions</th>
      </tr></thead><tbody>`;
      cases.forEach(c => {
        html += `<tr>
          <td>${escHtml(c.case_number)}</td>
          <td>${escHtml(c.case_type)}</td>
          <td>${formatDate(c.flagged_at)}</td>
          <td>${escHtml(c.reason.substring(0,60))}${c.reason.length > 60 ? '...' : ''}</td>
          <td><button class="btn btn-sm btn-outline" onclick="requestViewCaptainDocket(${c.docket_id},'${escHtml(c.case_number)}','view')">View / Edit</button></td>
        </tr>`;
      });
      html += '</tbody></table>';
      wrap.innerHTML = html;
    })
    .catch(() => { wrap.innerHTML = '<div class="loading-state"><p>Failed to load.</p></div>'; });
}

// ── Docket view flow ──────────────────────────────────────────────────────────
function requestViewCaptainDocket(id, caseNum, context) {
  currentDocketId = id;
  currentDocketNumber = caseNum;
  document.getElementById('confirmDocketNumber').textContent = caseNum;
  openModal('confirmModal');
  document.querySelector('#confirmModal .btn-primary').onclick = () => {
    closeModal('confirmModal');
    confirmCaptainViewInternal(id, caseNum, context);
  };
}

function confirmCaptainView() {} // placeholder overridden inline above

function confirmCaptainViewInternal(id, caseNum, context) {
  fetch(`/captain/api/confirm-view/${id}`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) openCaptainDocketModal(id, context);
      else showToast(data.message || 'Error', 'error');
    });
}

function openCaptainDocketModal(id, context) {
  openModal('docketModal');
  document.getElementById('docketModalBody').innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  document.getElementById('docketModalFooter').innerHTML = '';

  fetch(`/captain/api/docket/${id}`)
    .then(r => r.json())
    .then(d => {
      document.getElementById('modalCaseNum').textContent = d.case_number;
      currentDocketId = d.id;

      const docs = d.documents || [];
      const byType = {};
      docs.forEach(doc => {
        if (!byType[doc.document_type]) byType[doc.document_type] = [];
        byType[doc.document_type].push(doc);
      });

      const typeLabels = { affidavit: 'Affidavit', witness_statement: 'Witness Statements', investigation_diary: 'Investigation Diary', suspect_info: 'Suspect Info', evidence: 'Evidence' };
      let docList = Object.keys(typeLabels).flatMap(type =>
        (byType[type] || []).map(doc => {
          const normalizedPath = doc.file_path.replace(/\\/g, '/');
          const fileUrl = `/captain/file/${encodeURIComponent(normalizedPath)}`;
          return `<li class="doc-item"><span class="doc-type">${typeLabels[type]}</span><span><a href="${fileUrl}" target="_blank" rel="noopener">${escHtml(doc.file_name)}</a></span><span class="doc-ver">v${doc.version}</span></li>`;
        })
      ).join('');

      let statusOpts = '';
      if (context === 'close') {
        statusOpts = `<option value="Investigation Completed" ${d.status==='Investigation Completed'?'selected':''}>Investigation Completed</option>
                      <option value="Case Closed">Case Closed</option>`;
      } else if (context === 'escalated') {
        statusOpts = `<option value="Escalated to Captain" ${d.status==='Escalated to Captain'?'selected':''}>Escalated to Captain</option>
                      <option value="Investigation in Progress">Investigation in Progress</option>
                      <option value="Case Closed">Case Closed</option>`;
      } else {
        statusOpts = ['Case Reported','Investigator Assigned','Investigation in Progress','Court Proceedings','Escalated to Captain','Investigation Completed','Case Closed']
          .map(s => `<option value="${s}" ${s===d.status?'selected':''}>${s}</option>`).join('');
      }

      document.getElementById('docketModalBody').innerHTML = `
        <div class="docket-view-section">
          <h4>Case Details</h4>
          <div class="detail-row">
            <div class="detail-col"><label>Complainant</label><input type="text" value="${escHtml(d.complainant_full_name)}" readonly style="background:#f5f6fa;"></div>
            <div class="detail-col"><label>Complainant ID</label><input type="text" value="${escHtml(d.complainant_id_number)}" readonly style="background:#f5f6fa;"></div>
          </div>
          <div class="detail-row">
            <div class="detail-col"><label>Case Type</label><input type="text" value="${escHtml(d.case_type)}" data-field="case_type"></div>
            <div class="detail-col"><label>Reporting Station</label><input type="text" value="${escHtml(d.reporting_station)}" data-field="reporting_station"></div>
          </div>
          <div class="detail-row">
            <div class="detail-col"><label>Investigating Officer</label><input type="text" value="${escHtml(d.investigating_officer)}" readonly style="background:#f5f6fa;"></div>
            <div class="detail-col"><label>Status</label><select data-field="status">${statusOpts}</select></div>
          </div>
        </div>
        ${docList ? `<div class="docket-view-section"><h4>Documents</h4><ul class="doc-list">${docList}</ul></div>` : ''}
      `;

      // Footer buttons
      let footerHtml = `<button class="btn btn-outline" onclick="closeModal('docketModal')">Close</button>
        <button class="btn btn-primary" onclick="saveCaptainDocket()">Save Changes</button>`;
      if (context === 'close') {
        footerHtml += `<button class="btn btn-primary" style="background:var(--success);border-color:var(--success);" onclick="closeCase(${d.id})">Close Case</button>`;
      }
      document.getElementById('docketModalFooter').innerHTML = footerHtml;
    })
    .catch(() => { document.getElementById('docketModalBody').innerHTML = '<p>Failed to load docket.</p>'; });
}

function saveCaptainDocket() {
  const body = document.getElementById('docketModalBody');
  const fd = new FormData();
  body.querySelectorAll('[data-field]').forEach(el => fd.append(el.dataset.field, el.value));

  fetch(`/captain/api/docket/${currentDocketId}/save`, { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        closeModal('docketModal');
        showToast(data.message, 'success');
        loadStats();
        if (currentTab === 'cases-to-close') loadCasesToClose();
        if (currentTab === 'escalated') loadEscalated();
        if (currentTab === 'flagged') loadFlagged();
      } else {
        showToast(data.message || 'Save failed.', 'error');
      }
    });
}

function closeCase(id) {
  if (!confirm('Are you sure you want to close this case? This action will be logged.')) return;
  fetch(`/captain/api/close-case/${id}`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        closeModal('docketModal');
        showToast(data.message, 'success');
        loadStats();
        loadCasesToClose();
      } else {
        showToast(data.message || 'Failed to close.', 'error');
      }
    });
}

// ── Flag docket ───────────────────────────────────────────────────────────────
let flagDocketId = null;
function openFlagModal(id, caseNum) {
  flagDocketId = id;
  document.getElementById('flagDocketNum').textContent = caseNum;
  document.getElementById('flagReason').value = '';
  document.getElementById('flagError').style.display = 'none';
  openModal('flagModal');
}

function submitFlag() {
  const reason = document.getElementById('flagReason').value.trim();
  if (!reason) {
    document.getElementById('flagError').textContent = 'Please provide a reason for flagging.';
    document.getElementById('flagError').style.display = 'block';
    return;
  }
  const fd = new FormData();
  fd.append('reason', reason);
  fetch(`/captain/api/flag/${flagDocketId}`, { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        closeModal('flagModal');
        showToast(data.message, 'success');
        loadCasesToClose();
        loadStats();
      } else {
        document.getElementById('flagError').textContent = data.message;
        document.getElementById('flagError').style.display = 'block';
      }
    });
}

// ── Profile ───────────────────────────────────────────────────────────────────
function loadCaptainProfile() {
  fetch('/captain/api/profile')
    .then(r => r.json())
    .then(d => {
      setVal('pf_name', d.full_name);
      setVal('pf_email', d.email);
      setVal('pf_oid', d.officer_id);
      setVal('pf_rank', d.rank_name);
      if (d.profile_picture) {
        const av = document.getElementById('profileAvatar');
        if (av) av.innerHTML = `<img src="/captain/file/${d.profile_picture}" alt="Profile">`;
      }
    });
}

function setVal(id, v) { const el = document.getElementById(id); if (el) el.value = v || ''; }

function saveCaptainProfile() {
  const fd = new FormData(document.getElementById('profileForm'));
  fetch('/captain/api/profile/update', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      const msg = document.getElementById('profileMsg');
      msg.className = 'alert ' + (data.success ? 'alert-success' : 'alert-error');
      msg.textContent = data.message;
      msg.style.display = 'block';
    });
}

function changeCaptainPassword() {
  const fd = new FormData();
  fd.append('current_password', document.getElementById('curPw').value);
  fd.append('new_password', document.getElementById('newPw').value);
  fd.append('confirm_password', document.getElementById('confPw').value);
  fetch('/captain/api/profile/password', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      const msg = document.getElementById('pwMsg');
      msg.className = 'alert ' + (data.success ? 'alert-success' : 'alert-error');
      msg.textContent = data.message;
      msg.style.display = 'block';
    });
}

function uploadCaptainProfilePicture(input) {
  if (!input.files || !input.files[0]) return;
  const fd = new FormData();
  fd.append('profile_picture', input.files[0]);
  fetch('/captain/api/profile/picture', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        const av = document.getElementById('profileAvatar');
        if (av) av.innerHTML = `<img src="/captain/file/${data.path}" alt="Profile">`;
        showToast('Profile picture updated.', 'success');
      } else {
        showToast(data.message, 'error');
      }
    });
}

// ── File serve ────────────────────────────────────────────────────────────────
// Captain serves files through admin route (read-only)
// Add route to captain blueprint if needed

function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
