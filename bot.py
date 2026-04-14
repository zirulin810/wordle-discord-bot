import os
import io
import sys
import asyncio
import aiohttp
import discord
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from PIL import Image
from datetime import datetime, timezone, timedelta

load_dotenv()

TW_TZ = timezone(timedelta(hours=8))

GEMINI_API_KEY    = os.environ["GEMINI_API_KEY"]
DISCORD_TOKEN     = os.environ["DISCORD_TOKEN"]
WATCH_CHANNEL_IDS = [int(x) for x in os.environ["WATCH_CHANNEL_IDS"].split(",") if x.strip()]

client_genai = genai.Client(api_key=GEMINI_API_KEY)

def build_prompt() -> str:
    today = datetime.now(TW_TZ).strftime("%Y/%m/%d")
    return f"""
該圖片為 Wordle 的遊戲截圖。
請從圖片中辨識出今日的答案（如果有的話），並**嚴格**依照以下格式輸出，不得新增或省略任何欄位：

{today}
<英文單字，大寫>
<詞性縮寫> <繁體中文解釋>
<一句英文例句>
<該例句的繁體中文翻譯>
"""

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def analyze_image(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    mime_type = Image.MIME.get(image.format, "image/jpeg")
    image_part = genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    for attempt, model in enumerate(models):
        try:
            response = await asyncio.to_thread(
                client_genai.models.generate_content,
                model=model,
                contents=[build_prompt(), image_part],
            )
            return response.text.strip()
        except genai_errors.ServerError as e:
            print(f"[WARN] {model} failed ({e}){', retrying with fallback model' if attempt < len(models) - 1 else ', no more fallback models'}")
            if attempt == len(models) - 1:
                raise


def format_reply(filename: str, analysis: str) -> str:
    is_spoiler = filename.startswith("SPOILER_")
    body = f"```\n{analysis}\n```"
    if is_spoiler:
        return f"||{body}||"
    return body


async def process_image(session: aiohttp.ClientSession, url: str, filename: str) -> str:
    async with session.get(url) as resp:
        if resp.status != 200:
            print(f"[WARN] failed to download image: {filename} (HTTP {resp.status})")
            return None
        image_bytes = await resp.read()

    print(f"[INFO] analyzing image: {filename}")
    analysis = await analyze_image(image_bytes)
    return format_reply(filename, analysis)


async def run_once():
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    today = datetime.now(TW_TZ).date()
    async with aiohttp.ClientSession(headers=headers) as session:
        for channel_id in WATCH_CHANNEL_IDS:
            async with session.get(f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=10") as resp:
                if resp.status != 200:
                    print(f"[WARN] failed to fetch channel {channel_id} messages: HTTP {resp.status}")
                    continue
                messages = await resp.json()

            for msg in messages:
                msg_date = datetime.fromisoformat(msg["timestamp"]).astimezone(TW_TZ).date()
                if msg_date != today:
                    continue

                if msg.get("author", {}).get("bot"):
                    continue
                attachments = msg.get("attachments", [])
                image_attachments = [
                    att for att in attachments
                    if att.get("content_type", "").startswith("image/")
                ]
                if not image_attachments:
                    continue

                att = image_attachments[0]
                reply_content = await process_image(session, att["url"], att["filename"])
                if reply_content is None:
                    continue

                payload = {
                    "content": reply_content,
                    "message_reference": {"message_id": msg["id"]}
                }
                async with session.post(f"https://discord.com/api/v10/channels/{channel_id}/messages", json=payload) as reply_resp:
                    if reply_resp.status == 200:
                        print(f"[OK] replied to message ID: {msg['id']}")
                    else:
                        print(f"[ERROR] reply failed: HTTP {reply_resp.status}")
                break


@client.event
async def on_ready():
    print(f"[OK] bot online: {client.user} (ID: {client.user.id})")
    if WATCH_CHANNEL_IDS:
        print(f"[INFO] watching channel IDs: {WATCH_CHANNEL_IDS}")
    else:
        print("[INFO] watching all channels")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if WATCH_CHANNEL_IDS and message.channel.id not in WATCH_CHANNEL_IDS:
        return

    image_attachments = [
        att for att in message.attachments
        if att.content_type and att.content_type.startswith("image/")
    ]

    if not image_attachments:
        return

    async with message.channel.typing():
        async with aiohttp.ClientSession() as session:
            for att in image_attachments:
                try:
                    reply = await process_image(session, att.url, att.filename)
                    if reply:
                        await message.reply(reply)

                except Exception as e:
                    print(f"[ERROR] failed to process image: {e}")


if __name__ == "__main__":
    if "--run_once" in sys.argv:
        asyncio.run(run_once())
    else:
        client.run(DISCORD_TOKEN)
