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

### Step 2: Test-driven development

When fixing a bug or adding new logic:

1. **Write a failing test first** in `test_bot.py` that reproduces the problem
2. Run the test to confirm it fails:
   ```bash
   python test_bot.py
   ```
3. Fix the implementation in `bot.py`
4. Run again until the test passes
5. Only push when all tests pass

Install dependencies locally if needed:
```bash
pip install -r requirements.txt --user
```

> For API behavior that is hard to predict (e.g. model list structure,
> response fields), add a `[DIAG]` test first that prints raw data, then
> write the assertion test based on what you observe.

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
| `test_bot.py` | Local test script — run before every push |
| `.env.example` | Template for local environment variables |
| `.github/workflows/daily-wordle.yml` | GitHub Actions: runs at 14:30 UTC (22:30 TW) daily |

## Environment variables

**Local development:** Copy `.env.example` to `.env` and fill in real values.
`.env` is listed in `.gitignore` and will never be committed.

**GitHub Actions:** Values are injected automatically from GitHub Secrets — no `.env` file needed.
Required secrets: `DISCORD_TOKEN`, `GEMINI_API_KEY`, `WATCH_CHANNEL_IDS` (comma-separated channel IDs).
