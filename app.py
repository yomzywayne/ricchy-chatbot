import os
import json
import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Set up API key
if "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = "AIzaSyB-2vQd-y_M1EnVuX1Bk9EbA_klDLpV6UA"

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

if not firebase_admin._apps:
    cred = credentials.Certificate(os.environ["FIREBASE_CREDENTIALS"])
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Create the chatbot model with Gemini-1.5 or Gemini-2
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-pro-002",
    system_instruction=(
        "You are Ricchy's Bot, a friendly and knowledgeable customer support chatbot for an online clothing store. "
        "You can help customers with product information, order tracking, return policies, promotions, fashion tips, sizing advice, and general fashion-related questions. "
        "Respond clearly, professionally, and with a touch of personality that suits an online clothing brand."
    )
)

# Initialize chat session
chat_session = model.start_chat(history=[])

# Set up chat history and customer name
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "customer_name" not in st.session_state:
    st.session_state.customer_name = None

st.set_page_config(page_title="Ricchy's Chatbot", layout="centered")

# Enhanced UI Styling
st.markdown("""
    <style>
        body { font-family: 'Segoe UI', sans-serif; }
        .chat-container {
            max-width: 750px;
            margin: 20px auto;
            padding: 20px;
            background-color: #fdfdfd;
            border-radius: 12px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .user-msg, .bot-msg {
            padding: 10px 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            max-width: 80%;
            display: inline-block;
            line-height: 1.4;
        }
        .user-msg {
            background-color: #dcf8c6;
            align-self: flex-end;
            text-align: right;
            float: right;
            clear: both;
        }
        .bot-msg {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            float: left;
            clear: both;
        }
        .chat-input-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 20px;
        }
        .chat-input-row input {
            flex-grow: 1;
            padding: 10px;
            font-size: 16px;
            border-radius: 10px;
            border: 1px solid #ccc;
            margin-right: 10px;
        }
        .chat-input-row button {
            padding: 10px 20px;
            border: none;
            background-color: #007bff;
            color: white;
            border-radius: 10px;
            cursor: pointer;
        }
        .chat-input-row button:hover {
            background-color: #0056b3;
        }
        .timestamp {
            font-size: 12px;
            color: #888;
            text-align: center;
            margin-top: 30px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 Ricchy's Online Clothing Store Chatbot")
#st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

# Display chat history
for entry in st.session_state.chat_history:
    role_class = "user-msg" if entry['role'] == 'user' else "bot-msg"
    st.markdown(f"<div class='{role_class}'>{entry['message']}</div>", unsafe_allow_html=True)
    if entry.get("image_url"):
        st.image(entry["image_url"], caption=entry.get("image_caption", ""), width=250)

st.markdown("</div>", unsafe_allow_html=True)

# Chat input UI
col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.text_input("Type your message here", key="user_input")
with col2:
    send_button = st.button("Send")

if send_button and user_input.strip():
    st.session_state.chat_history.append({"role": "user", "message": user_input})

    if "my name is" in user_input.lower():
        name = user_input.lower().replace("my name is", "").strip().title()
        st.session_state.customer_name = name
        db.collection("users").add({
            "customer_name": name,
            "created_at": firestore.SERVER_TIMESTAMP, 
            "last_active": firestore.SERVER_TIMESTAMP,
        })
        bot_response = f"Hi {name}, it's a pleasure to meet you! Is there anything I can help you with today? 😊"
        chat_entry = {"role": "bot", "message": bot_response}
    else:
        matched_product = None
        products_ref = db.collection("products").stream()
        for product in products_ref:
            product_data = product.to_dict()
            if product_data["name"].lower() in user_input.lower():
                matched_product = product_data
                break

        if matched_product:
            try:
                response = chat_session.send_message(user_input.strip())
                bot_response = response.text
            except Exception:
                bot_response = "Hmm, I couldn't find an exact answer for that, but I'm always here to help. What else can I assist you with? 😊"
            chat_entry = {"role": "bot", "message": bot_response}
        else:
            bot_response = f"{matched_product['description']}\n\nYou can visit our website to view the full collection and prices."
            chat_entry = {
                "role": "bot",
                "message": bot_response,
                "image_url": matched_product.get("image_url"),
                "image_caption": matched_product.get("name", "")
            }

        db.collection("messages").add({
            "customer_name": st.session_state.customer_name or "Anonymous",
            "user_message": user_input,
            "bot_response": bot_response,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })

    st.session_state.chat_history.append(chat_entry)
    st.rerun()

# Footer
st.markdown(f"<div class='timestamp'>Chat started on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
