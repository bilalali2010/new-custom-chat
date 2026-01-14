import streamlit as st
import os
import requests
import PyPDF2
from datetime import datetime
import re

# -----------------------------
# CONFIG
# -----------------------------
ADMIN_PASSWORD = "@supersecret"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    st.error("⚠️ OPENROUTER_API_KEY missing")
    st.stop()

KNOWLEDGE_FILE = "knowledge.txt"
MAX_CONTEXT = 4500

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Chat with Bilal", layout="centered")

# -----------------------------
# WHATSAPP STYLE CSS
# -----------------------------
st.markdown("""
<style>
.chat-header {
    position: sticky;
    top: 0;
    background: #075E54;
    color: white;
    padding: 12px;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    border-radius: 10px;
    margin-bottom: 10px;
}
.chat-container {
    max-width: 700px;
    margin: auto;
}
div[data-testid="stChatMessage"][data-role="user"] > div {
    background-color: #DCF8C6;
    border-radius: 15px;
    padding: 10px 14px;
    max-width: 75%;
}
div[data-testid="stChatMessage"][data-role="assistant"] > div {
    background-color: #FFFFFF;
    border-radius: 15px;
    padding: 10px 14px;
    max-width: 75%;
    border: 1px solid #eee;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SESSION STATE
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "appointments" not in st.session_state:
    st.session_state.appointments = []

if "booking_step" not in st.session_state:
    st.session_state.booking_step = None

if "booking_data" not in st.session_state:
    st.session_state.booking_data = {}

if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False

# -----------------------------
# LOAD KNOWLEDGE
# -----------------------------
knowledge = ""
if os.path.exists(KNOWLEDGE_FILE):
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        knowledge = f.read()

# -----------------------------
# INTENT DETECTION
# -----------------------------
def detect_intent(text):
    t = text.lower()

    if re.search(r"\b(book|appointment|meeting|schedule|call)\b", t):
        return "appointment"
    if re.search(r"\b(hi|hello|hey|assalam)\b", t):
        return "greeting"
    if re.search(r"\b(thank|thanks|great|nice)\b", t):
        return "appreciation"
    if re.search(r"\b(who is|what is|elon musk|capital|history)\b", t):
        return "irrelevant"
    return "business"

# -----------------------------
# CHAT UI
# -----------------------------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
st.markdown('<div class="chat-header">Chat with Bilal</div>', unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# CHAT INPUT (BOTTOM)
# -----------------------------
user_input = st.chat_input("Type a message...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    intent = detect_intent(user_input)

    # ---- Appointment Flow ----
    if intent == "appointment" or st.session_state.booking_step:
        if st.session_state.booking_step is None:
            st.session_state.booking_step = "name"
            reply = "Sure 👍 What is your **full name**?"
        elif st.session_state.booking_step == "name":
            st.session_state.booking_data["name"] = user_input
            st.session_state.booking_step = "datetime"
            reply = "Please share your **preferred date & time**."
        elif st.session_state.booking_step == "datetime":
            st.session_state.booking_data["datetime"] = user_input
            st.session_state.booking_step = "purpose"
            reply = "What is the **purpose** of the appointment?"
        else:
            st.session_state.booking_data["purpose"] = user_input
            st.session_state.appointments.append({
                **st.session_state.booking_data,
                "created": datetime.now()
            })
            st.session_state.booking_step = None
            st.session_state.booking_data = {}
            reply = "✅ **Appointment booked successfully!** We’ll contact you soon."

    elif intent == "greeting":
        reply = "Hello 👋 How can I help you with IGCSE, A Levels, or appointments?"

    elif intent == "appreciation":
        reply = "Thank you 😊 Happy to help!"

    elif intent == "irrelevant":
        reply = (
            "I’m a **business-specific assistant**.\n\n"
            "I can help with:\n"
            "• IGCSE / A Levels info\n"
            "• Aspire System services\n"
            "• Booking appointments"
        )

    else:
        payload = {
            "model": "nvidia/nemotron-3-nano-30b-a3b:free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Chat with Bilal, a STRICT business assistant. "
                        "Use ONLY the provided knowledge. "
                        "Refuse general knowledge questions."
                    )
                },
                {
                    "role": "user",
                    "content": f"Knowledge:\n{knowledge}\n\nQuestion:\n{user_input}"
                }
            ],
            "max_output_tokens": 150,
            "temperature": 0.3
        }

        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30
            )
            reply = res.json()["choices"][0]["message"]["content"].strip()
        except:
            reply = "Sorry, I couldn’t process that right now."

    st.session_state.messages.append({"role": "assistant", "content": reply})

# -----------------------------
# ADMIN PANEL (?admin)
# -----------------------------
if "admin" in st.query_params:
    st.sidebar.header("🔐 Admin Panel")

    if not st.session_state.admin_unlocked:
        pwd = st.sidebar.text_input("Admin Password", type="password")
        if st.sidebar.button("Unlock"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_unlocked = True
                st.sidebar.success("Admin unlocked")
            else:
                st.sidebar.error("Wrong password")

    if st.session_state.admin_unlocked:
        st.sidebar.subheader("📚 Knowledge Management")

        pdfs = st.sidebar.file_uploader(
            "Upload PDF Knowledge",
            type="pdf",
            accept_multiple_files=True
        )

        text_data = st.sidebar.text_area(
            "Add Training Text",
            height=150,
            placeholder="Paste institute info here..."
        )

        if st.sidebar.button("💾 Save Knowledge"):
            combined = ""
            if pdfs:
                for pdf in pdfs:
                    reader = PyPDF2.PdfReader(pdf)
                    for page in reader.pages:
                        combined += page.extract_text() or ""
            if text_data.strip():
                combined += "\n\n" + text_data.strip()

            combined = combined[:MAX_CONTEXT]

            with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
                f.write(combined)

            st.sidebar.success("Knowledge saved successfully ✅")

        st.sidebar.subheader("📅 Booked Appointments")
        if not st.session_state.appointments:
            st.sidebar.info("No appointments yet.")
        else:
            for a in st.session_state.appointments:
                st.sidebar.markdown(
                    f"**Name:** {a['name']}\n\n"
                    f"**Date/Time:** {a['datetime']}\n\n"
                    f"**Purpose:** {a['purpose']}\n\n---"
                )
