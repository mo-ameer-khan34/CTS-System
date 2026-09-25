-- TRACE: Transparent Records & Accountability for Case Enforcement
-- MySQL Database Schema

CREATE DATABASE IF NOT EXISTS trace_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE trace_db;

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE
);
INSERT IGNORE INTO roles (name) VALUES ('constable'), ('captain'), ('admin');

-- Officers (constables and captains)
CREATE TABLE IF NOT EXISTS officers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(255) NOT NULL,
    sa_id_number VARCHAR(13) NOT NULL,
    date_of_birth DATE NOT NULL,
    officer_id VARCHAR(50) NOT NULL UNIQUE,
    rank_name VARCHAR(100) NOT NULL,
    department VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT NOT NULL,
    status ENUM('pending','approved','disapproved') DEFAULT 'pending',
    profile_picture VARCHAR(500) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Signup requests
CREATE TABLE IF NOT EXISTS signup_requests (
    id INT PRIMARY KEY AUTO_INCREMENT,
    officer_id INT NOT NULL,
    role_id INT NOT NULL,
    status ENUM('pending','approved','disapproved') DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (officer_id) REFERENCES officers(id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Password reset requests
CREATE TABLE IF NOT EXISTS password_reset_requests (
    id INT PRIMARY KEY AUTO_INCREMENT,
    officer_id INT NOT NULL,
    status ENUM('pending','otp_sent','completed','expired') DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (officer_id) REFERENCES officers(id)
);

-- OTPs
CREATE TABLE IF NOT EXISTS otps (
    id INT PRIMARY KEY AUTO_INCREMENT,
    officer_id INT NOT NULL,
    reset_request_id INT NOT NULL,
    otp_code VARCHAR(10) NOT NULL,
    is_used TINYINT(1) DEFAULT 0,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (officer_id) REFERENCES officers(id),
    FOREIGN KEY (reset_request_id) REFERENCES password_reset_requests(id)
);

-- Dockets / Cases
CREATE TABLE IF NOT EXISTS dockets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    case_number VARCHAR(100) NOT NULL UNIQUE,
    complainant_full_name VARCHAR(255) NOT NULL,
    complainant_id_number VARCHAR(13) NOT NULL,
    case_type VARCHAR(255) NOT NULL,
    date_reported DATE NOT NULL,
    reporting_station VARCHAR(255) NOT NULL,
    status VARCHAR(100) NOT NULL DEFAULT 'Case Reported',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    closed_by INT NULL DEFAULT NULL,
    closed_at TIMESTAMP NULL DEFAULT NULL,
    ai_check_result VARCHAR(50) DEFAULT NULL,
    force_saved TINYINT(1) DEFAULT 0,
    FOREIGN KEY (created_by) REFERENCES officers(id),
    FOREIGN KEY (closed_by) REFERENCES officers(id)
);

-- Docket documents (with versioning support)
CREATE TABLE IF NOT EXISTS docket_documents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    docket_id INT NOT NULL,
    document_type ENUM('affidavit','witness_statement','investigation_diary','suspect_info','evidence') NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT DEFAULT NULL,
    mime_type VARCHAR(100) DEFAULT NULL,
    version INT DEFAULT 1,
    uploaded_by INT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (docket_id) REFERENCES dockets(id),
    FOREIGN KEY (uploaded_by) REFERENCES officers(id)
);

-- Audit / Access logs (CRITICAL FEATURE)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    officer_id INT NOT NULL,
    officer_name VARCHAR(255) NOT NULL,
    officer_role VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    docket_id INT DEFAULT NULL,
    case_number VARCHAR(100) DEFAULT NULL,
    case_status VARCHAR(100) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    action_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (officer_id) REFERENCES officers(id)
);

-- Case status history
CREATE TABLE IF NOT EXISTS case_status_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    docket_id INT NOT NULL,
    old_status VARCHAR(100) DEFAULT NULL,
    new_status VARCHAR(100) NOT NULL,
    changed_by INT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (docket_id) REFERENCES dockets(id),
    FOREIGN KEY (changed_by) REFERENCES officers(id)
);

-- Flagged cases
CREATE TABLE IF NOT EXISTS flagged_cases (
    id INT PRIMARY KEY AUTO_INCREMENT,
    docket_id INT NOT NULL,
    flagged_by INT NOT NULL,
    reason TEXT NOT NULL,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (docket_id) REFERENCES dockets(id),
    FOREIGN KEY (flagged_by) REFERENCES officers(id)
);

-- Complainant appeals
CREATE TABLE IF NOT EXISTS appeals (
    id INT PRIMARY KEY AUTO_INCREMENT,
    docket_id INT NOT NULL,
    complainant_full_name VARCHAR(255) NOT NULL,
    complainant_id_number VARCHAR(13) NOT NULL,
    reason TEXT NOT NULL,
    appeal_status ENUM('Pending','Review Case','Case Closed') DEFAULT 'Pending',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (docket_id) REFERENCES dockets(id)
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    recipient_role VARCHAR(20) NOT NULL,
    recipient_id INT DEFAULT NULL,
    message TEXT NOT NULL,
    related_type VARCHAR(50) DEFAULT NULL,
    related_id INT DEFAULT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Admin account (single account, seeded)
CREATE TABLE IF NOT EXISTS admin_account (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL DEFAULT 'System Administrator',
    profile_picture VARCHAR(500) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
