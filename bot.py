import os
import asyncio
import requests
import re  # ماژول برای تمیزکاری متن
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- تنظیمات و دریافت اطلاعات سری ---
# از get استفاده کردیم تا موقع روشن شدن اولیه سرور رندر، ارور نده
API_ID = int(os.environ.get("APP_ID", 0))
API_HASH = os.environ.get("APP_HASH", "")
LOGIN_KEY = os.environ.get("LOGIN_KEY", "")

# آدرس پل (Bridge) - همون آدرس جدیدی که ست کردیم
BRIDGE_URL = 'https://bahadorjadid-py-text-processor.hf.space'

# لیست کانال‌های هدف
TARGET_CHANNELS = [
    '@Marambashi2', '@zedmodeonvpn', '@lightning6', 
    '@servergod2', '@TEHRANARGO', '@DirectVPN', '@prrofile_purple', '@Gp_config'
]

# ساخت اپلیکیشن وب برای رندر
app = Flask(__name__)

def log(msg):
    """تابع برای چاپ لاگ در کنسول"""
    print(msg, flush=True)

def send_text_via_bridge(text):
    """ارسال متن کانفیگ به بله (بدون هیچ حاشیه و تبلیغات)"""
    try:
        requests.post(f"{BRIDGE_URL}/send_text", json={"text": text}, timeout=10)
        log("      ✅ Clean Config sent to Bale")
    except Exception as e:
        log(f"      ❌ Bridge Text Error: {e}")

def send_file_via_bridge(path):
    """ارسال فایل کانفیگ به بله (بدون کپشن و تبلیغات)"""
    try:
        with open(path, 'rb') as f:
            files = {'file': f}
            # این خط خالی باعث میشه هیچ متنی زیر فایل نیاد
            data = {'caption': ""} 
            requests.post(f"{BRIDGE_URL}/send_file", data=data, files=files, timeout=60)
        log("      ✅ File sent (No Caption)")
    except Exception as e:
        log(f"      ❌ Bridge File Error: {e}")

def extract_configs(text):
    """
    نسخه ارتقا یافته: پیدا کردن کانفیگ‌های V2Ray + پراکسی‌های تلگرام
    1. لینک رو پیدا میکنه.
    2. علامت‌های مزاحم رو از تهش پاک میکنه.
    """
    if not text:
        return []
    
    # پترن اول: کانفیگ‌های Vless, Vmess, Trojan, SS
    pattern_vpn = r'(?:vless|vmess|trojan|ss)://[\S]+'
    
    # پترن دوم: پراکسی‌های مخصوص خود تلگرام (هم t.me و هم tg://)
    pattern_proxy = r'(?:https?://t\.me/proxy\?|tg://proxy\?)[\S]+'
    
    # ترکیب هر دو پترن برای شکار تمام لینک‌ها
    raw_configs = re.findall(f'{pattern_vpn}|{pattern_proxy}', text)
    
    clean_list = []
    for conf in raw_configs:
        # مرحله 2: پاکسازی نهایی (Stripping)
        # هر چیزی که توی پرانتز پایین هست رو از اول و آخر لینک حذف میکنه
        clean_conf = conf.strip('`"\'()[]<>')
        clean_list.append(clean_conf)
        
    return clean_list

async def main_bot_logic():
    """این همون تابع main قبلی خودته که اسمش رو عوض کردیم تا با وب‌سرور قاطی نشه"""
    try:
        # اتصال به تلگرام
        client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
        await client.start()
        
        # تایم چک کردن: 20 دقیقه اخیر
        now = datetime.now(timezone.utc)
        time_limit = now - timedelta(minutes=20) 

        log(f"--- 🧹 Smart Bot Started at: {now.strftime('%H:%M')} ---")

        for ch in TARGET_CHANNELS:
            try:
                # گرفتن 200 پیام آخر برای گروه‌های شلوغ
                msgs = await client.get_messages(ch, limit=200)
                found_count = 0
                
                for m in msgs:
                    # فقط پیام‌هایی که جدیدتر از 20 دقیقه پیش هستند
                    if m.date > time_limit:
                        
                        # --- اول چک کردن متن (حتی اگر پیام عکس دار باشه کپشنش رو می‌خونه) ---
                        # این بخش از elif خارج شد تا اگر پیام هم عکس داشت هم متن، متن جا نیفته
                        if m.text:
                            # کانفیگ‌ها و پراکسی‌ها رو میکشیم بیرون
                            clean_configs = extract_configs(m.text)
                            
                            if clean_configs:
                                log(f"    📝 Found {len(clean_configs)} valid configs/proxies in {ch}")
                                # کانفیگ‌ها رو با دو خط فاصله به هم میچسبونیم
                                final_message = "\n\n".join(clean_configs)
                                send_text_via_bridge(final_message)
                                found_count += 1

                        # --- دوم چک کردن فایل دانلودی ---
                        if m.file:
                            # [اصلاح مهم]: اگر پیام عکس، ویدیو، ویس یا استیکر بود، کلا فایلش رو دانلود نکن
                            if not (getattr(m, 'photo', None) or getattr(m, 'video', None) or getattr(m, 'voice', None) or getattr(m, 'sticker', None)):
                                # چک کردن حجم (زیر 20 مگابایت)
                                if m.file.size < 20 * 1024 * 1024: 
                                    # لیست پسوندهای مجاز
                                    allowed_exts = ['.npvt', '.napsternetv', '.apk', '.conf']
                                    file_name = m.file.name.lower() if m.file.name else ""

                                    # شرط: فقط و فقط اگر پسوندش توی لیست بالا باشه دانلود میکنه
                                    if file_name and any(file_name.endswith(ext) for ext in allowed_exts):
                                        log(f"    ⬇️ Downloading Config File from {ch}")
                                        path = await m.download_media()
                                        send_file_via_bridge(path)
                                        os.remove(path) # پاک کردن فایل از حافظه موقت
                                        found_count += 1
                    else:
                        # اگر به پیام‌های قدیمی رسیدیم، دیگه ادامه نده
                        break
                
                if found_count > 0:
                    log(f"    ✅ Processed {found_count} items from {ch}")

            except Exception as e:
                log(f"⚠️ Error checking {ch}: {e}")

        await client.disconnect()
        log("--- 🏁 Cycle Finished ---")
        
    except Exception as e:
        log(f"❌ CRITICAL ERROR: {e}")

def start_background_loop():
    """این تابع ربات رو تو پس‌زمینه اجرا می‌کنه تا سرور قفل نکنه"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_bot_logic())
    loop.close()

@app.route('/')
def home():
    """آدرس اصلی که نشون میده ربات روشنه"""
    return "VPN Bot is Alive and running on Render!"

@app.route('/run')
def trigger():
    """هر بار سایت کرون‌جاب این آدرس رو باز کنه، ربات یک دور کارش رو انجام میده"""
    # کلمه daemon=True اضافه شد تا به محض دریافت دستور، به کرون‌جاب اوکی بده و قطع کنه
    Thread(target=start_background_loop, daemon=True).start()
    return "Triggered bot successfully!", 200

if __name__ == '__main__':
    # پورت رو رندر خودش مشخص می‌کنه، اگر نبود 10000 میذاریم
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
