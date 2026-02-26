import os
import json
import asyncio
import requests
import re  # ماژول برای تمیزکاری متن
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread, Lock

# --- تنظیمات و دریافت اطلاعات سری ---
API_ID = int(os.environ.get("APP_ID", 0))
API_HASH = os.environ.get("APP_HASH", "")
LOGIN_KEY = os.environ.get("LOGIN_KEY", "")

BRIDGE_URL = 'https://bahadorjadid-py-text-processor.hf.space'

TARGET_CHANNELS = [
    '@Marambashi2', '@zedmodeonvpn', '@lightning6', 
    '@servergod2', '@TEHRANARGO', '@DirectVPN', '@prrofile_purple', '@Gp_config'
]

# فایل دیتابیس برای ذخیره آیدی پیام‌ها
DB_FILE = 'last_processed_ids.json'

app = Flask(__name__)

# --- قفل ضد تداخل برای کرون جاب ---
is_bot_running = False
lock = Lock()

def log(msg):
    """تابع برای چاپ لاگ در کنسول"""
    print(msg, flush=True)

def load_db():
    """خواندن آخرین آیدی‌های پردازش شده از دیتابیس"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    """ذخیره آیدی‌های جدید در دیتابیس"""
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        log(f"⚠️ DB Save Error: {e}")

def send_text_via_bridge(text):
    """ارسال متن کانفیگ به بله"""
    try:
        requests.post(f"{BRIDGE_URL}/send_text", json={"text": text}, timeout=10)
        log("      ✅ Clean Config sent to Bale")
    except Exception as e:
        log(f"      ❌ Bridge Text Error: {e}")

def send_file_via_bridge(path):
    """ارسال فایل کانفیگ به بله"""
    try:
        with open(path, 'rb') as f:
            files = {'file': f}
            data = {'caption': ""} 
            requests.post(f"{BRIDGE_URL}/send_file", data=data, files=files, timeout=60)
        log("      ✅ File sent (No Caption)")
    except Exception as e:
        log(f"      ❌ Bridge File Error: {e}")

def extract_configs(text):
    """پیدا کردن کانفیگ‌های V2Ray + پراکسی‌های تلگرام و پاکسازی"""
    if not text:
        return []
    
    pattern_vpn = r'(?:vless|vmess|trojan|ss)://[\S]+'
    pattern_proxy = r'(?:https?://t\.me/proxy\?|tg://proxy\?)[\S]+'
    raw_configs = re.findall(f'{pattern_vpn}|{pattern_proxy}', text)
    
    clean_list = []
    for conf in raw_configs:
        clean_conf = conf.strip('`"\'()[]<>')
        clean_list.append(clean_conf)
        
    return clean_list

async def main_bot_logic():
    try:
        client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
        await client.start()
        
        # لود کردن حافظه ربات
        db = load_db()
        
        # زمان جایگزین: اگر دیتابیس خالی بود (مثلا دفعه اول)، فقط 15 دقیقه اخیر رو چک کن 
        # تا یهو پیام‌های قدیمی رو رگباری نفرسته تو گروه
        now = datetime.now(timezone.utc)
        fallback_limit = now - timedelta(minutes=15) 

        log(f"--- 🧹 Smart Bot Started at: {now.strftime('%H:%M')} ---")

        for ch in TARGET_CHANNELS:
            try:
                # گرفتن 400 پیام آخر (ظرفیت بیشتر برای احتیاط)
                msgs = await client.get_messages(ch, limit=400)
                found_count = 0
                
                # خواندن آخرین آیدی پردازش شده این کانال
                last_processed_id = db.get(ch, 0)
                max_id_this_run = last_processed_id
                
                # 🔴 پیام‌ها از قدیمی به جدید بررسی می‌شوند 🔴
                for m in reversed(msgs):
                    
                    # اگر پیام رو قبلا خوندیم، ردش کن
                    if m.id <= last_processed_id:
                        continue
                    
                    # جلوگیری از ارسال پیام‌های خیلی قدیمی در اجرای اول (وقتی دیتابیس خالیه)
                    if last_processed_id == 0 and m.date < fallback_limit:
                        continue
                    
                    # --- 1. چک کردن متن ---
                    if m.text:
                        clean_configs = extract_configs(m.text)
                        if clean_configs:
                            log(f"    📝 Found {len(clean_configs)} valid configs/proxies in {ch}")
                            final_message = "\n\n".join(clean_configs)
                            send_text_via_bridge(final_message)
                            found_count += 1

                    # --- 2. چک کردن فایل ---
                    if m.file:
                        if not (getattr(m, 'photo', None) or getattr(m, 'video', None) or getattr(m, 'voice', None) or getattr(m, 'sticker', None)):
                            if m.file.size < 20 * 1024 * 1024: 
                                allowed_exts = ['.npvt', '.napsternetv', '.apk', '.conf']
                                file_name = m.file.name.lower() if m.file.name else ""

                                if file_name and any(file_name.endswith(ext) for ext in allowed_exts):
                                    log(f"    ⬇️ Downloading Config File from {ch}")
                                    path = await m.download_media()
                                    send_file_via_bridge(path)
                                    os.remove(path)
                                    found_count += 1
                
                    # آپدیت کردن بزرگترین آیدی که با موفقیت بررسی شد
                    if m.id > max_id_this_run:
                        max_id_this_run = m.id

                # ذخیره آخرین آیدی این کانال در حافظه
                db[ch] = max_id_this_run
                
                if found_count > 0:
                    log(f"    ✅ Processed {found_count} items from {ch}")

            except Exception as e:
                log(f"⚠️ Error checking {ch}: {e}")

        # سیو کردن نهایی دیتابیس
        save_db(db)
        
        await client.disconnect()
        log("--- 🏁 Cycle Finished ---")
        
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
        # وقتی کار ربات تموم شد، قفل رو باز می‌کنه
        with lock:
            is_bot_running = False

@app.route('/')
def home():
    return "VPN Bot is Alive and running on Render!"

@app.route('/run')
def trigger():
    global is_bot_running
    
    with lock:
        # اگر ربات در حال اجرا باشه، دستور کرون جاب رو با احترام رد می‌کنه تا تداخل پیش نیاد
        if is_bot_running:
            return "Bot is already running. Skipped this trigger to prevent overlap.", 200
        
        # اگر آزاد بود، قفل رو فعال می‌کنه و ربات رو استارت می‌زنه
        is_bot_running = True
        
    Thread(target=start_background_loop, daemon=True).start()
    return "Triggered bot successfully!", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
