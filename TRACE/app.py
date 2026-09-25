import os
from flask import Flask, render_template
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from extensions import mail

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    mail.init_app(app)

    from models.db import init_app as db_init
    db_init(app)

    from routes.auth import auth_bp
    from routes.constable import constable_bp
    from routes.captain import captain_bp
    from routes.admin import admin_bp
    from routes.complainant import complainant_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(constable_bp, url_prefix='/constable')
    app.register_blueprint(captain_bp, url_prefix='/captain')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(complainant_bp, url_prefix='/complainant')

    with app.app_context():
        _seed_database(app)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    return app


def _seed_database(app):
    from models.db import get_db, execute_db, query_db
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Ensure roles exist
        cursor.execute("INSERT IGNORE INTO roles (name) VALUES ('constable'), ('captain'), ('admin')")
        db.commit()

        # Seed admin account if not present
        cursor.execute("SELECT id FROM admin_account LIMIT 1")
        if not cursor.fetchone():
            pw_hash = generate_password_hash(app.config.get('ADMIN_PASSWORD', 'Admin@TRACE2025'))
            cursor.execute(
                "INSERT INTO admin_account (username, email, password_hash, full_name) VALUES (%s,%s,%s,%s)",
                (
                    app.config.get('ADMIN_USERNAME', 'admin'),
                    app.config.get('ADMIN_EMAIL', 'admin@trace.gov.za'),
                    pw_hash,
                    'System Administrator'
                )
            )
            db.commit()
        cursor.close()
    except Exception as e:
        print(f"[TRACE] Database seed warning: {e}")


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
