import json
import logging
import os
import re
import time
import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

import requests
import schedule
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = (os.getenv("SPREADSHEET_ID") or "").strip()
WORKSHEET_NAME = (os.getenv("WORKSHEET_NAME") or "Цены").strip() or "Цены"
GOOGLE_CREDENTIALS_PATH = (os.getenv("GOOGLE_CREDENTIALS_PATH") or "service_account.json").strip()

TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
TELEGRAM_CHAT_ID = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

CHECK_INTERVAL_HOURS = int((os.getenv("CHECK_INTERVAL_HOURS") or "1").strip() or "1")
USER_AGENT = (os.getenv("USER_AGENT") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36").strip()

BASE_DIR = Path(__file__).resolve().parent
TARGETS_PATH = BASE_DIR / "targets.json"
STATE_PATH = BASE_DIR / "state.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("price-monitor")


@dataclass(frozen=True)
class Target:
    name: str
    url: str
    selectors: list[str]
    currency: str = ""


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, Any] = {"last": {}}  # {name: {price: "", ts: ""}}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if "last" not in self.data or not isinstance(self.data["last"], dict):
                self.data = {"last": {}}
        except Exception:
            self.data = {"last": {}}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_last_price(self, name: str) -> Optional[str]:
        last = self.data.get("last", {}).get(name)
        if not isinstance(last, dict):
            return None
        p = last.get("price")
        return str(p) if p is not None else None

    def set_last_price(self, name: str, price: str, ts_iso: str) -> None:
        self.data.setdefault("last", {})[name] = {"price": price, "ts": ts_iso}


class SheetsWriter:
    def __init__(self, spreadsheet_id: str, worksheet_name: str, creds_path: str):
        self.enabled = False
        self.ws = None

        if not spreadsheet_id:
            return

        try:
            import gspread  # optional dependency

            gc = gspread.service_account(filename=creds_path)
            sh = gc.open_by_key(spreadsheet_id)
            try:
                self.ws = sh.worksheet(worksheet_name)
            except Exception:
                self.ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=10)

            self._ensure_header()
            self.enabled = True
            logger.info("Google Sheets: включено")
        except Exception as e:
            logger.warning("Google Sheets: отключено (%s)", e)

    def _ensure_header(self) -> None:
        if not self.ws:
            return
        try:
            first_row = self.ws.row_values(1)
            if first_row and any(cell.strip() for cell in first_row):
                return
            self.ws.append_row(
                ["ts", "name", "url", "price", "currency", "changed", "prev_price"],
                value_input_option="USER_ENTERED",
            )
        except Exception:
            pass

    def append(self, row: list[str]) -> None:
        if not self.enabled or not self.ws:
            return
        self.ws.append_row(row, value_input_option="USER_ENTERED")


def load_targets(path: Path) -> list[Target]:
    if not path.exists():
        raise RuntimeError(f"Не найден {path.name}. Создай файл рядом со скриптом.")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("targets.json должен быть массивом объектов")

    targets: list[Target] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        url = str(item.get("url") or "").strip()
        selectors = item.get("price_selectors") or item.get("selectors")
        currency = str(item.get("currency") or "").strip()

        if not name or not url:
            continue
        if not isinstance(selectors, list) or not selectors:
            raise RuntimeError(f"У '{name}' нет price_selectors (список CSS-селекторов)")

        selectors_str = [str(s).strip() for s in selectors if str(s).strip()]
        if not selectors_str:
            raise RuntimeError(f"У '{name}' пустые price_selectors")

        targets.append(Target(name=name, url=url, selectors=selectors_str, currency=currency))

    if not targets:
        raise RuntimeError("targets.json пустой - добавь хотя бы 1 товар")

    return targets


def fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.8"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.text


def extract_price_text(html: str, selectors: list[str]) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    for sel in selectors:
        el = soup.select_one(sel)
        if not el:
            continue
        if el.name == "meta":
            meta_val = (el.get("content") or "").strip()
            if meta_val:
                return meta_val

        attr_val = (el.get("content") or el.get("value") or "").strip()
        if attr_val:
            return attr_val

        for attr in ("data-price", "data-value", "data-amount"):
            v = (el.get(attr) or "").strip()
            if v:
                return v

        text = el.get_text(" ", strip=True)
        if text:
            return text
    return None


def normalize_price(price_text: str) -> Optional[str]:
    t = price_text.strip()
    if not t:
        return None

    t = t.replace("\u00a0", " ").replace(" ", "")
    m = re.search(r"(\d+[\d\.,]*)", t)
    if not m:
        return None

    num = m.group(1)

    if "," in num and "." in num:
        if num.rfind(",") > num.rfind("."):
            num = num.replace(".", "").replace(",", ".")
        else:
            num = num.replace(",", "")
    elif "," in num and "." not in num:
        num = num.replace(",", ".")

    try:
        d = Decimal(num)
        d = d.quantize(Decimal("0.01")) if d.as_tuple().exponent < -2 else d
        return format(d, "f")
    except (InvalidOperation, ValueError):
        return None


def send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15).raise_for_status()
    except Exception as e:
        logger.warning("Telegram notify failed: %s", e)


def check_once(targets: list[Target], state: StateStore, sheets: SheetsWriter) -> None:
    ts = datetime.now().astimezone().replace(microsecond=0).isoformat()

    for t in targets:
        try:
            html = fetch_html(t.url)
            raw_price = extract_price_text(html, t.selectors)
            price = normalize_price(raw_price or "")

            if not price:
                logger.warning("%s: не удалось извлечь цену (raw=%r)", t.name, raw_price)
                continue

            prev = state.get_last_price(t.name)
            changed = "1" if (prev is not None and prev != price) else "0"

            sheets.append([ts, t.name, t.url, price, t.currency, changed, prev or ""])  # type: ignore[arg-type]

            if prev is None:
                logger.info("%s: %s", t.name, price)
            elif prev != price:
                logger.info("%s: %s -> %s", t.name, prev, price)
                send_telegram(f"Цена изменилась: {t.name}\n{prev} -> {price}\n{t.url}")

            state.set_last_price(t.name, price, ts)

        except Exception as e:
            logger.error("%s: ошибка проверки: %s", t.name, e)

    state.save()


def main() -> None:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--once", action="store_true", help="Run single check and exit")
    parser.add_argument("--test-notify", action="store_true", help="Send test Telegram message and exit")
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=CHECK_INTERVAL_HOURS,
        help="Check interval in hours (default from env)",
    )
    args = parser.parse_args()

    if args.test_notify:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Telegram не настроен. Заполни TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env")
            raise SystemExit(1)

        ts = datetime.now().astimezone().replace(microsecond=0).isoformat()
        try:
            send_telegram(f"TEST: price-monitor уведомления работают ({ts})")
        except Exception as e:
            logger.error("Ошибка отправки Telegram: %s", e)
            raise SystemExit(1)

        logger.info("OK: test message sent")
        raise SystemExit(0)

    targets = load_targets(TARGETS_PATH)
    state = StateStore(STATE_PATH)
    sheets = SheetsWriter(SPREADSHEET_ID, WORKSHEET_NAME, GOOGLE_CREDENTIALS_PATH)

    interval_hours = int(args.interval_hours) if int(args.interval_hours) > 0 else CHECK_INTERVAL_HOURS
    logger.info("Целей: %s. Интервал: %sч", len(targets), interval_hours)

    check_once(targets, state, sheets)

    if args.once:
        return

    schedule.every(interval_hours).hours.do(check_once, targets=targets, state=state, sheets=sheets)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
