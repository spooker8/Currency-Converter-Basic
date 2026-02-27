# Wallapop Product Alert

Watches Wallapop for new listings matching your keywords and emails you the
moment one appears. Runs a real headless Firefox browser so Wallapop's
bot-detection sees it as a normal visitor — no API key needed.

---

## Requirements

| Requirement | Minimum version |
|---|---|
| Python | 3.10+ |
| OS | Windows 10, macOS 12, or any modern Linux |
| Disk | ~120 MB (headless Firefox download) |
| Network | Must be able to reach `es.wallapop.com` |

---

## Step 1 — Install dependencies

Open a terminal in the `wallapop_alert` folder and run:

```bash
pip3 install -r requirements.txt
```

Then download the headless browser (one-time, ~100 MB):

```bash
python3 -m playwright install firefox
```

> **Windows users:** open Command Prompt or PowerShell and use `python`
> instead of `python3`.

---

## Step 2 — Configure `config.json`

Open `config.json` in any text editor. It looks like this:

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
    "max_results_per_keyword": 40
  }
}
```

### Keywords

```json
"keywords": ["iphone 13", "bicicleta montaña", "ps5"]
```

- Add as many terms as you like
- Searches are case-insensitive
- Accented characters work (`ñ`, `é`, `ü`)
- Phrases work — Wallapop will match listings containing all the words

### Check interval

```json
"check_interval_minutes": 5
```

How often the script wakes up and checks. Minimum is 1 minute.
5–10 minutes is a sensible balance between speed and server load.

### Max results per keyword

```json
"wallapop": {
  "max_results_per_keyword": 40
}
```

How many listings to fetch each time (newest first). Keep at 40 unless you
want a wider net on your first run.

---

## Step 3 — Set up email

The script needs an email account to send alerts from. You can send to
yourself (same address as sender).

### Gmail (recommended)

Google requires an **App Password** instead of your real password for scripts.

1. Make sure 2-Step Verification is on:
   <https://myaccount.google.com/security>
2. Go to App Passwords:
   <https://myaccount.google.com/apppasswords>
3. Click **Create** → name it anything (e.g. "Wallapop Alert")
4. Copy the 16-character code Google gives you

In `config.json`:

```json
"email": {
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "sender_email": "you@gmail.com",
  "sender_password": "abcd efgh ijkl mnop",
  "recipient_email": "you@gmail.com"
}
```

> Paste the 16-char App Password as `sender_password`, **not** your Gmail
> login password.

### Outlook / Hotmail

```json
"email": {
  "smtp_host": "smtp-mail.outlook.com",
  "smtp_port": 587,
  "sender_email": "you@outlook.com",
  "sender_password": "YOUR_OUTLOOK_PASSWORD",
  "recipient_email": "you@outlook.com"
}
```

### Yahoo Mail

1. Enable App Passwords: <https://help.yahoo.com/kb/generate-app-password>
2. Use:

```json
"email": {
  "smtp_host": "smtp.mail.yahoo.com",
  "smtp_port": 587,
  "sender_email": "you@yahoo.com",
  "sender_password": "YOUR_APP_PASSWORD",
  "recipient_email": "you@yahoo.com"
}
```

---

## Step 4 — Run the script

```bash
python3 wallapop_alert.py
```

You will see output like:

```
2024-03-15 10:00:01  INFO     =======================================================
2024-03-15 10:00:01  INFO     Wallapop Alert started
2024-03-15 10:00:01  INFO     Keywords : ['iphone 13', 'macbook pro']
2024-03-15 10:00:01  INFO     Interval : 5 min
2024-03-15 10:00:01  INFO     Notify   : you@gmail.com
2024-03-15 10:00:01  INFO     =======================================================
2024-03-15 10:00:01  INFO     Checking keyword: 'iphone 13'
2024-03-15 10:00:03  INFO       Loading Wallapop search for 'iphone 13'…
2024-03-15 10:00:07  INFO       → 38 new item(s) found — sending email
2024-03-15 10:00:08  INFO       Email sent — 38 item(s) for 'iphone 13'
2024-03-15 10:00:08  INFO     Checking keyword: 'macbook pro'
...
2024-03-15 10:00:14  INFO     Sleeping 5 minutes…
```

On the **first run** all listings found are emailed because nothing has been
seen before. From the second run onwards you only get alerts for genuinely
new listings.

Press `Ctrl+C` to stop.

---

## Running in the background

### Linux / macOS

```bash
nohup python3 wallapop_alert.py > alert.log 2>&1 &
echo "PID: $!"
```

Watch the logs live:

```bash
tail -f alert.log
```

Stop it:

```bash
# find the PID
ps aux | grep wallapop_alert.py
# then kill it
kill <PID>
```

### Windows (PowerShell)

```powershell
Start-Process python -ArgumentList "wallapop_alert.py" `
  -RedirectStandardOutput "alert.log" `
  -RedirectStandardError "alert_err.log" `
  -WindowStyle Hidden
```

### Run automatically at startup (Linux — systemd)

Create `/etc/systemd/system/wallapop-alert.service`:

```ini
[Unit]
Description=Wallapop Product Alert
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/wallapop_alert/wallapop_alert.py
WorkingDirectory=/path/to/wallapop_alert
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable wallapop-alert
sudo systemctl start wallapop-alert
sudo journalctl -u wallapop-alert -f   # live logs
```

---

## Managing keywords

Edit `config.json` and restart the script. Seen items are remembered in
`.seen_items.json`, so you will **never get duplicate emails** even after
adding or removing keywords and restarting.

To get a fresh email of all current listings for a keyword (e.g. after a
long break), delete `.seen_items.json` before starting the script.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ERROR: config.json is missing required key` | Misconfigured JSON | Open `config.json`, compare to the example above, check for missing commas or keys |
| `Failed to send email` | Wrong password or SMTP settings | For Gmail, make sure `sender_password` is an **App Password**, not your login password |
| `Authentication Required` from Gmail | 2FA not enabled or App Password not created | Follow the Gmail App Password steps in Step 3 |
| Script crashes with `playwright._impl._errors.Error` | Firefox not installed | Run `python3 -m playwright install firefox` |
| `No new items` every run but you expect results | All items already seen | Delete `.seen_items.json` to reset — you'll get one catch-up email |
| Lots of irrelevant results | Keyword too broad | Use more specific terms, e.g. `"iphone 13 128gb"` instead of `"iphone"` |
| Too many emails | Interval too short or keyword too broad | Increase `check_interval_minutes` and/or narrow keywords |
| Script exits immediately | Python version too old | Run `python3 --version` — needs 3.10 or newer |
