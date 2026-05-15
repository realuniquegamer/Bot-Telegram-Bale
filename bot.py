import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread, Lock

# --- تنظیمات و دریافت اطلاعات از رندر ---
API_ID = int(os.environ.get("APP_ID", 0))
API_HASH = os.environ.get("APP_HASH", "")
LOGIN_KEY = os.environ.get("LOGIN_KEY", "")

# کانال مقصد تو
MY_CHANNEL = '@Hame_Yeja'

# لیست یکپارچه و بدون تکرار کانال‌های منبع (۳۲ کانال)
TARGET_CHANNELS = [
    '@Skyportall', '@ultrasurf_12', '@GuessWhaat', '@Do1rcci',
    '@JynMarket', '@crayingroom', '@IDeathBirth', '@RezZonez',
    '@SPIDER_CONFIG', '@saministamm', '@xixv2ray', '@Configir98',
    '@Begoo_VPN', '@zedmodeonvpn', '@prrofile_purple', '@DirectVPN',
    '@marambashi2', '@TEHRANARGO', '@lightning6', '@servergod2',
    '@madzteam', '@EfixVPN', '@tasiyanc', '@mitivpn',
    '@v2rayng_proxymelli', '@ConfigX2ray', '@netmelli15', '@appxa',
    '@Config_HATunnel', '@khabari', '@Spotify_Porteghali', '@ironpv'
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

async def main_bot_logic():
    try:
        # اتصال مستقیم به تلگرام
        client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
        await client.start()
        
        db = load_db()
        now = datetime.now(timezone.utc)
        # در اولین اجرا، پیام‌های ۱۰ دقیقه اخیر را بررسی می‌کند
        fallback_limit = now - timedelta(minutes=10)

        log(f"--- 🚀 Ultimate Shoveling Started at: {now.strftime('%H:%M')} ---")

        for ch in TARGET_CHANNELS:
            try:
                # گرفتن ۵۰ پیام اخیر از هر کانال
                msgs = await client.get_messages(ch, limit=50)
                last_processed_id = db.get(ch, 0)
                max_id_this_run = last_processed_id
                
                # بررسی پیام‌ها از قدیمی به جدید
                for m in reversed(msgs):
                    if m.id <= last_processed_id: continue
                    if last_processed_id == 0 and m.date < fallback_limit: continue
                    
                    try:
                        # اگر پیام دارای هرگونه مدیا باشد (عکس، ویدئو، فایل کانفیگ، ویس و...)
                        if m.media:
                            log(f"🖼️/📁 Transferring media/file from {ch} to {MY_CHANNEL}")
                            # فایل به همراه متن زیرش (کپشن) ارسال می‌شود
                            await client.send_file(MY_CHANNEL, m.media, caption=m.text or "")
                        
                        # اگر پیام فقط یک متن ساده باشد
                        elif m.text:
                            log(f"📝 Forwarding text from {ch} to {MY_CHANNEL}")
                            await client.send_message(MY_CHANNEL, m.text)
                    
                    except Exception as e:
                        log(f"⚠️ Failed to send a specific message from {ch}: {e}")
                    
                    # آپدیت کردن آیدی پیام برای جلوگیری از ارسال تکراری در دفعات بعد
                    if m.id > max_id_this_run: max_id_this_run = m.id

                db[ch] = max_id_this_run
            except Exception as e:
                log(f"⚠️ Error in channel {ch}: {e}")

        save_db(db)
        await client.disconnect()
        log("--- 🏁 Cycle Finished Successfully ---")
    except Exception as e:
        log(f"❌ CRITICAL ERROR: {e}")

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
def home(): return "Telegram Ultimate Shovel Bot is Active!"

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
