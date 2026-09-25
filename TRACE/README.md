# TRACE — Transparent Records & Accountability for Case Enforcement

Digital Docket Accountability and Incident Reporting System for SAPS.

## Quick Start

### 1. Install Python dependencies
```
pip install -r requirements.txt
```

### 2. Configure environment
Edit `.env` with your MySQL credentials and email settings:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=trace_db
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_gmail_app_password
ANTHROPIC_API_KEY=your_anthropic_key   # optional for AI check
```

### 3. Set up the database
```
python setup_db.py
```

### 4. Run the application
```
python app.py
```

Open your browser at: http://localhost:5000

---

## Credentials

| Role | Login | Password |
|------|-------|----------|
| Admin | admin | Admin@TRACE2025 |
| Constable | Sign up → wait for Admin approval | — |
| Captain | Sign up → wait for Admin approval | — |
| Complainant | No login needed | — |

**Force Save PIN:** `TRACE9247` (keep private)

---

## Features
- 4 user roles: Constable, Captain, Admin, Complainant
- Docket creation with document uploads (PDF, images, video, audio)
- Full tamper-proof audit trail
- AI affidavit check (word count + Claude AI context check)
- Force Save with PIN override
- OTP-based forgot password (email)
- Case status tracker for complainants
- Complainant appeal system
- Captain case closure and flagging
- Admin oversight dashboard
