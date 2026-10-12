"""
Streamlit app: Audit Logs & Admin Dashboard.

Covers FR-13 (audit logs) and FR-14 (admin dashboard).
Fully self-contained — generates its own demo data.
"""
import json
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from database import (
    init_db, EventType, Outcome, SourceModule,
)
from audit import query, stats, clear_all
from demo_data import generate_demo


init_db()

st.set_page_config(
    page_title="Audit Logs & Admin Dashboard",
    page_icon="📜",
    layout="wide",
)

st.title("📜 Audit Logs & Admin Dashboard")
st.caption("Project 8 — FR-13 (audit logs) + FR-14 (admin dashboard)")


# ---------- Empty state ----------
s = stats()
if s["total"] == 0:
    st.info("No audit events yet.")
    if st.button("🎲 Generate demo data (40 events)", type="primary"):
        generate_demo(40)
        st.rerun()
    st.stop()


# ---------- Sidebar ----------
st.sidebar.header("⚙️ Actions")

if st.sidebar.button("🎲 Add 20 more demo events", use_container_width=True):
    generate_demo(20)
    st.rerun()

if st.sidebar.button("🗑️ Clear all logs", use_container_width=True):
    clear_all()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"""
    ### 📊 Summary

    - **Total events:** {s['total']}
    - **Last 24h:** {s['last_24h']}
    - **Unique actors:** {s['actors_count']}
    - **Source modules:** {len(s['by_module'])}
    """
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "🔒 **Privacy:** Passwords, private keys, and raw biometric "
    "samples are never logged. Metadata is sanitized before storage."
)


# ---------- Tab layout ----------
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📜 Event Log", "📥 Export"])


# ==================================================================
# TAB 1: Dashboard
# ==================================================================
with tab1:
    st.subheader("Key metrics")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total events", s["total"])
    with col2:
        st.metric("Last 24 hours", s["last_24h"])
    with col3:
        st.metric("Unique actors", s["actors_count"])
    with col4:
        st.metric("Source modules", len(s["by_module"]))

    st.markdown("---")

    # Event types
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Events by type")
        by_type = s["by_type"]
        if by_type:
            df = pd.DataFrame([
                {"Event type": k, "Count": v}
                for k, v in sorted(by_type.items(), key=lambda x: -x[1])
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("Events by outcome")
        by_outcome = s["by_outcome"]
        if by_outcome:
            df = pd.DataFrame([
                {"Outcome": k, "Count": v}
                for k, v in sorted(by_outcome.items(), key=lambda x: -x[1])
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # By module
    st.subheader("Events by source module")
    by_mod = s["by_module"]
    if by_mod:
        df = pd.DataFrame([
            {"Module": k, "Count": v}
            for k, v in sorted(by_mod.items(), key=lambda x: -x[1])
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Recent activity (last 10 events)")
    recent = query(limit=10)
    if recent:
        for e in recent:
            ts = e["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(
                f"`{ts}` &nbsp; **{e['event_type']}** &nbsp; "
                f"→ **{e['outcome']}** &nbsp; "
                f"(actor: `{e['actor']}`, module: `{e['source_module']}`)"
                + (f", target: `{e['target']}`" if e["target"] else "")
            )


# ==================================================================
# TAB 2: Event Log
# ==================================================================
with tab2:
    st.subheader("Filterable event log")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Event types present
        all_types = sorted(s["by_type"].keys())
        type_filter = st.selectbox(
            "Event type",
            ["All"] + all_types,
        )

    with col2:
        all_outcomes = sorted(s["by_outcome"].keys())
        outcome_filter = st.selectbox(
            "Outcome",
            ["All"] + all_outcomes,
        )

    with col3:
        all_modules = sorted(s["by_module"].keys())
        module_filter = st.selectbox(
            "Source module",
            ["All"] + all_modules,
        )

    with col4:
        actor_filter = st.selectbox(
            "Actor",
            ["All"] + sorted(s["actors"]),
        )

    # Days filter
    days = st.slider("Show last N days", 1, 30, 7)
    since = datetime.utcnow() - timedelta(days=days)

    logs = query(
        limit=1000,
        event_type=None if type_filter == "All" else type_filter,
        outcome=None if outcome_filter == "All" else outcome_filter,
        source_module=None if module_filter == "All" else module_filter,
        actor=None if actor_filter == "All" else actor_filter,
        since=since,
    )

    st.markdown(f"**{len(logs)} events** (last {days} days)")

    if logs:
        df = pd.DataFrame([
            {
                "ID": e["id"],
                "Time": e["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                "Actor": e["actor"],
                "Event": e["event_type"],
                "Outcome": e["outcome"],
                "Target": e["target"] or "—",
                "Module": e["source_module"],
                "Metadata": e["metadata"] or "",
            }
            for e in logs
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No events match the filters.")


# ==================================================================
# TAB 3: Export
# ==================================================================
with tab3:
    st.subheader("Export audit logs")

    st.markdown(
        """
        Download a CSV snapshot of the full audit log for offline analysis
        or compliance reporting.
        """
    )

    logs = query(limit=10000)

    if logs:
        df = pd.DataFrame([
            {
                "id": e["id"],
                "timestamp": e["timestamp"].isoformat(),
                "actor": e["actor"],
                "event_type": e["event_type"],
                "outcome": e["outcome"],
                "target": e["target"] or "",
                "source_module": e["source_module"],
                "safe_metadata": e["metadata"] or "",
            }
            for e in logs
        ])

        st.markdown(f"**{len(df)} rows** ready for export")

        st.download_button(
            "📥 Download CSV",
            df.to_csv(index=False),
            file_name=f"audit_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("---")
        st.markdown("### Sample (first 20 rows)")
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)
    else:
        st.info("No events to export.")


# ---------- Footer ----------
st.markdown("---")
st.caption(
    "🔒 **Privacy policy:** This audit log never stores passwords, password hashes, "
    "private keys, tokens, or raw biometric samples. "
    "See `audit.py::_sanitize_metadata` for the redaction list."
)