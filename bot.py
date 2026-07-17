import os
import json
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaWebPage
from flask import Flask
from threading import Thread, Lock

# --- تنظیمات و دریافت اطلاعات ---
API_ID = int(os.environ.get("APP_ID", 0))
API_HASH = os.environ.get("APP_HASH", "")
LOGIN_KEY = os.environ.get("LOGIN_KEY", "")

# کانال مقصد
MY_CHANNEL = '@Hame_Yeja'

TARGET_CHANNELS = [
    '@Skyportall', '@ultrasurf_12', '@GuessWhaat', '@Do1rcci',
    '@JynMarket', '@crayingroom', '@IDeathBirth', '@RezZonez',
    '@SPIDER_CONFIG', '@saministamm', '@xixv2ray', '@Configir98',
    '@Begoo_VPN', '@zedmodeonvpn', '@prrofile_purple', '@DirectVPN',
    '@marambashi2', '@TEHRANARGO', '@lightning6', '@servergod2',
    '@EfixVPN', '@tasiyanc', '@mitivpn',
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
        client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
        await client.start()
        
        db = load_db()
        seen_hashes = db.get('seen_hashes', [])
        
        now = datetime.now(timezone.utc)
        fallback_limit = now - timedelta(minutes=10)

        log(f"--- 🚀 Ultimate Perfect Shoveling Started at: {now.strftime('%H:%M')} ---")

        for ch in TARGET_CHANNELS:
            try:
                try:
                    entity = await client.get_entity(ch)
                except Exception as e:
                    log(f"⚠️ نمی‌توانم اطلاعات {ch} را بگیرم: {e}")
                    continue

                if getattr(entity, 'broadcast', None) is not True:
                    continue
                
                channel_title = getattr(entity, 'title', ch)
                msgs = await client.get_messages(entity, limit=50)
                last_processed_id = db.get(ch, 0)
                max_id_this_run = last_processed_id
                
                for m in reversed(msgs):
                    if m.id <= last_processed_id: continue
                    if last_processed_id == 0 and m.date < fallback_limit: continue
                    
                    msg_text = m.message or ""
                    text_hash = None
                    
                    if msg_text:
                        text_hash = hashlib.sha256(msg_text.encode('utf-8')).hexdigest()
                        if text_hash in seen_hashes:
                            if m.id > max_id_this_run: max_id_this_run = m.id
                            continue
                    
                    try:
                        # بررسی: اگر مدیا هست و "وب‌پیج" نیست (یعنی فایل واقعیه)
                        if m.media and not isinstance(m.media, MessageMediaWebPage):
                            log(f"🖼️/📁 انتقال مدیا از {channel_title}")
                            await client.send_message(
                                MY_CHANNEL,
                                msg_text,
                                file=m.media,
                                formatting_entities=m.entities,
                                parse_mode=None,
                                link_preview=False
                            )
                            await asyncio.sleep(2) 
                        
                        # اگر فقط متنه (یا مدیا بوده ولی فقط لینک پیش‌نمایشه)
                        elif msg_text:
                            log(f"📝 انتقال متن از {channel_title}")
                            await client.send_message(
                                MY_CHANNEL,
                                msg_text,
                                formatting_entities=m.entities,
                                parse_mode=None,
                                link_preview=False
                            )
                            await asyncio.sleep(2) 
                        
                        if text_hash:
                            seen_hashes.append(text_hash)
                            if len(seen_hashes) > 5000:
                                seen_hashes = seen_hashes[-5000:]
                                
                    except Exception as e:
                        log(f"⚠️ خطا در ارسال پیام {m.id} از {ch}: {e}")
                    
                    if m.id > max_id_this_run: max_id_this_run = m.id

                db[ch] = max_id_this_run
            except Exception as e:
                log(f"⚠️ خطای کلی در پردازش آیدی {ch}: {e}")

        db['seen_hashes'] = seen_hashes
        save_db(db)
        await client.disconnect()
        log("--- 🏁 Perfect Cycle Finished Successfully ---")
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
def home(): return "Telegram Ultimate Perfect Shovel Bot is Active!"

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
