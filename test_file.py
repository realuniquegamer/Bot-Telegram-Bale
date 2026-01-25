import os
import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession

# دریافت اطلاعات
API_ID = int(os.environ["APP_ID"])
API_HASH = os.environ["APP_HASH"]
LOGIN_KEY = os.environ["LOGIN_KEY"]
BRIDGE_URL = 'https://kioto-osano-manager-bot.hf.space'

# فقط همین کانال که فایل نپسترن داره
TARGET_CHANNEL = '@Marambashi2'

def log(msg):
    print(msg, flush=True)

def send_file_via_bridge(path, caption):
    try:
        log(f"      🚀 Sending {path} to Bridge...")
        with open(path, 'rb') as f:
            files = {'file': f}
            data = {'caption': caption}
            resp = requests.post(f"{BRIDGE_URL}/send_file", data=data, files=files, timeout=60)
        
        if resp.status_code == 200:
            log("      ✅ SUCCESS! File sent to Bale.")
        else:
            log(f"      ❌ Bridge Error: {resp.text}")
            
    except Exception as e:
        log(f"      ❌ Connection Error: {e}")

async def main():
    log("--- 🧪 STARTING FILE TEST ---")
    client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
    await client.start()
    
    log(f"👉 Looking for .npvt files in {TARGET_CHANNEL} (Checking last 50 messages)...")
    
    # 50 تا پیام آخر رو چک میکنه تا فایل پیدا کنه
    msgs = await client.get_messages(TARGET_CHANNEL, limit=50)
    
    found = False
    for m in msgs:
        # شرط: فایل باشه + اسمش با npvt تموم بشه
        if m.file and m.file.name and m.file.name.endswith('.npvt'):
            log(f"   ⬇️ Found Napsternet File: {m.file.name}")
            
            # دانلود
            path = await m.download_media()
            log(f"   📦 Downloaded ({os.path.getsize(path)} bytes). Uploading...")
            
            # ارسال
            caption = f"🧪 TEST FILE\n{m.file.name}"
            send_file_via_bridge(path, caption)
            
            # پاک کردن
            os.remove(path)
            found = True
            break # فقط یکی بفرست و تموم کن
            
    if not found:
        log("   ❌ No .npvt file found in last 50 messages.")

    await client.disconnect()
    log("--- 🏁 TEST FINISHED ---")

if __name__ == '__main__':
    asyncio.run(main())
