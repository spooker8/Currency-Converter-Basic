#!/usr/bin/env python3
"""
Wallapop Product Alert
======================
Polls the Wallapop API every N minutes for new listings matching your keywords
and sends you an email when a new one appears.

Setup
-----
1. Edit config.json with your keywords and email credentials.
2. For Gmail, use an App Password (not your main password):
   https://myaccount.google.com/apppasswords
3. Run:  python3 wallapop_alert.py
"""

import json
import time
import smtplib
import logging
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
SEEN_FILE = BASE_DIR / ".seen_items.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Wallapop API
# ---------------------------------------------------------------------------
WALLAPOP_SEARCH_URL = "https://api.wallapop.com/api/v3/general/search"
WALLAPOP_ITEM_URL = "https://es.wallapop.com/item/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://es.wallapop.com",
    "Referer": "https://es.wallapop.com/",
}


def load_config() -> dict:
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def load_seen() -> set:
    if SEEN_FILE.exists():
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set) -> None:
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_wallapop(keyword: str, config: dict) -> list[dict]:
    """Return a list of item dicts for the given keyword."""
    params = {
        "keywords": keyword,
        "language": config["wallapop"].get("language", "en"),
        "filters_source": "default_filters",
        "order_by": "newest",
        "start": 0,
        "step": config["wallapop"].get("max_results_per_keyword", 40),
    }
    try:
        resp = requests.get(
            WALLAPOP_SEARCH_URL,
            headers=HEADERS,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        # The search results live under data -> section_responses -> [0] -> items
        # depending on Wallapop API version; handle both shapes gracefully.
        items = (
            data.get("data", {})
            .get("section_responses", [{}])[0]
            .get("items", [])
        )
        if not items:
            # Fallback: try flat list shape
            items = data.get("items", [])
        return items
    except Exception as exc:
        log.warning("Search failed for '%s': %s", keyword, exc)
        return []


def parse_item(raw: dict) -> dict | None:
    """Normalise a raw Wallapop item into a flat dict we care about."""
    try:
        item = raw.get("item", raw)  # some responses nest under "item"
        item_id = item.get("id") or item.get("itemId")
        if not item_id:
            return None
        title = item.get("title", "No title")
        price_info = item.get("price", {}) or {}
        price = price_info.get("amount", "N/A")
        currency = price_info.get("currency", "€")
        slug = item.get("web_slug") or item.get("webSlug") or str(item_id)
        url = f"{WALLAPOP_ITEM_URL}{slug}"
        description = item.get("description", "")[:300]
        location = (item.get("location") or {}).get("city", "Unknown location")
        return {
            "id": str(item_id),
            "title": title,
            "price": f"{price} {currency}",
            "url": url,
            "description": description,
            "location": location,
        }
    except Exception as exc:
        log.debug("Could not parse item: %s | raw=%s", exc, raw)
        return None


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def build_email_body(keyword: str, new_items: list[dict]) -> str:
    rows = ""
    for item in new_items:
        rows += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #eee;">
            <a href="{item['url']}" style="font-size:16px;font-weight:bold;color:#1a73e8;text-decoration:none;">
              {item['title']}
            </a><br>
            <span style="color:#e53935;font-size:14px;font-weight:bold;">{item['price']}</span>
            &nbsp;&nbsp;<span style="color:#888;font-size:13px;">📍 {item['location']}</span><br>
            <span style="color:#555;font-size:13px;">{item['description']}</span><br>
            <a href="{item['url']}" style="font-size:13px;color:#1a73e8;">View on Wallapop →</a>
          </td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
      <h2 style="background:#13c1ac;color:#fff;padding:16px;border-radius:6px 6px 0 0;margin:0;">
        🔔 {len(new_items)} new Wallapop listing(s) for "{keyword}"
      </h2>
      <table width="100%" style="border-collapse:collapse;">{rows}</table>
      <p style="color:#aaa;font-size:12px;padding:10px;">
        Sent by Wallapop Alert &mdash; {datetime.now().strftime('%Y-%m-%d %H:%M')}
      </p>
    </body></html>
    """


def send_email(keyword: str, new_items: list[dict], config: dict) -> None:
    cfg = config["email"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Wallapop Alert] {len(new_items)} new result(s) for \"{keyword}\""
    msg["From"] = cfg["sender_email"]
    msg["To"] = cfg["recipient_email"]
    msg.attach(MIMEText(build_email_body(keyword, new_items), "html"))

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.sendmail(cfg["sender_email"], cfg["recipient_email"], msg.as_string())
        log.info("Email sent for keyword '%s' (%d item(s))", keyword, len(new_items))
    except Exception as exc:
        log.error("Failed to send email: %s", exc)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def check_once(config: dict, seen: set) -> set:
    """Run one full check across all keywords; return updated seen set."""
    newly_seen: set = set()

    for keyword in config["keywords"]:
        log.info("Checking keyword: '%s'", keyword)
        raw_items = search_wallapop(keyword, config)
        new_for_keyword = []

        for raw in raw_items:
            parsed = parse_item(raw)
            if parsed is None:
                continue
            item_id = parsed["id"]
            if item_id not in seen:
                new_for_keyword.append(parsed)
                newly_seen.add(item_id)
            seen.add(item_id)

        if new_for_keyword:
            log.info("  → %d new item(s) found for '%s'", len(new_for_keyword), keyword)
            send_email(keyword, new_for_keyword, config)
        else:
            log.info("  → No new items for '%s'", keyword)

    return seen


def main() -> None:
    config = load_config()
    interval = config.get("check_interval_minutes", 5) * 60
    seen = load_seen()

    log.info("Wallapop Alert started.")
    log.info("Keywords  : %s", config["keywords"])
    log.info("Interval  : %d minutes", interval // 60)
    log.info("Notify    : %s", config["email"]["recipient_email"])

    while True:
        try:
            seen = check_once(config, seen)
            save_seen(seen)
        except KeyboardInterrupt:
            log.info("Stopped by user.")
            break
        except Exception as exc:
            log.error("Unexpected error: %s", exc)

        log.info("Sleeping %d minutes until next check...", interval // 60)
        time.sleep(interval)


if __name__ == "__main__":
    main()
