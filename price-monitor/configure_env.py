import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

FIELDS = [
    ("TELEGRAM_BOT_TOKEN", "Telegram Bot Token (можно пусто)", ""),
    ("TELEGRAM_CHAT_ID", "Telegram Chat ID (можно пусто)", ""),
    ("CHECK_INTERVAL_HOURS", "Интервал проверки (часы, по умолчанию: 1)", "1"),
    ("USER_AGENT", "User-Agent (по умолчанию: стандартный)", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
]


def prompt(name: str, label: str, default: str) -> str:
    env_val = os.getenv(name)
    if env_val is not None and str(env_val).strip() != "":
        return str(env_val).strip()

    suffix = f" [default: {default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    if value == "" and default != "":
        return default
    return value


def main() -> None:
    lines: list[str] = []
    for name, label, default in FIELDS:
        val = prompt(name, label, default)
        lines.append(f"{name}={val}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: записал {ENV_PATH}")


if __name__ == "__main__":
    main()
