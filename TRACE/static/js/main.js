// TRACE — Shared Utilities

function togglePw(inputId, btn) {
  const inp = document.getElementById(inputId);
  if (!inp) return;
  if (inp.type === 'password') {
    inp.type = 'text';
    btn.textContent = 'Hide';
  } else {
    inp.type = 'password';
    btn.textContent = 'Show';
  }
}

function showTab(tabName, clickedEl) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const tab = document.getElementById('tab-' + tabName);
  if (tab) tab.classList.add('active');
  if (clickedEl) clickedEl.classList.add('active');
  return false;
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'flex';
}

function showToast(msg, type) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.className = 'toast toast-' + (type || 'info');
  toast.style.display = 'block';
  setTimeout(() => { toast.style.display = 'none'; }, 4000);
}

function updateFileLabel(input) {
  // Input is inside the label, so find the .file-chosen span that is a sibling of the label
  const block = input.closest('.upload-block');
  const span = block ? block.querySelector('.file-chosen') : null;
  if (!span) return;
  if (input.files && input.files.length > 0) {
    if (input.multiple) {
      span.textContent = Array.from(input.files).map(f => f.name).join(', ');
    } else {
      span.textContent = input.files[0].name;
    }
  } else {
    span.textContent = input.multiple ? 'No files chosen' : 'No file chosen';
  }
}

function statusChip(status) {
  const map = {
    'Case Reported': 'chip-blue',
    'Investigator Assigned': 'chip-blue',
    'Investigation in Progress': 'chip-yellow',
    'Court Proceedings': 'chip-yellow',
    'Escalated to Captain': 'chip-yellow',
    'Investigation Completed': 'chip-blue',
    'Case Closed': 'chip-green',
  };
  const cls = map[status] || 'chip-dark';
  return `<span class="chip ${cls}">${status}</span>`;
}

function formatDate(dt) {
  if (!dt) return '—';
  const d = new Date(dt);
  return d.toLocaleDateString('en-ZA') + ' ' + d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' });
}

function formatDateOnly(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString('en-ZA');
}

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(f => {
      f.style.opacity = '0';
      f.style.transition = 'opacity .5s';
      setTimeout(() => f.remove(), 500);
    });
  }, 5000);
});
