import urllib.request
import json

base_url = "http://127.0.0.1:5000"

def get(path):
    url = f"{base_url}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as res:
        return res.status, json.loads(res.read().decode("utf-8"))

def post(path, body):
    url = f"{base_url}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        return res.status, json.loads(res.read().decode("utf-8"))

print("=== Running Live Server Integration Verification ===")

# 1. Health
s, d = get("/api/health")
assert s == 200 and d["success"] and d["data"]["status"] == "healthy", f"Health failed: {d}"
print("[PASS] GET /api/health -> 200 OK")

# 2. Dashboard Stats
s, d = get("/api/dashboard/stats")
assert s == 200 and d["success"] and d["data"]["total_policies"] > 0, f"Stats failed: {d}"
print(f"[PASS] GET /api/dashboard/stats -> 200 OK (total={d['data']['total_policies']}, active_sources={d['data']['active_sources']})")

# 3. Policies
s, d = get("/api/policies?page=1&per_page=5")
assert s == 200 and d["success"] and len(d["data"]) == 5, f"Policies failed: {d}"
print(f"[PASS] GET /api/policies -> 200 OK (returned {len(d['data'])} policies, total={d['meta']['total']})")

# 4. Policy Detail
s, d = get("/api/policies/1")
assert s == 200 and d["success"] and d["data"]["id"] == 1, f"Policy 1 detail failed: {d}"
print(f"[PASS] GET /api/policies/1 -> 200 OK (title={d['data']['title'][:40]}...)")

# 5. Versions
s, d = get("/api/policies/1/versions")
assert s == 200 and d["success"] and len(d["data"]) >= 1, f"Versions failed: {d}"
print(f"[PASS] GET /api/policies/1/versions -> 200 OK ({len(d['data'])} versions found)")

# 6. Changes
s, d = get("/api/policies/1/changes")
assert s == 200 and d["success"], f"Changes failed: {d}"
print(f"[PASS] GET /api/policies/1/changes -> 200 OK")

# 7. Categories
s, d = get("/api/categories")
assert s == 200 and d["success"] and len(d["data"]) >= 10, f"Categories failed: {d}"
print(f"[PASS] GET /api/categories -> 200 OK ({len(d['data'])} categories found)")

# 8. Sources
s, d = get("/api/sources")
assert s == 200 and d["success"] and len(d["data"]) >= 5, f"Sources failed: {d}"
print(f"[PASS] GET /api/sources -> 200 OK ({len(d['data'])} government sources found)")

# 9. Monitoring Logs
s, d = get("/api/monitoring/logs")
assert s == 200 and d["success"] and len(d["data"]) >= 1, f"Logs failed: {d}"
print(f"[PASS] GET /api/monitoring/logs -> 200 OK ({len(d['data'])} crawler logs found)")

# 10. Compare
s, d = post("/api/policies/1/compare", {"v1": 1, "v2": 1})
assert s == 200 and d["success"], f"Compare failed: {d}"
print(f"[PASS] POST /api/policies/1/compare -> 200 OK (identical={d['data']['identical']})")

# 11. AI Ask
s, d = post("/api/ai/ask", {"question": "What is PM-KISAN?", "language": "en"})
assert s == 200 and d["success"] and "answer" in d["data"], f"AI Ask failed: {d}"
print(f"[PASS] POST /api/ai/ask -> 200 OK (confidence={d['data']['confidence_score']})")

# 12. AI Summarize
s, d = post("/api/ai/summarize", {"policy_id": 1, "language": "en"})
assert s == 200 and d["success"] and "summary" in d["data"], f"AI Summarize failed: {d}"
print(f"[PASS] POST /api/ai/summarize -> 200 OK (provisions={len(d['data']['key_provisions'])})")

# 13. Frontend Web Pages
pages = ["/", "/policies", "/policies/1", "/search", "/ask", "/monitor", "/settings"]
for p in pages:
    req = urllib.request.Request(f"{base_url}{p}")
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        print(f"[PASS] Web View {p} -> HTTP 200 OK")

print("\nALL 12 APIS AND FRONTEND PAGES ARE 100% OPERATIONAL!")
