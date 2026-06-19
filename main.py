import os
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file (for local testing)
load_dotenv()

# ---------- CREATE THE APP ----------
app = FastAPI()

# ---------- ALLOW ANY WEBSITE TO CALL THIS API (CORS) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- CONNECT TO SUPABASE ----------
supabase_url = os.getenv("https://dbtrhxuscvskwsaurmrb.supabase.co")
supabase_key = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRidHJoeHVzY3Zza3dzYXVybXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTIyNDQ4OSwiZXhwIjoyMDk2ODAwNDg5fQ.HWPrGIP0H80o-T_7nhvbemunv2j-m5o81ihILUDvmgA")  # Use SERVICE key for backend
supabase: Client = create_client(supabase_url, supabase_key)

# ---------- CONNECT TO GOOGLE GEMINI ----------
gemini_api_key = os.getenv("AQ.Ab8RN6ISpigXQ8Ve97utf0gyLDrb1YjBIHHZl4vpiQ4IiSfpDA")
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")  # Fast and cheap

# ---------- DEFINE WHAT A CHAT REQUEST LOOKS LIKE ----------
class ChatRequest(BaseModel):
    session_id: str | None = None  # Optional: if new chat, leave blank
    user_message: str
    property_data: str | None = None  # Optional info about listings

# ---------- THE CHAT ENDPOINT (this is what the widget calls) ----------
@app.post("/chat")
async def chat(request: ChatRequest):
    # 1. If no session_id, create a new one (UUID)
    if not request.session_id:
        session_id = str(uuid.uuid4())
    else:
        session_id = request.session_id

    # 2. Save the user's message to Supabase
    supabase.table("chat_logs").insert({
        "session_id": session_id,
        "role": "user",
        "content": request.user_message,
        "timestamp": datetime.utcnow().isoformat()
    }).execute()

    # 3. Build a prompt for Gemini (tells it how to act as a real estate agent)
    prompt = f"""
You are a friendly real estate assistant for a website. 
You help visitors find properties, answer questions about listings, and book appointments.

Here are the property listings (if any): {request.property_data or "No specific listings provided."}

The user said: {request.user_message}

Respond in a helpful, professional, and short way. 
If they ask to book a viewing, tell them you will connect them with an agent and ask for their name and phone number.
Always ask a follow-up question to keep the conversation going.
"""

    # 4. Get reply from Gemini
    response = model.generate_content(prompt)
    bot_reply = response.text

    # 5. Save the bot's reply to Supabase
    supabase.table("chat_logs").insert({
        "session_id": session_id,
        "role": "assistant",
        "content": bot_reply,
        "timestamp": datetime.utcnow().isoformat()
    }).execute()

    # 6. Send back the reply and session_id to the widget
    return {
        "session_id": session_id,
        "reply": bot_reply
    }

# ---------- HEALTH CHECK (for Render to know it's alive) ----------
@app.get("/")
def health():
    return {"status": "alive", "message": "Real estate chatbot is running!"}
