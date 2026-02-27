#!/usr/bin/env python3
"""
Wallapop Product Alert
======================
Uses a headless Firefox browser (Playwright) to load Wallapop's own search
page and intercept the JSON API responses it makes internally.
This bypasses Cloudflare / bot-detection because the real browser handles
all cookies, fingerprinting and TLS negotiation automatically.

Setup
-----
1. pip3 install -r requirements.txt
2. python3 -m playwright install firefox
3. Edit config.json  (keywords + email credentials)
4. python3 wallapop_alert.py

Gmail users: create an App Password at
  https://myaccount.google.com/apppasswords
and put that 16-char code in sender_password (not your real Gmail password).
"""

import html as html_mod
import json
import os
import tempfile
import time
import smtplib
import logging
import threading
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
SEEN_FILE   = BASE_DIR / ".seen_items.json"

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
# Config / state helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


MAX_SEEN = 10_000   # cap to avoid unbounded growth


def load_seen() -> set:
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, ValueError):
            log.warning("Seen-items file was corrupted — starting fresh.")
            SEEN_FILE.unlink(missing_ok=True)
    return set()


def save_seen(seen: set) -> None:
    # Trim to the most-recent MAX_SEEN entries (sets are unordered so we just slice)
    items = list(seen)
    if len(items) > MAX_SEEN:
        items = items[-MAX_SEEN:]

    # Atomic write: write to a temp file then rename so a crash never corrupts the file
    fd, tmp_path = tempfile.mkstemp(dir=SEEN_FILE.parent, prefix=".seen_tmp_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(items, f)
        os.replace(tmp_path, SEEN_FILE)
    except Exception:
        os.unlink(tmp_path)
        raise


# ---------------------------------------------------------------------------
# Wallapop scraping via Playwright response interception
# ---------------------------------------------------------------------------

SEARCH_URL = "https://es.wallapop.com/app/search"
ITEM_BASE  = "https://es.wallapop.com/item/"

# Wallapop's frontend calls this endpoint; we intercept the response.
API_PATTERN = "**/api/v3/general/search*"


def _extract_items_from_api_json(body: dict) -> list[dict]:
    """Parse normalised item list from Wallapop's internal API JSON."""
    items = []
    # Shape 1: data.section_responses[0].items
    try:
        for section in body.get("data", {}).get("section_responses", []):
            for raw in section.get("items", []):
                item = raw.get("item", raw)
                parsed = _normalise(item)
                if parsed:
                    items.append(parsed)
    except Exception:
        pass

    # Shape 2: flat items array at root
    if not items:
        for raw in body.get("items", []):
            parsed = _normalise(raw)
            if parsed:
                items.append(parsed)

    return items


_CURRENCY_SYMBOL = {"EUR": "€", "USD": "$", "GBP": "£", "MXN": "$", "ARS": "$"}


def _normalise(item: dict) -> dict | None:
    """Turn a raw Wallapop item dict into the fields we care about."""
    try:
        item_id = str(item.get("id") or item.get("itemId") or "")
        if not item_id:
            return None
        title    = item.get("title", "No title")
        price_d  = item.get("price") or {}
        amount   = price_d.get("amount", "?")
        currency_code = price_d.get("currency", "EUR")
        symbol   = _CURRENCY_SYMBOL.get(currency_code, currency_code)
        slug     = item.get("web_slug") or item.get("webSlug") or item_id
        url      = f"{ITEM_BASE}{slug}"
        desc     = (item.get("description") or "")[:300]
        location = (item.get("location") or {}).get("city", "")
        image    = ""
        images   = item.get("images") or []
        if images:
            image = (images[0] or {}).get("medium") or (images[0] or {}).get("large") or ""
        return {
            "id":       item_id,
            "title":    title,
            "price":    f"{amount} {symbol}",
            "url":      url,
            "desc":     desc,
            "location": location,
            "image":    image,
        }
    except Exception:
        return None


def _extract_items_from_dom(page) -> list[dict]:
    """
    Fallback: parse product cards directly from the rendered DOM.
    Wallapop renders <tsl-item-card> web components; we grab every
    link that points to /item/ and extract nearby text.
    """
    items = []
    try:
        cards = page.query_selector_all("a[href*='/item/']")
        seen_hrefs: set = set()
        for card in cards:
            href = card.get_attribute("href") or ""
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            # Build a unique ID from the slug in the URL
            slug    = href.rstrip("/").split("/")[-1]
            item_id = slug
            url     = href if href.startswith("http") else f"https://es.wallapop.com{href}"

            # Try to get price and title text from descendants
            title_el = card.query_selector("[class*='title'], [class*='Title'], h2, h3")
            title    = title_el.inner_text().strip() if title_el else card.inner_text()[:60].strip()
            price_el = card.query_selector("[class*='price'], [class*='Price']")
            price    = price_el.inner_text().strip() if price_el else ""

            items.append({
                "id":       item_id,
                "title":    title,
                "price":    price,
                "url":      url,
                "desc":     "",
                "location": "",
                "image":    "",
            })
    except Exception as exc:
        log.debug("DOM parse error: %s", exc)
    return items


def search_wallapop(keyword: str, config: dict, browser) -> list[dict]:
    """
    Open a fresh browser page, navigate to the Wallapop search, intercept
    the API JSON response, and return a list of normalised item dicts.
    """
    wconf   = config.get("wallapop", {})
    max_res = wconf.get("max_results_per_keyword", 40)

    qs = urlencode({"keywords": keyword, "order_by": "newest", "step": max_res})
    target_url = f"{SEARCH_URL}?{qs}"

    captured: list[dict] = []
    capture_done = threading.Event()

    ctx  = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
            "Gecko/20100101 Firefox/122.0"
        ),
        locale="es-ES",
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.new_page()

    def on_response(response):
        """Called for every network response; we watch for the search API."""
        if "api/v3/general/search" not in response.url:
            return
        try:
            body = response.json()
            items = _extract_items_from_api_json(body)
            if items:
                captured.extend(items)
                log.debug("Intercepted %d items for '%s'", len(items), keyword)
                capture_done.set()
        except Exception as exc:
            log.debug("Could not parse intercepted response: %s", exc)

    page.on("response", on_response)

    try:
        log.info("  Loading Wallapop search for '%s'…", keyword)
        page.goto(target_url, timeout=40_000, wait_until="domcontentloaded")

        # Wait up to 15 s for the API response to arrive after DOM load
        capture_done.wait(timeout=15)

        if not captured:
            # Fallback: parse the DOM directly
            log.info("  API interception got nothing — trying DOM parse…")
            page.wait_for_timeout(3000)
            captured.extend(_extract_items_from_dom(page))

    except PWTimeout:
        log.warning("  Page load timed out for keyword '%s' — trying DOM parse anyway", keyword)
        try:
            captured.extend(_extract_items_from_dom(page))
        except Exception:
            pass
    except Exception as exc:
        log.warning("  Error loading page for '%s': %s", keyword, exc)
    finally:
        try:
            page.close()
            ctx.close()
        except Exception:
            pass

    return captured


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def _h(text: str) -> str:
    """Escape a string for safe insertion into HTML."""
    return html_mod.escape(str(text), quote=True)


def _item_html(item: dict) -> str:
    img_tag = (
        f'<img src="{_h(item["image"])}" width="120" '
        f'style="float:left;margin:0 12px 8px 0;border-radius:4px;" />'
        if item["image"] else ""
    )
    location_span = (
        f"&nbsp;&nbsp;<span style='color:#888;font-size:13px;'>📍 {_h(item['location'])}</span>"
        if item["location"] else ""
    )
    desc_span = (
        f"<span style='color:#555;font-size:13px;'>{_h(item['desc'])}</span><br>"
        if item["desc"] else ""
    )
    return f"""
    <tr>
      <td style="padding:14px 10px;border-bottom:1px solid #eee;overflow:hidden;">
        {img_tag}
        <a href="{_h(item['url'])}"
           style="font-size:16px;font-weight:bold;color:#1a73e8;text-decoration:none;">
          {_h(item['title'])}
        </a><br>
        <span style="color:#e53935;font-size:15px;font-weight:bold;">{_h(item['price'])}</span>
        {location_span}
        <br>
        {desc_span}
        <a href="{_h(item['url'])}"
           style="font-size:13px;color:#1a73e8;">View on Wallapop →</a>
        <div style="clear:both;"></div>
      </td>
    </tr>"""


def build_email_html(keyword: str, new_items: list[dict]) -> str:
    rows = "".join(_item_html(i) for i in new_items)
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:620px;margin:auto;">
      <h2 style="background:#13c1ac;color:#fff;padding:16px 20px;
                 border-radius:6px 6px 0 0;margin:0;">
        🔔 {len(new_items)} new listing{"s" if len(new_items)>1 else ""}
        for &ldquo;{keyword}&rdquo;
      </h2>
      <table width="100%" style="border-collapse:collapse;">{rows}</table>
      <p style="color:#aaa;font-size:12px;padding:10px 10px 2px;">
        Wallapop Alert &mdash; {ts}
      </p>
    </body></html>
    """


def send_email(keyword: str, new_items: list[dict], config: dict) -> None:
    cfg = config["email"]
    msg = MIMEMultipart("alternative")
    n   = len(new_items)
    msg["Subject"] = f"[Wallapop] {n} new result{'s' if n>1 else ''} for \"{keyword}\""
    msg["From"]    = cfg["sender_email"]
    msg["To"]      = cfg["recipient_email"]
    msg.attach(MIMEText(build_email_html(keyword, new_items), "html"))

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.sendmail(cfg["sender_email"], cfg["recipient_email"], msg.as_string())
        log.info("  Email sent — %d item(s) for '%s'", n, keyword)
    except Exception as exc:
        log.error("  Failed to send email: %s", exc)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def validate_config(config: dict) -> None:
    """Raise a clear error if required config keys are missing."""
    required = {
        "keywords": list,
        "email": dict,
    }
    for key, typ in required.items():
        if key not in config:
            raise KeyError(f"config.json is missing required key: '{key}'")
        if not isinstance(config[key], typ):
            raise TypeError(f"config.json '{key}' must be a {typ.__name__}")
    email_keys = ["smtp_host", "smtp_port", "sender_email", "sender_password", "recipient_email"]
    for k in email_keys:
        if k not in config["email"]:
            raise KeyError(f"config.json is missing email.{k}")
    if not config["keywords"]:
        raise ValueError("config.json 'keywords' list must not be empty")


def check_once(config: dict, seen: set, browser) -> set:
    keywords = [kw for kw in config["keywords"] if kw and kw.strip()]
    for keyword in keywords:
        log.info("Checking keyword: '%s'", keyword)
        items = search_wallapop(keyword, config, browser)

        new_items = [i for i in items if i["id"] not in seen]
        for i in items:
            seen.add(i["id"])

        if new_items:
            log.info("  → %d new item(s) found — sending email", len(new_items))
            send_email(keyword, new_items, config)
        else:
            log.info("  → No new items")

    return seen


def _launch_browser(pw):
    return pw.firefox.launch(headless=True)


def main() -> None:
    config = load_config()
    try:
        validate_config(config)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

    interval = max(1, config.get("check_interval_minutes", 5)) * 60
    seen     = load_seen()

    log.info("=" * 55)
    log.info("Wallapop Alert started")
    log.info("Keywords : %s", config["keywords"])
    log.info("Interval : %d min", interval // 60)
    log.info("Notify   : %s", config["email"]["recipient_email"])
    log.info("=" * 55)

    with sync_playwright() as pw:
        browser = _launch_browser(pw)
        try:
            while True:
                try:
                    seen = check_once(config, seen, browser)
                    save_seen(seen)
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    log.error("Unexpected error during check: %s", exc)
                    # If the browser crashed, relaunch it for the next round
                    try:
                        browser.close()
                    except Exception:
                        pass
                    log.info("Relaunching browser after error…")
                    browser = _launch_browser(pw)

                log.info("Sleeping %d minutes…", interval // 60)
                time.sleep(interval)
        except KeyboardInterrupt:
            log.info("Stopped by user.")
        finally:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
