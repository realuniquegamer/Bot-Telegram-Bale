import os
import json
import asyncio
import requests
import re
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread, Lock

# --- تنظیمات و دریافت اطلاعات سری ---
API_ID = int(os.environ.get("APP_ID", 0))
API_HASH = os.environ.get("APP_HASH", "")
LOGIN_KEY = os.environ.get("LOGIN_KEY", "")

# آدرس پل در هاگینگ فیس
BRIDGE_URL = 'https://bahadorjadid-py-text-processor.hf.space'

# لیست ۲۰ کانال جدید و قدیمی تو
TARGET_CHANNELS = [
    '@Skyportall', '@ultrasurf_12', '@GuessWhaat', '@Do1rcci',
    '@JynMarket', '@crayingroom', '@IDeathBirth', '@RezZonez',
    '@SPIDER_CONFIG', '@saministamm', '@xixv2ray', '@Configir98',
    '@Begoo_VPN', '@zedmodeonvpn', '@prrofile_purple', '@DirectVPN',
    '@marambashi2', '@TEHRANARGO', '@lightning6', '@servergod2'
]

DB_FILE = 'last_processed_ids.json'
app = Flask(__name__)
is_bot_running = False
lock = Lock()

def log(msg):
    print(msg, flush=True)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except Exception: return {}
    return {}

def save_db(data):
    try:
        with open(DB_FILE, 'w') as f: json.dump(data, f)
    except Exception as e: log(f"⚠️ DB Save Error: {e}")

def send_text_via_bridge(text):
    try:
        # زمان انتظار از ۱۵ به ۶۰ ثانیه افزایش یافت
        requests.post(f"{BRIDGE_URL}/send_text", json={"text": text}, timeout=60)
        log("      ✅ Text sent to Bale")
    except Exception as e: log(f"      ❌ Bridge Text Error: {e}")

def send_file_via_bridge(path, caption=""):
    try:
        with open(path, 'rb') as f:
            files = {'file': f}
            data = {'caption': caption}
            # زمان انتظار از ۶۰ به ۱۲۰ ثانیه افزایش یافت
            requests.post(f"{BRIDGE_URL}/send_file", data=data, files=files, timeout=120)
        log("      ✅ File sent to Bale")
    except Exception as e: log(f"      ❌ Bridge File Error: {e}")

async def main_bot_logic():
    try:
        client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
        await client.start()
        db = load_db()
        now = datetime.now(timezone.utc)
        fallback_limit = now - timedelta(minutes=10) # در اولین اجرا فقط ۱۰ دقیقه اخیر رو بگیر

        log(f"--- 🚀 Shoveling Started at: {now.strftime('%H:%M')} ---")

        for ch in TARGET_CHANNELS:
            try:
                msgs = await client.get_messages(ch, limit=50)
                last_processed_id = db.get(ch, 0)
                max_id_this_run = last_processed_id
                
                # بررسی پیام‌ها از قدیمی به جدید
                for m in reversed(msgs):
                    if m.id <= last_processed_id: continue
                    if last_processed_id == 0 and m.date < fallback_limit: continue
                    
                    # ۱. ارسال متن (هر متنی که وجود داشته باشه رو می‌فرستیم - بدون فیلتر)
                    if m.text and len(m.text.strip()) > 5:
                        log(f"    📝 Forwarding text from {ch}")
                        send_text_via_bridge(m.text)

                    # ۲. ارسال فایل (کانفیگ‌ها و فایل‌های اجرایی)
                    if m.file:
                        file_name = m.file.name.lower() if m.file.name else ""
                        allowed_exts = ['.npvt', '.napsternetv', '.apk', '.conf', '.txt', '.json']
                        if any(file_name.endswith(ext) for ext in allowed_exts):
                            log(f"    ⬇️ Downloading file from {ch}")
                            path = await m.download_media()
                            send_file_via_bridge(path, m.text or "")
                            if os.path.exists(path): os.remove(path)
                    
                    if m.id > max_id_this_run: max_id_this_run = m.id

                db[ch] = max_id_this_run
            except Exception as e:
                log(f"⚠️ Error in channel {ch}: {e}")

        save_db(db)
        await client.disconnect()
        log("--- 🏁 Cycle Finished ---")
    except Exception as e:
        log(f"❌ CRITICAL: {e}")

def start_background_loop():
    global is_bot_running
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_bot_logic())
        loop.close()
    finally:
        with lock: is_bot_running = False

@app.route('/')
def home(): return "Bot is Active!"

@app.route('/run')
def trigger():
    global is_bot_running
    with lock:
        if is_bot_running: return "Already running", 200
        is_bot_running = True
    Thread(target=start_background_loop, daemon=True).start()
    return "Triggered!", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
