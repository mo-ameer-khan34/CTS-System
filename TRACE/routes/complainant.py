from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory
from models.db import query_db, execute_db

complainant_bp = Blueprint('complainant', __name__)


@complainant_bp.route('/')
def portal():
    return render_template('complainant/portal.html')


@complainant_bp.route('/check-case', methods=['POST'])
def check_case():
    full_name = request.form.get('full_name', '').strip()
    id_number = request.form.get('id_number', '').strip()
    case_number = request.form.get('case_number', '').strip()

    if not all([full_name, id_number, case_number]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    docket = query_db(
        """SELECT d.*, o.full_name AS investigating_officer
           FROM dockets d
           JOIN officers o ON o.id=d.created_by
           WHERE d.case_number=%s
             AND d.complainant_full_name=%s
             AND d.complainant_id_number=%s""",
        (case_number, full_name, id_number), one=True
    )

    if not docket:
        return jsonify({'success': False, 'message': 'No case found matching those details. Please verify your information.'}), 404

    # Get affidavit document
    affidavit = query_db(
        """SELECT * FROM docket_documents
           WHERE docket_id=%s AND document_type='affidavit'
           ORDER BY version DESC LIMIT 1""",
        (docket['id'],), one=True
    )

    # Get appeal status
    appeal = query_db(
        "SELECT * FROM appeals WHERE docket_id=%s ORDER BY submitted_at DESC LIMIT 1",
        (docket['id'],), one=True
    )

    result = {
        'success': True,
        'docket_id': docket['id'],
        'case_number': docket['case_number'],
        'date_reported': str(docket['date_reported']),
        'case_type': docket['case_type'],
        'reporting_station': docket['reporting_station'],
        'investigating_officer': docket['investigating_officer'],
        'status': docket['status'],
        'has_affidavit': affidavit is not None,
        'appeal_status': appeal['appeal_status'] if appeal else None,
        'appeal_submitted': appeal is not None
    }
    return jsonify(result)


@complainant_bp.route('/view-affidavit', methods=['POST'])
def view_affidavit():
    case_number = request.form.get('case_number', '').strip()
    id_number = request.form.get('id_number', '').strip()
    full_name = request.form.get('full_name', '').strip()

    docket = query_db(
        "SELECT id FROM dockets WHERE case_number=%s AND complainant_id_number=%s AND complainant_full_name=%s",
        (case_number, id_number, full_name), one=True
    )
    if not docket:
        return jsonify({'success': False, 'message': 'Case not found.'}), 404

    affidavit = query_db(
        """SELECT * FROM docket_documents WHERE docket_id=%s AND document_type='affidavit'
           ORDER BY version DESC LIMIT 1""",
        (docket['id'],), one=True
    )
    if not affidavit:
        return jsonify({'success': False, 'message': 'No affidavit found for this case.'}), 404

    return jsonify({'success': True, 'file_path': affidavit['file_path'], 'file_name': affidavit['file_name']})


@complainant_bp.route('/file/<path:filepath>')
def serve_file(filepath):
    safe_path = filepath.replace('\\', '/').lstrip('/')
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], safe_path)


@complainant_bp.route('/submit-appeal', methods=['POST'])
def submit_appeal():
    full_name = request.form.get('full_name', '').strip()
    id_number = request.form.get('id_number', '').strip()
    case_number = request.form.get('case_number', '').strip()
    reason = request.form.get('reason', '').strip()

    if not all([full_name, id_number, case_number, reason]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    # Word limit check
    word_count = len(reason.split())
    if word_count > 100:
        return jsonify({'success': False, 'message': f'Reason must be 100 words or fewer. Current: {word_count} words.'}), 400

    docket = query_db(
        "SELECT * FROM dockets WHERE case_number=%s AND complainant_full_name=%s AND complainant_id_number=%s",
        (case_number, full_name, id_number), one=True
    )
    if not docket:
        return jsonify({'success': False, 'message': 'Case not found.'}), 404

    if docket['status'] != 'Case Closed':
        return jsonify({'success': False, 'message': 'Appeals can only be submitted for closed cases.'}), 400

    # Check for existing pending appeal
    existing = query_db(
        "SELECT id FROM appeals WHERE docket_id=%s AND appeal_status='Pending'",
        (docket['id'],), one=True
    )
    if existing:
        return jsonify({'success': False, 'message': 'You already have a pending appeal for this case.'}), 409

    execute_db(
        """INSERT INTO appeals
           (docket_id, complainant_full_name, complainant_id_number, reason, appeal_status)
           VALUES (%s,%s,%s,%s,'Pending')""",
        (docket['id'], full_name, id_number, reason)
    )
    execute_db(
        "INSERT INTO notifications (recipient_role, message, related_type, related_id) VALUES ('admin',%s,'appeal',%s)",
        (f"Complainant {full_name} submitted an appeal for case {case_number}.", docket['id'])
    )
    return jsonify({'success': True, 'message': 'Your appeal has been submitted and is under review.'})


@complainant_bp.route('/appeal-status', methods=['POST'])
def appeal_status():
    case_number = request.form.get('case_number', '').strip()
    id_number = request.form.get('id_number', '').strip()

    docket = query_db("SELECT id FROM dockets WHERE case_number=%s AND complainant_id_number=%s",
                      (case_number, id_number), one=True)
    if not docket:
        return jsonify({'success': False, 'message': 'Case not found.'}), 404

    appeal = query_db(
        "SELECT appeal_status, submitted_at FROM appeals WHERE docket_id=%s ORDER BY submitted_at DESC LIMIT 1",
        (docket['id'],), one=True
    )
    if not appeal:
        return jsonify({'success': False, 'message': 'No appeal found.'}), 404

    return jsonify({'success': True, 'status': appeal['appeal_status'],
                    'submitted_at': str(appeal['submitted_at'])})
