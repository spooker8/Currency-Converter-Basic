# Wallapop Product Alert

Monitors Wallapop every 5 minutes for new listings matching your keywords and sends you an email the moment one appears.

## Quick Start

### 1. Install dependencies
```bash
cd wallapop_alert
pip3 install -r requirements.txt
```

### 2. Edit `config.json`

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
  }
}
```

| Field | Description |
|---|---|
| `keywords` | List of search terms to monitor |
| `check_interval_minutes` | How often to poll (default 5) |
| `sender_email` | Gmail address used to send alerts |
| `sender_password` | **App Password** (not your Gmail password) |
| `recipient_email` | Where alerts are delivered |

> **Gmail App Password**: Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), create a password for "Mail", and paste the 16-character code here.

### 3. Run
```bash
python3 wallapop_alert.py
```

The script runs forever. Press `Ctrl+C` to stop.

### Run in the background (Linux/macOS)
```bash
nohup python3 wallapop_alert.py > alert.log 2>&1 &
```

## How it works

1. Every N minutes, it calls the Wallapop search API for each keyword.
2. New item IDs are stored in `.seen_items.json` so you never get duplicate emails.
3. When a new listing is found, an HTML email is sent with the title, price, location, and a direct link.

## Adding / removing keywords

Edit the `keywords` array in `config.json` — no restart needed if you stop and re-run.
