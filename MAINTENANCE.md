---
name: Project Maintenance Workflow
description: How to fix bugs in DC_Wordle_Bot when GitHub Actions fails, including test and deploy steps
type: project
---

## Bug Fix Workflow for DC_Wordle_Bot

When GitHub Actions fails, follow this process:

### Step 1: Fix the bug

1. Read the full error traceback from the user (GitHub Actions log)
2. Read the relevant source files: `bot.py`, `requirements.txt`
3. Apply the fix

### Step 2: Test locally before pushing

Install dependencies locally if needed:
```bash
pip install google-genai Pillow aiohttp discord.py --user
```

Run these checks in order:
```bash
# 1. Syntax check
python -m py_compile bot.py

# 2. Import + logic check (no API key needed)
python -c "
from google import genai
from PIL import Image
import io
img = Image.new('RGB', (100, 100))
buf = io.BytesIO()
img.save(buf, format='JPEG')
image_bytes = buf.getvalue()
image = Image.open(io.BytesIO(image_bytes))
mime_type = Image.MIME.get(image.format, 'image/jpeg')
image_part = genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
print('OK:', type(image_part))
"
```

Only proceed to push if both checks pass.

### Step 3: Commit and push

```bash
git add bot.py requirements.txt   # only changed files
git commit -m "Fix: <description>"
git push
```

Then trigger GitHub Actions manually via `workflow_dispatch` to confirm the fix.

---

## Known past bugs and fixes

### 2026-04-09: google-generativeai deprecated
- **Error**: `All support for the google.generativeai package has ended`
- **Fix**: Changed `requirements.txt` from `google-generativeai` to `google-genai>=1.0.0`
- Changed import from `import google.generativeai as genai` to `from google import genai`
- Changed client init from `genai.configure()` + `GenerativeModel()` to `genai.Client(api_key=...)`
- Changed API call: `model.generate_content(...)` → `client_genai.models.generate_content(model=..., contents=...)`

### 2026-04-09: PIL Image not accepted by new SDK
- **Error**: Crash inside `google/genai/models.py` when passing PIL Image object directly
- **Fix**: Use `genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type)` instead of passing PIL Image directly
- Get mime_type via `Image.MIME.get(image.format, "image/jpeg")`

---

## Key files

| File | Purpose |
|------|---------|
| `bot.py` | Main bot logic — Gemini API call is in `analyze_image()` |
| `requirements.txt` | Python dependencies |
| `.github/workflows/daily-wordle.yml` | GitHub Actions: runs at 14:30 UTC (22:30 TW) daily |

## Environment variables (set as GitHub Secrets)
- `DISCORD_TOKEN` — Discord bot token
- `GEMINI_API_KEY` — Google Gemini API key
