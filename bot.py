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
SKIP_TAGS = ("preview", "exp", "latest", "tts", "audio", "live", "-image", "lite")


def _fetch_flash_models() -> list[str]:
    models = sorted(
        [m.name.removeprefix("models/") for m in client_genai.models.list()
         if "flash" in m.name and not any(t in m.name for t in SKIP_TAGS)],
        reverse=True,
    )
    if not models:
        raise RuntimeError("no available Flash models found")
    print(f"[INFO] available Flash models: {models}")
    return models

GEMINI_MODELS = _fetch_flash_models()


def build_prompt(date_str: str) -> str:
    return f"""
該圖片為 Wordle 的遊戲截圖。
請從圖片中辨識出今日的答案（全綠的單字），並**嚴格**依照以下格式輸出，不得新增或省略任何欄位：

{date_str}
<英文單字，大寫>
<詞性縮寫> <繁體中文解釋>
<含該單字的英文例句>
<該例句的繁體中文翻譯>
"""

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def analyze_image(image_bytes: bytes, date_str: str) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    part = genai.types.Part.from_bytes(data=image_bytes, mime_type=Image.MIME.get(image.format, "image/jpeg"))
    prompt = build_prompt(date_str)
    for i, model in enumerate(GEMINI_MODELS):
        try:
            r = await asyncio.to_thread(
                client_genai.models.generate_content,
                model=model,
                contents=[prompt, part],
            )
            print(f"[INFO] model used: {model}")
            return r.text.strip()
        except genai_errors.ServerError as e:
            has_fallback = i < len(GEMINI_MODELS) - 1
            print(f"[WARN] {model} failed ({e}), {'retrying with fallback model' if has_fallback else 'no more fallback models'}")
            if not has_fallback:
                raise


def format_reply(filename: str, analysis: str) -> str:
    body = f"```\n{analysis}\n```"
    return f"||{body}||" if filename.startswith("SPOILER_") else body


async def process_image(session: aiohttp.ClientSession, url: str, filename: str, date_str: str) -> str | None:
    async with session.get(url) as resp:
        if resp.status != 200:
            print(f"[WARN] failed to download image: {filename} (HTTP {resp.status})")
            return None
        image_bytes = await resp.read()
    print(f"[INFO] analyzing image: {filename}")
    return format_reply(filename, await analyze_image(image_bytes, date_str))


async def run_once():
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    now = datetime.now(TW_TZ)
    date_str, today = now.strftime("%Y/%m/%d"), now.date()
    async with aiohttp.ClientSession(headers=headers) as session:
        for channel_id in WATCH_CHANNEL_IDS:
            async with session.get(f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=10") as resp:
                if resp.status != 200:
                    print(f"[WARN] failed to fetch channel {channel_id} messages: HTTP {resp.status}")
                    continue
                messages = await resp.json()

            for msg in messages:
                if datetime.fromisoformat(msg["timestamp"]).astimezone(TW_TZ).date() != today:
                    continue
                if msg.get("author", {}).get("bot"):
                    continue
                images = [a for a in msg.get("attachments", []) if a.get("content_type", "").startswith("image/")]
                if not images:
                    continue
                reply = await process_image(session, images[0]["url"], images[0]["filename"], date_str)
                if not reply:
                    continue
                payload = {"content": reply, "message_reference": {"message_id": msg["id"]}}
                async with session.post(f"https://discord.com/api/v10/channels/{channel_id}/messages", json=payload) as r:
                    ok = r.status == 200
                    print(f"[{'OK' if ok else 'ERROR'}] replied to message {msg['id']}" + ("" if ok else f" (HTTP {r.status})"))
                break


@client.event
async def on_ready():
    print(f"[OK] bot online: {client.user} (ID: {client.user.id})")
    print(f"[INFO] watching channel IDs: {WATCH_CHANNEL_IDS}" if WATCH_CHANNEL_IDS else "[INFO] watching all channels")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user or (WATCH_CHANNEL_IDS and message.channel.id not in WATCH_CHANNEL_IDS):
        return
    images = [a for a in message.attachments if a.content_type and a.content_type.startswith("image/")]
    if not images:
        return
    date_str = datetime.now(TW_TZ).strftime("%Y/%m/%d")
    async with message.channel.typing():
        async with aiohttp.ClientSession() as session:
            for att in images:
                try:
                    reply = await process_image(session, att.url, att.filename, date_str)
                    if reply:
                        await message.reply(reply)
                except Exception as e:
                    print(f"[ERROR] failed to process image: {e}")


if __name__ == "__main__":
    if "--run_once" in sys.argv:
        asyncio.run(run_once())
    else:
        client.run(DISCORD_TOKEN)
