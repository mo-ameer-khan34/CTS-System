import random
import string
from datetime import datetime, timedelta

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify, current_app)
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import mail
from models.db import query_db, execute_db

auth_bp = Blueprint('auth', __name__)


# ── Landing page ────────────────────────────────────────────────────────────
@auth_bp.route('/')
def index():
    return render_template('index.html')


# ── Constable signup ─────────────────────────────────────────────────────────
@auth_bp.route('/constable/signup', methods=['GET', 'POST'])
def constable_signup():
    if request.method == 'POST':
        data = request.form
        full_name = data.get('full_name', '').strip()
        sa_id = data.get('sa_id_number', '').strip()
        dob = data.get('date_of_birth', '').strip()
        officer_id = data.get('officer_id', '').strip()
        rank = data.get('rank_name', '').strip()
        department = data.get('department', '').strip()
        password = data.get('password', '')
        confirm = data.get('confirm_password', '')
        email = data.get('email', '').strip().lower()

        errors = []
        if not all([full_name, sa_id, dob, officer_id, rank, department, password, confirm, email]):
            errors.append('All fields are required.')
        if password != confirm:
            errors.append('Passwords do not match.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if len(sa_id) != 13 or not sa_id.isdigit():
            errors.append('South African ID number must be 13 digits.')

        existing_oid = query_db("SELECT id FROM officers WHERE officer_id=%s", (officer_id,), one=True)
        if existing_oid:
            errors.append('Officer ID already registered.')
        existing_email = query_db("SELECT id FROM officers WHERE email=%s", (email,), one=True)
        if existing_email:
            errors.append('Email address already registered.')

        if errors:
            return render_template('constable/signup.html', errors=errors, form=data)

        role = query_db("SELECT id FROM roles WHERE name='constable'", one=True)
        pw_hash = generate_password_hash(password)
        officer_db_id = execute_db(
            """INSERT INTO officers
               (full_name, sa_id_number, date_of_birth, officer_id, rank_name,
                department, email, password_hash, role_id, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",
            (full_name, sa_id, dob, officer_id, rank, department, email, pw_hash, role['id'])
        )
        execute_db(
            "INSERT INTO signup_requests (officer_id, role_id, status) VALUES (%s,%s,'pending')",
            (officer_db_id, role['id'])
        )
        _notify_admin('New constable signup request', 'signup_request', officer_db_id,
                      f"Constable {full_name} ({officer_id}) has submitted a signup request.")
        flash('Your signup request has been submitted. Please wait for Admin approval before logging in.', 'success')
        return redirect(url_for('auth.constable_login'))

    return render_template('constable/signup.html', errors=[], form={})


# ── Constable login ──────────────────────────────────────────────────────────
@auth_bp.route('/constable/login', methods=['GET', 'POST'])
def constable_login():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        officer_id = request.form.get('officer_id', '').strip()
        password = request.form.get('password', '')

        officer = query_db(
            """SELECT o.*, r.name AS role_name FROM officers o
               JOIN roles r ON r.id=o.role_id
               WHERE o.full_name=%s AND o.officer_id=%s AND r.name='constable'""",
            (full_name, officer_id), one=True
        )

        if not officer or not check_password_hash(officer['password_hash'], password):
            flash('Invalid credentials. Please check your Full Name, Officer ID and Password.', 'error')
            return render_template('constable/login.html')

        if officer['status'] == 'pending':
            flash('Your account is pending Admin approval. Please try again later.', 'warning')
            return render_template('constable/login.html')

        if officer['status'] == 'disapproved':
            flash('Your signup request was not approved. Please contact the Administrator.', 'error')
            return render_template('constable/login.html')

        session.clear()
        session['user_id'] = officer['id']
        session['role'] = 'constable'
        session['full_name'] = officer['full_name']
        session['officer_id'] = officer['officer_id']
        return redirect(url_for('constable.dashboard'))

    return render_template('constable/login.html')


# ── Captain signup ───────────────────────────────────────────────────────────
@auth_bp.route('/captain/signup', methods=['GET', 'POST'])
def captain_signup():
    if request.method == 'POST':
        data = request.form
        full_name = data.get('full_name', '').strip()
        sa_id = data.get('sa_id_number', '').strip()
        dob = data.get('date_of_birth', '').strip()
        officer_id = data.get('officer_id', '').strip()
        rank = data.get('rank_name', '').strip()
        department = data.get('department', '').strip()
        password = data.get('password', '')
        confirm = data.get('confirm_password', '')
        email = data.get('email', '').strip().lower()

        errors = []
        if not all([full_name, sa_id, dob, officer_id, rank, department, password, confirm, email]):
            errors.append('All fields are required.')
        if password != confirm:
            errors.append('Passwords do not match.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if len(sa_id) != 13 or not sa_id.isdigit():
            errors.append('South African ID number must be 13 digits.')

        if query_db("SELECT id FROM officers WHERE officer_id=%s", (officer_id,), one=True):
            errors.append('Officer ID already registered.')
        if query_db("SELECT id FROM officers WHERE email=%s", (email,), one=True):
            errors.append('Email address already registered.')

        if errors:
            return render_template('captain/signup.html', errors=errors, form=data)

        role = query_db("SELECT id FROM roles WHERE name='captain'", one=True)
        pw_hash = generate_password_hash(password)
        officer_db_id = execute_db(
            """INSERT INTO officers
               (full_name, sa_id_number, date_of_birth, officer_id, rank_name,
                department, email, password_hash, role_id, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",
            (full_name, sa_id, dob, officer_id, rank, department, email, pw_hash, role['id'])
        )
        execute_db(
            "INSERT INTO signup_requests (officer_id, role_id, status) VALUES (%s,%s,'pending')",
            (officer_db_id, role['id'])
        )
        _notify_admin('New captain signup request', 'signup_request', officer_db_id,
                      f"Captain {full_name} ({officer_id}) has submitted a signup request.")
        flash('Your signup request has been submitted. Please wait for Admin approval.', 'success')
        return redirect(url_for('auth.captain_login'))

    return render_template('captain/signup.html', errors=[], form={})


# ── Captain login ────────────────────────────────────────────────────────────
@auth_bp.route('/captain/login', methods=['GET', 'POST'])
def captain_login():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        officer_id = request.form.get('officer_id', '').strip()
        password = request.form.get('password', '')

        officer = query_db(
            """SELECT o.*, r.name AS role_name FROM officers o
               JOIN roles r ON r.id=o.role_id
               WHERE o.full_name=%s AND o.officer_id=%s AND r.name='captain'""",
            (full_name, officer_id), one=True
        )

        if not officer or not check_password_hash(officer['password_hash'], password):
            flash('Invalid credentials.', 'error')
            return render_template('captain/login.html')

        if officer['status'] == 'pending':
            flash('Your account is pending Admin approval.', 'warning')
            return render_template('captain/login.html')

        if officer['status'] == 'disapproved':
            flash('Your signup request was not approved.', 'error')
            return render_template('captain/login.html')

        session.clear()
        session['user_id'] = officer['id']
        session['role'] = 'captain'
        session['full_name'] = officer['full_name']
        session['officer_id'] = officer['officer_id']
        return redirect(url_for('captain.dashboard'))

    return render_template('captain/login.html')


# ── Admin login ──────────────────────────────────────────────────────────────
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        admin = query_db("SELECT * FROM admin_account WHERE username=%s", (username,), one=True)
        if not admin or not check_password_hash(admin['password_hash'], password):
            flash('Invalid admin credentials.', 'error')
            return render_template('admin/login.html')

        session.clear()
        session['user_id'] = admin['id']
        session['role'] = 'admin'
        session['full_name'] = admin['full_name']
        session['username'] = admin['username']
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/login.html')


# ── Logout ────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.index'))


# ── Forgot password (officer submits request) ─────────────────────────────────
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        officer_id = request.form.get('officer_id', '').strip()
        role_name = request.form.get('role', 'constable')

        officer = query_db(
            """SELECT o.*, r.name AS role_name FROM officers o
               JOIN roles r ON r.id=o.role_id
               WHERE o.full_name=%s AND o.officer_id=%s AND r.name=%s AND o.status='approved'""",
            (full_name, officer_id, role_name), one=True
        )

        if not officer:
            flash('No approved account found matching those details.', 'error')
            return render_template('forgot_password.html', role=role_name)

        req_id = execute_db(
            "INSERT INTO password_reset_requests (officer_id, status) VALUES (%s,'pending')",
            (officer['id'],)
        )
        _notify_admin(
            'Password reset request',
            'password_reset',
            req_id,
            f"Officer {full_name} ({officer_id}) has requested a password reset."
        )
        flash('Your password reset request has been submitted. '
              'An OTP will be sent to your registered email once the Admin processes it. '
              'Please check back shortly.', 'info')
        return render_template('otp_waiting.html', officer_id=officer['id'], role=role_name)

    role = request.args.get('role', 'constable')
    return render_template('forgot_password.html', role=role)


# ── Check OTP status (officer polls) ─────────────────────────────────────────
@auth_bp.route('/check-otp-status', methods=['POST'])
def check_otp_status():
    officer_id = request.form.get('officer_id')
    otp = query_db(
        """SELECT o.* FROM otps o
           JOIN password_reset_requests pr ON pr.id=o.reset_request_id
           WHERE o.officer_id=%s AND o.is_used=0 AND o.expires_at > NOW()
           ORDER BY o.created_at DESC LIMIT 1""",
        (officer_id,), one=True
    )
    if otp:
        return jsonify({'ready': True})
    return jsonify({'ready': False})


# ── Verify OTP ────────────────────────────────────────────────────────────────
@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    officer_id = request.form.get('officer_id')
    entered_otp = request.form.get('otp', '').strip()

    otp_record = query_db(
        """SELECT o.*, pr.id as req_id FROM otps o
           JOIN password_reset_requests pr ON pr.id=o.reset_request_id
           WHERE o.officer_id=%s AND o.is_used=0 AND o.expires_at > NOW()
           ORDER BY o.created_at DESC LIMIT 1""",
        (officer_id,), one=True
    )

    if not otp_record or otp_record['otp_code'] != entered_otp:
        return jsonify({'success': False, 'message': 'Invalid or expired OTP.'})

    # Mark OTP used
    execute_db("UPDATE otps SET is_used=1 WHERE id=%s", (otp_record['id'],))
    execute_db("UPDATE password_reset_requests SET status='completed' WHERE id=%s", (otp_record['req_id'],))

    # Store in session temporarily to allow password reset
    session['otp_verified_officer'] = int(officer_id)
    return jsonify({'success': True})


# ── Reset password (after OTP verified) ──────────────────────────────────────
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        officer_id = session.get('otp_verified_officer')
        if not officer_id:
            flash('Session expired. Please start over.', 'error')
            return redirect(url_for('auth.index'))

        new_password = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        if new_password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html')
        if len(new_password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('reset_password.html')

        pw_hash = generate_password_hash(new_password)
        execute_db("UPDATE officers SET password_hash=%s WHERE id=%s", (pw_hash, officer_id))
        session.pop('otp_verified_officer', None)
        flash('Password successfully updated. You may now log in.', 'success')
        return redirect(url_for('auth.index'))

    if not session.get('otp_verified_officer'):
        flash('Unauthorized.', 'error')
        return redirect(url_for('auth.index'))
    return render_template('reset_password.html')


# ── Helper ────────────────────────────────────────────────────────────────────
def _notify_admin(subject, related_type, related_id, message):
    try:
        execute_db(
            "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('admin',%s,%s,%s)",
            (message, related_type, related_id)
        )
    except Exception:
        pass
