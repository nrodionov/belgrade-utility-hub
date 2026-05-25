import asyncio, aiohttp, asyncpg, hashlib, logging, os, pytz, re, traceback
import cyrtranslit
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

DB_URL = os.getenv("DATABASE_URL")
TZ = pytz.timezone("Europe/Belgrade")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}

MUNICIPALITIES_SR = ["Барајево", "Чукарица", "Гроцка", "Лазаревац", "Младеновац", "Нови Београд", "Обреновац", "Палилула", "Раковица", "Савски венац", "Сопот", "Стари град", "Сурчин", "Вождовац", "Врачар", "Земун", "Звездара"]
MUNICIPALITIES = ["Barajevo", "Čukarica", "Grocka", "Lazarevac", "Mladenovac", "Novi Beograd", "Obrenovac", "Palilula", "Rakovica", "Savski venac", "Sopot", "Stari grad", "Surčin", "Voždovac", "Vračar", "Zemun", "Zvezdara"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def to_latin(text):
    if not text: return ""
    try: return cyrtranslit.to_latin(text, "sr")
    except: return text

def parse_dates(text):
    if not text: return None, None
    found = []
    p1 = re.findall(r'(\d{1,2})\s*[\./]\s*(\d{1,2})\s*[\./]\s*(\d{4})', text)
    for d, m, y in p1:
        try: found.append(datetime(int(y), int(m), int(d), tzinfo=TZ))
        except: pass
    if not found: return None, None
    found.sort()
    return (found[0], (found[-1] if len(found) > 1 else None))

def clean_text(text):
    if not text: return ""
    text = re.sub(r'[\n\r\t]+', ' ', text)
    text = re.sub(r' +', ' ', text).strip()
    return text

def detect_municipality(text):
    if not text: return None
    t_low = text.lower()
    for sr, en in sorted(zip(MUNICIPALITIES_SR, MUNICIPALITIES), key=lambda x: len(x[0]), reverse=True):
        if sr.lower() in t_low or en.lower() in t_low: return en
    return None

async def translate_safe(text, target):
    if not text or len(text) < 5: return text
    # Very aggressive chunking for memory safety
    MAX_CHUNK = 800 
    chunks = [text[i:i+MAX_CHUNK] for i in range(0, len(text), MAX_CHUNK)]
    translated = []
    for c in chunks:
        try:
            res = GoogleTranslator(source='auto', target=target).translate(c)
            translated.append(res if res else c)
        except: translated.append(c)
        await asyncio.sleep(2) # Strong throttling
    return " ".join(translated)

async def save_event(conn, event):
    try:
        clean_sr = clean_text(event['description_sr'])
        muni = event.get('municipality') or detect_municipality(event['title_sr'] + " " + clean_sr)
        
        # Check if already exists with good description
        row = await conn.fetchrow("SELECT description_sr FROM events WHERE hash_id = $1", event['hash_id'])
        if row and len(row['description_sr']) >= len(clean_sr): return

        t_ru = await translate_safe(event['title_sr'], 'ru')
        t_en = await translate_safe(event['title_sr'], 'en')
        raw_ru = await translate_safe(clean_sr, 'ru')
        raw_en = await translate_safe(clean_sr, 'en')

        await conn.execute("""
            INSERT INTO events (category, title_sr, title_ru, title_en, title_sl, description_sr, description_ru, description_en, description_sl, region, municipality, start_time, end_time, source_url, hash_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            ON CONFLICT (hash_id) DO UPDATE SET 
                description_sr = EXCLUDED.description_sr,
                description_ru = EXCLUDED.description_ru,
                description_en = EXCLUDED.description_en,
                source_url = EXCLUDED.source_url
        """, event['category'], event['title_sr'], t_ru, t_en, to_latin(event['title_sr']), 
           clean_sr, raw_ru, raw_en, to_latin(clean_sr), 
           event['region'], muni, event['start_time'], event['end_time'], event['source_url'], event['hash_id'])
    except Exception as e: logging.error(f"Save error: {e}")

async def scrape_electricity(session):
    events = []
    for i in range(3):
        url = f"https://elektrodistribucija.rs/planirana-iskljucenja-beograd/Dan_{i}_Iskljucenja.htm"
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as resp:
                if resp.status != 200: continue
                soup = BeautifulSoup(await resp.text(), 'lxml')
                # Find the correct table (one that has data rows)
                target_table = None
                for t in soup.find_all('table'):
                    if len(t.find_all('tr')) > 1:
                        txt = t.get_text()
                        if "Општина" in txt or "Opština" in txt:
                            target_table = t
                            break
                if not target_table: continue
                
                # Parse date from the page header if present
                date_tag = soup.find('b')
                f_date = None
                if date_tag:
                    d_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_tag.get_text())
                    if d_match:
                        y, m, d = d_match.groups()
                        f_date = datetime(int(y), int(m), int(d), tzinfo=TZ)
                
                f_date = f_date or (datetime.now(TZ) + timedelta(days=i))
                
                for row in target_table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        m_sr, t_rng, strs = cols[0].get_text(strip=True), cols[1].get_text(strip=True), cols[2].get_text(strip=True)
                        if not m_sr or m_sr == "Општина": continue
                        
                        start_time = f_date.replace(hour=8, minute=0, second=0, microsecond=0)
                        end_time = f_date.replace(hour=16, minute=0, second=0, microsecond=0)

                        # Try to parse exact hours from t_rng (e.g. "08:30 - 10:30")
                        h_match = re.search(r'(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})', t_rng)
                        if h_match:
                            h1, m1, h2, m2 = h_match.groups()
                            start_time = start_time.replace(hour=int(h1), minute=int(m1))
                            end_time = start_time.replace(hour=int(h2), minute=int(m2))
                            
                        events.append({
                            'category': 'electricity', 
                            'title_sr': f"Струја ({t_rng}): {m_sr}", 
                            'description_sr': f"Општина: {m_sr}\nВреме: {t_rng}\nУлице: {strs}", 
                            'region': "Beograd", 
                            'municipality': detect_municipality(m_sr),
                            'start_time': start_time, 
                            'end_time': end_time, 
                            'source_url': url, 
                            'hash_id': hashlib.sha256(f"elec:{strs[:50]}:{start_time.date()}".encode()).hexdigest()
                        })
        except Exception as e:
            logging.error(f"Error scraping electricity Day {i}: {e}")
    return events

async def scrape_water(session):
    urls = [("https://www.bvk.rs/planirani-radovi/", "water"), ("https://www.bvk.rs/kvarovi-na-mrezi/", "water")]
    events = []
    for url, cat in urls:
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as resp:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                for toggle in soup.select('.toggler'):
                    t_text = toggle.get_text(strip=True)
                    content = toggle.find_next('div', class_='toggle_wrap')
                    desc = content.get_text(strip=True) if content else t_text
                    s_date, _ = parse_dates(t_text + desc)
                    s_date = s_date or datetime.now(TZ)
                    events.append({'category': 'water', 'title_sr': t_text, 'description_sr': desc, 'region': "Beograd", 'start_time': s_date.replace(hour=8, minute=0, second=0, microsecond=0), 'end_time': s_date.replace(hour=20, minute=0, second=0, microsecond=0), 'source_url': url, 'hash_id': hashlib.sha256(f"water:{t_text}".encode()).hexdigest()})
        except: pass
    return events

async def scrape_transport(session):
    events = []
    url_base = "https://www.bgprevoz.rs"
    url_gsp = f"{url_base}/izmena-rezima/aktuelne-izmene"
    try:
        async with session.get(url_gsp, headers=HEADERS, timeout=20) as resp:
            soup = BeautifulSoup(await resp.text(), 'lxml')
            for row in soup.select('tr.aktuelne_izmene'):
                cols = row.select('td')
                if len(cols) < 2: continue
                title = cols[0].get_text(strip=True)
                link = row.find('a', href=re.compile(r'/linije/aktuelne-izmene/\d+'))
                detail_url = (url_base + link['href'] if not link['href'].startswith('http') else link['href']) if link else url_gsp
                description = title
                if link:
                    try:
                        async with session.get(detail_url, headers=HEADERS, timeout=20) as d_resp:
                            d_soup = BeautifulSoup(await d_resp.text(), 'lxml')
                            main_tag = d_soup.find('main')
                            if main_tag: description = main_tag.get_text(separator=' ', strip=True)
                    except: pass
                events.append({'category': 'transport', 'title_sr': title, 'description_sr': description, 'region': "Beograd", 'start_time': datetime.now(TZ), 'end_time': datetime.now(TZ)+timedelta(days=2), 'source_url': detail_url, 'hash_id': hashlib.sha256(title.encode()).hexdigest()})
    except: pass
    return events

async def run_cycle():
    while True:
        try:
            conn = await asyncpg.connect(DB_URL)
            async with aiohttp.ClientSession() as session:
                logging.info("Starting sequential scrape...")
                # Sequential to save memory
                for func in [scrape_electricity, scrape_water, scrape_transport]:
                    evs = await func(session)
                    for e in evs: 
                        await save_event(conn, e)
                        await asyncio.sleep(0.5) # Throttle DB writes
                await conn.execute("UPDATE system_stats SET val_ts = $1 WHERE key = 'last_scrape'", datetime.now(pytz.utc))
                logging.info("Scrape cycle complete. Sleeping 30m.")
            await conn.close()
        except Exception as e: logging.error(f"Cycle error: {e}")
        await asyncio.sleep(1800)

if __name__ == "__main__":
    asyncio.run(run_cycle())
