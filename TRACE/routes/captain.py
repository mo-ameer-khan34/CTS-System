import os
import uuid
from functools import wraps

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify, current_app)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models.db import query_db, execute_db

captain_bp = Blueprint('captain', __name__)


def captain_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'captain':
            flash('Access denied.', 'error')
            return redirect(url_for('auth.captain_login'))
        return f(*args, **kwargs)
    return decorated


def _log_audit(officer_id, officer_name, role, action, docket_id=None, case_number=None, case_status=None, desc=None):
    execute_db(
        """INSERT INTO audit_logs
           (officer_id, officer_name, officer_role, action, docket_id, case_number, case_status, description)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (officer_id, officer_name, role, action, docket_id, case_number, case_status, desc)
    )


def _allowed_doc(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_DOC_EXTENSIONS']


def _allowed_evidence(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EVIDENCE_EXTENSIONS']


def _save_upload(file, subfolder, docket_id):
    upload_base = current_app.config['UPLOAD_FOLDER']
    dest = os.path.join(upload_base, str(docket_id), subfolder)
    os.makedirs(dest, exist_ok=True)
    ext = secure_filename(file.filename).rsplit('.', 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(dest, unique_name)
    file.save(filepath)
    rel_path = os.path.join(str(docket_id), subfolder, unique_name).replace('\\', '/')
    return rel_path, secure_filename(file.filename), os.path.getsize(filepath)


# ── Dashboard ─────────────────────────────────────────────────────────────────
@captain_bp.route('/dashboard')
@captain_required
def dashboard():
    officer = query_db("SELECT * FROM officers WHERE id=%s", (session['user_id'],), one=True)
    return render_template('captain/dashboard.html', officer=officer)


# ── API: Dashboard stats ───────────────────────────────────────────────────────
@captain_bp.route('/api/stats')
@captain_required
def api_stats():
    closed = query_db(
        "SELECT COUNT(*) AS cnt FROM dockets WHERE status='Case Closed' AND MONTH(closed_at)=MONTH(NOW()) AND YEAR(closed_at)=YEAR(NOW())",
        one=True
    )
    escalated = query_db(
        "SELECT COUNT(*) AS cnt FROM dockets WHERE status='Escalated to Captain' AND MONTH(updated_at)=MONTH(NOW()) AND YEAR(updated_at)=YEAR(NOW())",
        one=True
    )
    flagged = query_db(
        "SELECT COUNT(*) AS cnt FROM flagged_cases WHERE MONTH(flagged_at)=MONTH(NOW()) AND YEAR(flagged_at)=YEAR(NOW())",
        one=True
    )
    return jsonify({
        'closed': closed['cnt'] if closed else 0,
        'escalated': escalated['cnt'] if escalated else 0,
        'flagged': flagged['cnt'] if flagged else 0
    })


# ── API: Cases to be closed (status = Investigation Completed) ────────────────
@captain_bp.route('/api/cases-to-close')
@captain_required
def api_cases_to_close():
    cases = query_db(
        """SELECT d.*, o.full_name AS officer_name FROM dockets d
           JOIN officers o ON o.id=d.created_by
           WHERE d.status='Investigation Completed'
           ORDER BY d.updated_at DESC"""
    )
    result = []
    for c in (cases or []):
        row = dict(c)
        row['date_reported'] = str(row.get('date_reported', ''))
        row['created_at'] = str(row.get('created_at', ''))
        row['updated_at'] = str(row.get('updated_at', ''))
        result.append(row)
    return jsonify(result)


# ── API: Escalated cases ───────────────────────────────────────────────────────
@captain_bp.route('/api/escalated-cases')
@captain_required
def api_escalated_cases():
    cases = query_db(
        """SELECT d.*, o.full_name AS officer_name FROM dockets d
           JOIN officers o ON o.id=d.created_by
           WHERE d.status='Escalated to Captain'
           ORDER BY d.updated_at DESC"""
    )
    result = []
    for c in (cases or []):
        row = dict(c)
        row['date_reported'] = str(row.get('date_reported', ''))
        row['created_at'] = str(row.get('created_at', ''))
        row['updated_at'] = str(row.get('updated_at', ''))
        result.append(row)
    return jsonify(result)


# ── API: Flagged cases ────────────────────────────────────────────────────────
@captain_bp.route('/api/flagged-cases')
@captain_required
def api_flagged_cases():
    cases = query_db(
        """SELECT fc.*, d.case_number, d.case_type, d.status, d.complainant_full_name,
                  o.full_name AS flagged_by_name
           FROM flagged_cases fc
           JOIN dockets d ON d.id=fc.docket_id
           JOIN officers o ON o.id=fc.flagged_by
           WHERE fc.flagged_by=%s
           ORDER BY fc.flagged_at DESC""",
        (session['user_id'],)
    )
    result = []
    for c in (cases or []):
        row = dict(c)
        row['flagged_at'] = str(row.get('flagged_at', ''))
        result.append(row)
    return jsonify(result)


# ── API: View a docket (captain) ──────────────────────────────────────────────
@captain_bp.route('/api/docket/<int:docket_id>')
@captain_required
def api_docket(docket_id):
    docket = query_db("SELECT * FROM dockets WHERE id=%s", (docket_id,), one=True)
    if not docket:
        return jsonify({'error': 'Not found'}), 404

    docs = query_db(
        "SELECT * FROM docket_documents WHERE docket_id=%s ORDER BY document_type, version DESC",
        (docket_id,)
    )
    officer = query_db("SELECT full_name FROM officers WHERE id=%s", (docket['created_by'],), one=True)

    docket_dict = dict(docket)
    docket_dict['date_reported'] = str(docket_dict.get('date_reported', ''))
    docket_dict['created_at'] = str(docket_dict.get('created_at', ''))
    docket_dict['updated_at'] = str(docket_dict.get('updated_at', ''))
    docket_dict['documents'] = [dict(d) for d in docs] if docs else []
    docket_dict['investigating_officer'] = officer['full_name'] if officer else 'Unknown'
    return jsonify(docket_dict)


# ── API: Confirm view docket (captain) ────────────────────────────────────────
@captain_bp.route('/api/confirm-view/<int:docket_id>', methods=['POST'])
@captain_required
def confirm_view(docket_id):
    docket = query_db("SELECT * FROM dockets WHERE id=%s", (docket_id,), one=True)
    if not docket:
        return jsonify({'success': False, 'message': 'Not found'}), 404
    _log_audit(
        session['user_id'], session['full_name'], 'Captain',
        'Viewed Docket', docket_id, docket['case_number'], docket['status'],
        f"Captain {session['full_name']} viewed docket {docket['case_number']}."
    )
    return jsonify({'success': True})


# ── API: Save changes to a docket (captain) ────────────────────────────────────
@captain_bp.route('/api/docket/<int:docket_id>/save', methods=['POST'])
@captain_required
def save_docket(docket_id):
    docket = query_db("SELECT * FROM dockets WHERE id=%s", (docket_id,), one=True)
    if not docket:
        return jsonify({'success': False, 'message': 'Not found'}), 404

    data = request.form
    new_status = data.get('status', docket['status'])

    # Captain cannot set status back to constable-only statuses in a weird way
    old_status = docket['status']

    update_fields = {
        'case_type': data.get('case_type', docket['case_type']),
        'reporting_station': data.get('reporting_station', docket['reporting_station']),
        'status': new_status
    }

    if new_status == 'Case Closed':
        execute_db(
            """UPDATE dockets SET case_type=%s, reporting_station=%s, status=%s,
               closed_by=%s, closed_at=NOW() WHERE id=%s""",
            (update_fields['case_type'], update_fields['reporting_station'],
             new_status, session['user_id'], docket_id)
        )
        _log_audit(
            session['user_id'], session['full_name'], 'Captain',
            'Closed Case', docket_id, docket['case_number'], 'Case Closed',
            f"Captain {session['full_name']} closed case {docket['case_number']}."
        )
        execute_db(
            "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('admin',%s,'docket',%s)",
            (f"Captain {session['full_name']} closed case {docket['case_number']}.", docket_id)
        )
    else:
        execute_db(
            "UPDATE dockets SET case_type=%s, reporting_station=%s, status=%s WHERE id=%s",
            (update_fields['case_type'], update_fields['reporting_station'], new_status, docket_id)
        )
        _log_audit(
            session['user_id'], session['full_name'], 'Captain',
            'Edited Docket', docket_id, docket['case_number'], new_status,
            f"Captain {session['full_name']} edited docket {docket['case_number']}."
        )

    if old_status != new_status:
        execute_db(
            "INSERT INTO case_status_history (docket_id, old_status, new_status, changed_by) VALUES (%s,%s,%s,%s)",
            (docket_id, old_status, new_status, session['user_id'])
        )

    # Handle document uploads
    doc_types = ['affidavit', 'witness_statement', 'investigation_diary', 'suspect_info']
    for doc_type in doc_types:
        file = request.files.get(doc_type)
        if file and file.filename and _allowed_doc(file.filename):
            cur = query_db(
                "SELECT MAX(version) AS mv FROM docket_documents WHERE docket_id=%s AND document_type=%s",
                (docket_id, doc_type), one=True
            )
            next_ver = (cur['mv'] or 0) + 1
            rel_path, orig_name, fsize = _save_upload(file, doc_type, docket_id)
            execute_db(
                """INSERT INTO docket_documents
                   (docket_id, document_type, file_name, file_path, file_size, mime_type, version, uploaded_by)
                   VALUES (%s,%s,%s,%s,%s,'application/pdf',%s,%s)""",
                (docket_id, doc_type, orig_name, rel_path, fsize, next_ver, session['user_id'])
            )

    execute_db(
        "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('admin',%s,'docket',%s)",
        (f"Captain {session['full_name']} updated docket {docket['case_number']}.", docket_id)
    )
    return jsonify({'success': True, 'message': 'Docket updated.'})


# ── API: Close case ────────────────────────────────────────────────────────────
@captain_bp.route('/api/close-case/<int:docket_id>', methods=['POST'])
@captain_required
def close_case(docket_id):
    docket = query_db("SELECT * FROM dockets WHERE id=%s", (docket_id,), one=True)
    if not docket:
        return jsonify({'success': False, 'message': 'Not found'}), 404

    old_status = docket['status']
    execute_db(
        "UPDATE dockets SET status='Case Closed', closed_by=%s, closed_at=NOW() WHERE id=%s",
        (session['user_id'], docket_id)
    )
    execute_db(
        "INSERT INTO case_status_history (docket_id, old_status, new_status, changed_by) VALUES (%s,%s,'Case Closed',%s)",
        (docket_id, old_status, session['user_id'])
    )
    _log_audit(
        session['user_id'], session['full_name'], 'Captain',
        'Closed Case', docket_id, docket['case_number'], 'Case Closed',
        f"Captain {session['full_name']} closed case {docket['case_number']}."
    )
    execute_db(
        "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('admin',%s,'docket',%s)",
        (f"Captain {session['full_name']} closed case {docket['case_number']}.", docket_id)
    )
    return jsonify({'success': True, 'message': 'Case closed successfully.'})


# ── API: Update escalated case status ─────────────────────────────────────────
@captain_bp.route('/api/escalated/<int:docket_id>/update', methods=['POST'])
@captain_required
def update_escalated(docket_id):
    new_status = request.form.get('status', '')
    if new_status not in ['Investigation in Progress', 'Case Closed']:
        return jsonify({'success': False, 'message': 'Invalid status for escalated case.'}), 400

    docket = query_db("SELECT * FROM dockets WHERE id=%s AND status='Escalated to Captain'", (docket_id,), one=True)
    if not docket:
        return jsonify({'success': False, 'message': 'Docket not found or not escalated.'}), 404

    old_status = docket['status']
    if new_status == 'Case Closed':
        execute_db(
            "UPDATE dockets SET status=%s, closed_by=%s, closed_at=NOW() WHERE id=%s",
            (new_status, session['user_id'], docket_id)
        )
    else:
        execute_db("UPDATE dockets SET status=%s WHERE id=%s", (new_status, docket_id))

    execute_db(
        "INSERT INTO case_status_history (docket_id, old_status, new_status, changed_by) VALUES (%s,%s,%s,%s)",
        (docket_id, old_status, new_status, session['user_id'])
    )
    _log_audit(
        session['user_id'], session['full_name'], 'Captain',
        f'Updated Escalated Case to {new_status}', docket_id, docket['case_number'], new_status,
        f"Captain {session['full_name']} updated escalated case {docket['case_number']} to {new_status}."
    )
    return jsonify({'success': True, 'message': f'Status updated to {new_status}.'})


# ── API: Flag docket ──────────────────────────────────────────────────────────
@captain_bp.route('/api/flag/<int:docket_id>', methods=['POST'])
@captain_required
def flag_docket(docket_id):
    reason = request.form.get('reason', '').strip()
    if not reason:
        return jsonify({'success': False, 'message': 'A reason for flagging is required.'}), 400

    docket = query_db("SELECT * FROM dockets WHERE id=%s", (docket_id,), one=True)
    if not docket:
        return jsonify({'success': False, 'message': 'Docket not found.'}), 404

    execute_db(
        "INSERT INTO flagged_cases (docket_id, flagged_by, reason) VALUES (%s,%s,%s)",
        (docket_id, session['user_id'], reason)
    )
    _log_audit(
        session['user_id'], session['full_name'], 'Captain',
        'Flagged Docket', docket_id, docket['case_number'], docket['status'],
        f"Captain {session['full_name']} flagged docket {docket['case_number']}. Reason: {reason}"
    )
    execute_db(
        "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('admin',%s,'flag',%s)",
        (f"Captain {session['full_name']} flagged docket {docket['case_number']}. Reason: {reason}", docket_id)
    )
    return jsonify({'success': True, 'message': 'Docket flagged successfully.'})


# ── Profile API ────────────────────────────────────────────────────────────────
@captain_bp.route('/api/profile')
@captain_required
def api_profile():
    officer = query_db("SELECT * FROM officers WHERE id=%s", (session['user_id'],), one=True)
    if not officer:
        return jsonify({'error': 'Not found'}), 404
    d = dict(officer)
    d.pop('password_hash', None)
    d['date_of_birth'] = str(d.get('date_of_birth', ''))
    d['created_at'] = str(d.get('created_at', ''))
    d['updated_at'] = str(d.get('updated_at', ''))
    return jsonify(d)


@captain_bp.route('/api/profile/update', methods=['POST'])
@captain_required
def update_profile():
    data = request.form
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    officer_id = data.get('officer_id', '').strip()
    rank = data.get('rank_name', '').strip()

    if not all([full_name, email, officer_id, rank]):
        return jsonify({'success': False, 'message': 'Required fields missing.'}), 400

    if query_db("SELECT id FROM officers WHERE officer_id=%s AND id!=%s", (officer_id, session['user_id']), one=True):
        return jsonify({'success': False, 'message': 'Officer ID already in use.'}), 409
    if query_db("SELECT id FROM officers WHERE email=%s AND id!=%s", (email, session['user_id']), one=True):
        return jsonify({'success': False, 'message': 'Email already in use.'}), 409

    execute_db(
        "UPDATE officers SET full_name=%s, email=%s, officer_id=%s, rank_name=%s WHERE id=%s",
        (full_name, email, officer_id, rank, session['user_id'])
    )
    session['full_name'] = full_name
    session['officer_id'] = officer_id
    return jsonify({'success': True, 'message': 'Profile updated.'})


@captain_bp.route('/api/profile/password', methods=['POST'])
@captain_required
def change_password():
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    officer = query_db("SELECT * FROM officers WHERE id=%s", (session['user_id'],), one=True)
    if not check_password_hash(officer['password_hash'], current_pw):
        return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 400
    if new_pw != confirm:
        return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400
    if len(new_pw) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'}), 400

    execute_db("UPDATE officers SET password_hash=%s WHERE id=%s",
               (generate_password_hash(new_pw), session['user_id']))
    return jsonify({'success': True, 'message': 'Password changed.'})


@captain_bp.route('/api/profile/picture', methods=['POST'])
@captain_required
def upload_profile_picture():
    file = request.files.get('profile_picture')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'No file uploaded.'}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return jsonify({'success': False, 'message': 'Only JPG/PNG images allowed.'}), 400
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
    os.makedirs(upload_dir, exist_ok=True)
    unique_name = f"officer_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(upload_dir, unique_name))
    rel = f"profiles/{unique_name}"
    execute_db("UPDATE officers SET profile_picture=%s WHERE id=%s", (rel, session['user_id']))
    return jsonify({'success': True, 'path': rel})


# ── Serve uploaded files ──────────────────────────────────────────────────────
@captain_bp.route('/file/<path:filepath>')
@captain_required
def serve_file(filepath):
    from flask import send_from_directory
    safe_path = filepath.replace('\\', '/').lstrip('/')
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], safe_path)
