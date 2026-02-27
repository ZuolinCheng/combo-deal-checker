#!/bin/bash
# run_scheduled.sh — Cron wrapper with auto-expiry
# Schedule: hourly 8AM-4AM, every 2h 4AM-8AM
# Auto-removes cron job after EXPIRY_DATE.

PROJECT_DIR="/Users/zc/Desktop/ClaudeCode/Projects/Computer/combo-deal-checker"
PYTHON="/opt/anaconda3/bin/python"
EXPIRY_DATE="2026-03-05"  # 7 days from 2026-02-26

# Check if expired
TODAY=$(date +%Y-%m-%d)
if [[ "$TODAY" > "$EXPIRY_DATE" ]]; then
    echo "$(date): Scheduled run expired ($EXPIRY_DATE). Removing cron job."
    crontab -l 2>/dev/null | grep -v "combo-deal-checker" | crontab -
    exit 0
fi

# Run the deal checker
cd "$PROJECT_DIR"
echo "$(date): Starting combo deal checker"
$PYTHON main.py 2>&1
echo "$(date): Finished"
