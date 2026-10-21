import os
import json
import datetime
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = str(os.getenv("ADMIN_ID", ""))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# KV auto detect - Vercel ja nam dey sob support
KV_URL = (
    os.getenv("KV_REST_API_URL") or
    os.getenv("UPSTASH_REDIS_REST_URL") or
    os.getenv("STORAGE_URL") or
    os.getenv("KV_URL") or
    os.getenv("STORAGE_REST_API_URL")
)
KV_TOKEN = (
    os.getenv("KV_REST_API_TOKEN") or
    os.getenv("UPSTASH_REDIS_REST_TOKEN") or
    os.getenv("STORAGE_TOKEN") or
    os.getenv("STORAGE_REST_API_TOKEN") or
    os.getenv("KV_REST_API_READ_ONLY_TOKEN")
)

def kv_get(key):
    if not KV_URL or not KV_TOKEN:
        return None
    try:
        url = f"{KV_URL}/get/{key}"
        r = requests.get(url, headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=10)
        if r.ok:
            return r.json().get("result")
    except Exception as e:
        print(f"kv_get error {e}")
    return None

def kv_set(key, value):
    if not KV_URL or not KV_TOKEN:
        return
    try:
        url = f"{KV_URL}/set/{key}/{value}"
        requests.get(url, headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=10)
    except Exception as e:
        print(f"kv_set error {e}")

def tg_send(chat_id, text, reply_markup=None):
    if not BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"send error {e}")

def ask_gemini(prompt):
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY Vercel e add koro nai."
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        data = {
            "contents": [{"parts": [{"text": f"You are Py-JS Sentinel, friendly Bangla-English teacher. Explain clearly: {prompt}"}]}]
        }
        r = requests.post(url, json=data, timeout=25)
        j = r.json()
        return j["candidates"][0]["content"]["parts"][0]["text"][:4000]
    except Exception as e:
        return f"AI Error: {e}\nRaw: {str(r.text)[:500] if 'r' in locals() else ''}"

# 90 Days Content
CLASSES_PY_JS = []
for i in range(90):
    CLASSES_PY_JS.append(
        f"*Day {i+1} / 90 - Py-JS Sentinel*\n\n"
        f"*Python:* Day {i+1} - variables, loops, functions, oop, file, api\n"
        f"*JavaScript:* Day {i+1} - let/const, array, object, promise, DOM\n"
        f"*Task:* Ajke 1 ta mini project banaw\n"
        f"*Example:* print('Day {i+1}'), console.log('Day {i+1}')\n\n"
        f"Porer class pete /next likho"
    )

@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        kv_ok = "YES" if KV_URL and KV_TOKEN else "NO"
        return f"Py-JS Sentinel Running - KV:{kv_ok} - Time:{datetime.datetime.now()} - BOT:{'OK' if BOT_TOKEN else 'NO'}", 200

    update = request.get_json(force=True, silent=True) or {}
    message = update.get("message") or update.get("edited_message") or {}
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "") or ""
    from_id = str(message.get("from", {}).get("id", ""))

    if not chat_id:
        return "ok", 200

    # Save user list
    try:
        raw_users = kv_get("all_users") or "[]"
        all_users = json.loads(raw_users) if raw_users else []
    except:
        all_users = []
    if chat_id not in all_users:
        all_users.append(chat_id)
        kv_set("all_users", json.dumps(all_users))

    # progress
    prog_raw = kv_get(f"progress:{chat_id}")
    try:
        progress = int(prog_raw) if prog_raw is not None else 0
    except:
        progress = 0

    if text.startswith("/start"):
        kb = {
            "inline_keyboard": [
                [{"text": "📚 Next Class", "callback_data": "next"}],
                [{"text": "🤖 Ask AI", "callback_data": "ask"}]
            ]
        }
        tg_send(chat_id, f"🚀 *Welcome to Py-JS Sentinel*\n\n90 Days Python + JS Bootcamp\n\nTumar Progress: Day {progress}/90\n\nCommands:\n/start - restart\n/next - next class\n/ask <proshno> - AI ke jiges koro\n\nChannel: {CHANNEL_ID or 'Not set'}", kb)

    elif text.startswith("/next"):
        if progress >= 90:
            tg_send(chat_id, "🎉 *Congratulations!* 90 din complete! Tumi ekhon Python+JS e boss!")
        else:
            tg_send(chat_id, CLASSES_PY_JS[progress])
            kv_set(f"progress:{chat_id}", str(progress + 1))
            if CHANNEL_ID:
                try:
                    tg_send(CHANNEL_ID, f"User {chat_id} completed Day {progress+1}")
                except:
                    pass

    elif text.startswith("/broadcast") and from_id == ADMIN_ID:
        btext = text.replace("/broadcast", "").strip()
        if not btext:
            tg_send(chat_id, "Use: /broadcast tomar message")
        else:
            sent = 0
            for uid in all_users:
                tg_send(uid, f"📢 *Broadcast*\n\n{btext}")
                sent += 1
            tg_send(chat_id, f"Broadcast done to {sent} users")

    elif text.startswith("/ask"):
        q = text.replace("/ask", "").strip()
        if not q:
            tg_send(chat_id, "Likho: /ask Python loop ki?")
        else:
            ans = ask_gemini(q)
            tg_send(chat_id, ans)

    elif text.startswith("/users") and from_id == ADMIN_ID:
        tg_send(chat_id, f"Total users: {len(all_users)}\nKV: {KV_URL}\nList: {all_users[:20]}")

    else:
        # any normal message = AI
        if text:
            ans = ask_gemini(text)
            tg_send(chat_id, ans)

    return "ok", 200
