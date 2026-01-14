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

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Chat with Bilal",
    layout="centered"
)

# -----------------------------
# WHATSAPP / INSTAGRAM STYLE CSS
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
    z-index: 100;
    border-radius: 10px;
    margin-bottom: 10px;
}
.chat-container {
    max-width: 700px;
    margin: auto;
}
div[data-testid="stChatMessage"][data-role="user"] > div {
    background-color: #DCF8C6;
    color: black;
    border-radius: 15px;
    padding: 10px 14px;
    margin: 5px 0;
    max-width: 75%;
}
div[data-testid="stChatMessage"][data-role="assistant"] > div {
    background-color: #FFFFFF;
    color: black;
    border-radius: 15px;
    padding: 10px 14px;
    margin: 5px 0;
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
def detect_intent(text: str):
    t = text.lower()

    if re.search(r"\b(book|appointment|meeting|schedule|call)\b", t):
        return "appointment"

    if re.search(r"\b(hi|hello|hey|assalam|good morning|good evening)\b", t):
        return "greeting"

    if re.search(r"\b(thank|thanks|great|awesome|nice|good job)\b", t):
        return "appreciation"

    if re.search(r"\b(who is|what is|define|history|elon musk|president|capital)\b", t):
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

    # -----------------------------
    # APPOINTMENT FLOW
    # -----------------------------
    if intent == "appointment" or st.session_state.booking_step:

        if st.session_state.booking_step is None:
            st.session_state.booking_step = "name"
            bot_reply = "Sure 👍 What is your **full name**?"

        elif st.session_state.booking_step == "name":
            st.session_state.booking_data["name"] = user_input
            st.session_state.booking_step = "datetime"
            bot_reply = "Please tell me your **preferred date & time** for the appointment."

        elif st.session_state.booking_step == "datetime":
            st.session_state.booking_data["datetime"] = user_input
            st.session_state.booking_step = "purpose"
            bot_reply = "What is the **purpose** of this appointment?"

        elif st.session_state.booking_step == "purpose":
            st.session_state.booking_data["purpose"] = user_input

            st.session_state.appointments.append({
                "name": st.session_state.booking_data["name"],
                "datetime": st.session_state.booking_data["datetime"],
                "purpose": st.session_state.booking_data["purpose"],
                "created_at": datetime.now()
            })

            st.session_state.booking_step = None
            st.session_state.booking_data = {}

            bot_reply = "✅ **Your appointment has been booked successfully!**\n\nWe will contact you soon."

    # -----------------------------
    # GREETING
    # -----------------------------
    elif intent == "greeting":
        bot_reply = "Hello 👋 How can I assist you regarding IGCSE, A Levels, or appointments?"

    # -----------------------------
    # APPRECIATION
    # -----------------------------
    elif intent == "appreciation":
        bot_reply = "Thank you! 😊 I’m always here to help."

    # -----------------------------
    # IRRELEVANT
    # -----------------------------
    elif intent == "irrelevant":
        bot_reply = (
            "I’m sorry 🙏 I’m a **business-specific assistant**.\n\n"
            "I can help with:\n"
            "• IGCSE / A Levels information\n"
            "• Booking appointments\n"
            "• Aspire System services"
        )

    # -----------------------------
    # BUSINESS QUERY (AI)
    # -----------------------------
    else:
        payload = {
            "model": "nvidia/nemotron-3-nano-30b-a3b:free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Chat with Bilal, a STRICT business assistant for Aspire System. "
                        "Answer ONLY using provided knowledge. "
                        "DO NOT answer general knowledge questions."
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
            bot_reply = res.json()["choices"][0]["message"]["content"].strip()
        except:
            bot_reply = "I couldn’t process that right now. Please try again."

    st.session_state.messages.append({"role": "assistant", "content": bot_reply})

# -----------------------------
# ADMIN PANEL (HIDDEN)
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
        st.sidebar.subheader("📅 Booked Appointments")

        if not st.session_state.appointments:
            st.sidebar.info("No appointments yet.")
        else:
            for a in st.session_state.appointments:
                st.sidebar.markdown(
                    f"""
                    **Name:** {a['name']}  
                    **Date/Time:** {a['datetime']}  
                    **Purpose:** {a['purpose']}  
                    ---
                    """
                )
