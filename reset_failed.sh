#!/bin/bash
docker exec belgrade_db_hm psql -U belgrade_user -d belgrade_monitor -c "UPDATE events SET translation_status = 'pending', retry_count = 0 WHERE translation_status = 'failed';"
