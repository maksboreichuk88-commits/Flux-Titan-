# Agent Instructions (AGENTS.md)

If you are an AI Coding Agent assisting with the `Flux-Titan` repository, please strictly adhere to the following rules:

## 1. Do Not Commit Runtime State
- The `processed.db` SQLite database must NEVER be committed or tracked via version control.
- Ensure `.gitignore` rules regarding `*.db`, `*.db-wal`, and `*.db-shm` remain intact.

## 2. Keep Diffs Small & Reviewable
- Propose the minimum changes necessary to achieve an objective.
- Avoid large-scale refactors unless explicitly instructed by the user.
- If re-formatting code, isolate it to independent commits.

## 3. Protect Secrets
- NEVER hardcode API keys or tokens (e.g., `TG_TOKEN`, `GEMINI_API_KEY`) within Python scripts.
- Rely on the `.env` approach defined in `src/flux_titan/config.py`.

## 4. Testing
- If modifying parsing logic in `src/flux_titan/feeds.py`, verify new functionality correctly handles edge cases.
- If making significant design changes, propose tests to ensure stability.

## 5. Simplicity Default
- Avoid over-engineering. Maintain the current simple "cron-style" one-shot pipeline deploy flow (perfect for lightweight GitHub Actions runs).
- Favor standard Python dependencies (`aiohttp`, `httpx`, `sqlite3`) over heavy alternatives when extending the system.

## 6. Scope
- Do not add unrelated features.
- Ensure any modifications keep the core purpose intact: `RSS -> Summarize -> Publish to Telegram`.
