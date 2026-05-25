# Belgrade Utility Hub 🇷🇸

A high-fidelity urban monitoring dashboard for Belgrade, Serbia. Automatically tracks utility outages, transport changes, air quality, and city events from official sources.

## 🚀 Features

- **Real-time Monitoring**:
    - ⚡ **Electricity**: Planned outages from EDS (Elektrodistribucija Srbije).
    - 💧 **Water**: Emergency repairs and maintenance from BVK (Beogradski Vodovod).
    - 🚌 **Public Transport**: Deep-link scraping of detours and stop changes from BGPrevoz.
    - 🛣️ **Traffic**: Road closures and regime changes from the Secretariat for Transport.
    - 🍃 **Ecology**: Air Quality Index (AQI) from Beoeko.
    - 🏙️ **Events**: Major city news, protests, and strikes.
- **Multi-language Support**: Full localization in Serbian (Latin/Cyrillic), Russian, and English.
- **Smart Text Processing**: Automatic text cleaning and intelligent chunked translation.
- **Mobile Responsive**: Dark-mode UI optimized for both desktop and mobile users.

## 🛠 Tech Stack

- **Frontend**: FastAPI (Jinja2 Templates), Tailwind CSS, FontAwesome.
- **Backend**: Python (Asyncio), aiohttp, BeautifulSoup4.
- **Database**: PostgreSQL 15.
- **Infrastructure**: Docker Compose, Nginx Reverse Proxy.
- **Translation**: Deep Translator (Google API) with intelligent chunking.

## 🚦 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/belgrade-hub.git
cd belgrade-hub
```

### 2. Configure Environment
Copy the example environment file and fill in your secure credentials:
```bash
cp .env.example .env
nano .env
```

### 3. Deploy with Docker
```bash
docker-compose up -d --build
```
The application will be available at `http://localhost:8000`.

## 📂 Project Structure

- `scraper/`: Async Python service that polls official sources every 30 minutes.
- `web/`: FastAPI web server and responsive templates.
- `init_db/`: Initial database schema for automated setup.
- `docker-compose.yml`: Full container orchestration and resource management.

## 🛡 Resource Management

The scraper is configured with hard limits to ensure server stability:
- **Memory Limit**: 512MB RAM.
- **CPU Limit**: 0.5 Cores.
- **Throttling**: Sequential processing with mandatory delays between translation chunks and database writes.

## 📜 License
MIT License. Created for the Belgrade community.
