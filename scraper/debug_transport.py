import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}

async def test():
    async with aiohttp.ClientSession() as session:
        url_gsp = "https://www.bgprevoz.rs/izmena-rezima/aktuelne-izmene"
        async with session.get(url_gsp, headers=HEADERS, timeout=15) as resp:
            soup = BeautifulSoup(await resp.text(), 'lxml')
            rows = soup.select('tr.aktuelne_izmene')
            print(f"Found {len(rows)} rows")
            for row in rows[:2]:
                title_td = row.select('td')[0]
                t_text = title_td.get_text(strip=True)
                print(f"TITLE: {t_text}")
                link_tag = row.find('a', string=re.compile(r'Опширније|Opširnije', re.I))
                if link_tag:
                    detail_url = link_tag['href']
                    if detail_url.startswith('/'): detail_url = "https://www.bgprevoz.rs" + detail_url
                    print(f"LINK: {detail_url}")
                    async with session.get(detail_url, headers=HEADERS, timeout=15) as det_resp:
                        det_soup = BeautifulSoup(await det_resp.text(), 'lxml')
                        main_tag = det_soup.find('main')
                        if main_tag:
                            print(f"MAIN FOUND, length: {len(main_tag.get_text())}")
                        else:
                            print("MAIN NOT FOUND")
                else:
                    print("LINK NOT FOUND")

asyncio.run(test())
