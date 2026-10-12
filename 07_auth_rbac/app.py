"""
Streamlit app: Authentication & Role-Based Access Control.

Covers FR-01: login/logout with role-based permissions.
Covers partial FR-14: admin dashboard.
Covers partial FR-13: audit log for auth events.
"""
import streamlit as st
from datetime import datetime

from database import init_db, ROLES, PERMISSIONS
from auth import (
    authenticate, create_user, change_password, log_event,
    has_permission, list_permissions,
    list_users, set_user_active, set_user_role, delete_user,
    get_audit_logs, ensure_default_admin,
    DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD,
)


# ---------- Init ----------
init_db()
ensure_default_admin()


st.set_page_config(
    page_title="Auth & RBAC",
    page_icon="🔐",
    layout="wide",
)


# ---------- Session ----------
if "user" not in st.session_state:
    st.session_state.user = None


# ==================================================================
# NOT LOGGED IN — Login / Register page
# ==================================================================
def show_login_page():
    st.title("🔐 Biometric Platform — Authentication")
    st.caption("Project 7 — FR-01: User authentication & role-based access control")

    tab_login, tab_register, tab_help = st.tabs(
        ["🔑 Login", "➕ Register", "ℹ️ Help"]
    )

    with tab_login:
        st.subheader("Sign in")

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", type="primary", use_container_width=True)

        if submit:
            ok, user, err = authenticate(email, password)
            if ok:
                st.session_state.user = user
                st.success(f"Welcome, {user['email']}")
                st.rerun()
            else:
                st.error(f"❌ {err}")

    with tab_register:
        st.subheader("Create a new account")
        st.caption(
            "Only the admin can create accounts with elevated roles. "
            "New self-registered accounts get the **Verification Operator** role."
        )

        with st.form("register_form"):
            new_email = st.text_input("Email", placeholder="you@example.com")
            new_pwd = st.text_input("Password", type="password",
                                    help="Min 8 chars, at least 1 letter and 1 number")
            new_pwd2 = st.text_input("Confirm password", type="password")
            role = st.selectbox(
                "Requested role",
                options=["verification_operator", "document_signer", "document_verifier"],
                format_func=lambda r: ROLES.get(r, r),
            )
            submit_reg = st.form_submit_button("Register", type="primary",
                                                use_container_width=True)

        if submit_reg:
            if new_pwd != new_pwd2:
                st.error("Passwords do not match.")
            else:
                ok, err, _ = create_user(new_email, new_pwd, role)
                if ok:
                    st.success("Account created. Please log in.")
                else:
                    st.error(f"❌ {err}")

    with tab_help:
        st.markdown(
            f"""
            ### Default admin account

            For demo purposes, an admin account is auto-created on first run:

            - **Email:** `{DEFAULT_ADMIN_EMAIL}`
            - **Password:** `{DEFAULT_ADMIN_PASSWORD}`
            - **Role:** Administrator

            ⚠️ **In production:** disable auto-bootstrap and provision admin via a secure channel.

            ### Roles in this system (from SRS Section 3)

            | Role | Purpose |
            |---|---|
            | **Administrator** | Manage users, view audit logs, enroll identities |
            | **Verification Operator** | Run face/fingerprint verification |
            | **Document Signer** | Upload and sign PDFs |
            | **Document Verifier** | Verify signed PDFs |
            """
        )


# ==================================================================
# LOGGED IN — Main app
# ==================================================================
def show_sidebar():
    user = st.session_state.user
    role = user["role"]
    role_display = ROLES.get(role, role)

    st.sidebar.markdown(f"### 👤 {user['email']}")
    st.sidebar.markdown(f"**Role:** `{role_display}`")

    perms = list_permissions(role)
    st.sidebar.markdown("**Permissions:**")
    for p in perms:
        st.sidebar.markdown(f"- `{p}`")

    st.sidebar.markdown("---")

    # Build menu based on permissions
    menu = []
    if has_permission(role, "manage_users"):
        menu.append("👥 Manage Users")
    if has_permission(role, "verify_biometric"):
        menu.append("🧑 Biometric Verification")
    if has_permission(role, "sign_documents"):
        menu.append("✍️ Sign Documents")
    if has_permission(role, "verify_signatures"):
        menu.append("🔍 Verify Signatures")
    if has_permission(role, "view_audit_logs"):
        menu.append("📜 Audit Logs")
    menu.append("🔑 Change Password")

    page = st.sidebar.radio("Navigate", menu, label_visibility="collapsed")

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        log_event(user["email"], "logout", "success")
        st.session_state.user = None
        st.rerun()

    return page


def page_manage_users():
    st.subheader("👥 Manage Users")
    st.caption("Admin-only: create, activate/deactivate, change role, delete users.")

    # Create user form
    with st.expander("➕ Create a new user", expanded=False):
        with st.form("admin_create_user"):
            c1, c2 = st.columns(2)
            with c1:
                email = st.text_input("Email")
                pwd = st.text_input("Password", type="password")
            with c2:
                role = st.selectbox("Role", list(ROLES.keys()),
                                    format_func=lambda r: ROLES[r])
                pwd2 = st.text_input("Confirm password", type="password")

            submit = st.form_submit_button("Create user", type="primary",
                                            use_container_width=True)

        if submit:
            if pwd != pwd2:
                st.error("Passwords do not match.")
            else:
                ok, err, _ = create_user(email, pwd, role)
                if ok:
                    st.success(f"User {email} created.")
                    st.rerun()
                else:
                    st.error(f"❌ {err}")

    st.markdown("---")
    st.markdown("### All users")

    users = list_users()
    if not users:
        st.info("No users found.")
        return

    for u in users:
        with st.container():
            cols = st.columns([3, 3, 2, 2, 1])

            with cols[0]:
                st.markdown(f"**{u['email']}**")
                st.caption(f"Created: {u['created_at'].strftime('%Y-%m-%d')}")

            with cols[1]:
                new_role = st.selectbox(
                    "Role",
                    options=list(ROLES.keys()),
                    index=list(ROLES.keys()).index(u["role"]),
                    format_func=lambda r: ROLES[r],
                    key=f"role_{u['id']}",
                    label_visibility="collapsed",
                )
                if new_role != u["role"]:
                    if st.button(f"Update role", key=f"upd_role_{u['id']}"):
                        ok, err = set_user_role(u["id"], new_role)
                        if ok:
                            st.success("Role updated.")
                            st.rerun()
                        else:
                            st.error(err)

            with cols[2]:
                status = "🟢 Active" if u["is_active"] else "🔴 Inactive"
                st.markdown(status)
                if st.button("Toggle", key=f"toggle_{u['id']}"):
                    set_user_active(u["id"], not u["is_active"])
                    st.rerun()

            with cols[3]:
                last = u["last_login"].strftime("%Y-%m-%d %H:%M") if u["last_login"] else "—"
                st.caption(f"Last login: {last}")

            with cols[4]:
                # Prevent self-deletion
                if u["email"] != st.session_state.user["email"]:
                    if st.button("🗑️", key=f"del_{u['id']}"):
                        delete_user(u["id"])
                        st.rerun()
                else:
                    st.caption("(you)")

            st.markdown("---")


def page_biometric_verification():
    st.subheader("🧑 Biometric Verification")
    st.info(
        "This would open the face/fingerprint verification flow from **Project 1–4**. "
        "In an integrated deployment, this page links to the biometric modules."
    )
    st.markdown(
        """
        **In production, this page would:**
        1. Open the webcam capture interface (Project 1)
        2. Run quality checks with red/green indicators (Project 3)
        3. Match against enrolled identities (Project 4)
        4. Fall back to fingerprint verification (Project 2) if needed
        5. Write the verification result to the audit log (Project 8)
        """
    )
    if st.button("Log a demo verification attempt"):
        log_event(st.session_state.user["email"], "biometric_verify_demo", "success")
        st.success("Demo verification logged.")


def page_sign_documents():
    st.subheader("✍️ Sign Documents")
    st.info(
        "This would open the PDF signing flow from **Project 5**. "
        "Only Document Signers and Admins can access this page."
    )
    st.markdown(
        """
        **In production, this page would:**
        1. Let the user upload a PDF
        2. Optionally attach a drawn signature image
        3. Sign server-side with the private key (never exposed to browser)
        4. Provide the signed PDF for download
        5. Log the signing event
        """
    )


def page_verify_signatures():
    st.subheader("🔍 Verify Signatures")
    st.info(
        "This would open the signature verification flow from **Project 6**. "
        "Only Document Verifiers and Admins can access this page."
    )
    st.markdown(
        """
        **In production, this page would:**
        1. Accept an uploaded signed PDF
        2. Verify integrity, cryptographic validity, and trust
        3. Show red/green indicators per FR-12
        4. Log the verification result
        """
    )


def page_audit_logs():
    st.subheader("📜 Audit Logs")
    st.caption("Admin-only: view authentication and permission events.")

    logs = get_audit_logs(limit=200)

    if not logs:
        st.info("No audit entries yet.")
        return

    import pandas as pd

    # Filter
    col1, col2 = st.columns(2)
    with col1:
        outcome_filter = st.selectbox("Outcome", ["All", "success", "failure"])
    with col2:
        event_filter = st.selectbox(
            "Event type",
            ["All"] + sorted({l["event_type"] for l in logs}),
        )

    filtered = logs
    if outcome_filter != "All":
        filtered = [l for l in filtered if l["outcome"] == outcome_filter]
    if event_filter != "All":
        filtered = [l for l in filtered if l["event_type"] == event_filter]

    st.markdown(f"**{len(filtered)} entries**")

    df = pd.DataFrame([
        {
            "Time": l["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "User": l["user_email"] or "—",
            "Event": l["event_type"],
            "Outcome": l["outcome"],
            "Metadata": l["metadata"] or "",
        }
        for l in filtered
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)


def page_change_password():
    st.subheader("🔑 Change Password")

    with st.form("change_pwd_form"):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password",
                            help="Min 8 chars, 1 letter, 1 number")
        new2 = st.text_input("Confirm new password", type="password")
        submit = st.form_submit_button("Change password", type="primary")

    if submit:
        if new != new2:
            st.error("New passwords do not match.")
        else:
            ok, err = change_password(st.session_state.user["id"], old, new)
            if ok:
                st.success("Password updated.")
            else:
                st.error(f"❌ {err}")


# ==================================================================
# Router
# ==================================================================
if st.session_state.user is None:
    show_login_page()
else:
    page = show_sidebar()

    if page == "👥 Manage Users":
        page_manage_users()
    elif page == "🧑 Biometric Verification":
        page_biometric_verification()
    elif page == "✍️ Sign Documents":
        page_sign_documents()
    elif page == "🔍 Verify Signatures":
        page_verify_signatures()
    elif page == "📜 Audit Logs":
        page_audit_logs()
    elif page == "🔑 Change Password":
        page_change_password()