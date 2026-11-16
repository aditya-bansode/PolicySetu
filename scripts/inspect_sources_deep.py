"""
Inspect deep structure of candidate sources:
1. PIB: AllRel.aspx links and RssMain.aspx
2. IndiaCode: https://indiacode.gov.in
3. Maharashtra GR: gr.maharashtra.gov.in table elements
4. e-Gazette: Search / latest gazette structure
"""
import ssl
import sys
import urllib.request
import urllib.error
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 PolicySetu-Monitor/1.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
        return resp.read()


# 1. PIB RSS
print("=== Inspecting PIB RSS ===")
try:
    rss_html = fetch("https://pib.gov.in/RssMain.aspx").decode("utf-8", errors="replace")
    soup = BeautifulSoup(rss_html, "html.parser")
    rss_links = [a.get("href") for a in soup.find_all("a") if a.get("href") and ("rss" in a.get("href").lower() or "xml" in a.get("href").lower())]
    print(f"PIB RSS Links found: {len(rss_links)}")
    for l in rss_links[:10]:
        print("  -", l)
except Exception as e:
    print("PIB RSS error:", e)

# 2. PIB AllRel.aspx structure
print("\n=== Inspecting PIB AllRel.aspx ===")
try:
    allrel_html = fetch("https://pib.gov.in/AllRel.aspx").decode("utf-8", errors="replace")
    soup = BeautifulSoup(allrel_html, "html.parser")
    # Find release links (PressReleasePage or PressReleaseIframePage or PRID)
    pr_links = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if "PRID=" in href or "PressRelease" in href:
            pr_links.append((a.get_text(strip=True), href))
    print(f"PIB Press Release Links found: {len(pr_links)}")
    for text, href in pr_links[:5]:
        print(f"  * [{text[:60]}] -> {href}")
    
    # Check date selectors or ministry selectors
    selects = soup.find_all("select")
    print("Select dropdowns in PIB AllRel:", [s.get("id") or s.get("name") for s in selects])
except Exception as e:
    print("PIB AllRel error:", e)

# 3. India Code https://indiacode.gov.in
print("\n=== Inspecting India Code (https://indiacode.gov.in) ===")
try:
    ic_html = fetch("https://indiacode.gov.in").decode("utf-8", errors="replace")
    soup = BeautifulSoup(ic_html, "html.parser")
    print("India Code title:", soup.title.string if soup.title else "No title")
    links = [a.get("href") for a in soup.find_all("a") if a.get("href")]
    print(f"India Code total links: {len(links)}")
    # Look for acts / browse
    act_links = [l for l in links if "handle" in l or "repealed" in l or "browse" in l or "act" in l.lower()]
    print(f"India Code Act/Browse links: {act_links[:5]}")
except Exception as e:
    print("India Code error:", e)

# 4. Maharashtra GR structure
print("\n=== Inspecting Maharashtra GR ===")
try:
    gr_html = fetch("https://gr.maharashtra.gov.in/1145/Government-Resolutions").decode("utf-8", errors="replace")
    soup = BeautifulSoup(gr_html, "html.parser")
    tables = soup.find_all("table")
    print(f"Maharashtra GR tables found: {len(tables)}")
    for t_idx, t in enumerate(tables):
        rows = t.find_all("tr")
        print(f"\n--- Table #{t_idx} (rows: {len(rows)}) ---")
        for i, r in enumerate(rows[:5]):
            cols = [td.get_text(strip=True) for td in r.find_all(["th", "td"])]
            print(f"  Row {i}: {cols[:5]}")
            for a in r.find_all("a"):
                print(f"    Link: text='{a.get_text(strip=True)[:40]}' href='{a.get('href')}'")
except Exception as e:
    print("Maharashtra GR error:", e)


# 5. e-Gazette structure
print("\n=== Inspecting e-Gazette ===")
try:
    egaz_html = fetch("https://egazette.gov.in/").decode("utf-8", errors="replace")
    soup = BeautifulSoup(egaz_html, "html.parser")
    print("e-Gazette title:", soup.title.string if soup.title else "No title")
    # Check for search form or recent gazette links
    egaz_links = [a.get("href") for a in soup.find_all("a") if a.get("href") and ("gazette" in a.get("href").lower() or "pdf" in a.get("href").lower())]
    print(f"e-Gazette gazette/pdf links: {len(egaz_links)}")
    for l in egaz_links[:5]:
        print("  -", l)
except Exception as e:
    print("e-Gazette error:", e)
