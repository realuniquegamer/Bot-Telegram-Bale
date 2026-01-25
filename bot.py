import os
import asyncio
import requests
import re  # <--- این ماژول برای تمیزکاری اضافه شد
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# دریافت اطلاعات سری
API_ID = int(os.environ["APP_ID"])
API_HASH = os.environ["APP_HASH"]
LOGIN_KEY = os.environ["LOGIN_KEY"]

# آدرس پل (Bridge)
BRIDGE_URL = 'https://kioto-osano-manager-bot.hf.space'

TARGET_CHANNELS = [
    '@Marambashi2', '@zedmodeonvpn', '@lightning6', 
    '@servergod2', '@TEHRANARGO', '@DirectVPN', '@prrofile_purple'
]

def log(msg):
    """تابع برای چاپ لاگ"""
    print(msg, flush=True)

def send_text_via_bridge(text):
    try:
        # ارسال متن تمیز شده بدون هیچ علامت اضافه
        requests.post(f"{BRIDGE_URL}/send_text", json={"text": text}, timeout=10)
        log("      ✅ Clean Config sent to Bale")
    except Exception as e:
        log(f"      ❌ Bridge Text Error: {e}")

def send_file_via_bridge(path):
    try:
        with open(path, 'rb') as f:
            files = {'file': f}
            # کپشن رو حذف کردیم که تبلیغات نیاد
            data = {'caption': ""} 
            requests.post(f"{BRIDGE_URL}/send_file", data=data, files=files, timeout=60)
        log("      ✅ File sent (No Caption)")
    except Exception as e:
        log(f"      ❌ Bridge File Error: {e}")

def extract_configs(text):
    """
    این تابع مثل الک عمل میکنه.
    متن رو میگیره و فقط کانفیگ های سالم رو میکشه بیرون.
    """
    if not text:
        return []
    
    # الگوی پیدا کردن کانفیگ‌ها (شروع با پروتکل، پایان با فاصله یا خط بعد)
    pattern = r'(vless|vmess|trojan|ss)://[\S]+'
    
    found_configs = re.findall(pattern, text)
    return found_configs

async def main():
    try:
        client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
        await client.start()
        
        # بررسی پیام‌های 20 دقیقه اخیر (یکم بیشتر گذاشتیم که چیزی جا نیفته)
        now = datetime.now(timezone.utc)
        time_limit = now - timedelta(minutes=20) 

        log(f"--- 🧹 Smart Bot Started at: {now.strftime('%H:%M')} ---")

        for ch in TARGET_CHANNELS:
            try:
                # log(f"👉 Scanning {ch}...") 
                
                msgs = await client.get_messages(ch, limit=15)
                found_count = 0
                
                for m in msgs:
                    # فقط پیام‌های جدید
                    if m.date > time_limit:
                        
                        # 1. اگر فایل بود (مثل .npvt)
                        if m.file:
                            # چک کردن حجم (زیر 20 مگ) و پسوند فایل
                            file_name = m.file.name if m.file.name else ""
                            allowed_exts = ['.npvt', '.napsternetv', '.apk', '.conf']
                            
                            # اگر پسوند فایل یکی از موارد بالا بود یا کلا فایل ناشناس بود
                            if m.file.size < 20 * 1024 * 1024: 
                                log(f"    ⬇️ Downloading File from {ch}")
                                path = await m.download_media()
                                send_file_via_bridge(path) # بدون کپشن ارسال میشه
                                os.remove(path)
                                found_count += 1

                        # 2. اگر متن بود (کانفیگ متنی)
                        elif m.text:
                            # استخراج کانفیگ‌های تمیز
                            clean_configs = extract_configs(m.text)
                            
                            if clean_configs:
                                log(f"    📝 Found {len(clean_configs)} valid configs in {ch}")
                                # کانفیگ‌ها رو با دو تا اینتر فاصله به هم می‌چسبونیم
                                final_message = "\n\n".join(clean_configs)
                                send_text_via_bridge(final_message)
                                found_count += 1
                    else:
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
