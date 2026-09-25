// TRACE — Constable Dashboard JavaScript

let currentDocketId = null;
let currentDocketNumber = null;
let aiCheckPassed = false;
let aiCheckData = null;

// ── On load ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadProfile();
  loadCases();
});

// ── Tab: My Cases ─────────────────────────────────────────────────────────────
function loadCases(query = '') {
  const wrap = document.getElementById('casesTable');
  wrap.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading your dockets...</p></div>';
  fetch(`/constable/api/cases?q=${encodeURIComponent(query)}`)
    .then(r => r.json())
    .then(cases => {
      if (!cases || cases.length === 0) {
        wrap.innerHTML = '<div class="loading-state"><p>No dockets found.</p></div>';
        return;
      }
      let html = `<table class="cases-table">
        <thead><tr>
          <th>Case Number</th><th>Case Type</th><th>Status</th><th>Date Reported</th>
        </tr></thead><tbody>`;
      cases.forEach(c => {
        html += `<tr onclick="requestViewDocket(${c.id}, '${escHtml(c.case_number)}')">
          <td>${escHtml(c.case_number)}</td>
          <td>${escHtml(c.case_type)}</td>
          <td>${statusChip(c.status)}</td>
          <td>${formatDateOnly(c.date_reported)}</td>
        </tr>`;
      });
      html += '</tbody></table>';
      wrap.innerHTML = html;
    })
    .catch(() => {
      wrap.innerHTML = '<div class="loading-state"><p>Failed to load dockets.</p></div>';
    });
}

function searchCases() {
  const q = document.getElementById('caseSearch').value;
  loadCases(q);
}

// ── Confirm view flow ─────────────────────────────────────────────────────────
function requestViewDocket(id, caseNum) {
  currentDocketId = id;
  currentDocketNumber = caseNum;
  document.getElementById('confirmDocketNumber').textContent = caseNum;
  openModal('confirmModal');
}

function confirmViewDocket() {
  closeModal('confirmModal');
  fetch(`/constable/api/confirm-view/${currentDocketId}`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        openDocketModal(currentDocketId);
      } else {
        showToast(data.message || 'Could not log view.', 'error');
      }
    });
}

// ── Docket modal ──────────────────────────────────────────────────────────────
function openDocketModal(id) {
  openModal('docketModal');
  document.getElementById('docketModalBody').innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';

  fetch(`/constable/api/docket/${id}`)
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

      let docList = '';
      const typeLabels = {
        affidavit: 'Affidavit',
        witness_statement: 'Witness Statements',
        investigation_diary: 'Investigation Diary',
        suspect_info: 'Suspect Information & Supporting Documents',
        evidence: 'Evidence'
      };
      Object.keys(typeLabels).forEach(type => {
        const items = byType[type] || [];
        items.forEach(doc => {
          const normalizedPath = doc.file_path.replace(/\\/g, '/');
          const fileUrl = `/constable/file/${encodeURIComponent(normalizedPath)}`;
          docList += `<li class="doc-item">
            <span class="doc-type">${typeLabels[type]}</span>
            <span><a href="${fileUrl}" target="_blank" rel="noopener">${escHtml(doc.file_name)}</a></span>
            <span class="doc-ver">v${doc.version} — ${formatDate(doc.uploaded_at)}</span>
          </li>`;
        });
      });

      document.getElementById('docketModalBody').innerHTML = `
        <div class="docket-view-section">
          <h4>Case Information</h4>
          <div class="detail-row">
            <div class="detail-col"><label>Complainant</label><input type="text" value="${escHtml(d.complainant_full_name)}" data-field="complainant_full_name"></div>
            <div class="detail-col"><label>Complainant ID</label><input type="text" value="${escHtml(d.complainant_id_number)}" data-field="complainant_id_number"></div>
          </div>
          <div class="detail-row">
            <div class="detail-col"><label>Case Type</label><input type="text" value="${escHtml(d.case_type)}" data-field="case_type"></div>
            <div class="detail-col"><label>Date Reported</label><input type="date" value="${d.date_reported ? d.date_reported.split('T')[0] : ''}" data-field="date_reported"></div>
          </div>
          <div class="detail-row">
            <div class="detail-col"><label>Reporting Station</label><input type="text" value="${escHtml(d.reporting_station)}" data-field="reporting_station"></div>
            <div class="detail-col"><label>Status</label>
              <select data-field="status">
                ${buildStatusOptions(d.status)}
              </select>
            </div>
          </div>
        </div>

        <div class="docket-view-section">
          <h4>Upload Additional Documents (New Versions)</h4>
          <div class="upload-grid" style="grid-template-columns:1fr 1fr;">
            <div class="upload-block"><label class="upload-label"><span>Affidavit</span><small>PDF</small><input type="file" name="affidavit" accept=".pdf" onchange="updateFileLabel(this)"></label><span class="file-chosen">No file chosen</span></div>
            <div class="upload-block"><label class="upload-label"><span>Witness Statements</span><small>PDF</small><input type="file" name="witness_statement" accept=".pdf" onchange="updateFileLabel(this)"></label><span class="file-chosen">No file chosen</span></div>
            <div class="upload-block"><label class="upload-label"><span>Investigation Diary</span><small>PDF</small><input type="file" name="investigation_diary" accept=".pdf" onchange="updateFileLabel(this)"></label><span class="file-chosen">No file chosen</span></div>
            <div class="upload-block"><label class="upload-label"><span>Suspect Info</span><small>PDF</small><input type="file" name="suspect_info" accept=".pdf" onchange="updateFileLabel(this)"></label><span class="file-chosen">No file chosen</span></div>
            <div class="upload-block" style="grid-column:1/-1;"><label class="upload-label"><span>Evidence</span><small>Images, PDF, Video, MP3</small><input type="file" name="evidence" multiple accept=".pdf,.jpg,.jpeg,.png,.gif,.mp4,.avi,.mov,.mkv,.mp3,.wav" onchange="updateFileLabel(this)"></label><span class="file-chosen">No files chosen</span></div>
          </div>
        </div>

        ${docList ? `<div class="docket-view-section"><h4>Existing Documents</h4><ul class="doc-list">${docList}</ul></div>` : ''}
      `;
    })
    .catch(() => {
      document.getElementById('docketModalBody').innerHTML = '<div class="loading-state"><p>Failed to load docket.</p></div>';
    });
}

function buildStatusOptions(current) {
  const opts = [
    'Case Reported', 'Investigator Assigned', 'Investigation in Progress',
    'Court Proceedings', 'Escalated to Captain', 'Investigation Completed'
  ];
  return opts.map(s => `<option value="${s}" ${s === current ? 'selected' : ''}>${s}</option>`).join('');
}

function saveDocketChanges() {
  const body = document.getElementById('docketModalBody');
  const fd = new FormData();

  body.querySelectorAll('[data-field]').forEach(el => {
    fd.append(el.dataset.field, el.value);
  });
  body.querySelectorAll('input[type="file"]').forEach(inp => {
    if (inp.files && inp.files.length > 0) {
      if (inp.multiple) {
        Array.from(inp.files).forEach(f => fd.append(inp.name, f));
      } else {
        fd.append(inp.name, inp.files[0]);
      }
    }
  });

  fetch(`/constable/api/docket/${currentDocketId}/save`, { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        closeModal('docketModal');
        showToast(data.message, 'success');
        loadCases();
      } else {
        showToast(data.message || 'Save failed.', 'error');
      }
    })
    .catch(() => showToast('Network error.', 'error'));
}

// ── AI Check ──────────────────────────────────────────────────────────────────
function openAICheck() {
  const form = document.getElementById('addDocketForm');
  const affidavitInput = form.querySelector('input[name="affidavit"]');

  if (!affidavitInput || !affidavitInput.files || affidavitInput.files.length === 0) {
    showToast('Please upload an affidavit PDF before running the AI Check.', 'error');
    return;
  }

  openModal('aiModal');
  const modalBody = document.getElementById('aiModalBody');
  const modalFooter = document.getElementById('aiModalFooter');
  modalBody.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Analysing affidavit...</p></div>';
  modalFooter.innerHTML = '';

  const fd = new FormData();
  fd.append('affidavit', affidavitInput.files[0]);

  fetch('/constable/api/ai-check', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      aiCheckData = data;
      aiCheckPassed = data.ai_valid;

      const wordChip = data.word_check === 'Accepted'
        ? '<span class="ai-status ai-accepted">Word Count Accepted</span>'
        : '<span class="ai-status ai-rejected">Word Count Rejected</span>';
      const aiChip = data.ai_valid
        ? '<span class="ai-status ai-accepted">AI Check: Valid</span>'
        : '<span class="ai-status ai-rejected">AI Check: Invalid</span>';

      modalBody.innerHTML = `
        <div class="ai-result">
          <div class="ai-wordcount">${data.word_count}</div>
          <div class="ai-label">Words in Affidavit</div>
          ${wordChip}
          ${data.word_check === 'Accepted' ? aiChip : ''}
          ${data.ai_reason ? `<div class="ai-reason" style="margin-top:1rem;">${escHtml(data.ai_reason)}</div>` : ''}
        </div>
      `;

      if (data.ai_valid && data.word_check === 'Accepted') {
        modalFooter.innerHTML = `<button class="btn btn-primary" onclick="saveDocketFromAI()">Save Docket</button>`;
      } else {
        modalFooter.innerHTML = `
          <button class="btn btn-outline" onclick="backToDocket()">Back to Docket for Review</button>
          <button class="btn btn-danger" onclick="openForceSave()">Force Save</button>
        `;
      }
    })
    .catch(err => {
      modalBody.innerHTML = `<div class="alert alert-error">AI check failed: ${err.message}</div>`;
      modalFooter.innerHTML = `<button class="btn btn-outline" onclick="closeModal('aiModal')">Close</button>`;
    });
}

function saveDocketFromAI() {
  closeModal('aiModal');
  submitDocket(false, '');
}

function backToDocket() {
  closeModal('aiModal');
  closeModal('forceSaveModal');
}

function openForceSave() {
  closeModal('aiModal');
  document.getElementById('forcePinInput').value = '';
  document.getElementById('forcePinError').style.display = 'none';
  openModal('forceSaveModal');
}

function submitForceSave() {
  const pin = document.getElementById('forcePinInput').value;
  if (!pin) {
    document.getElementById('forcePinError').textContent = 'Please enter the Force Save PIN.';
    document.getElementById('forcePinError').style.display = 'block';
    return;
  }
  closeModal('forceSaveModal');
  submitDocket(true, pin);
}

function submitDocket(forceMode, forcePin) {
  const form = document.getElementById('addDocketForm');
  const fd = new FormData(form);
  if (forceMode) {
    fd.append('force_save', 'true');
    fd.append('force_pin', forcePin);
  }

  fetch('/constable/api/add-docket', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        showToast(data.message, 'success');
        form.reset();
        document.querySelectorAll('.file-chosen').forEach(el => el.textContent = 'No file chosen');
        showTab('my-cases', document.querySelector('[data-tab="my-cases"]'));
        loadCases();
      } else {
        showToast(data.message || 'Failed to save docket.', 'error');
        if (data.message && data.message.includes('PIN')) {
          openForceSave();
          document.getElementById('forcePinError').textContent = data.message;
          document.getElementById('forcePinError').style.display = 'block';
        }
      }
    })
    .catch(() => showToast('Network error saving docket.', 'error'));
}

// ── Profile ───────────────────────────────────────────────────────────────────
function loadProfile() {
  fetch('/constable/api/profile')
    .then(r => r.json())
    .then(d => {
      if (d.error) return;
      setField('pf_name', d.full_name);
      setField('pf_email', d.email);
      setField('pf_oid', d.officer_id);
      setField('pf_rank', d.rank_name);
      if (d.profile_picture) {
        const av = document.getElementById('profileAvatar');
        const sav = document.getElementById('sidebarAvatar');
        if (av) av.innerHTML = `<img src="/constable/file/${d.profile_picture}" alt="Profile">`;
        if (sav) sav.innerHTML = `<img src="/constable/file/${d.profile_picture}" alt="Profile" style="width:44px;height:44px;border-radius:50%;object-fit:cover;">`;
      }
    });
}

function setField(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val || '';
}

function saveProfile() {
  const fd = new FormData(document.getElementById('profileForm'));
  fetch('/constable/api/profile/update', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      const msg = document.getElementById('profileMsg');
      msg.className = 'alert ' + (data.success ? 'alert-success' : 'alert-error');
      msg.textContent = data.message;
      msg.style.display = 'block';
      if (data.success) showToast(data.message, 'success');
    });
}

function changePassword() {
  const fd = new FormData();
  fd.append('current_password', document.getElementById('curPw').value);
  fd.append('new_password', document.getElementById('newPw').value);
  fd.append('confirm_password', document.getElementById('confPw').value);

  fetch('/constable/api/profile/password', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      const msg = document.getElementById('pwMsg');
      msg.className = 'alert ' + (data.success ? 'alert-success' : 'alert-error');
      msg.textContent = data.message;
      msg.style.display = 'block';
      if (data.success) {
        document.getElementById('curPw').value = '';
        document.getElementById('newPw').value = '';
        document.getElementById('confPw').value = '';
      }
    });
}

function uploadProfilePicture(input) {
  if (!input.files || !input.files[0]) return;
  const fd = new FormData();
  fd.append('profile_picture', input.files[0]);
  fetch('/constable/api/profile/picture', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        const av = document.getElementById('profileAvatar');
        const sav = document.getElementById('sidebarAvatar');
        if (av) av.innerHTML = `<img src="/constable/file/${data.path}" alt="Profile">`;
        if (sav) sav.innerHTML = `<img src="/constable/file/${data.path}" alt="P" style="width:44px;height:44px;border-radius:50%;object-fit:cover;">`;
        showToast('Profile picture updated.', 'success');
      } else {
        showToast(data.message, 'error');
      }
    });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
