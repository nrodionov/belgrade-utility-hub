from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import asyncpg, os, pytz
from datetime import datetime, timedelta

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
DB_URL = os.getenv("DATABASE_URL")
TZ = pytz.timezone("Europe/Belgrade")

MUNICIPALITIES = ["Barajevo", "Čukarica", "Grocka", "Lazarevac", "Mladenovac", "Novi Beograd", "Obrenovac", "Palilula", "Rakovica", "Savski venac", "Sopot", "Stari grad", "Surčin", "Voždovac", "Vračar", "Zemun", "Zvezdara"]
MUNICIPALITIES_SR = ["Барајево", "Чукарица", "Гроцка", "Лазаревац", "Младеновац", "Нови Београд", "Обреновац", "Палилула", "Раковица", "Савски венац", "Сопот", "Стари град", "Сурчин", "Вождовац", "Врачар", "Земун", "Звездара"]
MUNI_MAP = dict(zip(MUNICIPALITIES, MUNICIPALITIES_SR))

UI_TRANSLATIONS = {
    "ru": {
        "title": "БГ Монитор", "all": "Все ленты", "elec": "Свет", "water": "Вода", "trans": "Транспорт", "traffic": "Перекрытия", "heat": "Отопление", "eco": "Экология", "muni": "Все обштины", "last_upd": "Обновлено", "source": "Источник", "empty": "На ближайшие дни пусто", "about": "Об источниках",
        "src_title": "Источники данных", "src_desc": "Все данные собираются автоматически из официальных городских служб:",
        "src_list": [
            ("Электричество", "EDS (Elektrodistribucija Srbije) - официальные плановые отключения.", "https://elektrodistribucija.rs/planirana-iskljucenja/planirana-bgd"),
            ("Водоснабжение", "BVK (Beogradski vodovod) - аварийные и плановые работы.", "https://www.bvk.rs/"),
            ("Дороги", "Секретариат по транспорту - перекрытия и изменения режима движения.", "https://www.bgsaobracaj.rs/"),
            ("Общ. транспорт", "Секретариат по общественному транспорту (BGPrevoz).", "https://www.bgprevoz.rs/"),
            ("Отопление", "Beogradske elektrane - статус теплоснабжения города.", "https://beoelektrane.co.rs/"),
            ("Экология", "Beoeko - индекс качества воздуха в реальном времени.", "https://www.beoeko.com/"),
            ("События", "Danas.rs - забастовки, протесты и важные городские анонсы.", "https://www.danas.rs/")
        ]
    },
    "srp": {
        "title": "БГ Монитор", "all": "Сва обавештења", "elec": "Струја", "water": "Вода", "trans": "Превоз", "traffic": "Измене", "heat": "Грејање", "eco": "Екологија", "muni": "Све општине", "last_upd": "Ажурирано", "source": "Извор", "empty": "Нема обавештења", "about": "О изворима",
        "src_title": "Извори података", "src_desc": "Сви подаци се аутоматски прикупљају из званичних градских служби:",
        "src_list": [
            ("Електрична енергија", "ЕДС (Електродистрибуција Србије) - планова искључења.", "https://elektrodistribucija.rs/planirana-iskljucenja/planirana-bgd"),
            ("Водовод", "БВК (Београдски водовод и канализација).", "https://www.bvk.rs/"),
            ("Саобраћај", "Секретаријат за саобраћај - обуставе и измене режима.", "https://www.bgsaobracaj.rs/"),
            ("Јавни превоз", "Секретаријат за јавни превоз (БГПревоз).", "https://www.bgprevoz.rs/"),
            ("Грејање", "Београдске електране - стање у снабдевању.", "https://beoelektrane.co.rs/"),
            ("Екологија", "Беоеко - квалитет ваздуха у реалном времену.", "https://www.beoeko.com/"),
            ("Вести", "Danas.rs - протести и важне најаве.", "https://www.danas.rs/")
        ]
    },
    "srl": {
        "title": "BG Monitor", "all": "Sva obaveštenja", "elec": "Struja", "water": "Voda", "trans": "Prevoz", "traffic": "Izmene", "heat": "Grejanje", "eco": "Ekologija", "muni": "Sve opštine", "last_upd": "Ažurirano", "source": "Izvor", "empty": "Nema obaveštenja", "about": "O izvorima",
        "src_title": "Izvori podataka", "src_desc": "Svi podaci se automatski prikupljaju iz zvaničnih gradskih službi:",
        "src_list": [
            ("Električna energija", "EDS (Elektrodistribucija Srbije) - planirana isključenja.", "https://elektrodistribucija.rs/planirana-iskljucenja/planirana-bgd"),
            ("Vodovod", "BVK (Beogradski vodovod i kanalizacija).", "https://www.bvk.rs/"),
            ("Saobraćaj", "Sekretarijat za saobraćaj - obustave i izmene režima.", "https://www.bgsaobracaj.rs/"),
            ("Javni prevoz", "Sekretarijat za javni prevoz (BGPrevoz).", "https://www.bgprevoz.rs/"),
            ("Grejanje", "Beogradske elektrane - stanje u snabdevanju.", "https://beoelektrane.co.rs/"),
            ("Ekologija", "Beoeko - kvalitet vazduha u realnom vremenu.", "https://www.beoeko.com/"),
            ("Vesti", "Danas.rs - protesti i važne najave.", "https://www.danas.rs/")
        ]
    },
    "en": {
        "title": "BG Monitor", "all": "All", "elec": "Electricity", "water": "Water", "trans": "Transport", "traffic": "Traffic", "heat": "Heating", "eco": "Ecology", "muni": "All municipalities", "last_upd": "Updated", "source": "Source", "empty": "No alerts found", "about": "About sources",
        "src_title": "Data Sources", "src_desc": "All data is automatically aggregated from official Belgrade services:",
        "src_list": [
            ("Electricity", "EDS (Serbian Grid) - official planned outages.", "https://elektrodistribucija.rs/planirana-iskljucenja/planirana-bgd"),
            ("Water", "BVK (Belgrade Waterworks) - maintenance and repairs.", "https://www.bvk.rs/"),
            ("Traffic", "Secretariat for Transport - road closures and regime changes.", "https://www.bgsaobracaj.rs/"),
            ("Public Transport", "Secretariat for Public Transport (BGPrevoz).", "https://www.bgprevoz.rs/"),
            ("Heating", "Beogradske elektrane - city heating status.", "https://beoelektrane.co.rs/"),
            ("Ecology", "Beoeko - real-time air quality index.", "https://www.beoeko.com/"),
            ("News", "Danas.rs - protests and major city events.", "https://www.danas.rs/")
        ]
    }
}

@app.on_event("startup")
async def startup(): app.pool = await asyncpg.create_pool(DB_URL)

@app.get("/")
async def index(request: Request, category: str = None, municipality: str = None, lang: str = "ru"):
    now = datetime.now(TZ)
    if lang not in UI_TRANSLATIONS: lang = "ru"
    ui = UI_TRANSLATIONS[lang]
    page_title = ui["title"]
    db_lang = "sr" if lang == "srp" else ("sl" if lang == "srl" else lang)
    extras = []
    if category:
        cat_labels = {"electricity": ui["elec"], "water": ui["water"], "transport": ui["trans"], "traffic": ui["traffic"], "heating": ui["heat"], "ecology": ui["eco"]}
        extras.append(cat_labels.get(category, category))
    if municipality:
        m_name = MUNI_MAP.get(municipality, municipality) if lang in ["ru", "srp"] else municipality
        extras.append(m_name)
    if extras:
        page_title = f"{page_title} ({' - '.join(extras)})"
    end_of_period = (now.replace(hour=0, minute=0, second=0) + timedelta(days=4))
    async with app.pool.acquire() as conn:
        row_upd = await conn.fetchrow("SELECT val_ts FROM system_stats WHERE key = 'last_scrape'")
        last_scrape_time = row_upd[0] if row_upd else now
        base_query = "SELECT * FROM events WHERE (end_time >= $1 OR (end_time IS NULL AND start_time >= $1 - interval '5 days')) AND (start_time < $2)"
        args = [now, end_of_period]
        if category: base_query += f" AND category = ${len(args)+1}"; args.append(category)
        if municipality: base_query += f" AND ${len(args)+1} = ANY(municipality)"; args.append(municipality)
        base_query += " ORDER BY start_time ASC"
        rows = await conn.fetch(base_query, *args)
    events = []
    for row in rows:
        e = dict(row)
        e['title'], e['description'] = (e.get(f'title_{db_lang}') or e['title_sr']), (e.get(f'description_{db_lang}') or e['description_sr'])
        e['display_date'], e['display_time'] = e['start_time'].astimezone(TZ).strftime("%d.%m.%Y"), e['start_time'].astimezone(TZ).strftime("%H:%M")
        e['is_today'] = e['start_time'].astimezone(TZ).date() == now.date()
        events.append(e)
    return templates.TemplateResponse(request=request, name="index.html", context={"events": events, "current_category": category, "current_municipality": municipality, "current_lang": lang, "municipalities": MUNICIPALITIES, "now": last_scrape_time.astimezone(TZ).strftime("%d.%m %H:%M"), "ui": ui, "full_title": page_title})
