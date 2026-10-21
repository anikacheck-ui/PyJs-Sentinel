from flask import Flask, request
import os, json, asyncio
from telegram import Update
from telegram.ext import Application
import google.generativeai as genai
from upstash_redis import Redis

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CHANNEL_ID = os.environ.get("CHANNEL_ID")

redis = Redis(url=os.environ.get("KV_REST_API_URL"), token=os.environ.get("KV_REST_API_TOKEN"))
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def handle_logic(update: Update):
    if not update.message or not update.message.text:
        return
    uid = update.effective_user.id
    text = update.message.text.strip()
    if uid != ADMIN_ID and text.startswith("/"):
        return
    if uid != ADMIN_ID:
        res = model.generate_content(f"Student: {text}. Check in Bangla short.")
        await update.message.reply_text(res.text[:3500])
        return
    # admin
    raw = redis.get("progress")
    progress = json.loads(raw) if raw else {"course":"python","class_no":0,"js_unlocked":False,"state":"learning"}
    if text == "/start":
        await update.message.reply_text(f"PyJS Sentinel Active! Class {progress['class_no']}")
        return
    if text == "/reset":
        redis.set("progress", json.dumps({"course":"python","class_no":0,"js_unlocked":False,"state":"learning"}))
        await update.message.reply_text("Reset done")
        return
    if progress.get("state") == "waiting_test":
        res = model.generate_content(f"Test answer {text}. 70+ hole PASS else FAIL. Bangla.")
        await update.message.reply_text(res.text)
        if "PASS" in res.text.upper():
            progress.update({"js_unlocked":True,"course":"javascript","class_no":0,"state":"learning"})
            redis.set("progress", json.dumps(progress))
        return
    if text in ["/next","/test"]:
        from api.cron import run_lesson
        await run_lesson()

@app.route('/api/index', methods=['POST'])
@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    async def run():
        app_bot = Application.builder().token(BOT_TOKEN).build()
        update = Update.de_json(data, app_bot.bot)
        await handle_logic(update)
    asyncio.run(run())
    return "ok"

@app.route('/api/index', methods=['GET'])
def home():
    return "PyJS Sentinel Running"
