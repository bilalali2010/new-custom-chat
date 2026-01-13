import streamlit as st 
import os
import requests
import PyPDF2
from datetime import datetime
import random

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
# MESSAGES
# -----------------------------
FALLBACK_MESSAGES = [
    "Hmm, I’m not sure about that, but I can help you figure it out!",
    "Good question! I don’t have that info yet, but here’s something useful…",
    "I don’t know exactly, but let me give you a tip that might help!",
    "That’s tricky! Let’s explore together"
]

FUN_ENDINGS = [
    "😎 Hope that helps!",
    "🔥 Did you know this?",
    "🤔 Interesting, right?",
    "✨ Just a tip!"
]

GREETINGS = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
APPRECIATIONS = ["thanks", "thank you", "great job", "well done", "awesome"]

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Chat with Bilal",
    layout="wide"
)

# -----------------------------
# CSS FOR MOBILE-FRIENDLY CHAT
# -----------------------------
st.markdown("""
<style>
/* Chat container flex */
.chat-container {
    max-width:700px;
    margin:auto;
    border-radius:10px;
    overflow:hidden;
    border:1px solid #ddd;
    box-shadow:0 2px 12px rgba(0,0,0,0.1);
    background:#f7f7f7;
    display:flex;
    flex-direction:column;
    height:80vh;
}
.chat-header {
    background:linear-gradient(90deg,#25D366,#128C7E);
    padding:15px;
    color:white;
    font-weight:bold;
    font-size:18px;
    text-align:center;
    border-radius:10px 10px 0 0;
    font-family:Helvetica,Arial,sans-serif;
}
.chat-messages {
    flex:1;
    padding:10px;
    overflow-y:auto;
}
div[data-testid="stChatMessage"][data-role="user"] > div {
    background-color:#DCF8C6;
    color:black;
    border-radius:20px 20px 0 20px;
    padding:10px 15px;
    margin:5px 0;
    max-width:70%;
    float:right;
    clear:both;
    box-shadow:0 1px 2px rgba(0,0,0,0.1);
}
div[data-testid="stChatMessage"][data-role="assistant"] > div {
    background-color:white;
    color:black;
    border-radius:20px 20px 20px 0;
    padding:10px 15px;
    margin:5px 0;
    max-width:70%;
    float:left;
    clear:both;
    box-shadow:0 1px 2px rgba(0,0,0,0.15);
}
.stTextInput>div>div>input {
    border-radius:25px;
    padding:10px 15px;
}
div[data-role="user"]::before { content: "👤"; margin-right:5px; }
div[data-role="assistant"]::before { content: "🤖"; margin-right:5px; }
.timestamp {
    font-size:10px;
    color:#999;
    margin-top:2px;
    text-align:right;
}
.chat-input-container {
    padding:10px;
    border-top:1px solid #ddd;
    background:white;
    position:sticky;
    bottom:0;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SESSION STATE
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "appointments" not in st.session_state:
    st.session_state.appointments = []

if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False

if "booking_step" not in st.session_state:
    st.session_state.booking_step = 0

if "current_booking" not in st.session_state:
    st.session_state.current_booking = {}

# Add greeting once at the very start
if len(st.session_state.messages) == 0:
    st.session_state.messages.append(
        {"role": "assistant", "content": "Hi! I’m Chat with Bilal 🤖. I can help you with IGCSE/A Levels info and booking appointments."}
    )

# -----------------------------
# LOAD KNOWLEDGE
# -----------------------------
knowledge = ""
if os.path.exists(KNOWLEDGE_FILE):
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        knowledge = f.read()

# -----------------------------
# ADMIN PANEL
# -----------------------------
IS_ADMIN_PAGE = "admin" in st.query_params

if IS_ADMIN_PAGE:
    st.sidebar.header("🔐 Admin Panel")
    if not st.session_state.admin_unlocked:
        pwd_input = st.sidebar.text_input("Enter admin password", type="password")
        if st.sidebar.button("Unlock Admin"):
            if pwd_input == ADMIN_PASSWORD:
                st.session_state.admin_unlocked = True
                st.sidebar.success("Admin unlocked!")
                st.experimental_rerun()
            else:
                st.sidebar.error("Wrong password!")
    else:
        st.sidebar.success("Admin Unlocked")
        uploaded_pdfs = st.sidebar.file_uploader(
            "Upload PDF Knowledge", type="pdf", accept_multiple_files=True
        )
        text_knowledge = st.sidebar.text_area(
            "Add Training Text", height=150, placeholder="Paste custom knowledge here..."
        )
        if st.sidebar.button("💾 Save Knowledge"):
            combined_text = ""
            if uploaded_pdfs:
                for file in uploaded_pdfs:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        try:
                            combined_text += page.extract_text() or ""
                        except:
                            continue
            if text_knowledge.strip():
                combined_text += "\n\n" + text_knowledge.strip()
            combined_text = combined_text[:MAX_CONTEXT]
            if combined_text.strip():
                with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
                    f.write(combined_text)
                st.sidebar.success("✅ Knowledge saved")
            else:
                st.sidebar.warning("⚠️ No content to save")
        # Hidden appointments
        st.sidebar.subheader("📅 Appointments (Hidden)")
        if st.session_state.appointments:
            for idx, appt in enumerate(st.session_state.appointments, start=1):
                st.sidebar.markdown(
                    f"**{idx}. {appt['name']}**\n"
                    f"- Date/Time: {appt['datetime']}\n"
                    f"- Purpose: {appt['purpose']}\n"
                )
        else:
            st.sidebar.info("No appointments booked yet.")

# -----------------------------
# CHAT DISPLAY
# -----------------------------
def render_chat():
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown('<div class="chat-header">Chat with Bilal</div>', unsafe_allow_html=True)
    st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            st.markdown(f"<div class='timestamp'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# APPOINTMENT BOOKING
# -----------------------------
def handle_booking(user_input):
    step = st.session_state.booking_step
    if step == 1:
        st.session_state.current_booking["name"] = user_input
        st.session_state.booking_step = 2
        return "Great! What date and time would you like for the appointment? (e.g., 2026-01-20 14:30)"
    elif step == 2:
        st.session_state.current_booking["datetime"] = user_input
        st.session_state.booking_step = 3
        return "Noted. What is the purpose or topic of the meeting?"
    elif step == 3:
        st.session_state.current_booking["purpose"] = user_input
        st.session_state.appointments.append(st.session_state.current_booking.copy())
        confirmation = (
            f"✅ Appointment booked!\n"
            f"**Name:** {st.session_state.current_booking['name']}\n"
            f"**Date/Time:** {st.session_state.current_booking['datetime']}\n"
            f"**Purpose:** {st.session_state.current_booking['purpose']}"
        )
        st.session_state.current_booking = {}
        st.session_state.booking_step = 0
        return confirmation

# -----------------------------
# INTENT DETECTION
# -----------------------------
def detect_intent(user_input_lower):
    if any(greet in user_input_lower for greet in GREETINGS):
        return "greeting"
    elif any(apprec in user_input_lower for apprec in APPRECIATIONS):
        return "appreciation"
    elif "appointment" in user_input_lower or "meeting" in user_input_lower or "book" in user_input_lower:
        return "booking"
    else:
        return "business_query"

def respond_to_user(user_input):
    user_input_lower = user_input.lower()
    if st.session_state.booking_step > 0:
        return handle_booking(user_input)
    intent = detect_intent(user_input_lower)
    if intent == "greeting":
        return random.choice(["Hello! How can I assist you today?", "Hi there! Need help with IGCSE/A Levels or booking a meeting?"])
    elif intent == "appreciation":
        return random.choice(["You're welcome!", "Happy to help!", "Anytime!"])
    elif intent == "booking":
        st.session_state.booking_step = 1
        return "Sure! Let's book an appointment. First, may I have your full name?"
    elif intent == "business_query":
        MAX_CONTEXT_CHARS = 2000
        recent_chat_text = ""
        for u, b, _ in reversed(st.session_state.chat_history):
            pair = f"User: {u}\nBot: {b}\n"
            if len(recent_chat_text) + len(pair) > MAX_CONTEXT_CHARS:
                break
            recent_chat_text = pair + recent_chat_text
        prompt_content = ""
        if knowledge.strip():
            prompt_content += f"Document:\n{knowledge}\n\n"
        prompt_content += f"Recent chat:\n{recent_chat_text}\n\nQuestion:\n{user_input}"
        payload = {
            "model": "nvidia/nemotron-3-nano-30b-a3b:free",
            "messages": [
                {"role": "system",
                 "content": (
                     "You are Chat with Bilal. Answer concisely using the document if possible. "
                     "Do not answer unrelated general knowledge questions. Only answer business or service-related queries."
                 )
                 },
                {"role": "user", "content": prompt_content}
            ],
            "max_output_tokens": 150,
            "temperature": 0.4
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
            data = res.json()
            bot_reply = data["choices"][0]["message"]["content"].strip()
            irrelevant_keywords = ["elon musk", "history", "trivia", "random fact", "general knowledge"]
            if any(word in bot_reply.lower() for word in irrelevant_keywords):
                bot_reply = "I'm here to help with Aspire System related questions and appointment bookings only 😊."
            if not bot_reply:
                bot_reply = random.choice(FALLBACK_MESSAGES) + " " + random.choice(FUN_ENDINGS)
        except Exception:
            bot_reply = random.choice(FALLBACK_MESSAGES) + " " + random.choice(FUN_ENDINGS)
        return bot_reply

# -----------------------------
# CHAT INPUT AT BOTTOM
# -----------------------------
with st.container():
    user_input = st.chat_input("Type a message or book an appointment...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.chat_history.append((user_input, "", datetime.now()))
        bot_reply = respond_to_user(user_input)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        st.session_state.chat_history[-1] = (user_input, bot_reply, datetime.now())

# -----------------------------
# RENDER CHAT
# -----------------------------
render_chat()
