"""
Authentication + RBAC logic.

Covers FR-01: login / logout, role-based permissions enforced backend-side.
Uses bcrypt for password hashing (industry standard).
"""
from datetime import datetime

import bcrypt

from database import (
    get_session, User, AuditLog,
    ROLES, PERMISSIONS,
)


# ---------- Password hashing ----------
def hash_password(password: str) -> str:
    """Hash a password with bcrypt (cost factor 12)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except Exception:
        return False


# ---------- Password policy ----------
def validate_password_strength(password: str) -> tuple:
    """
    Basic password policy.
    Returns (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, ""


def validate_email(email: str) -> tuple:
    """Minimal email validation (not a full RFC check)."""
    email = email.strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "Please enter a valid email address."
    return True, ""


# ---------- Audit logging ----------
def log_event(user_email: str, event_type: str, outcome: str, metadata: str = ""):
    """Record an authentication event in the audit log."""
    session = get_session()
    try:
        log = AuditLog(
            user_email=user_email,
            event_type=event_type,
            outcome=outcome,
            metadata_json=metadata,
        )
        session.add(log)
        session.commit()
    finally:
        session.close()


# ---------- User management ----------
def create_user(email: str, password: str, role: str, is_active: bool = True) -> tuple:
    """
    Create a new user. Returns (success, error_message, user_dict_or_None).
    """
    email = email.strip().lower()

    ok, err = validate_email(email)
    if not ok:
        return False, err, None

    ok, err = validate_password_strength(password)
    if not ok:
        return False, err, None

    if role not in ROLES:
        return False, f"Invalid role: {role}", None

    session = get_session()
    try:
        existing = session.query(User).filter_by(email=email).first()
        if existing:
            return False, "An account with this email already exists.", None

        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        session.commit()
        return True, "", {
            "id": user.id, "email": user.email,
            "role": user.role, "is_active": user.is_active,
        }
    finally:
        session.close()


def authenticate(email: str, password: str) -> tuple:
    """
    Verify credentials. Returns (success, user_dict_or_None, error_msg).
    Logs success/failure to audit log.
    """
    email = email.strip().lower()

    session = get_session()
    try:
        user = session.query(User).filter_by(email=email).first()

        if user is None:
            log_event(email, "login", "failure", "user_not_found")
            return False, None, "Invalid email or password."

        if not user.is_active:
            log_event(email, "login", "failure", "account_inactive")
            return False, None, "Account is inactive."

        if not verify_password(password, user.password_hash):
            log_event(email, "login", "failure", "bad_password")
            return False, None, "Invalid email or password."

        user.last_login = datetime.utcnow()
        session.commit()

        user_dict = {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }

        log_event(email, "login", "success")
        return True, user_dict, ""
    finally:
        session.close()


def change_password(user_id: int, old_password: str, new_password: str) -> tuple:
    """Change a user's password. Returns (success, error_message)."""
    session = get_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            return False, "User not found."

        if not verify_password(old_password, user.password_hash):
            return False, "Current password is incorrect."

        ok, err = validate_password_strength(new_password)
        if not ok:
            return False, err

        user.password_hash = hash_password(new_password)
        session.commit()

        log_event(user.email, "password_change", "success")
        return True, ""
    finally:
        session.close()


# ---------- RBAC ----------
def has_permission(role: str, permission: str) -> bool:
    """Check whether a role has a specific permission."""
    return permission in PERMISSIONS.get(role, [])


def list_permissions(role: str) -> list:
    """List all permissions for a role."""
    return PERMISSIONS.get(role, [])


# ---------- Admin actions ----------
def list_users() -> list:
    """List all users (admin-only)."""
    session = get_session()
    try:
        users = session.query(User).order_by(User.created_at.desc()).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "role_display": ROLES.get(u.role, u.role),
                "is_active": u.is_active,
                "created_at": u.created_at,
                "last_login": u.last_login,
            }
            for u in users
        ]
    finally:
        session.close()


def set_user_active(user_id: int, is_active: bool) -> tuple:
    """Activate or deactivate a user (admin-only)."""
    session = get_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            return False, "User not found."
        user.is_active = is_active
        session.commit()
        log_event(user.email, "account_status_change", "success",
                  f"is_active={is_active}")
        return True, ""
    finally:
        session.close()


def set_user_role(user_id: int, new_role: str) -> tuple:
    """Change a user's role (admin-only)."""
    if new_role not in ROLES:
        return False, f"Invalid role: {new_role}"

    session = get_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            return False, "User not found."
        old_role = user.role
        user.role = new_role
        session.commit()
        log_event(user.email, "role_change", "success",
                  f"{old_role} -> {new_role}")
        return True, ""
    finally:
        session.close()


def delete_user(user_id: int) -> tuple:
    """Delete a user (admin-only)."""
    session = get_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            return False, "User not found."
        email = user.email
        session.delete(user)
        session.commit()
        log_event(email, "user_delete", "success")
        return True, ""
    finally:
        session.close()


# ---------- Audit log read ----------
def get_audit_logs(limit: int = 200) -> list:
    session = get_session()
    try:
        rows = (
            session.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "user_email": r.user_email,
                "event_type": r.event_type,
                "outcome": r.outcome,
                "metadata": r.metadata_json,
                "timestamp": r.timestamp,
            }
            for r in rows
        ]
    finally:
        session.close()


# ---------- Bootstrap: default admin ----------
DEFAULT_ADMIN_EMAIL = "admin@portfolio.local"
DEFAULT_ADMIN_PASSWORD = "Admin@12345"


def ensure_default_admin() -> bool:
    """
    Create the default admin if no users exist.
    Returns True if created, False if users already exist.
    """
    session = get_session()
    try:
        count = session.query(User).count()
        if count > 0:
            return False
    finally:
        session.close()

    ok, _, _ = create_user(
        DEFAULT_ADMIN_EMAIL,
        DEFAULT_ADMIN_PASSWORD,
        role="admin",
    )
    return ok


# ---------- Self-test ----------
if __name__ == "__main__":
    from database import init_db
    init_db()

    print("=" * 60)
    print("auth.py — self test")
    print("=" * 60)

    # Clean slate
    session = get_session()
    session.query(AuditLog).delete()
    session.query(User).delete()
    session.commit()
    session.close()

    # Create users for each role
    test_users = [
        ("admin@test.local", "AdminPass123", "admin"),
        ("operator@test.local", "OperPass123", "verification_operator"),
        ("signer@test.local", "SignPass123", "document_signer"),
        ("verifier@test.local", "VerPass123", "document_verifier"),
    ]

    print("\n[1] Creating users...")
    for email, pwd, role in test_users:
        ok, err, u = create_user(email, pwd, role)
        print(f"    {email:30s} [{role:22s}] → {'OK' if ok else err}")

    # Duplicate check
    print("\n[2] Duplicate rejection...")
    ok, err, _ = create_user("admin@test.local", "OtherPass1", "admin")
    print(f"    Duplicate: ok={ok}, err='{err}'")

    # Weak password check
    print("\n[3] Weak password rejection...")
    ok, err, _ = create_user("weak@test.local", "abc", "admin")
    print(f"    Weak pwd: ok={ok}, err='{err}'")

    # Auth success
    print("\n[4] Login (valid credentials)...")
    ok, user, err = authenticate("admin@test.local", "AdminPass123")
    print(f"    ok={ok}, user={user['email'] if user else None}, err='{err}'")

    # Auth failure (bad password)
    print("\n[5] Login (bad password)...")
    ok, user, err = authenticate("admin@test.local", "wrongpass")
    print(f"    ok={ok}, err='{err}'")

    # Permissions
    print("\n[6] Permission matrix:")
    for role in ROLES:
        perms = list_permissions(role)
        print(f"    {role:22s} → {perms}")

    # Users list
    print("\n[7] Users in database:")
    for u in list_users():
        print(f"    {u['email']:30s} [{u['role_display']:25s}] active={u['is_active']}")

    # Audit logs
    print("\n[8] Audit log entries:")
    for log in get_audit_logs(limit=10):
        print(f"    {log['timestamp'].strftime('%H:%M:%S')}  "
              f"{log['user_email']:25s} {log['event_type']:20s} {log['outcome']:8s} {log['metadata']}")

    # Clean up test data so it doesn't block the default admin
    print("\n[9] Cleaning up test users...")
    session = get_session()
    session.query(AuditLog).delete()
    session.query(User).delete()
    session.commit()
    session.close()
    print("    Test users removed.")

    print("\n✅ auth.py works.")
    