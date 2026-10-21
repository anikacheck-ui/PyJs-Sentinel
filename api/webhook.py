import os, json, asyncio
from telegram import Update
from telegram.ext import Application
import google.generativeai as genai
from upstash_redis import Redis

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CHANNEL_ID = os.environ.get("CHANNEL_ID")

redis = Redis(url=os.environ.get("KV_REST_API_URL"), token=os.environ.get("KV_REST_API_TOKEN"))
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def handle(update: Update):
    if not update.message or not update.message.text:
        return
    uid = update.effective_user.id
    text = update.message.text.strip()

    # --- SECURITY: Tui chara keu /start dile IGNORE ---
    if uid != ADMIN_ID:
        if text.startswith("/"):
            return
        # Baki user der homework check
        prompt = f"Student bolse: {text}. Vul/sothik check kore Bangla te short e bolo."
        res = model.generate_content(prompt)
        await update.message.reply_text(res.text[:3500])
        return

    # --- ADMIN ONLY ---
    raw = redis.get("progress")
    progress = json.loads(raw) if raw else {"course":"python","class_no":0,"js_unlocked":False,"state":"learning"}

    if text == "/start":
        await update.message.reply_text(f"🔥 PyJS Sentinel Active!\nCourse: {progress['course']} Class: {progress['class_no']}\n/next - ekhoni class\n/test - test\n/reset - reset")
        return

    if text == "/reset":
        redis.set("progress", json.dumps({"course":"python","class_no":0,"js_unlocked":False,"state":"learning"}))
        await update.message.reply_text("Reset done.")
        return

    if progress.get("state") == "waiting_test":
        prompt = f"Python Test Answer: {text}. 100 te number dao. 70+ hole PASS - JS UNLOCKED, naile FAIL. Bangla te."
        res = model.generate_content(prompt)
        await update.message.reply_text(res.text)
        if "PASS" in res.text.upper():
            progress["js_unlocked"] = True
            progress["course"] = "javascript"
            progress["class_no"] = 0
            progress["state"] = "learning"
            redis.set("progress", json.dumps(progress))
            await update.message.reply_text("🚀 JS UNLOCKED! Kalke theke JS shuru!")
        else:
            progress["state"] = "learning"
            redis.set("progress", json.dumps(progress))
        return

    if text in ["/next", "/test"]:
        from .cron import run_lesson
        await run_lesson()
        await update.message.reply_text("Class pathalam!")

async def main_handler(body):
    app = Application.builder().token(BOT_TOKEN).build()
    update = Update.de_json(body, app.bot)
    await handle(update)

def handler(request):
    try:
        body = request.get_json()
    except:
        body = {}
    asyncio.run(main_handler(body))
    return {"statusCode": 200, "body": "ok"}
