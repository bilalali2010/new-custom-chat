import streamlit as st 
import os
import requests
import PyPDF2
import time
import random
from datetime import datetime

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

DOMAIN_FALLBACK = "I’m here to help only with questions about Bilal, his skills, or his work. 🙂"

GREETING_KEYWORDS = ["hello", "hi", "hey", "greetings", "salam", "assalam"]
GREETING_RESPONSES = [
    "Hello! 👋 How can I assist you about Bilal today?",
    "Hi there! Ask me anything about Bilal’s skills or work.",
    "Hey! I’m Bilal’s AI assistant. How can I help?",
    "Greetings! 🤖 What would you like to know about Bilal?"
]

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Chat with Bilal", layout="centered")

# -----------------------------
# CSS
# -----------------------------
st.markdown("""
<style>
.chat-container { max-width: 750px; margin: auto; }
.chat-header {
    background: linear-gradient(90deg,#000428,#004e92);
    padding: 14px;
    color: white;
    text-align: center;
    font-weight: bold;
    border-radius: 10px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SESSION STATE
# -----------------------------
for key in ["messages", "chat_history", "admin_unlocked", "booking_step", "memory"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["messages", "chat_history", "memory"] else None

# -----------------------------
# LOAD KNOWLEDGE
# -----------------------------
knowledge = ""
if os.path.exists(KNOWLEDGE_FILE):
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        knowledge = f.read()

# -----------------------------
# HELPERS
# -----------------------------
def is_relevant_query(text: str) -> bool:
    keywords = [
        "bilal", "skill", "skills", "work", "project",
        "experience", "ai", "chatbot", "automation",
        "developer", "portfolio"
    ]
    return any(k in text.lower() for k in keywords)

def is_greeting(text: str) -> bool:
    return any(word in text.lower() for word in GREETING_KEYWORDS)

def is_urdu(text: str) -> bool:
    return any('\u0600' <= c <= '\u06FF' for c in text)

def typewriter_effect(message_index: int, text: str):
    """Update the last message in session_state.messages with typing effect."""
    placeholder = st.empty()
    message = ""
    for char in text:
        message += char
        placeholder.markdown(message)
        st.session_state.messages[message_index]["content"] = message
        time.sleep(0.01)

def get_bot_reply(user_input: str) -> str:
    # Appointment booking flow
    if st.session_state.booking_step == "name":
        st.session_state.client_name = user_input
        st.session_state.booking_step = "time"
        return "Thanks! What date and time do you prefer?"

    if st.session_state.booking_step == "time":
        with open("appointments.txt", "a") as f:
            f.write(f"{st.session_state.client_name} | {user_input}\n")
        st.session_state.booking_step = None
        return "✅ Appointment request saved. Bilal will contact you soon."

    if "appointment" in user_input.lower():
        st.session_state.booking_step = "name"
        return "Sure! What is your name?"

    # Greeting
    if is_greeting(user_input):
        return random.choice(GREETING_RESPONSES)

    # Simple question
    simple_qs = ["what bilal do", "who is bilal", "bilal does what"]
    if any(q in user_input.lower() for q in simple_qs):
        return ("Bilal is a seasoned software engineer with over five years of experience, "
                "specializing in full-stack development with JavaScript, Node.js, and React. "
                "He builds scalable web applications, mentors developers, and implements DevOps practices.")

    # Domain restriction
    if not is_relevant_query(user_input):
        return DOMAIN_FALLBACK

    # AI response
    prompt = ""
    if knowledge.strip():
        prompt += f"Knowledge:\n{knowledge}\n\n"

    prompt += f"User Memory:\n{st.session_state.memory[-5:]}\n\n"
    prompt += f"Question:\n{user_input}\n"
    prompt += "\nRespond in Urdu." if is_urdu(user_input) else "\nRespond in English."

    payload = {
        "model": "nvidia/nemotron-3-nano-30b-a3b:free",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional AI assistant representing Bilal. "
                    "Answer confidently about Bilal’s skills, experience, and work. "
                    "If the question is irrelevant, reply ONLY with: "
                    "'I’m here to help only with questions about Bilal and his skills or work.'"
                )
            },
            {"role": "user", "content": prompt}
        ],
        "max_output_tokens": 180,
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
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return DOMAIN_FALLBACK

# -----------------------------
# CHAT DISPLAY
# -----------------------------
def render_chat():
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown('<div class="chat-header">CHAT WITH BILAL</div>', unsafe_allow_html=True)

    # Show initial greeting if no messages
    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Hi! I’m Bilal’s AI Assistant 🤖. Ask anything about Bilal, his skills, or his work."
        })

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# CHAT INPUT & LOGIC
# -----------------------------
user_input = st.chat_input("Ask about Bilal, his skills, or his work...")

if user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.chat_history.append((user_input, "", datetime.now()))
    st.session_state.memory.append(user_input)

    # Append empty assistant message
    st.session_state.messages.append({"role": "assistant", "content": ""})
    bot_index = len(st.session_state.messages) - 1

    # Generate bot reply
    bot_reply = get_bot_reply(user_input)
    typewriter_effect(bot_index, bot_reply)

    # Update chat history
    st.session_state.chat_history[-1] = (user_input, bot_reply, datetime.now())

# -----------------------------
# FINAL RENDER
# -----------------------------
render_chat()
