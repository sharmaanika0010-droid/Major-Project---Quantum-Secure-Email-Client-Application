"""SCRUM-23 | QuMail UI: Level 1 (plain) + Level 2 (Quantum-aided AES) compose/send and inbox decrypt.

Ticket: SCRUM-23
Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
"""
import os
import tempfile

import streamlit as st

from crypto.aes import QuMailCryptoError
from crypto.level2 import KMClient, KMError, is_qumail_message, read_level2, send_level2
from email_service.gmail_adapter import GmailAdapter

st.set_page_config(page_title="QuMail", page_icon="📧")
st.title("QuMail")


@st.cache_resource
def get_adapter():
    return GmailAdapter().authenticate()


adapter = get_adapter()
km = KMClient()  # KM simulator at http://127.0.0.1:5000
st.session_state.setdefault("inbox", [])
st.session_state.setdefault("decrypted", {})
inbox_tab, compose_tab = st.tabs(["Inbox", "Compose"])

with inbox_tab:
    n = st.slider("Messages to fetch", 1, 25, 10)
    if st.button("Fetch inbox"):
        st.session_state["inbox"] = adapter.list_messages(max_results=n)
    for m in st.session_state["inbox"]:
        secure = is_qumail_message(m)
        label = f"{'🔒 ' if secure else ''}{m.subject or '(no subject)'} - {m.sender}"
        with st.expander(label):
            st.caption(m.date)
            if secure:
                dec = st.session_state["decrypted"].get(m.message_id)
                if dec is None:
                    st.info("QuMail Level 2 message. Decrypting uses up its key (one-time).")
                    if st.button("Decrypt", key=f"dec-{m.message_id}"):
                        try:
                            st.session_state["decrypted"][m.message_id] = read_level2(adapter, km, m)
                            st.rerun()
                        except (KMError, QuMailCryptoError) as e:
                            st.error(f"Could not decrypt: {e}")
                else:
                    st.write(dec.body)
                    for name, data in dec.attachments:
                        st.download_button(name, data, file_name=name,
                                           key=f"decf-{m.message_id}-{name}")
            else:
                st.write(m.body or m.snippet)
                for a in m.attachments:
                    data = adapter.download_attachment(m.message_id, a.attachment_id)
                    st.download_button(a.filename, data, file_name=a.filename,
                                       key=f"{m.message_id}-{a.filename}")

with compose_tab:
    level = st.radio("Security level",
                     ["Level 1 - No quantum security", "Level 2 - Quantum-aided AES"])
    to = st.text_input("To")
    subject = st.text_input("Subject")
    body = st.text_area("Message")
    upload = st.file_uploader("Attachment (optional)")
    if st.button("Send"):
        paths = []
        if upload:
            tmp = os.path.join(tempfile.mkdtemp(), upload.name)
            with open(tmp, "wb") as f:
                f.write(upload.getvalue())
            paths = [tmp]
        try:
            if level.startswith("Level 2"):
                msg_id, key_id = send_level2(adapter, km, to, subject, body, paths)
                st.success(f"Sent encrypted (Level 2), id {msg_id}, key {key_id}")
            else:
                st.success(f"Sent, id {adapter.send_message(to, subject, body, paths)}")
        except (KMError, QuMailCryptoError) as e:
            st.error(f"Not sent: {e}")
