// TRACE — Admin Dashboard JavaScript

let adminChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
  loadAdminStats();
  loadNotifications();
});

const origShowTab = window.showTab;
window.showTab = function(tabName, el) {
  origShowTab(tabName, el);
  if (tabName === 'access-history') loadAccessHistory();
  if (tabName === 'closed-cases') loadClosedCases();
  if (tabName === 'flagged-cases') loadFlaggedCases();
  if (tabName === 'appeals') loadAppeals();
  if (tabName === 'signup-requests') loadSignupRequests();
  if (tabName === 'forgot-pw') loadForgotPwRequests();
  if (tabName === 'profile') loadAdminProfile();
  if (tabName === 'dashboard') { loadAdminStats(); loadNotifications(); }
  return false;
};

// ── Stats ─────────────────────────────────────────────────────────────────────
function loadAdminStats() {
  fetch('/admin/api/stats')
    .then(r => r.json())
    .then(d => {
      setText('statClosed', d.closed);
      setText('statFlagged', d.flagged);
      setText('statAppeals', d.appeals);
      setText('statSignups', d.signups);

      const signupBadge = document.getElementById('signupBadge');
      if (signupBadge) {
        if (d.signups > 0) { signupBadge.textContent = d.signups; signupBadge.style.display = 'inline-block'; }
        else signupBadge.style.display = 'none';
      }
    });
}

// ── Notifications ─────────────────────────────────────────────────────────────
function loadNotifications() {
  fetch('/admin/api/notifications')
    .then(r => r.json())
    .then(notifs => {
      const list = document.getElementById('notificationsList');
      if (!notifs || !notifs.length) {
        list.innerHTML = '<p class="text-muted">No notifications.</p>';
        return;
      }
      let html = '<div class="notif-list">';
      notifs.forEach(n => {
        html += `<div class="notif-item ${n.is_read ? '' : 'unread'}">
          <div>
            <div class="notif-msg">${escHtml(n.message)}</div>
            <div class="notif-time">${formatDate(n.created_at)}</div>
          </div>
        </div>`;
      });
      html += '</div>';
      list.innerHTML = html;
    });
}

function setText(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

// ── Access History ────────────────────────────────────────────────────────────
function loadAccessHistory() {
  const q = (document.getElementById('historySearch') || {}).value || '';
  const date = (document.getElementById('historyDate') || {}).value || '';
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (date) params.set('date', date);

  const wrap = document.getElementById('accessHistoryTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch(`/admin/api/access-history?${params}`)
    .then(r => r.json())
    .then(logs => {
      if (!logs.length) { wrap.innerHTML = '<div class="loading-state"><p>No records found.</p></div>'; return; }
      let html = `<table class="cases-table"><thead><tr>
        <th>Officer</th><th>Role</th><th>Action</th><th>Case Number</th><th>Status</th><th>Date &amp; Time</th>
      </tr></thead><tbody>`;
      logs.forEach(l => {
        html += `<tr>
          <td>${escHtml(l.officer_name)}</td>
          <td><span class="chip chip-blue">${escHtml(l.officer_role)}</span></td>
          <td>${escHtml(l.action)}</td>
          <td>${escHtml(l.case_number) || '—'}</td>
          <td>${l.case_status ? statusChip(l.case_status) : '—'}</td>
          <td>${formatDate(l.action_at)}</td>
        </tr>`;
      });
      html += '</tbody></table>';
      wrap.innerHTML = html;
    })
    .catch(() => { wrap.innerHTML = '<div class="loading-state"><p>Failed to load.</p></div>'; });
}

function clearHistorySearch() {
  const sq = document.getElementById('historySearch');
  const sd = document.getElementById('historyDate');
  if (sq) sq.value = '';
  if (sd) sd.value = '';
  loadAccessHistory();
}

// ── Closed Cases ──────────────────────────────────────────────────────────────
function loadClosedCases() {
  const wrap = document.getElementById('closedCasesTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch('/admin/api/closed-cases')
    .then(r => r.json())
    .then(cases => {
      if (!cases.length) { wrap.innerHTML = '<div class="loading-state"><p>No closed cases.</p></div>'; return; }
      let html = `<table class="cases-table"><thead><tr>
        <th>Case Number</th><th>Case Type</th><th>Complainant</th><th>Closed By</th><th>Closed At</th><th>Actions</th>
      </tr></thead><tbody>`;
      cases.forEach(c => {
        html += `<tr>
          <td>${escHtml(c.case_number)}</td>
          <td>${escHtml(c.case_type)}</td>
          <td>${escHtml(c.complainant_full_name)}</td>
          <td>${escHtml(c.closed_by_name) || '—'}</td>
          <td>${formatDate(c.closed_at)}</td>
          <td><button class="btn btn-sm btn-outline" onclick="viewAdminDocket(${c.id})">View</button></td>
        </tr>`;
      });
      html += '</tbody></table>';
      wrap.innerHTML = html;
    });
}

// ── Flagged Cases ─────────────────────────────────────────────────────────────
function loadFlaggedCases() {
  const wrap = document.getElementById('flaggedCasesTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch('/admin/api/flagged-cases')
    .then(r => r.json())
    .then(cases => {
      if (!cases.length) { wrap.innerHTML = '<div class="loading-state"><p>No flagged cases.</p></div>'; return; }
      let html = `<table class="cases-table"><thead><tr>
        <th>Case Number</th><th>Flagged By</th><th>Flagged At</th><th>Reason</th><th>Actions</th>
      </tr></thead><tbody>`;
      cases.forEach(c => {
        html += `<tr>
          <td>${escHtml(c.case_number)}</td>
          <td>${escHtml(c.flagged_by_name)}</td>
          <td>${formatDate(c.flagged_at)}</td>
          <td>${escHtml(c.reason.substring(0,80))}${c.reason.length > 80 ? '...' : ''}</td>
          <td><button class="btn btn-sm btn-outline" onclick="viewAdminDocket(${c.docket_id})">View</button></td>
        </tr>`;
      });
      html += '</tbody></table>';
      wrap.innerHTML = html;
    });
}

// ── Appeals ───────────────────────────────────────────────────────────────────
function loadAppeals() {
  const wrap = document.getElementById('appealsTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch('/admin/api/appeals')
    .then(r => r.json())
    .then(appeals => {
      if (!appeals.length) { wrap.innerHTML = '<div class="loading-state"><p>No appeals.</p></div>'; return; }
      let html = '';
      appeals.forEach(a => {
        html += `<div class="request-card appeal-card">
          <div class="request-header">
            <div>
              <div class="request-name">${escHtml(a.complainant_full_name)}</div>
              <div class="request-sub">Case: ${escHtml(a.case_number)} &nbsp;|&nbsp; ID: ${escHtml(a.complainant_id_number)}</div>
            </div>
            <div>
              <span class="chip ${a.appeal_status === 'Pending' ? 'chip-yellow' : a.appeal_status === 'Review Case' ? 'chip-blue' : 'chip-green'}">${escHtml(a.appeal_status)}</span>
            </div>
          </div>
          <div style="margin-bottom:1rem;">
            <strong>Reason:</strong> ${escHtml(a.reason)}
          </div>
          <div class="request-sub" style="margin-bottom:.75rem;">Submitted: ${formatDate(a.submitted_at)}</div>
          <div class="request-actions">
            <button class="btn btn-sm btn-outline" onclick="updateAppealStatus(${a.id},'Review Case')">Mark as Review Case</button>
            <button class="btn btn-sm btn-primary" onclick="updateAppealStatus(${a.id},'Case Closed')">Mark as Case Closed</button>
          </div>
        </div>`;
      });
      wrap.innerHTML = html;
    });
}

function updateAppealStatus(id, status) {
  const fd = new FormData();
  fd.append('status', status);
  fetch(`/admin/api/appeals/${id}/status`, { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) { showToast(data.message, 'success'); loadAppeals(); loadAdminStats(); }
      else showToast(data.message || 'Failed.', 'error');
    });
}

// ── Signup Requests ───────────────────────────────────────────────────────────
function loadSignupRequests() {
  const wrap = document.getElementById('signupRequestsTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch('/admin/api/signup-requests')
    .then(r => r.json())
    .then(reqs => {
      if (!reqs.length) { wrap.innerHTML = '<div class="loading-state"><p>No pending signup requests.</p></div>'; return; }
      let html = '';
      reqs.forEach(r => {
        if (r.type === 'password_reset') {
          html += `<div class="request-card">
            <div class="request-header">
              <div>
                <div class="request-name">${escHtml(r.full_name)} <span class="chip chip-yellow">Password Reset</span></div>
                <div class="request-sub">Officer ID: ${escHtml(r.officer_id)} &nbsp;|&nbsp; Role: ${escHtml(r.role_name)} &nbsp;|&nbsp; Email: ${escHtml(r.email)}</div>
              </div>
              <div class="request-sub">Requested: ${formatDate(r.requested_at)}</div>
            </div>
            <div class="request-actions">
              <button class="btn btn-sm btn-primary btn-ai" onclick="generateOTP(${r.id}, this)">Generate &amp; Email OTP Pin</button>
            </div>
            <div id="otpResult_${r.id}" class="alert" style="display:none;margin-top:.75rem;"></div>
          </div>`;
          return;
        }

        const isCaptain = r.role_name === 'captain';
        html += `<div class="request-card ${isCaptain ? 'captain-card' : ''}">
          <div class="request-header">
            <div>
              <div class="request-name">${escHtml(r.full_name)} <span class="chip chip-${isCaptain ? 'dark' : 'blue'}">${escHtml(r.role_name)}</span></div>
              <div class="request-sub">Officer ID: ${escHtml(r.officer_id)} &nbsp;|&nbsp; Submitted: ${formatDate(r.requested_at)}</div>
            </div>
          </div>
          <div class="request-details">
            <div class="request-field"><span>Rank</span>${escHtml(r.rank_name)}</div>
            <div class="request-field"><span>Department</span>${escHtml(r.department)}</div>
            <div class="request-field"><span>SA ID</span>${escHtml(r.sa_id_number)}</div>
            <div class="request-field"><span>Date of Birth</span>${formatDateOnly(r.date_of_birth)}</div>
            <div class="request-field"><span>Email</span>${escHtml(r.email)}</div>
          </div>
          <div class="request-actions">
            <button class="btn btn-sm btn-danger" onclick="processSignup(${r.id},'disapprove')">Disapprove</button>
            <button class="btn btn-sm btn-primary" onclick="processSignup(${r.id},'approve')" style="background:var(--success);border-color:var(--success);">Approve</button>
          </div>
        </div>`;
      });
      wrap.innerHTML = html;
    });
}

function processSignup(id, action) {
  fetch(`/admin/api/signup-requests/${id}/${action}`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) { showToast(data.message, 'success'); loadSignupRequests(); loadAdminStats(); }
      else showToast(data.message || 'Failed.', 'error');
    });
}

// ── Forgot Password Requests ──────────────────────────────────────────────────
function loadForgotPwRequests() {
  const wrap = document.getElementById('forgotPwTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch('/admin/api/forgot-password-requests')
    .then(r => r.json())
    .then(reqs => {
      if (!reqs.length) { wrap.innerHTML = '<div class="loading-state"><p>No pending password reset requests.</p></div>'; return; }
      let html = '';
      reqs.forEach(r => {
        html += `<div class="request-card">
          <div class="request-header">
            <div>
              <div class="request-name">${escHtml(r.full_name)} <span class="chip chip-blue">${escHtml(r.role_name)}</span></div>
              <div class="request-sub">Officer ID: ${escHtml(r.officer_id)} &nbsp;|&nbsp; Email: ${escHtml(r.email)}</div>
            </div>
            <div class="request-sub">Requested: ${formatDate(r.requested_at)}</div>
          </div>
          <div class="request-actions">
            <button class="btn btn-sm btn-primary btn-ai" onclick="generateOTP(${r.id}, this)">Generate &amp; Email OTP Pin</button>
          </div>
          <div id="otpResult_${r.id}" class="alert" style="display:none;margin-top:.75rem;"></div>
        </div>`;
      });
      wrap.innerHTML = html;
    });
}

function generateOTP(reqId, btn) {
  btn.disabled = true;
  btn.textContent = 'Sending...';
  fetch(`/admin/api/forgot-password-requests/${reqId}/generate-otp`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      const resultEl = document.getElementById(`otpResult_${reqId}`);
      resultEl.className = 'alert ' + (data.success ? 'alert-success' : 'alert-error');
      resultEl.textContent = data.message;
      resultEl.style.display = 'block';
      btn.textContent = 'OTP Sent';
      if (data.success) {
        showToast('OTP generated and sent.', 'success');
        loadForgotPwRequests();
      }
    })
    .catch(() => {
      btn.disabled = false;
      btn.textContent = 'Generate & Email OTP Pin';
      showToast('Failed to generate OTP.', 'error');
    });
}

// ── Admin Docket View ─────────────────────────────────────────────────────────
function viewAdminDocket(id) {
  openModal('docketModal');
  document.getElementById('docketModalBody').innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  fetch(`/admin/api/docket/${id}`)
    .then(r => r.json())
    .then(d => {
      document.getElementById('modalCaseNum').textContent = d.case_number;

      const docs = d.documents || [];
      const typeLabels = { affidavit: 'Affidavit', witness_statement: 'Witness Statements', investigation_diary: 'Investigation Diary', suspect_info: 'Suspect Info', evidence: 'Evidence' };
      const byType = {};
      docs.forEach(doc => {
        if (!byType[doc.document_type]) byType[doc.document_type] = [];
        byType[doc.document_type].push(doc);
      });
      let docList = Object.keys(typeLabels).flatMap(type =>
        (byType[type] || []).map(doc => {
          const normalizedPath = doc.file_path.replace(/\\/g, '/');
          const fileUrl = `/admin/file/${encodeURIComponent(normalizedPath)}`;
          return `<li class="doc-item"><span class="doc-type">${typeLabels[type]}</span><span><a href="${fileUrl}" target="_blank" rel="noopener">${escHtml(doc.file_name)}</a></span><span class="doc-ver">v${doc.version}</span></li>`;
        })
      ).join('');

      document.getElementById('docketModalBody').innerHTML = `
        <div class="docket-view-section">
          <h4>Case Details</h4>
          <div class="detail-row">
            <div class="detail-col"><label>Complainant</label><input type="text" value="${escHtml(d.complainant_full_name)}" readonly style="background:#f5f6fa;"></div>
            <div class="detail-col"><label>Complainant ID</label><input type="text" value="${escHtml(d.complainant_id_number)}" readonly style="background:#f5f6fa;"></div>
          </div>
          <div class="detail-row">
            <div class="detail-col"><label>Case Type</label><input type="text" value="${escHtml(d.case_type)}" readonly style="background:#f5f6fa;"></div>
            <div class="detail-col"><label>Reporting Station</label><input type="text" value="${escHtml(d.reporting_station)}" readonly style="background:#f5f6fa;"></div>
          </div>
          <div class="detail-row">
            <div class="detail-col"><label>Investigating Officer</label><input type="text" value="${escHtml(d.investigating_officer)}" readonly style="background:#f5f6fa;"></div>
            <div class="detail-col"><label>Current Status</label><input type="text" value="${escHtml(d.status)}" readonly style="background:#f5f6fa;"></div>
          </div>
          <div class="detail-row">
            <div class="detail-col"><label>Date Reported</label><input type="text" value="${formatDateOnly(d.date_reported)}" readonly style="background:#f5f6fa;"></div>
            <div class="detail-col"><label>Force Saved</label><input type="text" value="${d.force_saved ? 'Yes (AI override)' : 'No'}" readonly style="background:#f5f6fa;"></div>
          </div>
        </div>
        ${docList ? `<div class="docket-view-section"><h4>Documents</h4><ul class="doc-list">${docList}</ul></div>` : ''}
      `;
    });
}

// ── Admin Profile ─────────────────────────────────────────────────────────────
function loadAdminProfile() {
  fetch('/admin/api/profile')
    .then(r => r.json())
    .then(d => {
      setVal('pf_name', d.full_name);
      setVal('pf_email', d.email);
      if (d.profile_picture) {
        const av = document.getElementById('profileAvatar');
        if (av) av.innerHTML = `<img src="/admin/file/${d.profile_picture}" alt="Profile">`;
      }
    });
}

function setVal(id, v) { const el = document.getElementById(id); if (el) el.value = v || ''; }

function saveAdminProfile() {
  const fd = new FormData();
  fd.append('full_name', document.getElementById('pf_name').value);
  fd.append('email', document.getElementById('pf_email').value);
  fetch('/admin/api/profile/update', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      const msg = document.getElementById('profileMsg');
      msg.className = 'alert ' + (data.success ? 'alert-success' : 'alert-error');
      msg.textContent = data.message;
      msg.style.display = 'block';
    });
}

function changeAdminPassword() {
  const fd = new FormData();
  fd.append('current_password', document.getElementById('curPw').value);
  fd.append('new_password', document.getElementById('newPw').value);
  fd.append('confirm_password', document.getElementById('confPw').value);
  fetch('/admin/api/profile/password', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      const msg = document.getElementById('pwMsg');
      msg.className = 'alert ' + (data.success ? 'alert-success' : 'alert-error');
      msg.textContent = data.message;
      msg.style.display = 'block';
    });
}

function uploadAdminProfilePicture(input) {
  if (!input.files || !input.files[0]) return;
  const fd = new FormData();
  fd.append('profile_picture', input.files[0]);
  fetch('/admin/api/profile/picture', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        const av = document.getElementById('profileAvatar');
        if (av) av.innerHTML = `<img src="/admin/file/${data.path}" alt="Profile">`;
        showToast('Profile picture updated.', 'success');
      } else showToast(data.message, 'error');
    });
}

function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
