"""
Check PIB English releases and e-Gazette GazetteDirectory.aspx
"""
import ssl
import sys
import urllib.request
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 PolicySetu-Monitor/1.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Cookie': 'Language=1;'
}

# 1. Test PIB with English query param
print("--- PIB English Check ---")
for url in ["https://pib.gov.in/AllRel.aspx?Language=1", "https://pib.gov.in/indexd.aspx"]:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")
            pr_links = []
            for a in soup.find_all("a"):
                href = a.get("href", "")
                if "PRID=" in href:
                    pr_links.append((a.get_text(strip=True), href))
            print(f"URL: {url} -> Status: {resp.status}, Releases found: {len(pr_links)}")
            for t, h in pr_links[:3]:
                print(f"   [{t[:60]}] -> {h}")
    except Exception as e:
        print(f"PIB check failed for {url}: {e}")

# 2. Test e-Gazette GazetteDirectory.aspx
print("\n--- e-Gazette Directory Check ---")
try:
    req = urllib.request.Request("https://egazette.gov.in/GazetteDirectory.aspx", headers=headers)
    with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        print(f"e-Gazette title: {soup.title.string if soup.title else 'No Title'}")
        forms = soup.find_all("form")
        print(f"Forms count: {len(forms)}")
        tables = soup.find_all("table")
        print(f"Tables count: {len(tables)}")
        pdf_links = [a.get("href") for a in soup.find_all("a") if a.get("href") and ".pdf" in a.get("href").lower()]
        print(f"PDF links directly on directory page: {len(pdf_links)}")
except Exception as e:
    print(f"e-Gazette directory check failed: {e}")

# 3. Test India Code API or sitemap
print("\n--- India Code Sitemap / Backend Check ---")
for path in ["https://indiacode.gov.in/sitemap.xml", "https://indiacode.gov.in/server/api/core/communities"]:
    try:
        req = urllib.request.Request(path, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            print(f"India Code {path} -> {resp.status} ({resp.headers.get('Content-Type')})")
    except Exception as e:
        print(f"India Code {path} -> {e}")
