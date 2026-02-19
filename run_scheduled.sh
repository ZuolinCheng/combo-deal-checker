#!/bin/bash
# run_scheduled.sh — Cron wrapper with auto-expiry
# Runs combo deal checker every 2 hours, auto-removes cron job after EXPIRY_DATE.

PROJECT_DIR="/mnt/Work2/Projects/combo-deal-checker"
PYTHON="$PROJECT_DIR/.venv/bin/python3"
EXPIRY_DATE="2026-02-21"  # 3 days from 2026-02-18

# Check if expired
TODAY=$(date +%Y-%m-%d)
if [[ "$TODAY" > "$EXPIRY_DATE" ]]; then
    echo "$(date): Scheduled run expired ($EXPIRY_DATE). Removing cron job."
    crontab -l 2>/dev/null | grep -v "run_scheduled.sh" | crontab -
    exit 0
fi

# Run the deal checker
cd "$PROJECT_DIR"
echo "$(date): Starting combo deal checker"
$PYTHON main.py 2>&1
echo "$(date): Finished"
