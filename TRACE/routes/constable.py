import os
import uuid
from datetime import datetime
from functools import wraps

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify, current_app)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models.db import query_db, execute_db

constable_bp = Blueprint('constable', __name__)


def constable_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'constable':
            flash('Access denied.', 'error')
            return redirect(url_for('auth.constable_login'))
        return f(*args, **kwargs)
    return decorated


def _allowed_doc(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_DOC_EXTENSIONS']


def _allowed_evidence(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EVIDENCE_EXTENSIONS']


def _log_audit(officer_id, officer_name, role, action, docket_id=None, case_number=None, case_status=None, desc=None):
    execute_db(
        """INSERT INTO audit_logs
           (officer_id, officer_name, officer_role, action, docket_id, case_number, case_status, description)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (officer_id, officer_name, role, action, docket_id, case_number, case_status, desc)
    )


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


# ── Dashboard (default: My Assigned Cases) ───────────────────────────────────
@constable_bp.route('/dashboard')
@constable_required
def dashboard():
    officer = query_db("SELECT * FROM officers WHERE id=%s", (session['user_id'],), one=True)
    unread = query_db(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE recipient_role='constable' AND recipient_id=%s AND is_read=0",
        (session['user_id'],), one=True
    )
    return render_template('constable/dashboard.html', officer=officer,
                           unread=unread['cnt'] if unread else 0)


# ── API: My cases ─────────────────────────────────────────────────────────────
@constable_bp.route('/api/cases')
@constable_required
def api_cases():
    search = request.args.get('q', '').strip()
    base = """SELECT d.* FROM dockets d WHERE d.created_by=%s"""
    params = [session['user_id']]
    if search:
        base += " AND (d.case_number LIKE %s OR d.status LIKE %s)"
        params += [f"%{search}%", f"%{search}%"]
    base += " ORDER BY d.created_at DESC"
    cases = query_db(base, params)
    return jsonify([dict(c) for c in cases] if cases else [])


# ── API: Confirm view docket (creates audit log) ──────────────────────────────
@constable_bp.route('/api/confirm-view/<int:docket_id>', methods=['POST'])
@constable_required
def confirm_view(docket_id):
    docket = query_db(
        "SELECT * FROM dockets WHERE id=%s AND created_by=%s",
        (docket_id, session['user_id']), one=True
    )
    if not docket:
        return jsonify({'success': False, 'message': 'Docket not found.'}), 404

    _log_audit(
        session['user_id'], session['full_name'], 'Constable',
        'Viewed Docket', docket_id, docket['case_number'], docket['status'],
        f"Constable {session['full_name']} viewed docket {docket['case_number']}."
    )
    return jsonify({'success': True})


# ── API: Get single docket ─────────────────────────────────────────────────────
@constable_bp.route('/api/docket/<int:docket_id>')
@constable_required
def api_docket(docket_id):
    docket = query_db(
        "SELECT * FROM dockets WHERE id=%s AND created_by=%s",
        (docket_id, session['user_id']), one=True
    )
    if not docket:
        return jsonify({'error': 'Not found'}), 404

    docs = query_db(
        "SELECT * FROM docket_documents WHERE docket_id=%s ORDER BY document_type, version DESC",
        (docket_id,)
    )
    docket_dict = dict(docket)
    docket_dict['date_reported'] = str(docket_dict.get('date_reported', ''))
    docket_dict['created_at'] = str(docket_dict.get('created_at', ''))
    docket_dict['updated_at'] = str(docket_dict.get('updated_at', ''))
    docket_dict['documents'] = [dict(d) for d in docs] if docs else []
    return jsonify(docket_dict)


# ── API: Save (edit) existing docket ─────────────────────────────────────────
@constable_bp.route('/api/docket/<int:docket_id>/save', methods=['POST'])
@constable_required
def save_docket(docket_id):
    docket = query_db(
        "SELECT * FROM dockets WHERE id=%s AND created_by=%s",
        (docket_id, session['user_id']), one=True
    )
    if not docket:
        return jsonify({'success': False, 'message': 'Docket not found.'}), 404

    data = request.form
    new_status = data.get('status', docket['status'])

    # Constables cannot set Case Closed
    if new_status == 'Case Closed':
        return jsonify({'success': False, 'message': 'Only a Captain can close a case.'}), 403

    old_status = docket['status']
    execute_db(
        """UPDATE dockets SET complainant_full_name=%s, complainant_id_number=%s,
           case_type=%s, date_reported=%s, reporting_station=%s, status=%s
           WHERE id=%s""",
        (data.get('complainant_full_name', docket['complainant_full_name']),
         data.get('complainant_id_number', docket['complainant_id_number']),
         data.get('case_type', docket['case_type']),
         data.get('date_reported', str(docket['date_reported'])),
         data.get('reporting_station', docket['reporting_station']),
         new_status, docket_id)
    )

    if old_status != new_status:
        execute_db(
            "INSERT INTO case_status_history (docket_id, old_status, new_status, changed_by) VALUES (%s,%s,%s,%s)",
            (docket_id, old_status, new_status, session['user_id'])
        )
        # Notify captain if escalated
        if new_status == 'Escalated to Captain':
            execute_db(
                "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('captain',%s,'docket',%s)",
                (f"Docket {docket['case_number']} has been escalated to Captain.", docket_id)
            )

    # Handle new document uploads
    doc_types = ['affidavit', 'witness_statement', 'investigation_diary', 'suspect_info']
    for doc_type in doc_types:
        file = request.files.get(doc_type)
        if file and file.filename and _allowed_doc(file.filename):
            # Get current max version
            cur = query_db(
                "SELECT MAX(version) AS mv FROM docket_documents WHERE docket_id=%s AND document_type=%s",
                (docket_id, doc_type), one=True
            )
            next_ver = (cur['mv'] or 0) + 1
            rel_path, orig_name, fsize = _save_upload(file, doc_type, docket_id)
            execute_db(
                """INSERT INTO docket_documents
                   (docket_id, document_type, file_name, file_path, file_size, mime_type, version, uploaded_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (docket_id, doc_type, orig_name, rel_path, fsize, 'application/pdf', next_ver, session['user_id'])
            )

    evidence_files = request.files.getlist('evidence')
    for file in evidence_files:
        if file and file.filename and _allowed_evidence(file.filename):
            cur = query_db(
                "SELECT MAX(version) AS mv FROM docket_documents WHERE docket_id=%s AND document_type='evidence'",
                (docket_id,), one=True
            )
            next_ver = (cur['mv'] or 0) + 1
            rel_path, orig_name, fsize = _save_upload(file, 'evidence', docket_id)
            mime = file.content_type or 'application/octet-stream'
            execute_db(
                """INSERT INTO docket_documents
                   (docket_id, document_type, file_name, file_path, file_size, mime_type, version, uploaded_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (docket_id, 'evidence', orig_name, rel_path, fsize, mime, next_ver, session['user_id'])
            )

    _log_audit(
        session['user_id'], session['full_name'], 'Constable',
        'Edited Docket', docket_id, docket['case_number'], new_status,
        f"Constable {session['full_name']} edited docket {docket['case_number']}."
    )
    # Notify admin
    execute_db(
        "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('admin',%s,'docket',%s)",
        (f"Constable {session['full_name']} edited docket {docket['case_number']}.", docket_id)
    )
    return jsonify({'success': True, 'message': 'Docket updated successfully.'})


# ── API: Add new docket (initial save or after AI check) ─────────────────────
@constable_bp.route('/api/add-docket', methods=['POST'])
@constable_required
def add_docket():
    data = request.form
    case_number = data.get('case_number', '').strip()
    complainant_name = data.get('complainant_full_name', '').strip()
    case_type = data.get('case_type', '').strip()
    complainant_id = data.get('complainant_id_number', '').strip()
    date_reported = data.get('date_reported', '').strip()
    reporting_station = data.get('reporting_station', '').strip()
    status = data.get('status', 'Case Reported')
    force_save_mode = data.get('force_save', 'false') == 'true'
    force_pin = data.get('force_pin', '')

    # Validate
    if not all([case_number, complainant_name, case_type, complainant_id, date_reported, reporting_station]):
        return jsonify({'success': False, 'message': 'All required fields must be filled.'}), 400

    if status == 'Case Closed':
        return jsonify({'success': False, 'message': 'Cannot set status to Case Closed.'}), 403

    if query_db("SELECT id FROM dockets WHERE case_number=%s", (case_number,), one=True):
        return jsonify({'success': False, 'message': 'Case number already exists in the system.'}), 409

    # Force save PIN check
    if force_save_mode:
        if force_pin != current_app.config['FORCE_SAVE_PIN']:
            return jsonify({'success': False, 'message': 'Incorrect Force Save PIN.'}), 403

    docket_id = execute_db(
        """INSERT INTO dockets
           (case_number, complainant_full_name, complainant_id_number, case_type,
            date_reported, reporting_station, status, created_by, force_saved)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (case_number, complainant_name, complainant_id, case_type,
         date_reported, reporting_station, status, session['user_id'],
         1 if force_save_mode else 0)
    )

    execute_db(
        "INSERT INTO case_status_history (docket_id, old_status, new_status, changed_by) VALUES (%s,NULL,%s,%s)",
        (docket_id, status, session['user_id'])
    )

    # Upload documents
    doc_types = ['affidavit', 'witness_statement', 'investigation_diary', 'suspect_info']
    for doc_type in doc_types:
        file = request.files.get(doc_type)
        if file and file.filename and _allowed_doc(file.filename):
            rel_path, orig_name, fsize = _save_upload(file, doc_type, docket_id)
            execute_db(
                """INSERT INTO docket_documents
                   (docket_id, document_type, file_name, file_path, file_size, mime_type, version, uploaded_by)
                   VALUES (%s,%s,%s,%s,%s,%s,1,%s)""",
                (docket_id, doc_type, orig_name, rel_path, fsize, 'application/pdf', session['user_id'])
            )

    evidence_files = request.files.getlist('evidence')
    for file in evidence_files:
        if file and file.filename and _allowed_evidence(file.filename):
            rel_path, orig_name, fsize = _save_upload(file, 'evidence', docket_id)
            mime = file.content_type or 'application/octet-stream'
            execute_db(
                """INSERT INTO docket_documents
                   (docket_id, document_type, file_name, file_path, file_size, mime_type, version, uploaded_by)
                   VALUES (%s,'evidence',%s,%s,%s,%s,1,%s)""",
                (docket_id, orig_name, rel_path, fsize, mime, session['user_id'])
            )

    action = 'Force Saved Docket' if force_save_mode else 'Added Docket'
    _log_audit(
        session['user_id'], session['full_name'], 'Constable',
        action, docket_id, case_number, status,
        f"Constable {session['full_name']} added docket {case_number}."
        + (' (Force Save used)' if force_save_mode else '')
    )
    msg = f"Constable {session['full_name']} added new docket {case_number}."
    if force_save_mode:
        msg += " (Force Save override used — AI check was invalid.)"
    execute_db(
        "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('admin',%s,'docket',%s)",
        (msg, docket_id)
    )

    if status == 'Escalated to Captain':
        execute_db(
            "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('captain',%s,'docket',%s)",
            (f"New docket {case_number} escalated to Captain.", docket_id)
        )

    return jsonify({'success': True, 'message': 'Docket saved successfully.', 'docket_id': docket_id})


# ── API: AI Check ─────────────────────────────────────────────────────────────
@constable_bp.route('/api/ai-check', methods=['POST'])
@constable_required
def ai_check():
    import fitz  # PyMuPDF
    file = request.files.get('affidavit')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'No affidavit uploaded.'}), 400
    if not _allowed_doc(file.filename):
        return jsonify({'success': False, 'message': 'Only PDF files accepted for affidavit.'}), 400

    # Extract text
    pdf_bytes = file.read()
    text = ''
    try:
        with fitz.open(stream=pdf_bytes, filetype='pdf') as pdf:
            for page in pdf:
                text += page.get_text()
    except Exception as e:
        return jsonify({'success': False, 'message': f'Could not read PDF: {str(e)}'}), 400

    words = text.split()
    word_count = len(words)

    if word_count <= 250:
        return jsonify({
            'success': True,
            'word_count': word_count,
            'word_check': 'Rejected',
            'ai_valid': False,
            'ai_result': 'Word count below 250 — affidavit rejected.',
            'message': f'The affidavit contains only {word_count} words. Minimum required is 250.'
        })

    # AI context check
    api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
    ai_valid = True
    ai_result = 'Valid'
    ai_reason = 'Affidavit appears valid and appropriate for a police docket.'

    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            prompt = (
                "You are reviewing a police affidavit submitted into a Digital Docket Accountability System for the South African Police Service (SAPS). "
                "Assess whether the following affidavit text appears to be a genuine, relevant and contextually appropriate police affidavit or statement. "
                "A valid affidavit should describe an incident, contain factual information about an alleged offence, and be consistent with a formal police docket record. "
                "Reply with ONLY a JSON object like: {\"valid\": true, \"reason\": \"...\"}. "
                f"\n\nAFFIDAVIT TEXT:\n{text[:4000]}"
            )
            response = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=200,
                messages=[{'role': 'user', 'content': prompt}]
            )
            import json
            raw = response.content[0].text.strip()
            # Extract JSON from response
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(raw[start:end])
                ai_valid = result.get('valid', True)
                ai_reason = result.get('reason', '')
                ai_result = 'Valid' if ai_valid else 'Invalid'
        except Exception as e:
            ai_reason = f'AI check unavailable: {str(e)}. Please review manually.'
            ai_valid = True  # Default to valid if AI unavailable
            ai_result = 'Valid (AI unavailable)'
    else:
        ai_reason = 'AI check not configured (ANTHROPIC_API_KEY not set). Affidavit accepted based on word count.'

    return jsonify({
        'success': True,
        'word_count': word_count,
        'word_check': 'Accepted',
        'ai_valid': ai_valid,
        'ai_result': ai_result,
        'ai_reason': ai_reason
    })


# ── Profile ───────────────────────────────────────────────────────────────────
@constable_bp.route('/api/profile', methods=['GET'])
@constable_required
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


@constable_bp.route('/api/profile/update', methods=['POST'])
@constable_required
def update_profile():
    data = request.form
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    officer_id = data.get('officer_id', '').strip()
    rank = data.get('rank_name', '').strip()

    if not all([full_name, email, officer_id, rank]):
        return jsonify({'success': False, 'message': 'Required fields missing.'}), 400

    # Check for duplicate officer_id/email (excluding self)
    dup_oid = query_db(
        "SELECT id FROM officers WHERE officer_id=%s AND id!=%s", (officer_id, session['user_id']), one=True
    )
    if dup_oid:
        return jsonify({'success': False, 'message': 'Officer ID already in use.'}), 409

    dup_email = query_db(
        "SELECT id FROM officers WHERE email=%s AND id!=%s", (email, session['user_id']), one=True
    )
    if dup_email:
        return jsonify({'success': False, 'message': 'Email already in use.'}), 409

    execute_db(
        "UPDATE officers SET full_name=%s, email=%s, officer_id=%s, rank_name=%s WHERE id=%s",
        (full_name, email, officer_id, rank, session['user_id'])
    )
    session['full_name'] = full_name
    session['officer_id'] = officer_id
    return jsonify({'success': True, 'message': 'Profile updated successfully.'})


@constable_bp.route('/api/profile/password', methods=['POST'])
@constable_required
def change_password():
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    officer = query_db("SELECT * FROM officers WHERE id=%s", (session['user_id'],), one=True)
    if not check_password_hash(officer['password_hash'], current_pw):
        return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 400
    if new_pw != confirm:
        return jsonify({'success': False, 'message': 'New passwords do not match.'}), 400
    if len(new_pw) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'}), 400

    execute_db("UPDATE officers SET password_hash=%s WHERE id=%s",
               (generate_password_hash(new_pw), session['user_id']))
    return jsonify({'success': True, 'message': 'Password changed successfully.'})


@constable_bp.route('/api/profile/picture', methods=['POST'])
@constable_required
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
    filepath = os.path.join(upload_dir, unique_name)
    file.save(filepath)
    rel = f"profiles/{unique_name}"
    execute_db("UPDATE officers SET profile_picture=%s WHERE id=%s", (rel, session['user_id']))
    return jsonify({'success': True, 'path': rel})


# ── Serve uploaded files ──────────────────────────────────────────────────────
@constable_bp.route('/file/<path:filepath>')
@constable_required
def serve_file(filepath):
    from flask import send_from_directory
    safe_path = filepath.replace('\\', '/').lstrip('/')
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], safe_path)
