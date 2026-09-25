"""
Run this script ONCE to set up the TRACE database and tables.
Usage: python setup_db.py
Make sure your .env file has the correct DB_USER, DB_PASSWORD, DB_HOST.
"""
import os
from dotenv import load_dotenv
import mysql.connector
from werkzeug.security import generate_password_hash

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
port = int(os.getenv('DB_PORT', 3306))
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD', '')
db_name = os.getenv('DB_NAME', 'trace_db')
admin_username = os.getenv('ADMIN_USERNAME', 'admin')
admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@TRACE2025')
admin_email = os.getenv('ADMIN_EMAIL', 'admin@trace.gov.za')

print(f"Connecting to MySQL at {host}:{port} as '{user}'...")

# Read schema
schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
with open(schema_path, 'r') as f:
    schema_sql = f.read()

try:
    conn = mysql.connector.connect(host=host, port=port, user=user, password=password)
    cursor = conn.cursor()

    # Execute schema (split on semicolons)
    statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
    for stmt in statements:
        try:
            cursor.execute(stmt)
            conn.commit()
        except mysql.connector.Error as e:
            if 'already exists' in str(e).lower() or e.errno == 1050:
                pass  # table already exists
            else:
                print(f"  Warning: {e}")

    # Switch to trace_db
    cursor.execute(f"USE {db_name}")

    # Seed admin account
    cursor.execute("SELECT id FROM admin_account WHERE username=%s", (admin_username,))
    if not cursor.fetchone():
        pw_hash = generate_password_hash(admin_password)
        cursor.execute(
            "INSERT INTO admin_account (username, email, password_hash, full_name) VALUES (%s,%s,%s,%s)",
            (admin_username, admin_email, pw_hash, 'System Administrator')
        )
        conn.commit()
        print(f"Admin account created: username='{admin_username}', password='{admin_password}'")
    else:
        print(f"Admin account already exists: username='{admin_username}'")

    cursor.close()
    conn.close()
    print("\nDatabase setup complete!")
    print(f"\nAdmin Login Credentials:")
    print(f"  Username: {admin_username}")
    print(f"  Password: {admin_password}")
    print(f"\nForce Save PIN: TRACE9247")
    print(f"\nRun the app with: python app.py")

except mysql.connector.Error as e:
    print(f"Error: {e}")
    print("\nPlease check your .env file and ensure MySQL is running.")
