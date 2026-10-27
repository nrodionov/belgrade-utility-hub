#!/bin/bash
# Kick the translation queue in PRODUCTION database (manual tool).
# Re-queues pending/failed events: fresh attempt budget, immediately eligible.
# NOTE: with the new retry policy (exponential backoff via next_attempt_at,
# MAX attempts via attempts) this is no longer needed on a schedule.

docker exec belgrade_db psql -U belgrade_user -d belgrade_monitor \
  -c "UPDATE events SET translation_status='pending', attempts=0, next_attempt_at=now() WHERE translation_status IN ('pending','failed');"
