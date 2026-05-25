import requests
from bs4 import BeautifulSoup

url = "https://www.bgprevoz.rs/linije/aktuelne-izmene/971"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'lxml')

print("TITLE:", soup.title.string)

# Find the main container - it might be a <main> tag or similar
main = soup.find('main')
if main:
    print("MAIN TEXT:", main.get_text(strip=True)[:500])
else:
    # If no main, find the largest text container
    for div in soup.find_all('div'):
        txt = div.get_text(strip=True)
        if len(txt) > 500:
             # Check if it's not a parent of another large div
             child_large = False
             for child in div.find_all('div'):
                 if len(child.get_text(strip=True)) > 500:
                     child_large = True
                     break
             if not child_large:
                 print(f"LARGE DIV ({div.get('class')}): {txt[:300]}")
