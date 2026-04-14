"""
Local test script — no API key required, no external requests made.
Run this after editing bot.py and before every push.
"""
import io
import subprocess
import sys


def test_syntax():
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", "bot.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Syntax error:\n{result.stderr}"
    print("[PASS] syntax check")


def test_imports_and_image_part():
    from google import genai
    from google.genai import errors as genai_errors
    from PIL import Image

    assert issubclass(genai_errors.ServerError, Exception)

    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()

    image = Image.open(io.BytesIO(image_bytes))
    mime_type = Image.MIME.get(image.format, "image/jpeg")
    image_part = genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    assert mime_type == "image/jpeg"
    assert image_part is not None
    print(f"[PASS] imports and Part.from_bytes (mime_type={mime_type})")


def test_dotenv_import():
    from dotenv import load_dotenv
    assert callable(load_dotenv)
    print("[PASS] python-dotenv import")


def _load_env():
    """Load .env and return True if it exists, False otherwise."""
    from pathlib import Path
    from dotenv import load_dotenv
    if not Path(".env").exists():
        return False
    load_dotenv()
    return True


def test_gemini_connectivity():
    import os
    from google import genai

    if not _load_env():
        print("[SKIP] Gemini connectivity — .env not found")
        return

    assert os.environ.get("GEMINI_API_KEY"), "GEMINI_API_KEY is missing or empty in .env"
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    models = list(client.models.list())
    assert any("gemini" in m.name for m in models), "No Gemini models found"
    print(f"[PASS] Gemini API reachable ({len(models)} models available)")


def test_discord_connectivity():
    import os
    import requests

    if not _load_env():
        print("[SKIP] Discord connectivity — .env not found")
        return

    assert os.environ.get("DISCORD_TOKEN"), "DISCORD_TOKEN is missing or empty in .env"
    resp = requests.get(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bot {os.environ['DISCORD_TOKEN']}"},
        timeout=10,
    )
    assert resp.status_code == 200, f"Discord token invalid (HTTP {resp.status_code})"
    print(f"[PASS] Discord token valid (bot: {resp.json().get('username', '?')})")


if __name__ == "__main__":
    tests = [
        test_syntax,
        test_imports_and_image_part,
        test_dotenv_import,
        test_gemini_connectivity,
        test_discord_connectivity,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n{failed} test(s) failed. Fix before pushing.")
        sys.exit(1)
    else:
        print("\nAll tests passed. Safe to push.")
