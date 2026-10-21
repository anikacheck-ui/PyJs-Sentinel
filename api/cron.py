from flask import Flask
import os, json, asyncio
from telegram import Bot
import google.generativeai as genai
from upstash_redis import Redis

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
CHANNEL_ID = os.environ["CHANNEL_ID"]

redis = Redis(url=os.environ.get("KV_REST_API_URL"), token=os.environ.get("KV_REST_API_TOKEN"))
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def run_lesson():
    bot = Bot(token=BOT_TOKEN)
    raw = redis.get("progress")
    progress = json.loads(raw) if raw else {"course":"python","class_no":0,"js_unlocked":False,"state":"learning"}
    no = progress["class_no"]
    if progress["course"] == "python" and no < 30:
        lesson = model.generate_content(f"Python Class {no+1} Bangla mix").text
        await bot.send_message(ADMIN_ID, f"PYTHON {no+1}/30\n{lesson}")
        await bot.send_message(CHANNEL_ID, f"PYTHON {no+1}/30\n{lesson}")
        progress["class_no"] += 1
        redis.set("progress", json.dumps(progress))
        return
    if progress["course"] == "python" and no >= 30 and not progress["js_unlocked"]:
        q = model.generate_content("Python MCQ + coding test").text
        await bot.send_message(ADMIN_ID, f"FINAL TEST\n{q}")
        progress["state"] = "waiting_test"
        redis.set("progress", json.dumps(progress))
        return
    if progress["js_unlocked"]:
        js = model.generate_content(f"JS Class {no+1} Python er sathe compare").text
        await bot.send_message(ADMIN_ID, js)
        await bot.send_message(CHANNEL_ID, js)
        progress["class_no"] += 1
        redis.set("progress", json.dumps(progress))

@app.route('/api/cron', methods=['GET'])
def cron():
    asyncio.run(run_lesson())
    return "cron ok"
