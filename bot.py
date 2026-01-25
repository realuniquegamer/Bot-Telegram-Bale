import os
import asyncio
import requests
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
    """تابع برای چاپ لاگ با flush که حتما نمایش داده بشه"""
    print(msg, flush=True)

def send_text_via_bridge(text):
    try:
        requests.post(f"{BRIDGE_URL}/send_text", json={"text": text}, timeout=10)
        log("      ✅ Text sent to Bale via Bridge")
    except Exception as e:
        log(f"      ❌ Bridge Text Error: {e}")

def send_file_via_bridge(path, caption):
    try:
        with open(path, 'rb') as f:
            files = {'file': f}
            data = {'caption': caption}
            requests.post(f"{BRIDGE_URL}/send_file", data=data, files=files, timeout=60)
        log("      ✅ File sent to Bale via Bridge")
    except Exception as e:
        log(f"      ❌ Bridge File Error: {e}")

async def main():
    try:
        client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
        await client.start()
        
        now = datetime.now(timezone.utc)
        time_limit = now - timedelta(minutes=16) 

        log(f"--- 🕒 Checking messages since: {time_limit.strftime('%H:%M:%S')} ---")

        for ch in TARGET_CHANNELS:
            try:
                log(f"👉 Checking {ch}...") # <--- این خط رو اضافه کردم که خیالت راحت شه
                
                msgs = await client.get_messages(ch, limit=10)
                found = False
                
                for m in msgs:
                    if m.date > time_limit:
                        keywords = ['vless://', 'vmess://', 'trojan://', 'ss://', 'napsternet', '.npvt']
                        
                        if m.file and m.file.size < 20 * 1024 * 1024:
                            log(f"   ⬇️ Found New File in {ch}")
                            path = await m.download_media()
                            caption = m.text or f"File from {ch}"
                            send_file_via_bridge(path, caption)
                            os.remove(path)
                            found = True
                        
                        elif m.text and any(k in m.text.lower() for k in keywords):
                            log(f"   📝 Found New Config in {ch}")
                            final_text = f"{m.text}\n\n🆔 {ch}"
                            send_text_via_bridge(final_text)
                            found = True
                    else:
                        break
                
                if not found:
                    log(f"   💤 No new messages in {ch}")

            except Exception as e:
                log(f"⚠️ Error checking {ch}: {e}")

        await client.disconnect()
        log("--- 🏁 Cycle Finished Successfully ---")
        
    except Exception as e:
        log(f"❌ CRITICAL ERROR: {e}")

if __name__ == '__main__':
    asyncio.run(main())
