# Anonymous Questions Bot Deployment Guide

## Requirements

- Ubuntu 20.04+ or other Linux distribution
- Python 3.10 or higher
- PostgreSQL 12+
- Git
- systemd (for auto-start)

## Step-by-Step Instructions

### 1. Server Preparation

```bash
# System update
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.10 python3.10-venv python3-pip postgresql postgresql-contrib git

# Create user for bot
sudo useradd -m -s /bin/bash botuser
sudo su - botuser
```

### 2. PostgreSQL Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL console:
CREATE USER botanon WITH PASSWORD 'your_secure_password';
CREATE DATABASE dbfrombot OWNER botanon;
GRANT ALL PRIVILEGES ON DATABASE dbfrombot TO botanon;
\q
```

### 3. Clone and Setup Project

```bash
# As botuser
cd ~
git clone https://github.com/yourusername/anon-questions-bot.git
cd anon-questions-bot

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configuration Setup

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

Fill in all required parameters:
- `BOT_TOKEN` - token from @BotFather
- `ADMIN_ID` - your Telegram ID
- `BOT_USERNAME` - bot username (without @)
- Database parameters

### 5. Database Initialization

```bash
python reset_database.py
```

### 6. First Run (Test)

```bash
# Check readiness
python deployment_check.py

# If all checks pass, start the bot
python main.py
```

Make sure the bot responds to commands. Press Ctrl+C to stop.

### 7. Setup Auto-start via systemd

```bash
# Exit from botuser
exit

# Copy service file
sudo cp anon-questions-bot.service /etc/systemd/system/

# Edit paths in service file
sudo nano /etc/systemd/system/anon-questions-bot.service

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable anon-questions-bot

# Start the bot
sudo systemctl start anon-questions-bot

# Check status
sudo systemctl status anon-questions-bot
```

### 8. Log Setup

```bash
# Create logs directory if not exists
sudo -u botuser mkdir -p /home/botuser/anon-questions-bot/logs

# Setup logrotate
sudo nano /etc/logrotate.d/anon-questions-bot
```

Logrotate file content:
```
/home/botuser/anon-questions-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 botuser botuser
}
```

### 9. Firewall Setup (Optional)

```bash
# If using ufw
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 5432/tcp  # PostgreSQL (only if external access needed)
sudo ufw enable
```

## Maintenance

### View Logs

```bash
# Systemd logs
sudo journalctl -u anon-questions-bot -f

# Application logs
tail -f /home/botuser/anon-questions-bot/logs/bot.log
```

### Update Bot

```bash
# Stop bot
sudo systemctl stop anon-questions-bot

# Switch to bot user
sudo su - botuser
cd anon-questions-bot

# Get updates
git pull

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Exit user
exit

# Start bot
sudo systemctl start anon-questions-bot
```

### Database Backup

```bash
# Manual backup
pg_dump -U botanon -h localhost dbfrombot > backup_$(date +%Y%m%d_%H%M%S).sql

# Automatic backup via cron
crontab -e
# Add line:
0 3 * * * pg_dump -U botanon -h localhost dbfrombot > /home/botuser/backups/backup_$(date +\%Y\%m\%d).sql
```

## Monitoring

### Check Bot Operation

```bash
# Quick check
make prod-check

# Detailed status
sudo systemctl status anon-questions-bot
```

### Alert Setup

1. Configure Sentry DSN in `.env` for error tracking
2. Use external monitoring (e.g., UptimeRobot) for availability checks

## Troubleshooting

### Bot Won't Start

1. Check logs: `sudo journalctl -u anon-questions-bot -n 100`
2. Check file permissions
3. Ensure PostgreSQL is running
4. Verify .env file correctness

### Database Connection Errors

1. Check PostgreSQL is running: `sudo systemctl status postgresql`
2. Verify connection parameters in .env
3. Check database user permissions

### Bot Not Responding to Commands

1. Check BOT_TOKEN is correct
2. Ensure bot is not blocked in Telegram
3. Check logs for errors

## Security

1. **Never** commit .env file to git
2. Use strong passwords for database
3. Regularly update system and dependencies
4. Configure firewall
5. Use separate user for bot (not root)
6. Regular database backups