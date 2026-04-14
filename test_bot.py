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


if __name__ == "__main__":
    tests = [test_syntax, test_imports_and_image_part, test_dotenv_import]
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
