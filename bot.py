import os
import asyncio
import requests
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# دریافت اطلاعات سری از مخزن گیت‌هاب
API_ID = int(os.environ["APP_ID"])
API_HASH = os.environ["APP_HASH"]
LOGIN_KEY = os.environ["LOGIN_KEY"] # همون کلید ورود

# آدرس پل (Bridge) در هاگینگ فیس
BRIDGE_URL = 'https://kioto-osano-manager-bot.hf.space'

TARGET_CHANNELS = [
    '@Marambashi2', '@zedmodeonvpn', '@lightning6', 
    '@servergod2', '@TEHRANARGO', '@DirectVPN', '@prrofile_purple'
]

def send_text_via_bridge(text):
    try:
        requests.post(f"{BRIDGE_URL}/send_text", json={"text": text}, timeout=10)
        print("   ✅ Text sent to Bale via Bridge")
    except Exception as e:
        print(f"   ❌ Bridge Text Error: {e}")

def send_file_via_bridge(path, caption):
    try:
        with open(path, 'rb') as f:
            files = {'file': f}
            data = {'caption': caption}
            requests.post(f"{BRIDGE_URL}/send_file", data=data, files=files, timeout=60)
        print("   ✅ File sent to Bale via Bridge")
    except Exception as e:
        print(f"   ❌ Bridge File Error: {e}")

async def main():
    client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
    await client.start()
    
    # زمان الان به وقت جهانی (UTC)
    now = datetime.now(timezone.utc)
    # زمان ۱۵ دقیقه پیش
    time_limit = now - timedelta(minutes=16) # یک دقیقه احتیاط

    print(f"--- 🕒 Checking messages since: {time_limit.strftime('%H:%M:%S')} ---")

    for ch in TARGET_CHANNELS:
        try:
            # فقط پیام‌های جدیدتر از ۱۵ دقیقه پیش رو بگیر
            # limit=10 کافیه چون توی ۱۵ دقیقه بعیده بیشتر از ۱۰ تا پست بذارن
            msgs = await client.get_messages(ch, limit=10)
            
            for m in msgs:
                # چک کردن تاریخ پیام
                if m.date > time_limit:
                    keywords = ['vless://', 'vmess://', 'trojan://', 'ss://', 'napsternet', '.npvt']
                    
                    # اگر فایل بود
                    if m.file and m.file.size < 20 * 1024 * 1024:
                        print(f"⬇️ New File in {ch}")
                        path = await m.download_media()
                        caption = m.text or f"File from {ch}"
                        send_file_via_bridge(path, caption)
                        os.remove(path)
                    
                    # اگر متن (کانفیگ) بود
                    elif m.text and any(k in m.text.lower() for k in keywords):
                        print(f"📝 New Config in {ch}")
                        final_text = f"{m.text}\n\n🆔 {ch}"
                        send_text_via_bridge(final_text)
                else:
                    # چون پیام‌ها به ترتیب هستن، اگر به پیام قدیمی رسیدیم، بقیه هم قدیمی‌ن
                    break
                    
        except Exception as e:
            print(f"⚠️ Error checking {ch}: {e}")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
