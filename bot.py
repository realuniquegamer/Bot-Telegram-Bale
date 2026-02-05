import os
import asyncio
import requests
import re  # ماژول برای تمیزکاری متن
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- تنظیمات و دریافت اطلاعات سری ---
API_ID = int(os.environ["APP_ID"])
API_HASH = os.environ["APP_HASH"]
LOGIN_KEY = os.environ["LOGIN_KEY"]

# آدرس پل (Bridge) - همون آدرس جدیدی که ست کردیم
BRIDGE_URL = 'https://bahadorjadid-py-text-processor.hf.space'

# لیست کانال‌های هدف
TARGET_CHANNELS = [
    '@Marambashi2', '@zedmodeonvpn', '@lightning6', 
    '@servergod2', '@TEHRANARGO', '@DirectVPN', '@prrofile_purple'
]

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
    نسخه اصلاح شده و دقیق:
    1. لینک رو پیدا میکنه.
    2. علامت‌های مزاحم مثل ` و ' و " و پرانتز رو از تهش پاک میکنه.
    """
    if not text:
        return []
    
    # مرحله 1: پیدا کردن خام لینک‌ها
    pattern = r'(?:vless|vmess|trojan|ss)://[\S]+'
    raw_configs = re.findall(pattern, text)
    
    clean_list = []
    for conf in raw_configs:
        # مرحله 2: پاکسازی نهایی (Stripping)
        # هر چیزی که توی پرانتز پایین هست رو از اول و آخر لینک حذف میکنه
        clean_conf = conf.strip('`"\'()[]<>')
        clean_list.append(clean_conf)
        
    return clean_list

async def main():
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
                # گرفتن 15 پیام آخر کانال
                msgs = await client.get_messages(ch, limit=15)
                found_count = 0
                
                for m in msgs:
                    # فقط پیام‌هایی که جدیدتر از 20 دقیقه پیش هستند
                    if m.date > time_limit:
                        
                        # --- حالت اول: پیام فایل است (مثل .npvt) ---
                        if m.file:
                            # [اصلاح مهم]: اگر پیام عکس، ویدیو، ویس یا استیکر بود، کلا نادیده بگیر و رد شو
                            if getattr(m, 'photo', None) or getattr(m, 'video', None) or getattr(m, 'voice', None) or getattr(m, 'sticker', None):
                                continue

                            # چک کردن حجم (زیر 20 مگابایت)
                            if m.file.size < 20 * 1024 * 1024: 
                                # لیست پسوندهای مجاز
                                allowed_exts = ['.npvt', '.napsternetv', '.apk', '.conf']
                                file_name = m.file.name.lower() if m.file.name else ""

                                # شرط: فقط و فقط اگر پسوندش توی لیست بالا باشه دانلود میکنه
                                # (اون قسمت که فایل‌های بدون اسم رو دانلود میکرد حذف شد تا عکس‌ها قاطی نشن)
                                if file_name and any(file_name.endswith(ext) for ext in allowed_exts):
                                    log(f"    ⬇️ Downloading Config File from {ch}")
                                    path = await m.download_media()
                                    send_file_via_bridge(path)
                                    os.remove(path) # پاک کردن فایل از حافظه موقت
                                    found_count += 1
                                
                        # --- حالت دوم: پیام متنی است (لینک Vless/Vmess) ---
                        elif m.text:
                            # کانفیگ‌ها رو میکشیم بیرون و تمیز میکنیم
                            clean_configs = extract_configs(m.text)
                            
                            if clean_configs:
                                log(f"    📝 Found {len(clean_configs)} valid configs in {ch}")
                                # کانفیگ‌ها رو با دو خط فاصله به هم میچسبونیم
                                final_message = "\n\n".join(clean_configs)
                                send_text_via_bridge(final_message)
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

if __name__ == '__main__':
    asyncio.run(main())
