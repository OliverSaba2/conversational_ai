"""
Streamlit admin board for viewing/cancelling reservations. Reads/writes the
same appointments.json/patients.json the chat uses, so it's live, not a mock.
Login via ADMIN_USERNAME/ADMIN_PASSWORD - see config.py's caveat on that.

Run with: streamlit run admin_board.py
"""

import plotly.express as px
import streamlit as st

import appointment_store
import patient_store
from config import ADMIN_PASSWORD, ADMIN_USERNAME, CLINIC_NAME
from schedule_view import build_schedule_dataframe

st.set_page_config(page_title=f"{CLINIC_NAME} Admin Board", page_icon="🩺", layout="wide")


def _require_login():
    if st.session_state.get("authenticated"):
        return

    st.title(f"{CLINIC_NAME} Admin Board")
    st.caption("Sign in to view and manage reservations.")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect username or password.")
    st.stop()


_require_login()

with st.sidebar:
    st.write(f"Signed in as **{ADMIN_USERNAME}**")
    if st.button("Log out"):
        st.session_state["authenticated"] = False
        st.rerun()

st.title(f"{CLINIC_NAME} Admin Board")
st.caption("Reservations and patients on file - reads/writes the same local files the chat assistant uses.")

if st.button("Refresh"):
    st.rerun()

appointments = appointment_store.list_all()
patients = patient_store.list_all()

st.subheader("Schedule")
schedule_df, unresolved_count = build_schedule_dataframe(appointments)
if schedule_df.empty:
    st.info("Nothing to plot yet - book an appointment with a concrete date/time to see it here.")
else:
    fig = px.timeline(
        schedule_df, x_start="Start", x_end="End", y="Doctor", color="Patient", text="Label",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_traces(textposition="inside")
    fig.update_layout(height=120 + 60 * schedule_df["Doctor"].nunique(), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)
    if unresolved_count:
        st.caption(f"{unresolved_count} appointment(s) with a vague date/time (e.g. \"next week\") aren't shown here.")

st.subheader(f"Appointments ({len(appointments)})")
if not appointments:
    st.info("No appointments on file.")
else:
    header = st.columns([2, 1.2, 1.5, 1.3, 1, 1])
    for col, label in zip(header, ["Patient", "Card", "Doctor", "Date", "Time", ""]):
        col.markdown(f"**{label}**")

    for i, appt in enumerate(appointments):
        row = st.columns([2, 1.2, 1.5, 1.3, 1, 1])
        row[0].write(appt.get("patient_name") or "")
        row[1].write(appt.get("patient_card") or "")
        row[2].write(appt.get("doctor") or "")
        row[3].write(appt.get("date") or "")
        row[4].write(appt.get("time") or "")
        if row[5].button("Cancel", key=f"cancel_{i}"):
            appointment_store.remove_appointment(appt["patient_card"], appt["doctor"], appt["date"])
            st.rerun()

st.subheader(f"Patients on file ({len(patients)})")
if not patients:
    st.info("No patients on file.")
else:
    st.table([{"Name": p.get("name"), "Card #": p.get("card_number")} for p in patients])
