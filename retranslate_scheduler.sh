#!/bin/bash
# Path to the project directory
PROJECT_DIR="/root/selfcheck/belgrade-utility-hub"
LOG_FILE="/var/log/retranslate.log"

cd $PROJECT_DIR

# Check if there are events needing translation (title_ru is still Serbian title or NULL)
# Based on our previous check, if title_ru is still Serbian, we need to retranslate.
# We'll count rows where title_sr and title_ru are the same.
PENDING=$(docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T db psql -U belgrade_user -d belgrade_monitor -t -c "SELECT count(*) FROM events WHERE title_sr = title_ru OR title_ru IS NULL;" | tr -d '[:space:]')

echo "$(date): Found $PENDING events needing translation." >> $LOG_FILE

if [ "$PENDING" -gt 0 ]; then
    echo "$(date): Starting retranslation..." >> $LOG_FILE
    docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T scraper python3 retranslate_fixed.py >> $LOG_FILE 2>&1
    echo "$(date): Retranslation cycle finished." >> $LOG_FILE
else
    echo "$(date): Database is up to date." >> $LOG_FILE
fi
