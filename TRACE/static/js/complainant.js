// TRACE — Complainant Portal JavaScript

let currentCase = null;
let caseIdNum = null;
let caseName = null;
let caseNum = null;

// ── Case search ────────────────────────────────────────────────────────────────
function searchCase() {
  const name = document.getElementById('c_name').value.trim();
  const id = document.getElementById('c_id').value.trim();
  const caseNumber = document.getElementById('c_case').value.trim();
  const errDiv = document.getElementById('searchError');
  errDiv.style.display = 'none';

  if (!name || !id || !caseNumber) {
    errDiv.textContent = 'All fields are required.';
    errDiv.style.display = 'block';
    return;
  }

  const fd = new FormData();
  fd.append('full_name', name);
  fd.append('id_number', id);
  fd.append('case_number', caseNumber);

  fetch('/complainant/check-case', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (!data.success) {
        errDiv.textContent = data.message;
        errDiv.style.display = 'block';
        return;
      }
      currentCase = data;
      caseName = name;
      caseIdNum = id;
      caseNum = caseNumber;
      showResults(data);
    })
    .catch(() => {
      errDiv.textContent = 'An error occurred. Please try again.';
      errDiv.style.display = 'block';
    });
}

function showResults(data) {
  document.getElementById('searchPanel').style.display = 'none';
  document.getElementById('resultsPanel').style.display = 'block';

  document.getElementById('r_case_number').textContent = data.case_number;
  document.getElementById('r_date_reported').textContent = formatDateOnly(data.date_reported);
  document.getElementById('r_case_type').textContent = data.case_type;
  document.getElementById('r_station').textContent = data.reporting_station;
  document.getElementById('r_officer').textContent = data.investigating_officer;

  // Status with coloured chip
  const statusEl = document.getElementById('r_status');
  statusEl.innerHTML = statusChip(data.status);

  // Affidavit button
  const affBtn = document.getElementById('affidavitBtn');
  if (!data.has_affidavit) {
    affBtn.disabled = true;
    affBtn.title = 'No affidavit on file for this case.';
    affBtn.style.opacity = '0.45';
  }

  // Appeal section
  if (data.status === 'Case Closed') {
    document.getElementById('appealSection').style.display = 'block';
    document.getElementById('appealDisabled').style.display = 'none';

    if (data.appeal_submitted) {
      document.getElementById('appealForm').style.display = 'none';
      document.getElementById('appealSubmitted').style.display = 'block';
      document.getElementById('appealStatusSection').style.display = 'block';
      document.getElementById('r_appeal_status').textContent = data.appeal_status || 'Pending';
    }
  } else {
    document.getElementById('appealSection').style.display = 'none';
    document.getElementById('appealDisabled').style.display = 'block';
  }
}

function resetSearch() {
  document.getElementById('resultsPanel').style.display = 'none';
  document.getElementById('searchPanel').style.display = 'block';
  document.getElementById('c_name').value = '';
  document.getElementById('c_id').value = '';
  document.getElementById('c_case').value = '';
  document.getElementById('searchError').style.display = 'none';
  currentCase = null;
}

// ── View affidavit ─────────────────────────────────────────────────────────────
function viewAffidavit() {
  if (!currentCase) return;
  const fd = new FormData();
  fd.append('case_number', currentCase.case_number);
  fd.append('id_number', caseIdNum);
  fd.append('full_name', caseName);

  fetch('/complainant/view-affidavit', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        const normalizedPath = data.file_path.replace(/\\/g, '/');
        const fileUrl = `/complainant/file/${encodeURIComponent(normalizedPath)}`;
        window.open(fileUrl, '_blank');
        showToast('Affidavit opened in a new tab.', 'success');
      } else {
        showToast(data.message, 'error');
      }
    });
}

// ── Appeal ─────────────────────────────────────────────────────────────────────
const appealReasonTa = document.getElementById('appealReason');
if (appealReasonTa) {
  appealReasonTa.addEventListener('input', () => {
    const wc = appealReasonTa.value.trim().split(/\s+/).filter(Boolean).length;
    document.getElementById('wordCount').textContent = `${wc} / 100 words`;
    document.getElementById('wordCount').style.color = wc > 100 ? 'var(--danger)' : 'var(--grey-500)';
  });
}

function submitAppeal() {
  const reason = document.getElementById('appealReason').value.trim();
  const errDiv = document.getElementById('appealError');
  errDiv.style.display = 'none';

  if (!reason) {
    errDiv.textContent = 'Please provide a reason for your appeal.';
    errDiv.style.display = 'block';
    return;
  }
  const wc = reason.split(/\s+/).filter(Boolean).length;
  if (wc > 100) {
    errDiv.textContent = `Reason must be 100 words or fewer (currently ${wc} words).`;
    errDiv.style.display = 'block';
    return;
  }

  const fd = new FormData();
  fd.append('full_name', caseName);
  fd.append('id_number', caseIdNum);
  fd.append('case_number', caseNum);
  fd.append('reason', reason);

  fetch('/complainant/submit-appeal', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        document.getElementById('appealForm').style.display = 'none';
        document.getElementById('appealSubmitted').style.display = 'block';
        showToast(data.message, 'success');
      } else {
        errDiv.textContent = data.message;
        errDiv.style.display = 'block';
      }
    })
    .catch(() => {
      errDiv.textContent = 'An error occurred. Please try again.';
      errDiv.style.display = 'block';
    });
}

// ── Enter key support ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  ['c_name','c_id','c_case'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') searchCase(); });
  });
});
