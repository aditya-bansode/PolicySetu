"""
PolicySetu — Comprehensive System-Wide Functional Verification
==============================================================
Tests and validates all features and subsystems:
1. Database Models & Seeding Integrity
2. Web UI Routes & Template Rendering (All Pages)
3. Multilingual System (EN, HI, MR, Future Languages)
4. REST API Endpoints (Health, Stats, Policies, Versions, Compare, Ask)
5. Bug Fixes (Official Links, Chatbot Citations, News Filtering, Status Tabs)
6. Document Processing & Comparison Engine
7. Government Source Adapters & Monitoring Engine
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import (
    GovernmentSource,
    PolicyDocument,
    DocumentVersion,
    PolicyChange,
    PolicyAnalysis,
    MonitoringLog,
    PolicyCategory,
)
from app.models.document import (
    is_placeholder_or_fake_url,
    normalize_document_type,
    VALID_POLICY_DOCUMENT_TYPES,
    EXCLUDED_DOCUMENT_TYPES,
)
from app.services.policy_service import PolicyService
from app.services.comparison_engine import PolicyComparisonEngine
from app.adapters.registry import get_adapter, get_all_registered_adapters, ADAPTER_MAP
from app.ai.rag_engine import PolicyRAGEngine
from app.extractors.pdf_extractor import PDFExtractor
from app.extractors.html_extractor import HTMLExtractor
from app.utils.helpers import hash_content, utc_now

def run_all_checks():
    app = create_app("testing")
    passed = 0
    failed = 0
    results = []

    def check(name, condition, details=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            results.append((True, name, details))
            print(f"  [PASS] {name}" + (f" -> {details}" if details else ""))
        else:
            failed += 1
            results.append((False, name, details))
            print(f"  [FAIL] {name}" + (f" -> {details}" if details else ""))

    with app.app_context():
        client = app.test_client()

        # ── 1. DATABASE & MODELS ─────────────────────────────────────────────
        print("\n--- 1. Database & Models Integrity ---")
        sources_count = GovernmentSource.query.count()
        check("Government Sources Count >= 4", sources_count >= 4, f"Found {sources_count} sources")

        docs_count = PolicyDocument.query.count()
        check("Policy Documents Count >= 10", docs_count >= 10, f"Found {docs_count} documents in DB")

        versions_count = DocumentVersion.query.count()
        check("Document Versions Count >= 10", versions_count >= 10, f"Found {versions_count} versions in DB")

        categories_count = PolicyCategory.query.count()
        check("Policy Categories Count >= 10", categories_count >= 10, f"Found {categories_count} categories in DB")

        nep_doc = PolicyDocument.query.filter(PolicyDocument.title.ilike("%National Education Policy%")).first()
        check("NEP 2020 Exists in Database", nep_doc is not None, f"ID: {nep_doc.id if nep_doc else 'None'}")
        if nep_doc:
            check("NEP 2020 Has Authentic Official URL", nep_doc.official_url and not is_placeholder_or_fake_url(nep_doc.official_url), nep_doc.official_url)

        # ── 2. WEB UI PAGES (HTML) ───────────────────────────────────────────
        print("\n--- 2. Web UI Pages & Navigation ---")
        pages_to_test = [
            ("/", "Home Dashboard", ["PolicySetu", "Total Policies", "Active Sources"]),
            ("/policies", "Policy Explorer", ["Policy Explorer", "All Policies", "New Policies", "Updated Policies"]),
            ("/policies/1", "Policy 1 Detail", ["View Official Document", "Details", "AI Summary"]),
            ("/policies/2", "Policy 2 Detail (NEP 2020)", ["National Education Policy", "education.gov.in"]),
            ("/policies/1/compare", "Version Compare UI", ["Version Comparison", "Diff"]),
            ("/policies/1/impact", "Impact Analysis UI", ["Impact Analysis", "Stakeholder Groups"]),
            ("/ask", "Ask PolicySetu AI", ["PolicySetu AI Assistant", "Suggested Inquiries"]),
            ("/monitor", "Source Monitor", ["Government Source Monitor", "Configured Adapters"]),
            ("/settings", "Settings", ["Preferences & Configuration", "Interface & Language Settings"]),
            ("/about", "About", ["About PolicySetu", "Bridging Government Policies"]),
        ]

        for path, name, expected_strings in pages_to_test:
            res = client.get(path)
            html = res.data.decode("utf-8", errors="ignore")
            all_found = all(s in html for s in expected_strings)
            check(f"Page '{name}' ({path}) -> 200 OK", res.status_code == 200 and all_found, f"Status: {res.status_code}")

        # ── 3. MULTILINGUAL SUPPORT ──────────────────────────────────────────
        print("\n--- 3. Multilingual Support (EN, HI, MR) ---")
        # English
        res_en = client.get("/?lang=en")
        html_en = res_en.data.decode("utf-8", errors="ignore")
        check("English Interface Loaded", "All Policies" in html_en and "Explore Policies" in html_en)

        # Hindi
        res_hi = client.get("/?lang=hi")
        html_hi = res_hi.data.decode("utf-8", errors="ignore")
        check("Hindi Interface Loaded", "सभी नीतियां" in html_hi or "डैशबोर्ड" in html_hi)

        # Marathi
        res_mr = client.get("/?lang=mr")
        html_mr = res_mr.data.decode("utf-8", errors="ignore")
        check("Marathi Interface Loaded", "सर्व धोरणे" in html_mr or "डॅशबोर्ड" in html_mr)

        # Coming Soon Languages Notice
        check("Coming Soon Languages Notice Present", "More Indian Languages Coming Soon" in html_en)

        # ── 4. REST API ENDPOINTS ────────────────────────────────────────────
        print("\n--- 4. REST API Endpoints ---")
        # /api/health
        res = client.get("/api/health")
        data = res.get_json()
        check("GET /api/health", res.status_code == 200 and data.get("data", {}).get("status") == "healthy", f"DB: {data.get('data', {}).get('database')}")

        # /api/dashboard/stats
        res = client.get("/api/dashboard/stats")
        data = res.get_json()
        s_data = data.get("data", {})
        check("GET /api/dashboard/stats", res.status_code == 200 and s_data.get("total_policies", 0) > 0, f"Total: {s_data.get('total_policies')}, Sources: {s_data.get('active_sources')}")

        # Granular stats
        res_cat = client.get("/api/stats/categories")
        check("GET /api/stats/categories", res_cat.status_code == 200 and len(res_cat.get_json().get("data", [])) > 0)

        res_jur = client.get("/api/stats/jurisdictions")
        check("GET /api/stats/jurisdictions", res_jur.status_code == 200 and len(res_jur.get_json().get("data", [])) > 0)

        res_time = client.get("/api/stats/timeline")
        check("GET /api/stats/timeline", res_time.status_code == 200)

        res_src = client.get("/api/stats/sources")
        check("GET /api/stats/sources", res_src.status_code == 200 and len(res_src.get_json().get("data", [])) > 0)

        # /api/policies (Pagination & basic fetch)
        res_pol = client.get("/api/policies?page=1&per_page=5")
        p_json = res_pol.get_json()
        check("GET /api/policies pagination", res_pol.status_code == 200 and len(p_json.get("data", [])) == 5, f"Returned 5 items, Total: {p_json.get('meta', {}).get('total')}")

        # /api/policies/<id>
        res_p1 = client.get("/api/policies/1")
        p1_data = res_p1.get_json().get("data", {})
        check("GET /api/policies/1", res_p1.status_code == 200 and p1_data.get("id") == 1, f"Title: {p1_data.get('title')[:35]}...")

        # /api/policies/1/versions
        res_v = client.get("/api/policies/1/versions")
        v_data = res_v.get_json().get("data", [])
        check("GET /api/policies/1/versions", res_v.status_code == 200 and len(v_data) >= 1, f"Versions found: {len(v_data)}")

        # /api/policies/3/compare (POST - Policy 3 has multiple versions)
        res_cmp = client.post("/api/policies/3/compare", json={"v1": 1, "v2": 2})
        cmp_data = res_cmp.get_json().get("data", {})
        check("POST /api/policies/3/compare", res_cmp.status_code == 200 and "diff" in cmp_data, f"Meaningful change: {cmp_data.get('meaningful_change')}, Additions: {cmp_data.get('additions')}")

        # ── 5. BUG FIXES VALIDATION ──────────────────────────────────────────
        print("\n--- 5. Bug Fixes Verification ---")
        # Bug 1: View Official Document Link
        res_nep_api = client.get("/api/policies/2")
        nep_api_data = res_nep_api.get_json().get("data", {})
        check("Bug 1: Official URL is authentic and available", nep_api_data.get("official_url_available") is True and nep_api_data.get("official_url").startswith("https://www.education.gov.in"), nep_api_data.get("official_url"))

        # Bug 2: AI Chatbot citations & real links
        res_ask = client.post("/api/ask", json={"question": "What is PM-KISAN subsidy?", "language": "en"})
        ask_data = res_ask.get_json().get("data", {})
        has_sources = len(ask_data.get("sources", [])) > 0
        first_src = ask_data.get("sources", [{}])[0] if has_sources else {}
        check("Bug 2: AI Chatbot returns real DB policy ID & detail_url", has_sources and isinstance(first_src.get("id"), int) and first_src.get("detail_url") == f"/policies/{first_src.get('id')}", f"Doc ID: {first_src.get('id')}, URL: {first_src.get('detail_url')}")

        res_ask_fake = client.post("/api/ask", json={"question": "Random alien spacecraft 99999", "language": "en"})
        fake_data = res_ask_fake.get_json().get("data", {})
        check("Bug 2: Unverified inquiry refuses to hallucinate fake links", fake_data.get("verified") is False and len(fake_data.get("sources", [])) == 0)

        # Bug 3: News & Press Releases filtered from All Policies
        res_all_pol = client.get("/api/policies?per_page=100")
        all_pol_data = res_all_pol.get_json().get("data", [])
        types_in_all = {p.get("document_type") for p in all_pol_data}
        check("Bug 3: Press releases and news strictly excluded from All Policies", "PRESS_RELEASE" not in types_in_all and "NEWS" not in types_in_all, f"Document types: {types_in_all}")

        # Bug 4: New Policies vs Updated Policies filters
        res_new = client.get("/api/policies?status=new")
        new_meta = res_new.get_json().get("meta", {})
        check("Bug 4: status=new returns newly detected policies", res_new.status_code == 200 and new_meta.get("total", 0) > 0, f"Total new: {new_meta.get('total')}")

        res_updated = client.get("/api/policies?status=updated")
        upd_meta = res_updated.get_json().get("meta", {})
        check("Bug 4: status=updated returns versioned policies", res_updated.status_code == 200 and upd_meta.get("total", 0) > 0, f"Total updated: {upd_meta.get('total')}")

        # ── 6. DOCUMENT PROCESSING & COMPARISON ENGINE ───────────────────────
        print("\n--- 6. Document Processing & Comparison Engine ---")
        # Text hashing
        h1 = hash_content("Test Policy Version 1")
        h2 = hash_content("Test Policy Version 2")
        check("SHA-256 Hashing generates valid 64-char hex", len(h1) == 64 and h1 != h2, f"Hash: {h1[:16]}...")

        # Diff Comparison Engine
        diff_res = PolicyComparisonEngine.compare(
            "Section 1: Eligible farmers receive 4000 rupees.\nSection 2: Applications online.",
            "Section 1: Eligible farmers receive 6000 rupees.\nSection 2: Applications online.\nSection 3: Aadhaar linking mandatory."
        )
        check("Comparison Engine detects additions & modifications", diff_res["meaningful_change"] is True and diff_res["additions_count"] > 0, f"Additions: {diff_res['additions_count']}, Deletions: {diff_res['deletions_count']}")

        # HTML Extractor
        html_sample = "<html><body><h1>Title of Policy</h1><p>This is official policy paragraph content.</p></body></html>"
        extracted_html = HTMLExtractor.extract(html_sample)
        check("HTML Extractor parses title and content", "Title of Policy" in extracted_html["text"] and "official policy paragraph" in extracted_html["text"])

        # ── 7. GOVERNMENT ADAPTERS REGISTRY ──────────────────────────────────
        print("\n--- 7. Government Source Adapters System ---")
        adapters = get_all_registered_adapters()
        check("Adapters Registry has all 4 government sources", len(adapters) >= 4, f"Registered: {list(adapters.keys())}")

        pib = get_adapter("pib")
        check("PIB Adapter Loaded", pib is not None and hasattr(pib, "fetch_recent_documents"))

        egaz = get_adapter("egazette")
        check("eGazette Adapter Loaded", egaz is not None and hasattr(egaz, "fetch_recent_documents"))

        india_code = get_adapter("india_code")
        check("India Code Adapter Loaded", india_code is not None and hasattr(india_code, "fetch_recent_documents"))

        maha_gr = get_adapter("maharashtra_gr")
        check("Maharashtra GR Adapter Loaded", maha_gr is not None and hasattr(maha_gr, "fetch_recent_documents"))

    print("\n=======================================================")
    print(f"VERIFICATION SUMMARY: {passed} PASSED, {failed} FAILED (Total: {passed + failed})")
    print("=======================================================")
    return failed == 0

if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
