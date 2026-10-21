import os
import json
import requests
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
KV_URL = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("STORAGE_URL") or os.getenv("KV_URL")
KV_TOKEN = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("STORAGE_TOKEN")

def kv_get(k):
    try:
        r = requests.get(f"{KV_URL}/get/{k}", headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=10)
        return r.json().get("result") if r.ok else None
    except:
        return None

def kv_set(k,v):
    try:
        requests.get(f"{KV_URL}/set/{k}/{v}", headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=10)
    except:
        pass

def send(cid, txt):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":txt,"parse_mode":"Markdown"}, timeout=15)
    except:
        pass

CLASSES = [f"*Day {i+1} Auto*\nPython+JS Task {i+1}\n/next diye poro" for i in range(90)]

@app.route("/api/cron", methods=["GET","POST"])
def cron_job():
    if not KV_URL or not KV_TOKEN:
        return "KV missing", 500
    raw = kv_get("all_users") or "[]"
    try:
        users = json.loads(raw)
    except:
        users = []
    sent = 0
    for cid in users:
        try:
            prog = int(kv_get(f"progress:{cid}") or 0)
            if prog < 90:
                send(cid, f"⏰ *Daily Auto Class - 8AM BD*\n\n{CLASSES[prog]}")
                kv_set(f"progress:{cid}", str(prog+1))
                sent += 1
        except:
            continue
    return f"Cron OK - Sent {sent}/{len(users)} users - KV:YES", 200
