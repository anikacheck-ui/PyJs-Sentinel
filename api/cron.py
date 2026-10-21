import os, json, asyncio
from telegram import Bot
import google.generativeai as genai
from upstash_redis import Redis

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
CHANNEL_ID = os.environ["CHANNEL_ID"]

redis = Redis(url=os.environ["KV_REST_API_URL"], token=os.environ["KV_REST_API_TOKEN"])
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def run_lesson():
    bot = Bot(token=BOT_TOKEN)
    raw = redis.get("progress")
    progress = json.loads(raw) if raw else {"course":"python","class_no":0,"js_unlocked":False,"state":"learning"}
    
    course = progress["course"]
    no = progress["class_no"]

    if course == "python" and no < 30:
        prompt = f"Python Zero to Hero Class {no+1} dao. Bangla+English mix, sohoj example, 2 ta homework. Shell basic o add koro majhe majhe."
        lesson = model.generate_content(prompt).text
        await bot.send_message(ADMIN_ID, f"📘 PYTHON CLASS {no+1}/30\n\n{lesson}")
        await bot.send_message(CHANNEL_ID, f"📘 PYTHON CLASS {no+1}/30\n\n{lesson}\n\n👇 Homework comment koro!")
        progress["class_no"] += 1
        redis.set("progress", json.dumps(progress))
        return

    if course == "python" and no >= 30 and not progress["js_unlocked"]:
        q = model.generate_content("Python er upor 1 ta MCQ + 1 ta coding challenge dao. Final test er moto.").text
        await bot.send_message(ADMIN_ID, f"⚠️ FINAL PYTHON TEST (70% lagbe JS unlock)\n\n{q}\n\nReply diye answer dao.")
        await bot.send_message(CHANNEL_ID, f"🧠 REVISION TEST\n\n{q}")
        progress["state"] = "waiting_test"
        redis.set("progress", json.dumps(progress))
        return

    if progress["js_unlocked"]:
        py_rev = model.generate_content("Python er 1 ta quick revision question dao.").text
        js_prompt = f"JavaScript Class {no+1} dao. Python er sathe compare kore bujhao. Bangla mix."
        js_lesson = model.generate_content(js_prompt).text
        full = f"🔁 PYTHON REVISION:\n{py_rev}\n\n---\n\n🚀 JAVASCRIPT CLASS {no+1}:\n{js_lesson}"
        await bot.send_message(ADMIN_ID, full)
        await bot.send_message(CHANNEL_ID, full)
        progress["class_no"] += 1
        progress["course"] = "javascript"
        redis.set("progress", json.dumps(progress))

def handler(request):
    asyncio.run(run_lesson())
    return {"statusCode": 200, "body": "ok"}
