# GA4 Anomaly Detection Agent — VPS Deployment Guide
================================================================

This guide walks you through deploying the GA4 Anomaly Agent on a
Linux VPS (Ubuntu 22.04 recommended) step by step.

Total time: ~45 minutes for first-time setup.

---

## WHAT YOU NEED BEFORE STARTING

1. A Linux VPS (Ubuntu 22.04) with SSH access
   - Recommended: DigitalOcean, Hetzner, Contabo (€4–8/month)
   - Minimum: 1 vCPU, 1GB RAM

2. A domain name (optional but nice for the dashboard UI)

3. API credentials (gather these before SSH-ing in):
   - GA4 Property ID (numeric) + Service Account JSON key
   - OpenAI API Key (from platform.openai.com)
   - Slack Bot Token (from api.slack.com)
   - Gmail App Password (from Google Account → Security)

---

## STEP 1: CONNECT TO YOUR VPS

```bash
ssh root@YOUR_VPS_IP
```

Update the system first:
```bash
apt update && apt upgrade -y
```

---

## STEP 2: INSTALL PYTHON & DEPENDENCIES

```bash
# Install Python 3.11 and pip
apt install -y python3.11 python3.11-pip python3.11-venv

# Install Git and Nginx (for serving the dashboard)
apt install -y git nginx

# Verify Python version
python3 --version   # Should show Python 3.11.x
```

---

## STEP 3: UPLOAD THE AGENT FILES

Option A — Clone from your private GitHub repo:
```bash
cd /var/www
git clone https://github.com/YOURUSERNAME/ga4-agent.git
cd ga4-agent
```

Option B — Upload via SCP from your local machine:
```bash
# Run this from YOUR LOCAL MACHINE (not VPS)
scp -r ./ga4-agent root@YOUR_VPS_IP:/var/www/
```

---

## STEP 4: CREATE PYTHON VIRTUAL ENVIRONMENT

```bash
cd /var/www/ga4-agent/backend

# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

You should see all packages install cleanly.

---

## STEP 5: UPLOAD YOUR GA4 SERVICE ACCOUNT JSON

From your LOCAL machine:
```bash
# Create secrets folder on VPS first
ssh root@YOUR_VPS_IP "mkdir -p /var/www/ga4-agent/backend/secrets"

# Upload your service account key
scp ./ga4-service-account.json root@YOUR_VPS_IP:/var/www/ga4-agent/backend/secrets/ga4-service-account.json
```

Secure the file:
```bash
chmod 600 /var/www/ga4-agent/backend/secrets/ga4-service-account.json
```

---

## STEP 6: CREATE YOUR .ENV FILE

```bash
cd /var/www/ga4-agent/backend

# Copy the example file
cp .env.example .env

# Open it for editing
nano .env
```

Fill in ALL values:
```
GA4_PROPERTY_ID=123456789
GA4_CREDENTIALS_PATH=secrets/ga4-service-account.json
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=#ga4-alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=youremail@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_EMAILS=client@example.com,you@agency.com
ZSCORE_THRESHOLD=2.0
PCT_DEVIATION_THRESHOLD=20.0
```

Save with Ctrl+O, then Ctrl+X.

Secure the .env file:
```bash
chmod 600 .env
```

---

## STEP 7: CREATE LOGS DIRECTORY

```bash
mkdir -p /var/www/ga4-agent/backend/logs
```

---

## STEP 8: TEST THE AGENT MANUALLY

```bash
cd /var/www/ga4-agent/backend
source venv/bin/activate
python agent.py
```

Watch the output. You should see:
```
2025-01-15 07:00:01 [INFO] GA4 Anomaly Agent started...
2025-01-15 07:00:02 [INFO] Step 1: Fetching GA4 data...
2025-01-15 07:00:04 [INFO] Fetched 35 rows...
2025-01-15 07:00:04 [INFO] Step 2: Running anomaly detection...
...
2025-01-15 07:00:09 [INFO] ✅ Agent run complete.
```

If you see errors, check:
- GA4: "PERMISSION_DENIED" → service account not added to GA4 property
- OpenAI: "AuthenticationError" → check OPENAI_API_KEY in .env
- Slack: "not_in_channel" → invite the bot: /invite @YourBotName
- Email: "SMTPAuthenticationError" → use Gmail App Password, not regular password

---

## STEP 9: SCHEDULE WITH CRON (Runs Daily at 7 AM)

```bash
# Open crontab for root user
crontab -e
```

Add this line at the bottom (press I to insert in vim):
```
# GA4 Anomaly Agent — run every day at 7:00 AM
0 7 * * * cd /var/www/ga4-agent/backend && /var/www/ga4-agent/backend/venv/bin/python agent.py >> logs/cron.log 2>&1
```

Save and exit (Esc → :wq in vim, or Ctrl+O, Ctrl+X in nano).

Verify the cron was saved:
```bash
crontab -l
```

The agent will now run automatically every day at 7:00 AM server time.

---

## STEP 10: CHECK SERVER TIMEZONE

Your alerts will go out at 7 AM in the server's timezone.
To check and set timezone:

```bash
# Check current timezone
timedatectl

# Set to Berlin (Germany)
timedatectl set-timezone Europe/Berlin

# Verify
timedatectl
```

---

## STEP 11: SERVE THE FRONTEND DASHBOARD (OPTIONAL)

Copy the frontend to nginx's web root:
```bash
cp -r /var/www/ga4-agent/frontend/* /var/www/html/
```

Or configure a virtual host for a subdomain:
```bash
nano /etc/nginx/sites-available/ga4-agent
```

Paste:
```nginx
server {
    listen 80;
    server_name ga4agent.yourdomain.com;
    root /var/www/ga4-agent/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

Enable it:
```bash
ln -s /etc/nginx/sites-available/ga4-agent /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

Add HTTPS with Let's Encrypt (free):
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d ga4agent.yourdomain.com
```

---

## STEP 12: SET UP SYSTEMD SERVICE (OPTIONAL — ALTERNATIVE TO CRON)

Use this if you prefer a persistent process over cron:

```bash
nano /etc/systemd/system/ga4-agent.service
```

Paste:
```ini
[Unit]
Description=GA4 Anomaly Detection Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/ga4-agent/backend
ExecStart=/var/www/ga4-agent/backend/venv/bin/python scheduler.py
Restart=always
RestartSec=10
StandardOutput=append:/var/www/ga4-agent/backend/logs/service.log
StandardError=append:/var/www/ga4-agent/backend/logs/service.log

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl daemon-reload
systemctl enable ga4-agent
systemctl start ga4-agent

# Check status
systemctl status ga4-agent

# View live logs
journalctl -u ga4-agent -f
```

---

## MONITORING YOUR AGENT

View last 50 log lines:
```bash
tail -50 /var/www/ga4-agent/backend/logs/agent.log
```

Watch live (after manual trigger or cron):
```bash
tail -f /var/www/ga4-agent/backend/logs/cron.log
```

Check if cron ran today:
```bash
grep "$(date +%Y-%m-%d)" /var/www/ga4-agent/backend/logs/agent.log
```

---

## UPDATING THE AGENT

When you push changes to GitHub:
```bash
cd /var/www/ga4-agent
git pull origin main
source backend/venv/bin/activate
pip install -r backend/requirements.txt

# If using systemd
systemctl restart ga4-agent
```

---

## FILE STRUCTURE REFERENCE

```
ga4-agent/
├── backend/
│   ├── agent.py              # Main orchestrator — run this
│   ├── ga4_client.py         # GA4 API data fetcher
│   ├── anomaly_detector.py   # Z-score + rolling avg detection
│   ├── hypothesis_generator.py # GPT-4o root-cause analysis
│   ├── slack_notifier.py     # Slack Block Kit alerts
│   ├── email_notifier.py     # SMTP email digest
│   ├── report_builder.py     # Formats alerts for Slack + email
│   ├── scheduler.py          # Daily schedule runner (alternative to cron)
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Template for .env
│   ├── .env                  # YOUR secrets (never commit to Git!)
│   ├── secrets/
│   │   └── ga4-service-account.json  # Your GA4 service account key
│   └── logs/
│       ├── agent.log         # Main run log
│       └── cron.log          # Cron output
└── frontend/
    └── index.html            # Web dashboard
```

---

## GITIGNORE — PROTECT YOUR SECRETS

Make sure your .gitignore contains:
```
.env
secrets/
logs/
__pycache__/
*.pyc
venv/
```

---

## COMMON ERRORS & FIXES

| Error | Cause | Fix |
|-------|-------|-----|
| PERMISSION_DENIED (GA4) | Service account not added | GA4 Admin → Access Management → add email |
| AuthenticationError (OpenAI) | Wrong API key | Double-check OPENAI_API_KEY in .env |
| not_in_channel (Slack) | Bot not in channel | /invite @YourBotName in the channel |
| SMTPAuthenticationError | Wrong email password | Use Gmail App Password, not login password |
| FileNotFoundError (credentials) | Wrong path | Check GA4_CREDENTIALS_PATH in .env |
| ModuleNotFoundError | venv not activated | source venv/bin/activate |

---

## RESUME BULLET (copy exactly)

> Developed a Python + GA4 API anomaly detection agent that monitors
> daily traffic and conversion data, flags anomalies with root-cause
> hypotheses, and delivers automated Slack and email digests to
> stakeholders.
