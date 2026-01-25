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

# آدرس پل (Bridge)
BRIDGE_URL = 'https://kioto-osano-manager-bot.hf.space'

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
    مهم‌ترین بخش: استخراج هوشمند لینک‌ها
    این تابع متن رو میگرده و فقط لینک‌های سالم رو در میاره.
    """
    if not text:
        return []
    
    # --- فیکس نهایی ---
    # عبارت (?:...) یعنی "این بخش رو پیدا کن ولی به عنوان نتیجه جداگانه برنگردون"
    # این باعث میشه کل لینک (شامل پروتکل و بقیه آدرس) انتخاب بشه
    pattern = r'(?:vless|vmess|trojan|ss)://[\S]+'
    
    # پیدا کردن تمام موارد مطابق الگو
    found_configs = re.findall(pattern, text)
    return found_configs

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
                            # چک کردن حجم (زیر 20 مگابایت)
                            if m.file.size < 20 * 1024 * 1024: 
                                # لیست پسوندهای مجاز
                                allowed_exts = ['.npvt', '.napsternetv', '.apk', '.conf']
                                file_name = m.file.name.lower() if m.file.name else ""

                                # شرط: یا پسوندش توی لیست باشه، یا کلا فایل ناشناس باشه (ریسک کم)
                                # معمولا کانال‌ها فایل‌های نامربوط کم میذارن، ولی این فیلتر خوبیه
                                if file_name and any(file_name.endswith(ext) for ext in allowed_exts):
                                    log(f"    ⬇️ Downloading Config File from {ch}")
                                    path = await m.download_media()
                                    send_file_via_bridge(path)
                                    os.remove(path) # پاک کردن فایل از حافظه موقت
                                    found_count += 1
                                # اگر فایل اسم نداشت ولی کوچیک بود هم میگیریم (محض احتیاط)
                                elif not file_name:
                                     log(f"    ⬇️ Downloading Unnamed File from {ch}")
                                     path = await m.download_media()
                                     send_file_via_bridge(path)
                                     os.remove(path)
                                     found_count += 1

                        # --- حالت دوم: پیام متنی است (لینک Vless/Vmess) ---
                        elif m.text:
                            # کانفیگ‌ها رو میکشیم بیرون
                            clean_configs = extract_configs(m.text)
                            
                            if clean_configs:
                                log(f"    📝 Found {len(clean_configs)} valid configs in {ch}")
                                # کانفیگ‌ها رو با دو خط فاصله به هم میچسبونیم که قاتی نشن
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
