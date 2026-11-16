"""
Inspect candidate government sources to determine accessibility, structure, feeds, and restrictions.
"""
import ssl
import sys
import urllib.request
import urllib.error
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 PolicySetu-Monitor/1.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

candidates = [
    ('PIB Releases', 'https://pib.gov.in/AllRel.aspx'),
    ('PIB RSS Main', 'https://pib.gov.in/RssMain.aspx'),
    ('PIB Robots', 'https://pib.gov.in/robots.txt'),
    ('e-Gazette Home', 'https://egazette.gov.in/'),
    ('e-Gazette Robots', 'https://egazette.gov.in/robots.txt'),
    ('India Code Home', 'https://www.indiacode.nic.in/'),
    ('India Code Robots', 'https://www.indiacode.nic.in/robots.txt'),
    ('Maharashtra GR', 'https://gr.maharashtra.gov.in/1145/Government-Resolutions'),
    ('Maharashtra GR Robots', 'https://gr.maharashtra.gov.in/robots.txt'),
]

for name, url in candidates:
    print(f"\n--- Checking: {name} ({url}) ---")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            content = resp.read()
            ct = resp.headers.get("Content-Type", "")
            print(f"Status: {resp.status} | Content-Type: {ct} | Size: {len(content)} bytes")
            if "text/html" in ct or "xml" in ct or "text/plain" in ct:
                text = content[:2000].decode("utf-8", errors="replace")
                print(f"Snippet:\n{text[:400]}...")
                
                # Check for forms, postbacks, javascript requirement
                if "__VIEWSTATE" in text:
                    print("NOTICE: Uses ASP.NET ViewState (complex postbacks required for dynamic pagination).")
                if "<rss" in text.lower() or "<feed" in text.lower():
                    print("NOTICE: RSS/Atom Feed found!")
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
