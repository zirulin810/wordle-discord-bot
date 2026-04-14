# Claude Code Instructions for DC_Wordle_Bot

## Security — NEVER expose sensitive data

The following must NEVER appear in any code, markdown, commit message, comment, or log output:

- `DISCORD_TOKEN`
- `GEMINI_API_KEY`
- `WATCH_CHANNEL_IDS`
- Any API key, token, secret, or credential

These values are stored as **GitHub Secrets** and accessed only via environment variables at runtime. When writing or editing code, always reference them as `os.environ["KEY_NAME"]` — never hardcode values.

If you ever see a real key or token in the codebase, remove it immediately and flag it to the user.

---

## Style rules for all files

- All `.md` files must be written entirely in English. Do not mix languages within the same file.
- Do not use emoji characters in any file (code, markdown, or comments). Use plain ASCII equivalents (e.g. `[OK]`, `[FAIL]`, `[WARN]`).

---

## Maintenance workflow

See [MAINTENANCE.md](MAINTENANCE.md) for the full bug fix process.

Short version:
1. Fix the bug
2. Test locally (`python test_bot.py`)
3. Commit and push only after tests pass
