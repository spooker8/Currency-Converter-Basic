# Wallapop Product Alert

Monitors Wallapop every 5 minutes for new listings matching your keywords and
emails you the moment one appears. Uses a **real headless Firefox browser**
(Playwright) so Wallapop's bot-detection never sees a plain HTTP scraper.

## How it works

```
Every N minutes
  └─ Open headless Firefox
      └─ Load es.wallapop.com/app/search?keywords=YOUR_KEYWORD&order_by=newest
          └─ Intercept the JSON the page fetches from Wallapop's own API
              └─ Compare item IDs against .seen_items.json
                  └─ Email you any items that are new
```

Because Playwright runs a real browser, Wallapop can't tell the difference
between your script and a human — no API keys needed, no blocked requests.

---

## Setup

### 1 — Install Python dependencies

```bash
cd wallapop_alert
pip3 install -r requirements.txt
```

### 2 — Install the headless browser (one-time, ~100 MB)

```bash
python3 -m playwright install firefox
```

### 3 — Edit `config.json`

```json
{
  "keywords": ["iphone 13", "macbook pro"],
  "check_interval_minutes": 5,
  "email": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "you@gmail.com",
    "sender_password": "xxxx xxxx xxxx xxxx",
    "recipient_email": "you@gmail.com"
  },
  "wallapop": {
    "language": "es",
    "max_results_per_keyword": 40
  }
}
```

| Field | What to put |
|---|---|
| `keywords` | Search terms to monitor — add as many as you like |
| `check_interval_minutes` | How often to check (default 5) |
| `sender_email` | Your Gmail address |
| `sender_password` | **App Password** — NOT your Gmail password (see below) |
| `recipient_email` | Where alerts go (can be the same address) |

#### Gmail App Password

Google blocks plain passwords for scripts. Create a dedicated App Password:

1. Go to <https://myaccount.google.com/apppasswords>
2. Select app → **Mail**, device → **Other** → name it "Wallapop Alert"
3. Copy the 16-character code and paste it as `sender_password`

> Using Outlook/Yahoo? Change `smtp_host` / `smtp_port` accordingly and use
> your normal password (or their equivalent app password).

### 4 — Run

```bash
python3 wallapop_alert.py
```

Press `Ctrl+C` to stop.

#### Run in the background (Linux/macOS)

```bash
nohup python3 wallapop_alert.py > alert.log 2>&1 &
# Check logs:
tail -f alert.log
```

---

## Adding / removing keywords

Edit the `keywords` list in `config.json` and restart the script.
Previously-seen items are remembered in `.seen_items.json`, so you'll never
get duplicate emails even after a restart.

## Troubleshooting

| Symptom | Fix |
|---|---|
| No emails sent | Check `sender_password` is an App Password, not your Gmail password |
| Script crashes on start | Run `python3 -m playwright install firefox` again |
| Finds 0 items | Wallapop may have changed their page — open a GitHub issue |
| Too many emails | Increase `check_interval_minutes` or narrow your keywords |
