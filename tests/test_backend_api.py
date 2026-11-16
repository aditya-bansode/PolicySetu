"""
PolicySetu — Automated Backend & API Test Suite
===============================================
Tests all 12 required API endpoints, database models, duplicate prevention,
SHA-256 content hashing, versioning, pagination, validation, and error envelopes.
"""

import unittest
import json
from app import create_app
from app.extensions import db
from app.models import PolicyDocument, DocumentVersion, PolicyChange, GovernmentSource, PolicyCategory
from app.services.policy_service import PolicyService
from app.utils.helpers import hash_content, utc_now


class PolicySetuBackendTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # ── 1. GET /api/health ────────────────────────────────────────────────────
    def test_01_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["status"], "healthy")
        self.assertEqual(data["data"]["database"], "connected")
        self.assertIn("timestamp", data["data"])

    # ── 2. GET /api/dashboard/stats ───────────────────────────────────────────
    def test_02_dashboard_stats(self):
        res = self.client.get("/api/dashboard/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        stats = data["data"]
        self.assertGreater(stats["total_policies"], 0)
        self.assertGreaterEqual(stats["active_sources"], 1)
        self.assertIsInstance(stats["categories"], list)
        self.assertIsInstance(stats["jurisdictions"], list)

    # ── 3. GET /api/policies (with pagination & filters) ──────────────────────
    def test_03_get_policies_pagination(self):
        res = self.client.get("/api/policies?page=1&per_page=5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertLessEqual(len(data["data"]), 5)
        self.assertEqual(data["meta"]["page"], 1)
        self.assertEqual(data["meta"]["per_page"], 5)
        self.assertGreater(data["meta"]["total"], 0)
        self.assertIn("total_pages", data["meta"])

    def test_04_policies_filtering_and_search(self):
        # Category filter
        res = self.client.get("/api/policies?category=Agriculture")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        for doc in data["data"]:
            self.assertEqual(doc["category"], "Agriculture")

        # Keyword search
        res = self.client.get("/api/policies?q=Kisan")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreater(len(data["data"]), 0)

        # Jurisdiction filter
        res = self.client.get("/api/policies?jurisdiction=Central Government")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreater(len(data["data"]), 0)

    # ── 4. GET /api/policies/<id> ─────────────────────────────────────────────
    def test_05_get_policy_by_id(self):
        # Success case
        res = self.client.get("/api/policies/1")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        doc = data["data"]
        self.assertEqual(doc["id"], 1)
        self.assertIn("canonical_url", doc)
        self.assertIn("content_hash", doc)
        self.assertEqual(len(doc["content_hash"]), 64)  # SHA-256 hex string

        # 404 Error case
        res_404 = self.client.get("/api/policies/99999")
        self.assertEqual(res_404.status_code, 404)
        data_404 = res_404.get_json()
        self.assertFalse(data_404["success"])
        self.assertIsNotNone(data_404["error"])

    # ── 5. GET /api/policies/<id>/versions ────────────────────────────────────
    def test_06_get_policy_versions(self):
        res = self.client.get("/api/policies/1/versions")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        versions = data["data"]
        self.assertIsInstance(versions, list)
        self.assertGreaterEqual(len(versions), 1)
        self.assertIn("version_number", versions[0])
        self.assertIn("content_hash", versions[0])

        # 404 for missing
        res_404 = self.client.get("/api/policies/99999/versions")
        self.assertEqual(res_404.status_code, 404)

    # ── 6. GET /api/policies/<id>/changes ─────────────────────────────────────
    def test_07_get_policy_changes(self):
        res = self.client.get("/api/policies/1/changes")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["data"], list)

        # 404 for missing
        res_404 = self.client.get("/api/policies/99999/changes")
        self.assertEqual(res_404.status_code, 404)

    # ── 7. GET /api/categories ────────────────────────────────────────────────
    def test_08_get_categories(self):
        res = self.client.get("/api/categories")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        cats = data["data"]
        self.assertGreater(len(cats), 0)
        self.assertIn("name_en", cats[0])
        self.assertIn("name_mr", cats[0])
        self.assertIn("name_hi", cats[0])

        # Localized query
        res_hi = self.client.get("/api/categories?lang=hi")
        self.assertEqual(res_hi.status_code, 200)
        data_hi = res_hi.get_json()
        self.assertTrue(data_hi["success"])

    # ── 8. GET /api/sources ───────────────────────────────────────────────────
    def test_09_get_sources(self):
        res = self.client.get("/api/sources")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        sources = data["data"]
        self.assertGreater(len(sources), 0)
        self.assertIn("base_url", sources[0])
        self.assertIn("jurisdiction", sources[0])

        # Enabled only
        res_en = self.client.get("/api/sources?enabled=1")
        self.assertEqual(res_en.status_code, 200)

    # ── 9. GET /api/monitoring/logs ───────────────────────────────────────────
    def test_10_get_monitoring_logs(self):
        res = self.client.get("/api/monitoring/logs?page=1&per_page=5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("meta", data)
        self.assertEqual(data["meta"]["page"], 1)
        self.assertIsInstance(data["data"], list)

    # ── 10. POST /api/policies/<id>/compare ───────────────────────────────────
    def test_11_compare_policy_versions(self):
        # Ayushman Bharat (id=3) has multiple versions seeded
        res = self.client.post("/api/policies/1/compare", json={"v1": 1, "v2": 1})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("diff", data["data"])
        self.assertIn("identical", data["data"])

        # 400 Bad input validation
        res_bad = self.client.post("/api/policies/1/compare", json={"v1": "invalid"})
        self.assertEqual(res_bad.status_code, 400)

        # 404 Missing document
        res_404 = self.client.post("/api/policies/99999/compare", json={"v1": 1, "v2": 2})
        self.assertEqual(res_404.status_code, 404)

    # ── 11. POST /api/ai/ask ──────────────────────────────────────────────────
    def test_12_ai_ask(self):
        # Valid question in English
        res = self.client.post("/api/ai/ask", json={
            "question": "What is PM-KISAN Samman Nidhi and who benefits?",
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        ans_data = data["data"]
        self.assertIn("answer", ans_data)
        self.assertIn("sources", ans_data)
        self.assertIn("confidence_score", ans_data)
        self.assertIn("disclaimer", ans_data)

        # Valid question in Hindi
        res_hi = self.client.post("/api/ai/ask", json={
            "question": "पीएम-किसान योजना क्या है?",
            "language": "hi"
        })
        self.assertEqual(res_hi.status_code, 200)
        self.assertTrue(res_hi.get_json()["success"])

        # 400 Missing question validation
        res_empty = self.client.post("/api/ai/ask", json={"question": ""})
        self.assertEqual(res_empty.status_code, 400)
        self.assertFalse(res_empty.get_json()["success"])

    # ── 12. POST /api/ai/summarize ────────────────────────────────────────────
    def test_13_ai_summarize(self):
        # Valid summarize in English
        res = self.client.post("/api/ai/summarize", json={"policy_id": 1, "language": "en"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        s_data = data["data"]
        self.assertEqual(s_data["policy_id"], 1)
        self.assertIn("summary", s_data)
        self.assertIn("key_provisions", s_data)

        # Valid summarize in Marathi
        res_mr = self.client.post("/api/ai/summarize", json={"policy_id": 1, "language": "mr"})
        self.assertEqual(res_mr.status_code, 200)
        self.assertTrue(res_mr.get_json()["success"])

        # 400 Missing policy_id validation
        res_missing = self.client.post("/api/ai/summarize", json={})
        self.assertEqual(res_missing.status_code, 400)

        # 404 Non-existent policy
        res_404 = self.client.post("/api/ai/summarize", json={"policy_id": 99999})
        self.assertEqual(res_404.status_code, 404)

    # ── 13. Duplicate Prevention & SHA-256 Versioning Test ───────────────────
    def test_14_duplicate_prevention_and_versioning(self):
        import uuid
        unique_url = f"https://pib.gov.in/test-unique-policy-{uuid.uuid4().hex}.html"
        initial_content = "Clause 1: Initial grant of ₹10,000 to beneficiaries."

        doc_data = {
            "title": "Test Unique Civic Policy",
            "canonical_url": unique_url,
            "content": initial_content,
            "category": "Social Welfare",
            "document_type": "scheme",
            "jurisdiction": "Central Government",
        }

        # 1. Create initial document
        doc1, is_updated = PolicyService.create_or_update_document(doc_data)
        self.assertFalse(is_updated)
        self.assertEqual(doc1.canonical_url, unique_url)
        self.assertEqual(doc1.content_hash, hash_content(initial_content))
        self.assertEqual(doc1.versions.count(), 1)

        # 2. Try inserting with identical content -> should NOT duplicate document
        count_before = PolicyDocument.query.count()
        doc2, is_updated2 = PolicyService.create_or_update_document(doc_data)
        self.assertEqual(PolicyDocument.query.count(), count_before)
        self.assertFalse(is_updated2)
        self.assertEqual(doc2.id, doc1.id)

        # 3. Update with NEW content -> should create version 2 and log PolicyChange
        updated_content = "Clause 1: Enhanced grant of ₹15,000 to beneficiaries under 2026 amendment."
        doc_data["content"] = updated_content
        doc_data["change_description"] = "Grant amount enhanced by ₹5,000."

        doc3, is_updated3 = PolicyService.create_or_update_document(doc_data)
        self.assertTrue(is_updated3)
        self.assertEqual(doc3.id, doc1.id)
        self.assertEqual(doc3.content_hash, hash_content(updated_content))
        self.assertEqual(doc3.versions.count(), 2)

        # Verify change log created
        changes = PolicyChange.query.filter_by(document_id=doc3.id).all()
        self.assertGreaterEqual(len(changes), 1)
        self.assertEqual(changes[0].change_description, "Grant amount enhanced by ₹5,000.")


if __name__ == "__main__":
    unittest.main()
