import asyncio, aiohttp, asyncpg, hashlib, logging, os, pytz, re, json
import cyrtranslit
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from groq import Groq


DB_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TZ = pytz.timezone("Europe/Belgrade")

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

MUNICIPALITIES = ["Barajevo", "Čukarica", "Grocka", "Lazarevac", "Mladenovac", "Novi Beograd", "Obrenovac", "Palilula", "Rakovica", "Savski venac", "Sopot", "Stari grad", "Surčin", "Voždovac", "Vračar", "Zemun", "Zvezdara"]
MUNICIPALITIES_SR = ["Барајево", "Чукарица", "Гроцка", "Лазаревац", "Младеновац", "Нови Београд", "Обреновац", "Палилула", "Раковица", "Савски венац", "Сопот", "Стари град", "Сурчин", "Вождовац", "Врачар", "Земун", "Звездара"]

TYPO_MAP = {
    "страи град": "Stari grad",
    "стари гард": "Stari grad",
    "воздовац": "Voždovac",
    "вождовац": "Voždovac",
    "чукарица": "Čukarica",
    "звездара": "Zvezdara",
    "савски венац": "Savski venac",
    "нови београд": "Novi Beograd"
}

REDUNDANT_PHRASES = [
    r'Opširnije', r'Опширније', r'Более подробно', r'In more detail', 
    r'Pročitajte više', r'Saznajte više', r'Read more'
]

CONNECTIVITY_KEYWORDS = ["internet", "mreža", "mreži", "prekid", "smetnje", "radovi", "modernizacija", "5g", "optika"]

MONTHS_MAP = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "maj": 5, "jun": 6, "jul": 7, "avg": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12}

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
    p2 = re.findall(r'(\d{4})-(\d{2})-(\d{2})', text)
    for y, m, d in p2:
        try: found.append(datetime(int(y), int(m), int(d), tzinfo=TZ))
        except: pass
    month_regex = "|".join(MONTHS_MAP.keys())
    p3 = re.findall(r'(\d{1,2})\.\s*(' + month_regex + r')[a-z]*\s*(\d{4})', text, re.IGNORECASE)
    for d, m_name, y in p3:
        try: found.append(datetime(int(y), MONTHS_MAP[m_name.lower()[:3]], int(d), tzinfo=TZ))
        except: pass
    p4 = re.search(r'(\d{1,2})-(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    if p4:
        d1, d2, m, y = p4.groups()
        try:
            found.append(datetime(int(y), int(m), int(d1), tzinfo=TZ))
            found.append(datetime(int(y), int(m), int(d2), tzinfo=TZ))
        except: pass
    if not found: return None, None
    found.sort()
    unique_found = []
    for f in found:
        if f not in unique_found: unique_found.append(f)
    if len(unique_found) >= 2: return unique_found[0], unique_found[-1]
    if len(unique_found) == 1: return unique_found[0], None
    return None, None

def clean_text(text):
    if not text: return ""
    for phrase in REDUNDANT_PHRASES:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)
    text = re.sub(r'[ \t]+', ' ', text)
    for m in MUNICIPALITIES_SR + ["ВРАЧАР", "ВОЖДОВАЦ", "ЗВЕЗДАРА", "ЗЕМУН", "НОВИ БЕОГРАД", "ПАЛИЛУЛА", "РАКОВИЦА", "САВСКИ ВЕНАЦ", "СТАРИ ГРАД"]:
        text = re.sub(f'({m})([А-ЯA-Z][а-яa-z])', r'\1 \2', text)
        text = re.sub(f'([а-яa-z])({m})', r'\1 \2', text)
    for m in MUNICIPALITIES_SR + MUNICIPALITIES + ["Воздовац", "Савски венац", "Стари град"]:
        text = re.sub(f'({m}:)', r'\n• \1', text, flags=re.IGNORECASE)
    text = re.sub(r'(\bДо \d{2}:\d{2})', r'\n📍 \1', text)
    text = re.sub(r'(\bUntil \d{2}:\d{2})', r'\n📍 \1', text)
    text = re.sub(r'([а-яa-z)])\.([А-ЯA-Z])', r'\1.\n\2', text)
    text = re.sub(r'(\d+)\s?([А-ЯA-Z][а-яa-z]{3,})', r'\1\n• \2', text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return '\n'.join(lines)

def detect_municipalities(text):
    if not text: return []
    t_low = text.lower()
    found = set()
    for sr, en in zip(MUNICIPALITIES_SR, MUNICIPALITIES):
        if sr.lower() in t_low or en.lower() in t_low:
            found.add(en)
    for typo, correct_en in TYPO_MAP.items():
        if typo in t_low:
            found.add(correct_en)
    return list(found)

def log_rate_limits(response):
    if response and hasattr(response, 'headers'):
        h = response.headers
        logging.info(f"Rate Limit Status: Tokens-Remaining={h.get('x-ratelimit-remaining-tokens')}, Requests-Remaining={h.get('x-ratelimit-remaining-requests')}, Reset={h.get('x-ratelimit-reset-tokens')}")

async def translate_both(text, model="qwen/qwen3.8-27b"):
    """Translate text into Russian and English in a single Groq API call with fallback support."""
    if not text: return "", ""

    # Specific fix for Air Quality to avoid hallucinations
    if "Ваздух:" in text or "Vazduh:" in text:
        mapping = {"NIZAK!": ("НИЗКИЙ!", "Low"), "SREDNJI!": ("СРЕДНИЙ!", "Moderate"), "VISOK!": ("ВЫСОКИЙ!", "High")}
        for sr_val, (ru_val, en_val) in mapping.items():
            if sr_val in text:
                t_ru = text.replace("Ваздух:", "Воздух:").replace("Vazduh:", "Воздух:").replace(sr_val, ru_val)
                t_en = text.replace("Ваздух:", "Air Quality:").replace("Vazduh:", "Air Quality:").replace(sr_val, en_val)
                return t_ru, t_en

    # Protect dates from translation
    dates = re.findall(r'\d{1,2}[\./\s]+\d{1,2}[\./\s]+\d{4}', text)
    for i, d in enumerate(dates):
        text = text.replace(d, f" [[DATE{i}]] ")

    if not groq_client:
        return text, text

    try:
        system_prompt = """You are a professional translator. 
Translate the provided Serbian text into BOTH Russian and English.

CRITICAL RULES:
1. Keep ALL place names, street names, municipality names EXACTLY as they appear in Serbian.
2. Return ONLY valid JSON: {"ru": "...", "en": "..."}
3. Translate ONLY the description, not the locations.
"""

        response = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:4000]}
            ],
            temperature=0.3,
            max_tokens=4096,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content.strip())
        t_ru, t_en = result.get('ru'), result.get('en')
        
        if not t_ru or not t_en:
            raise ValueError("Translation returned empty fields")

        for i, d in enumerate(dates):
            t_ru = re.sub(rf'\[\[DATE{i}\]\]', d, t_ru, flags=re.IGNORECASE)
            t_en = re.sub(rf'\[\[DATE{i}\]\]', d, t_en, flags=re.IGNORECASE)

        return t_ru, t_en

    except Exception as e:
        if hasattr(e, 'response') and e.response is not None:
            log_rate_limits(e.response)
        raise e

async def save_event(conn, event):
    try:
        raw_sr = event['description_sr']
        clean_sr = clean_text(raw_sr)
        if not clean_sr and raw_sr:
            clean_sr = raw_sr
        
        munis = event.get('municipalities') or detect_municipalities(event['title_sr'] + " " + clean_sr)
        end_t = event.get('end_time')
        if not end_t:
            if event['category'] in ['water', 'electricity', 'heating', 'ecology', 'connectivity']: end_t = event['start_time'].replace(hour=23, minute=59)
            else: end_t = event['start_time'] + timedelta(days=2)

        row = await conn.fetchrow("SELECT id FROM events WHERE hash_id = $1", event['hash_id'])
        
        if row:
            await conn.execute("""
                UPDATE events SET 
                    end_time = $1,
                    municipality = $2,
                    title_sr = $3,
                    description_sr = $4,
                    title_sl = $5,
                    description_sl = $6
                WHERE hash_id = $7
            """, end_t, munis if munis else None, event['title_sr'], clean_sr, to_latin(event['title_sr']), to_latin(clean_sr),
               event['hash_id'])
            return

        logging.info(f"Saving new: {event['category']} - {event['title_sr'][:30]}")
        
        await conn.execute("""
            INSERT INTO events (category, title_sr, title_sl, description_sr, description_sl, region, municipality, start_time, end_time, source_url, hash_id, translation_status, retry_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'pending', 0)
        """, event['category'], event['title_sr'], to_latin(event['title_sr']), clean_sr, to_latin(clean_sr), 
           event['region'], munis if munis else None, event['start_time'], end_t, event['source_url'], event['hash_id'])
    except Exception as e: logging.error(f"Save error: {e}")

async def scrape_electricity(session):
    events = []
    for i in range(4):
        url = f"https://elektrodistribucija.rs/planirana-iskljucenja-beograd/Dan_{i}_Iskljucenja.htm"
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as resp:
                if resp.status != 200: continue
                soup = BeautifulSoup(await resp.text(), 'lxml')
                date_tag = soup.find(['b', 'B'])
                s_date, _ = parse_dates(date_tag.get_text() if date_tag else None)
                f_date = s_date or (datetime.now(TZ) + timedelta(days=i))
                target_table = None
                for t in soup.find_all(['table', 'TABLE']):
                    if len(t.find_all(['tr', 'TR'])) > 1:
                        txt = t.get_text()
                        if "Општина" in txt or "Opština" in txt: target_table = t; break
                if not target_table: continue
                for row in target_table.find_all(['tr', 'TR'])[1:]:
                    cols = row.find_all(['td', 'TD'])
                    if len(cols) >= 3:
                        m_sr, t_rng, strs = cols[0].get_text(strip=True), cols[1].get_text(strip=True), cols[2].get_text(strip=True)
                        if not m_sr or m_sr == "Општина": continue
                        start_time = f_date.replace(hour=8, minute=0)
                        h_match = re.search(r'(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})', t_rng)
                        end_time = start_time.replace(hour=16, minute=0)
                        if h_match:
                            h1, m1, h2, m2 = h_match.groups()
                            start_time = start_time.replace(hour=int(h1), minute=int(m1))
                            end_time = start_time.replace(hour=int(h2), minute=int(m2))
                        events.append({'category': 'electricity', 'title_sr': f"Струја ({t_rng}): {m_sr}", 'description_sr': f"Општина: {m_sr}\nВреме: {t_rng}\nУлице: {strs}", 'region': "Beograd", 'municipalities': detect_municipalities(m_sr), 'start_time': start_time, 'end_time': end_time, 'source_url': url, 'hash_id': hashlib.sha256(f"elec:{strs[:50]}:{start_time.date()}".encode()).hexdigest()})
        except: pass
    return events

async def scrape_water(session):
    urls = [("https://www.bvk.rs/planirani-radovi/", "water"), ("https://www.bvk.rs/kvarovi-na-mrezi/", "water")]
    events = []
    for url, cat in urls:
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as resp:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                for toggle in soup.select('.toggler'):
                    t_text = toggle.get('data-title') or toggle.get_text(strip=True)
                    if not t_text: continue
                    content_div = toggle.find_next('div', class_='toggle_wrap')
                    desc = content_div.get_text(separator=' ', strip=True) if content_div else ""
                    s_date, e_date = parse_dates(t_text + " " + desc)
                    s_date = s_date or datetime.now(TZ)
                    if not e_date: e_date = s_date.replace(hour=23, minute=59)
                    clean_title = t_text
                    if re.match(r'^\d{1,2}[\./\s]+\d.[\./\s]+\d{4}\.?$', t_text): clean_title = f"Водовод: Радови {t_text}"
                    events.append({'category': 'water', 'title_sr': clean_title, 'description_sr': desc, 'region': "Beograd", 'municipalities': detect_municipalities(t_text + " " + desc), 'start_time': s_date.replace(hour=8, minute=0), 'end_time': e_date.replace(hour=23, minute=59), 'source_url': url, 'hash_id': hashlib.sha256(f"water:{t_text}:{s_date.date()}".encode()).hexdigest()})
        except: pass
    return events

async def scrape_transport(session):
    events = []
    list_url = "https://www.bgprevoz.rs/linije/aktuelne-izmene"
    try:
        async with session.get(list_url, headers=HEADERS, timeout=30) as resp:
            if resp.status != 200:
                logging.error(f"Transport list {list_url} returned status {resp.status}")
                return events
            soup = BeautifulSoup(await resp.text(), 'lxml')
            links = set()
            for a in soup.find_all('a', href=re.compile(r'/linije/aktuelne-izmene/\d+$')):
                url = a['href']
                if not url.startswith('http'): url = "https://www.bgprevoz.rs" + url
                links.add(url)
            
            for url in links:
                try:
                    async with session.get(url, headers=HEADERS, timeout=30) as d_resp:
                        if d_resp.status != 200:
                            logging.error(f"Transport article {url} returned status {d_resp.status}")
                            continue
                        d_soup = BeautifulSoup(await d_resp.text(), 'lxml')
                        title = d_soup.find('h1')
                        title_text = title.get_text(strip=True) if title else "Transport alert"
                        
                        content = d_soup.find('div', class_='editor')
                        description = content.get_text(separator=' ', strip=True) if content else ""
                        if not description:
                            main_content = d_soup.find('div', class_='max-w-6xl')
                            description = main_content.get_text(separator=' ', strip=True) if main_content else ""
                        
                        events.append({
                            'category': 'transport',
                            'title_sr': title_text,
                            'description_sr': description,
                            'region': "Beograd",
                            'municipalities': detect_municipalities(title_text + " " + description),
                            'start_time': datetime.now(TZ),
                            'end_time': datetime.now(TZ) + timedelta(days=2),
                            'source_url': url,
                            'hash_id': hashlib.sha256(url.encode()).hexdigest()
                        })
                except Exception as e:
                    logging.error(f"Error parsing transport article {url}: {type(e).__name__}: {e}")
    except Exception as e: logging.error(f"Transport list error: {type(e).__name__}: {e}")
    return events

async def scrape_traffic_official(session):
    events = []
    for p in range(0, 3):
        url = f"https://www.bgsaobracaj.rs/vesti?page={p}"
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as resp:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                for post in soup.select('#posts > div'):
                    title_a = post.select_one('.entry-title h2 a')
                    if not title_a: continue
                    t_text, pub_date = title_a.get_text(strip=True), post.select('.entry-meta li')[0].get_text(strip=True)
                    s_pub, _ = parse_dates(pub_date)
                    s_date, e_date = (s_pub or datetime.now(TZ)), None
                    try:
                        async with session.get(title_a['href'], headers=HEADERS, timeout=5) as in_resp:
                            in_soup = BeautifulSoup(await in_resp.text(), 'lxml')
                            itxt = in_soup.get_text()
                            s_in, e_in = parse_dates(itxt)
                            if s_in: s_date = s_in
                            if e_in: e_date = e_in
                    except: pass
                    events.append({'category': 'traffic', 'title_sr': t_text, 'description_sr': post.select_one('.entry-content').get_text(strip=True), 'region': "Beograd", 'municipalities': detect_municipalities(t_text), 'start_time': s_date.replace(hour=7, minute=0), 'end_time': e_date, 'source_url': title_a['href'], 'hash_id': hashlib.sha256(f"traffic:{t_text}:{s_date.date()}".encode()).hexdigest()})
        except: pass
    return events

async def scrape_connectivity(session):
    urls = [
        ("https://sbb.rs/podrska/vesti-i-informacije/", "SBB"),
        ("https://mts.rs/Vesti", "MTS"),
        ("https://www.yettel.rs/sr/privatni/podrska/vesti", "Yettel")
    ]
    events = []
    for url, provider in urls:
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as resp:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                items = soup.find_all(['article', 'div'], class_=re.compile(r'post|news|item', re.I))
                for item in items[:10]:
                    title_tag = item.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title', re.I))
                    if not title_tag: continue
                    t_text = title_tag.get_text(strip=True)
                    if any(kw.lower() in t_text.lower() for kw in CONNECTIVITY_KEYWORDS):
                        link = title_tag['href'] if title_tag.name == 'a' and title_tag.has_attr('href') else url
                        if link.startswith('/'): link = "/".join(url.split('/')[:3]) + link
                        s_date, _ = parse_dates(item.get_text())
                        s_date = s_date or datetime.now(TZ)
                        events.append({
                            'category': 'connectivity',
                            'title_sr': f"Internet ({provider}): {t_text}",
                            'description_sr': f"Obaveštenje operatera {provider} o radovima ili smetnjama na mreži.",
                            'region': "Beograd",
                            'municipalities': detect_municipalities(t_text),
                            'start_time': s_date,
                            'end_time': s_date + timedelta(days=1),
                            'source_url': link,
                            'hash_id': hashlib.sha256(f"conn:{provider}:{t_text}:{s_date.date()}".encode()).hexdigest()
                        })
        except: pass
    return events

async def scrape_heating(session):
    url = "https://beoelektrane.co.rs/poremecaji-u-snabdevanju/"
    events = []
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as resp:
            soup = BeautifulSoup(await resp.text(), 'lxml')
            for post in soup.select('.blog_holder article, article'):
                title_h = post.find(['h2', 'h3', 'h4'])
                if not title_h: continue
                t_text, desc = title_h.get_text(strip=True), post.get_text(strip=True)
                s_date, e_date = parse_dates(t_text + desc)
                s_date = s_date or datetime.now(TZ)
                events.append({'category': 'heating', 'title_sr': f"Грејање: {t_text}", 'description_sr': desc, 'region': "Beograd", 'municipalities': detect_municipalities(t_text + desc), 'start_time': s_date.replace(hour=6, minute=0), 'end_time': e_date or s_date.replace(hour=23, minute=59), 'source_url': url, 'hash_id': hashlib.sha256(f"heat:{t_text}:{s_date.date()}".encode()).hexdigest()})
    except: pass
    return events

async def scrape_air_quality(session):
    url = "https://www.beoeko.com/"
    events = []
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as resp:
            soup = BeautifulSoup(await resp.text(), 'lxml')
            status_tag = soup.select_one('.portal-status-card__title b')
            if status_tag:
                val = status_tag.get_text(strip=True)
                now = datetime.now(TZ)
                events.append({'category': 'ecology', 'title_sr': f"Ваздух: {val}", 'description_sr': f"Квалитет ваздуха у Београду: {val}.", 'region': "Beograd", 'municipalities': [], 'start_time': now, 'end_time': now + timedelta(hours=1), 'source_url': url, 'hash_id': hashlib.sha256(f"air:{now.strftime('%Y-%m-%d-%H')}".encode()).hexdigest()})
    except: pass
    return events

async def run_translator():
    conn = await asyncpg.connect(DB_URL)
    models = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
    
    while True:
        # Get pending events or failed events with retries < 3
        events = await conn.fetch("SELECT id, title_sr, description_sr FROM events WHERE translation_status IN ('pending', 'failed') AND retry_count < 3 LIMIT 10")
        
        for e in events:
            if len(e['description_sr'] or "") > 2000:
                logging.info(f"Skipping translation for event {e['id']} due to length (>2000 chars)")
                await conn.execute("UPDATE events SET title_ru=$1, title_en=$2, description_ru=$3, description_en=$4, translation_status='success' WHERE id=$5", e['title_sr'], e['title_sr'], e['description_sr'], e['description_sr'], e['id'])
                continue
            logging.info(f"Translating event {e['id']}")
            success = False
            
            for model in models:
                try:
                    t_ru, t_en = await translate_both(e['title_sr'], model=model)
                    d_ru, d_en = await translate_both(e['description_sr'], model=model)
                    
                    if t_ru and t_en and d_ru and d_en:
                        await conn.execute("UPDATE events SET title_ru=$1, title_en=$2, description_ru=$3, description_en=$4, translation_status='success', retry_count=retry_count+1 WHERE id=$5", t_ru, t_en, d_ru, d_en, e['id'])
                        logging.info(f"Success with model {model} for event {e['id']}")
                        success = True
                        break # Exit model loop on success
                    else:
                        raise Exception("Empty translation")
                except Exception as ex:
                    err_msg = str(ex)
                    if "429" in err_msg or "rate_limit" in err_msg:
                        logging.warning(f"Model {model} rate limited, trying next...")
                        continue # Try next model
                    else:
                        logging.error(f"Translation error with {model}: {ex}")
            
            if not success:
                await conn.execute("UPDATE events SET translation_status='failed', retry_count=retry_count+1 WHERE id=$1", e['id'])
                logging.info(f"Could not translate event {e['id']} with any model currently, will retry next cycle.")
        
        await asyncio.sleep(60) # 1 minute interval

async def run_scraper():
    conn = await asyncpg.connect(DB_URL)
    async with aiohttp.ClientSession() as session:
        while True:
            logging.info("Scrape cycle starting...")
            tasks = [scrape_electricity(session), scrape_water(session), scrape_transport(session), scrape_traffic_official(session), scrape_heating(session), scrape_air_quality(session), scrape_connectivity(session)]
            results = await asyncio.gather(*tasks)
            for sublist in results:
                for e in sublist: await save_event(conn, e)
            await conn.execute("""INSERT INTO system_stats (key, val_ts) VALUES ('last_scrape', CURRENT_TIMESTAMP) ON CONFLICT (key) DO UPDATE SET val_ts = CURRENT_TIMESTAMP""")
            logging.info("Scrape cycle complete.")
            await asyncio.sleep(600) # 10 minutes interval

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(run_translator())
    loop.run_until_complete(run_scraper())
