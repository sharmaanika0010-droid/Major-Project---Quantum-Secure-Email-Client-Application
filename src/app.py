"""SCRUM-17 | QuMail Level 1 baseline UI: inbox fetch + plain compose/send.

Ticket: SCRUM-17
Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
"""
import os
import tempfile

import streamlit as st

from email_service.gmail_adapter import GmailAdapter

st.set_page_config(page_title="QuMail", page_icon="📧")
st.title("QuMail - Level 1 (No Quantum Security)")


@st.cache_resource
def get_adapter():
    return GmailAdapter().authenticate()


adapter = get_adapter()
inbox_tab, compose_tab = st.tabs(["Inbox", "Compose"])

with inbox_tab:
    n = st.slider("Messages to fetch", 1, 25, 10)
    if st.button("Fetch inbox"):
        for m in adapter.list_messages(max_results=n):
            with st.expander(f"{m.subject or '(no subject)'} - {m.sender}"):
                st.caption(m.date)
                st.write(m.body or m.snippet)
                for a in m.attachments:
                    data = adapter.download_attachment(m.message_id, a.attachment_id)
                    st.download_button(a.filename, data, file_name=a.filename,
                                       key=f"{m.message_id}-{a.filename}")

with compose_tab:
    to = st.text_input("To")
    subject = st.text_input("Subject")
    body = st.text_area("Message")
    upload = st.file_uploader("Attachment (optional)")
    if st.button("Send (Level 1)"):
        paths = []
        if upload:
            tmp = os.path.join(tempfile.mkdtemp(), upload.name)
            with open(tmp, "wb") as f:
                f.write(upload.getvalue())
            paths = [tmp]
        st.success(f"Sent, id {adapter.send_message(to, subject, body, paths)}")
