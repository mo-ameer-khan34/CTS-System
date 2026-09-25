import os
import random
import string
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify, current_app)
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import mail
from models.db import query_db, execute_db

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    admin = query_db("SELECT * FROM admin_account WHERE id=%s", (session['user_id'],), one=True)
    return render_template('admin/dashboard.html', admin=admin)


# ── API: Dashboard stats ──────────────────────────────────────────────────────
@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    closed = query_db(
        "SELECT COUNT(*) AS cnt FROM dockets WHERE status='Case Closed' AND MONTH(closed_at)=MONTH(NOW()) AND YEAR(closed_at)=YEAR(NOW())",
        one=True
    )
    flagged = query_db(
        "SELECT COUNT(*) AS cnt FROM flagged_cases WHERE MONTH(flagged_at)=MONTH(NOW()) AND YEAR(flagged_at)=YEAR(NOW())",
        one=True
    )
    appeals = query_db("SELECT COUNT(*) AS cnt FROM appeals WHERE appeal_status='Pending'", one=True)
    signups = query_db("SELECT COUNT(*) AS cnt FROM signup_requests WHERE status='pending'", one=True)
    unread = query_db("SELECT COUNT(*) AS cnt FROM notifications WHERE recipient_role='admin' AND is_read=0", one=True)

    return jsonify({
        'closed': closed['cnt'] if closed else 0,
        'flagged': flagged['cnt'] if flagged else 0,
        'appeals': appeals['cnt'] if appeals else 0,
        'signups': signups['cnt'] if signups else 0,
        'unread_notifications': unread['cnt'] if unread else 0
    })


# ── API: Recent notifications ─────────────────────────────────────────────────
@admin_bp.route('/api/notifications')
@admin_required
def api_notifications():
    notifs = query_db(
        "SELECT * FROM notifications WHERE recipient_role='admin' ORDER BY created_at DESC LIMIT 20"
    )
    result = []
    for n in (notifs or []):
        row = dict(n)
        row['created_at'] = str(row.get('created_at', ''))
        result.append(row)
    # Mark all as read
    execute_db("UPDATE notifications SET is_read=1 WHERE recipient_role='admin' AND is_read=0")
    return jsonify(result)


# ── API: Docket access history ─────────────────────────────────────────────────
@admin_bp.route('/api/access-history')
@admin_required
def api_access_history():
    q = request.args.get('q', '').strip()
    date_filter = request.args.get('date', '').strip()

    sql = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    if q:
        sql += " AND (officer_name LIKE %s OR case_number LIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    if date_filter:
        sql += " AND DATE(action_at)=%s"
        params.append(date_filter)
    sql += " ORDER BY action_at DESC LIMIT 200"

    logs = query_db(sql, params)
    result = []
    for log in (logs or []):
        row = dict(log)
        row['action_at'] = str(row.get('action_at', ''))
        result.append(row)
    return jsonify(result)


# ── API: Closed cases ──────────────────────────────────────────────────────────
@admin_bp.route('/api/closed-cases')
@admin_required
def api_closed_cases():
    cases = query_db(
        """SELECT d.*, o_create.full_name AS created_by_name,
                  o_close.full_name AS closed_by_name
           FROM dockets d
           JOIN officers o_create ON o_create.id=d.created_by
           LEFT JOIN officers o_close ON o_close.id=d.closed_by
           WHERE d.status='Case Closed'
           ORDER BY d.closed_at DESC"""
    )
    result = []
    for c in (cases or []):
        row = dict(c)
        row['date_reported'] = str(row.get('date_reported', ''))
        row['created_at'] = str(row.get('created_at', ''))
        row['closed_at'] = str(row.get('closed_at', ''))
        result.append(row)
    return jsonify(result)


# ── API: Flagged cases ─────────────────────────────────────────────────────────
@admin_bp.route('/api/flagged-cases')
@admin_required
def api_flagged_cases():
    cases = query_db(
        """SELECT fc.*, d.case_number, d.case_type, d.status, d.complainant_full_name,
                  o.full_name AS flagged_by_name
           FROM flagged_cases fc
           JOIN dockets d ON d.id=fc.docket_id
           JOIN officers o ON o.id=fc.flagged_by
           ORDER BY fc.flagged_at DESC"""
    )
    result = []
    for c in (cases or []):
        row = dict(c)
        row['flagged_at'] = str(row.get('flagged_at', ''))
        result.append(row)
    return jsonify(result)


# ── API: Get any docket (admin view) ──────────────────────────────────────────
@admin_bp.route('/api/docket/<int:docket_id>')
@admin_required
def api_docket(docket_id):
    docket = query_db("SELECT * FROM dockets WHERE id=%s", (docket_id,), one=True)
    if not docket:
        return jsonify({'error': 'Not found'}), 404
    docs = query_db(
        "SELECT * FROM docket_documents WHERE docket_id=%s ORDER BY document_type, version DESC",
        (docket_id,)
    )
    officer = query_db("SELECT full_name FROM officers WHERE id=%s", (docket['created_by'],), one=True)
    d = dict(docket)
    d['date_reported'] = str(d.get('date_reported', ''))
    d['created_at'] = str(d.get('created_at', ''))
    d['updated_at'] = str(d.get('updated_at', ''))
    d['closed_at'] = str(d.get('closed_at', ''))
    d['documents'] = [dict(doc) for doc in docs] if docs else []
    d['investigating_officer'] = officer['full_name'] if officer else 'Unknown'
    return jsonify(d)


# ── API: Complainant appeals ───────────────────────────────────────────────────
@admin_bp.route('/api/appeals')
@admin_required
def api_appeals():
    appeals = query_db(
        """SELECT a.*, d.case_number FROM appeals a
           JOIN dockets d ON d.id=a.docket_id
           ORDER BY a.submitted_at DESC"""
    )
    result = []
    for a in (appeals or []):
        row = dict(a)
        row['submitted_at'] = str(row.get('submitted_at', ''))
        result.append(row)
    return jsonify(result)


@admin_bp.route('/api/appeals/<int:appeal_id>/status', methods=['POST'])
@admin_required
def update_appeal_status(appeal_id):
    new_status = request.form.get('status', '')
    if new_status not in ['Review Case', 'Case Closed']:
        return jsonify({'success': False, 'message': 'Invalid status.'}), 400
    execute_db(
        "UPDATE appeals SET appeal_status=%s, processed_at=NOW() WHERE id=%s",
        (new_status, appeal_id)
    )
    return jsonify({'success': True, 'message': f'Appeal status updated to {new_status}.'})


# ── API: Signup requests ───────────────────────────────────────────────────────
@admin_bp.route('/api/signup-requests')
@admin_required
def api_signup_requests():
    requests_list = query_db(
        """SELECT sr.*, o.full_name, o.officer_id, o.rank_name, o.department,
                  o.sa_id_number, o.date_of_birth, o.email, r.name AS role_name
           FROM signup_requests sr
           JOIN officers o ON o.id=sr.officer_id
           JOIN roles r ON r.id=sr.role_id
           WHERE sr.status='pending'
           ORDER BY sr.requested_at DESC"""
    )
    reset_requests = query_db(
        """SELECT pr.*, o.full_name, o.officer_id, o.email, r.name AS role_name
           FROM password_reset_requests pr
           JOIN officers o ON o.id=pr.officer_id
           JOIN roles r ON r.id=o.role_id
           WHERE pr.status='pending'
           ORDER BY pr.requested_at DESC"""
    )
    result = []
    for r in (requests_list or []):
        row = dict(r)
        row['type'] = 'signup'
        row['requested_at'] = str(row.get('requested_at', ''))
        row['date_of_birth'] = str(row.get('date_of_birth', ''))
        result.append(row)
    for r in (reset_requests or []):
        row = dict(r)
        row['type'] = 'password_reset'
        row['requested_at'] = str(row.get('requested_at', ''))
        row['role_name'] = row.get('role_name', 'officer')
        result.append(row)
    return jsonify(result)


@admin_bp.route('/api/signup-requests/<int:req_id>/approve', methods=['POST'])
@admin_required
def approve_signup(req_id):
    req = query_db("SELECT * FROM signup_requests WHERE id=%s", (req_id,), one=True)
    if not req:
        return jsonify({'success': False, 'message': 'Request not found.'}), 404
    execute_db("UPDATE officers SET status='approved' WHERE id=%s", (req['officer_id'],))
    execute_db(
        "UPDATE signup_requests SET status='approved', processed_at=NOW() WHERE id=%s",
        (req_id,)
    )
    return jsonify({'success': True, 'message': 'Officer approved. They may now log in.'})


@admin_bp.route('/api/signup-requests/<int:req_id>/disapprove', methods=['POST'])
@admin_required
def disapprove_signup(req_id):
    req = query_db("SELECT * FROM signup_requests WHERE id=%s", (req_id,), one=True)
    if not req:
        return jsonify({'success': False, 'message': 'Request not found.'}), 404
    execute_db("UPDATE officers SET status='disapproved' WHERE id=%s", (req['officer_id'],))
    execute_db(
        "UPDATE signup_requests SET status='disapproved', processed_at=NOW() WHERE id=%s",
        (req_id,)
    )
    return jsonify({'success': True, 'message': 'Request disapproved.'})


# ── API: Forgot password requests ─────────────────────────────────────────────
@admin_bp.route('/api/forgot-password-requests')
@admin_required
def api_forgot_password_requests():
    reqs = query_db(
        """SELECT pr.*, o.full_name, o.officer_id, o.email, r.name AS role_name
           FROM password_reset_requests pr
           JOIN officers o ON o.id=pr.officer_id
           JOIN roles r ON r.id=o.role_id
           WHERE pr.status='pending'
           ORDER BY pr.requested_at DESC"""
    )
    result = []
    for r in (reqs or []):
        row = dict(r)
        row['requested_at'] = str(row.get('requested_at', ''))
        result.append(row)
    return jsonify(result)


@admin_bp.route('/api/forgot-password-requests/<int:req_id>/generate-otp', methods=['POST'])
@admin_required
def generate_otp(req_id):
    req = query_db(
        """SELECT pr.*, o.full_name, o.email, o.id AS officer_db_id
           FROM password_reset_requests pr
           JOIN officers o ON o.id=pr.officer_id
           WHERE pr.id=%s""",
        (req_id,), one=True
    )
    if not req:
        return jsonify({'success': False, 'message': 'Request not found.'}), 404

    # Generate OTP
    otp_code = ''.join(random.choices(string.digits, k=6))
    expires = datetime.now() + timedelta(minutes=current_app.config['OTP_EXPIRY_MINUTES'])

    execute_db(
        "INSERT INTO otps (officer_id, reset_request_id, otp_code, expires_at) VALUES (%s,%s,%s,%s)",
        (req['officer_db_id'], req_id, otp_code, expires)
    )
    execute_db("UPDATE password_reset_requests SET status='otp_sent' WHERE id=%s", (req_id,))

    # Send email
    try:
        msg = Message(
            subject='TRACE System — Password Reset OTP',
            recipients=[req['email']],
            body=(
                f"Dear {req['full_name']},\n\n"
                f"Your One-Time Password (OTP) for the TRACE Digital Docket System is:\n\n"
                f"    {otp_code}\n\n"
                f"This OTP is valid for {current_app.config['OTP_EXPIRY_MINUTES']} minutes.\n"
                f"Do not share this code with anyone.\n\n"
                f"If you did not request a password reset, please contact your administrator immediately.\n\n"
                f"TRACE System\nTransparent Records & Accountability for Case Enforcement"
            )
        )
        mail.send(msg)
        return jsonify({'success': True, 'message': f'OTP generated and sent to {req["email"]}.'})
    except Exception as e:
        return jsonify({
            'success': True,
            'message': f'OTP generated but email could not be sent ({str(e)}). '
                       f'Please configure email settings. OTP: {otp_code}'
        })


# ── Admin Profile ─────────────────────────────────────────────────────────────
@admin_bp.route('/api/profile')
@admin_required
def api_profile():
    admin = query_db("SELECT * FROM admin_account WHERE id=%s", (session['user_id'],), one=True)
    if not admin:
        return jsonify({'error': 'Not found'}), 404
    d = dict(admin)
    d.pop('password_hash', None)
    d['created_at'] = str(d.get('created_at', ''))
    return jsonify(d)


@admin_bp.route('/api/profile/update', methods=['POST'])
@admin_required
def update_profile():
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    if not full_name or not email:
        return jsonify({'success': False, 'message': 'Name and email required.'}), 400
    execute_db(
        "UPDATE admin_account SET full_name=%s, email=%s WHERE id=%s",
        (full_name, email, session['user_id'])
    )
    session['full_name'] = full_name
    return jsonify({'success': True, 'message': 'Profile updated.'})


@admin_bp.route('/api/profile/password', methods=['POST'])
@admin_required
def change_password():
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    admin = query_db("SELECT * FROM admin_account WHERE id=%s", (session['user_id'],), one=True)
    if not check_password_hash(admin['password_hash'], current_pw):
        return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 400
    if new_pw != confirm:
        return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400
    if len(new_pw) < 8:
        return jsonify({'success': False, 'message': 'Minimum 8 characters required.'}), 400

    execute_db("UPDATE admin_account SET password_hash=%s WHERE id=%s",
               (generate_password_hash(new_pw), session['user_id']))
    return jsonify({'success': True, 'message': 'Password changed.'})


@admin_bp.route('/api/profile/picture', methods=['POST'])
@admin_required
def upload_profile_picture():
    file = request.files.get('profile_picture')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'No file uploaded.'}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return jsonify({'success': False, 'message': 'Only JPG/PNG allowed.'}), 400
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
    os.makedirs(upload_dir, exist_ok=True)
    unique_name = f"admin_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(upload_dir, unique_name))
    rel = f"profiles/{unique_name}"
    execute_db("UPDATE admin_account SET profile_picture=%s WHERE id=%s", (rel, session['user_id']))
    return jsonify({'success': True, 'path': rel})


# ── Serve uploaded files ──────────────────────────────────────────────────────
@admin_bp.route('/file/<path:filepath>')
@admin_required
def serve_file(filepath):
    from flask import send_from_directory
    safe_path = filepath.replace('\\', '/').lstrip('/')
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], safe_path)
