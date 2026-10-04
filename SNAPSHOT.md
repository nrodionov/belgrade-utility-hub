# Belgrade Utility Hub - System Snapshot (2026-09-19)

## Current Status
- **Production (bg.ss.ru)**: Stable. Running from `/root/selfcheck/belgrade_bg`.
- **Development (hm.ss.ru)**: Stable. Running from `/root/selfcheck/belgrade_hm`.

## Critical Configuration

### Networking & Proxy
- **Scraper Proxy**: Must route all outbound traffic through `http://v.ss.ru:8888`.
  - Configured in: `/root/selfcheck/belgrade_hm/docker-compose.yml` (environment variables `HTTP_PROXY`, `HTTPS_PROXY`).
- **Production Ports**: `bg.ss.ru` maps to host `127.0.0.1:8000`.
- **Dev Ports**: `hm.ss.ru` maps to host `8002:8000`.

### Translation (Groq)
- **Model**: `qwen/qwen3.8-27b`
- **Configuration**: Set in `/root/selfcheck/belgrade_hm/.env` via `GROQ_API_KEY`.

### Database
- **Host**: `db` (internal container name).
- **Credentials**: `belgrade_user:belgrade_password@db:5432/belgrade_monitor` (configured in `.env`).

## Recovery Procedure
If the scraper or web services become unstable:
1. Ensure the `v.ss.ru:8888` proxy is reachable from the host.
2. Verify `.env` file exists with correct `GROQ_API_KEY` and `DATABASE_URL`.
3. Use `docker compose -f <compose_file> up -d --force-recreate` to reset containers.
4. If translation fails, check logs for `403 Forbidden` (indicates invalid API key) or `429 Too Many Requests` (daily token limit hit).
