import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- تنظیمات (از Secrets گیت‌هاب خونده می‌شن) ---
API_ID = int(os.environ.get("APP_ID", 0))
API_HASH = os.environ.get("APP_HASH", "")
LOGIN_KEY = os.environ.get("LOGIN_KEY", "")

# کانال مقصد
MY_CHANNEL = '@Hame_Yeja'

# لیست کانال‌های منبع
TARGET_CHANNELS = [
    '@JynMarket',
    '@xixv2ray', '@Configir98',
    '@Begoo_VPN', '@zedmodeonvpn', '@prrofile_purple', '@DirectVPN',
    '@marambashi2', '@TEHRANARGO', '@lightning6', '@servergod2',
    '@mitivpn',
    '@v2rayng_proxymelli', '@ConfigX2ray', '@netmelli15', '@appxa',
    '@khabari', '@Spotify_Porteghali', '@ironpv', '@irMARTIN', '@Gp_config',
    '@Frenpv'
]

DB_FILE = 'last_processed_ids.json'


def log(msg):
    print(msg, flush=True)


def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_db(data):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        log(f"⚠️ DB Save Error: {e}")


async def main_bot_logic():
    client = TelegramClient(StringSession(LOGIN_KEY), API_ID, API_HASH)
    await client.start()

    db = load_db()
    now = datetime.now(timezone.utc)
    # فقط برای اولین اجرای یک کانال (وقتی هنوز سابقه‌ای ازش نداریم)
    fallback_limit = now - timedelta(minutes=15)

    log(f"--- 🚀 Run started at: {now.strftime('%Y-%m-%d %H:%M')} UTC ---")

    for ch in TARGET_CHANNELS:
        try:
            try:
                entity = await client.get_entity(ch)
            except Exception as e:
                log(f"⚠️ نمی‌توانم اطلاعات {ch} را بگیرم: {e}")
                continue

            if getattr(entity, 'broadcast', None) is not True:
                log(f"🚫 {ch} کانال نیست (احتمالا گروهه)، رد شد.")
                continue

            channel_title = getattr(entity, 'title', ch)
            channel_id = getattr(entity, 'id', 'Unknown')
            log(f"🔍 بررسی کانال: {channel_title} | ID: {channel_id}")

            msgs = await client.get_messages(entity, limit=50)
            last_processed_id = db.get(ch, 0)
            max_id_this_run = last_processed_id

            for m in reversed(msgs):
                if m.id <= last_processed_id:
                    continue
                if last_processed_id == 0 and m.date < fallback_limit:
                    continue

                try:
                    if m.media:
                        log(f"🖼️/📁 انتقال مدیا از {channel_title}")
                        await client.send_message(
                            MY_CHANNEL,
                            m.message or "",
                            file=m.media,
                            formatting_entities=m.entities,
                            parse_mode=None,
                            link_preview=False
                        )
                    elif m.message:
                        log(f"📝 انتقال متن از {channel_title}")
                        await client.send_message(
                            MY_CHANNEL,
                            m.message,
                            formatting_entities=m.entities,
                            parse_mode=None,
                            link_preview=False
                        )
                except Exception as e:
                    log(f"⚠️ خطا در ارسال پیام {m.id} از {ch}: {e}")

                if m.id > max_id_this_run:
                    max_id_this_run = m.id

            db[ch] = max_id_this_run
        except Exception as e:
            log(f"⚠️ خطای کلی در پردازش {ch}: {e}")

    save_db(db)
    await client.disconnect()
    log("--- 🏁 Run finished successfully ---")


if __name__ == "__main__":
    asyncio.run(main_bot_logic())
