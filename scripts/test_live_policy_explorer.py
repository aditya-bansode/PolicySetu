import urllib.request
import json

base = "http://127.0.0.1:5000"

def test_endpoint(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as res:
        d = json.loads(res.read().decode("utf-8"))
        print(f"[OK] {url} -> status {res.status}, items: {len(d.get('data', []))}, total: {d.get('meta', {}).get('total')}")

test_endpoint(f"{base}/api/search?q=finance")
test_endpoint(f"{base}/api/policies?category=finance-banking")
test_endpoint(f"{base}/api/policies?category=digital-india")
test_endpoint(f"{base}/api/policies?status=new")
test_endpoint(f"{base}/api/policies?status=updated")
test_endpoint(f"{base}/api/policies?type=act")
test_endpoint(f"{base}/api/policies?type=scheme")
test_endpoint(f"{base}/api/policies?type=guideline")
