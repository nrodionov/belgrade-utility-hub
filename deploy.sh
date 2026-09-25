#!/bin/bash
set -e
if [ ! -f .env ]; then
  echo "Error: .env file missing."
  exit 1
fi
docker compose up -d --build
docker exec belgrade_db psql -U belgrade_user -d belgrade_monitor -c "ALTER TABLE events ADD COLUMN IF NOT EXISTS translation_status text DEFAULT 'pending';"
docker exec belgrade_db psql -U belgrade_user -d belgrade_monitor -c "ALTER TABLE events ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;"
chmod +x ./reset_failed.sh
(crontab -l 2>/dev/null | grep -v "reset_failed.sh"; echo "0 4 * * * /root/selfcheck/belgrade_bg/reset_failed.sh") | crontab -
echo "Deployment finished."
