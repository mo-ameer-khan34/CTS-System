import mysql.connector
from mysql.connector import Error
from flask import g, current_app


def get_db():
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(
                host=current_app.config['DB_HOST'],
                port=current_app.config['DB_PORT'],
                user=current_app.config['DB_USER'],
                password=current_app.config['DB_PASSWORD'],
                database=current_app.config['DB_NAME'],
                autocommit=False,
                charset='utf8mb4'
            )
        except Error as e:
            raise RuntimeError(f"Database connection failed: {e}")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()


def query_db(sql, params=None, one=False, commit=False):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        if commit:
            db.commit()
            return cursor.lastrowid
        result = cursor.fetchone() if one else cursor.fetchall()
        return result
    except Error as e:
        db.rollback()
        raise e
    finally:
        cursor.close()


def execute_db(sql, params=None):
    return query_db(sql, params, commit=True)


def init_app(app):
    app.teardown_appcontext(close_db)
