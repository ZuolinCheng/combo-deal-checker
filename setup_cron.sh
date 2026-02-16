#!/bin/bash
# setup_cron.sh — Install cron job for combo deal checker on Ubuntu
# Usage: ./setup_cron.sh [path_to_project] [python_path]

set -e

PROJECT_DIR="${1:-$(pwd)}"
PYTHON="${2:-/usr/bin/python3}"

echo "Setting up cron job for Combo Deal Checker"
echo "  Project dir: $PROJECT_DIR"
echo "  Python: $PYTHON"

# Verify paths
if [ ! -f "$PROJECT_DIR/main.py" ]; then
    echo "ERROR: main.py not found in $PROJECT_DIR"
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: Python not found at $PYTHON"
    exit 1
fi

# Create log directory
mkdir -p "$PROJECT_DIR/logs"

# Add cron job (every 2 hours at minute 0)
CRON_CMD="0 */2 * * * cd $PROJECT_DIR && $PYTHON main.py >> $PROJECT_DIR/logs/cron.log 2>&1"

# Check if already installed
if crontab -l 2>/dev/null | grep -q "combo-deal-checker\|$PROJECT_DIR/main.py"; then
    echo "Cron job already exists. Replacing..."
    crontab -l 2>/dev/null | grep -v "$PROJECT_DIR/main.py" | crontab -
fi

(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "Cron job installed! Will run every 2 hours."
echo "Check logs at: $PROJECT_DIR/logs/cron.log"
echo ""
echo "To verify: crontab -l"
echo "To remove: crontab -l | grep -v '$PROJECT_DIR' | crontab -"
