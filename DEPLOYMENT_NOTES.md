# Deployment Notes for belgrade-utility-hub

This document summarizes the Nginx and Docker configuration for the production and development environments.

> **Server Hosting Note:** Both environments (`https://bg.ss.ru` and `https://hm.ss.ru`) are hosted on the same server `hm.ss.ru`. Server access is direct via `ssh hm.ss.ru` without any additional workarounds.

## Production (`https://bg.ss.ru`)

*   **Nginx Config File:** `/etc/nginx/sites-available/bg.ss.ru`
*   **Public Port:** `443` (HTTPS)
*   **Proxy Target:** `http://127.0.0.1:8000`
*   **Docker Container:** `belgrade_web`

## Development (`https://hm.ss.ru`)

*   **Nginx Config File:** `/etc/nginx/sites-available/hm.ss.ru`
*   **Public Port:** `443` (HTTPS)
*   **Proxy Target:** `http://127.0.0.1:8002`
*   **Docker Container:** `belgrade_web_hm`
