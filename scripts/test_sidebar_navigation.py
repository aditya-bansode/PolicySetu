"""
Test script to verify PolicySetu sidebar navigation updates:
1. POLICIES section contains ONLY "All Policies"
2. New Policies and Updated Policies navigation options are completely removed
3. Policy Explorer is removed from sidebar
4. DISCOVERY section contains ONLY "Keyword Search" and "Ask PolicySetu AI"
5. Active navigation states on /policies, /search, and /ask
6. All remaining pages return HTTP 200 OK
7. Keyword Search & All Policies APIs work smoothly
"""
import urllib.request
import re
import sys

BASE_URL = "http://127.0.0.1:5000"

def get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")

def run_tests():
    print("=== Testing PolicySetu Sidebar Navigation ===")
    
    # 1. Fetch Home and check sidebar
    status, html = get("/")
    assert status == 200, f"Expected 200, got {status}"
    
    # Extract sidebar navigation
    sidebar_match = re.search(r'<nav class="sidebar-nav"[^>]*>(.*?)</nav>', html, re.DOTALL)
    assert sidebar_match, "Sidebar navigation not found"
    sidebar_html = sidebar_match.group(1)
    
    # Check that New Policies, Updated Policies, and Policy Explorer are NOT in the sidebar
    assert "New Policies" not in sidebar_html, "FAIL: 'New Policies' still in sidebar"
    assert "is_new=1" not in sidebar_html, "FAIL: 'is_new=1' link still in sidebar"
    assert "Updated Policies" not in sidebar_html, "FAIL: 'Updated Policies' still in sidebar"
    assert "is_modified=1" not in sidebar_html, "FAIL: 'is_modified=1' link still in sidebar"
    assert "Policy Explorer" not in sidebar_html, "FAIL: 'Policy Explorer' still in sidebar"
    print("[PASS] Removed options: 'New Policies', 'Updated Policies', and 'Policy Explorer' are NOT in sidebar")
    
    # Check that All Policies, Keyword Search, and Ask PolicySetu AI ARE in the sidebar
    assert "All Policies" in sidebar_html, "FAIL: 'All Policies' not found in sidebar"
    assert "Keyword Search" in sidebar_html, "FAIL: 'Keyword Search' not found in sidebar"
    assert "Ask PolicySetu AI" in sidebar_html, "FAIL: 'Ask PolicySetu AI' not found in sidebar"
    print("[PASS] Kept options: 'All Policies', 'Keyword Search', and 'Ask PolicySetu AI' present in sidebar")
    
    # Check sections under POLICIES and DISCOVERY
    policies_section = re.search(r'class="nav-section-label">[^<]*Policies[^<]*</div>(.*?)</div>\s*<div class="nav-section">', sidebar_html, re.DOTALL)
    assert policies_section, "Policies nav-section not found"
    p_content = policies_section.group(1)
    assert "All Policies" in p_content, "All Policies not in Policies section"
    assert "New Policies" not in p_content, "New Policies in Policies section"
    assert "Updated Policies" not in p_content, "Updated Policies in Policies section"
    assert p_content.count("<a ") == 1, f"Expected exactly 1 link in Policies section, found {p_content.count('<a ')}"
    print("[PASS] POLICIES section contains ONLY 'All Policies' (exactly 1 link)")
    
    discovery_section = re.search(r'class="nav-section-label">[^<]*Discovery[^<]*</div>(.*?)</div>\s*<div class="nav-section">', sidebar_html, re.DOTALL)
    assert discovery_section, "Discovery nav-section not found"
    d_content = discovery_section.group(1)
    assert "Keyword Search" in d_content, "Keyword Search not in Discovery section"
    assert "Ask PolicySetu AI" in d_content, "Ask PolicySetu AI not in Discovery section"
    assert "Policy Explorer" not in d_content, "Policy Explorer in Discovery section"
    assert d_content.count("<a ") == 2, f"Expected exactly 2 links in Discovery section, found {d_content.count('<a ')}"
    print("[PASS] DISCOVERY section contains ONLY 'Keyword Search' and 'Ask PolicySetu AI' (exactly 2 links)")
    
    # 2. Check active navigation states
    # When on /policies
    status_p, html_p = get("/policies")
    assert status_p == 200
    assert 'href="/policies" class="nav-link active"' in html_p or 'href="http://127.0.0.1:5000/policies" class="nav-link active"' in html_p or re.search(r'href="[^"]*policies" class="nav-link\s+active"', html_p), "FAIL: 'All Policies' is not active on /policies"
    print("[PASS] Active state on /policies: 'All Policies' is highlighted as active")
    
    # When on /search
    status_s, html_s = get("/search")
    assert status_s == 200
    assert re.search(r'href="[^"]*search" class="nav-link\s+active"', html_s), "FAIL: 'Keyword Search' is not active on /search"
    print("[PASS] Active state on /search: 'Keyword Search' is highlighted as active")
    
    # When on /ask
    status_a, html_a = get("/ask")
    assert status_a == 200
    assert re.search(r'href="[^"]*ask" class="nav-link\s+active"', html_a), "FAIL: 'Ask PolicySetu AI' is not active on /ask"
    print("[PASS] Active state on /ask: 'Ask PolicySetu AI' is highlighted as active")
    
    # 3. Check remaining pages for 200 OK
    routes_to_test = [
        ("/", "Home"),
        ("/policies", "All Policies"),
        ("/search", "Keyword Search"),
        ("/ask", "Ask AI"),
        ("/monitor", "Source Monitor"),
        ("/settings", "Settings"),
        ("/about", "About"),
    ]
    for r, name in routes_to_test:
        st, _ = get(r)
        assert st == 200, f"Route {r} returned {st}"
        print(f"[PASS] Page {r} ({name}) -> HTTP 200 OK")
        
    # 4. Check API functionality remains intact
    import json
    st, data_str = get("/api/policies?per_page=5")
    data = json.loads(data_str)
    assert st == 200 and data.get("success") is True, f"Policy API failed: {data}"
    print(f"[PASS] GET /api/policies returns 200 OK (total={data['meta']['total']})")
    
    st, data_str = get("/api/search?q=kisan")
    data = json.loads(data_str)
    assert st == 200 and data.get("success") is True, f"Search API failed: {data}"
    print(f"[PASS] GET /api/search returns 200 OK (found={len(data['data'])})")
    
    print("\nALL SIDEBAR NAVIGATION AND SYSTEM INTEGRATION TESTS PASSED 100%!")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
