"""
PolicySetu — Automated Tests for 4 Major Bug Fixes
=================================================
Tests:
1. Bug 1: Official Document Link & Validation
2. Bug 2: AI Chatbot Policy Links & Citation Metadata
3. Bug 3: News & Press Releases Filtered from All Policies
4. Bug 4: New Policies and Updated Policies Filters
"""

import unittest
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models.document import (
    PolicyDocument,
    DocumentVersion,
    PolicyChange,
    is_placeholder_or_fake_url,
    normalize_document_type,
    DOC_TYPE_POLICY,
    DOC_TYPE_PRESS_RELEASE,
    DOC_TYPE_NEWS,
    EXCLUDED_DOCUMENT_TYPES,
)
from app.models.source import GovernmentSource
from app.services.policy_service import PolicyService
from app.ai.rag_engine import PolicyRAGEngine
from app.utils.helpers import utc_now, hash_content


class BugFixesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    # ── BUG 1: Official Document Link ──────────────────────────────────────────
    def test_bug1_is_placeholder_or_fake_url_detection(self):
        """Verify fake/placeholder URLs are identified and authentic URLs are accepted."""
        # Fabricated or broken placeholder URLs
        self.assertTrue(is_placeholder_or_fake_url("https://pib.gov.in/PressReleasePage.aspx?PRID=0000002"))
        self.assertTrue(is_placeholder_or_fake_url("https://pib.gov.in/PressReleasePage.aspx?PRID=000001"))
        self.assertTrue(is_placeholder_or_fake_url("https://egazette.gov.in/00001.pdf"))
        self.assertTrue(is_placeholder_or_fake_url(""))
        self.assertTrue(is_placeholder_or_fake_url("#"))
        self.assertTrue(is_placeholder_or_fake_url("none"))
        self.assertTrue(is_placeholder_or_fake_url(None))

        # Authentic URLs
        self.assertFalse(is_placeholder_or_fake_url("https://www.education.gov.in/sites/upload_files/mhrd/files/NEP_Final_English_0.pdf"))
        self.assertFalse(is_placeholder_or_fake_url("https://pmkisan.gov.in/"))
        self.assertFalse(is_placeholder_or_fake_url("https://pib.gov.in/PressReleasePage.aspx?PRID=2074312"))

    def test_bug1_nep_policy_official_document_url(self):
        """Verify National Education Policy 2020 has authentic verified document URL."""
        nep = PolicyDocument.query.filter(PolicyDocument.title.ilike("%National Education Policy%")).first()
        self.assertIsNotNone(nep, "National Education Policy 2020 should exist in DB")
        self.assertIsNotNone(nep.official_url)
        self.assertFalse(is_placeholder_or_fake_url(nep.official_url))
        self.assertNotIn("PRID=0000002", nep.official_url)
        self.assertTrue(nep.official_url.startswith("https://www.education.gov.in"))

        # Verify to_dict output contains official_url_available flag
        doc_dict = nep.to_dict()
        self.assertTrue(doc_dict["official_url_available"])
        self.assertEqual(doc_dict["official_url"], nep.official_url)

    def test_bug1_policy_detail_page_official_link_rendering(self):
        """Verify the detail page renders authentic URL in a new browser tab with noopener."""
        nep = PolicyDocument.query.filter(PolicyDocument.title.ilike("%National Education Policy%")).first()
        self.assertIsNotNone(nep)

        response = self.client.get(f"/policies/{nep.id}")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        # Must have the real link with target="_blank" and rel="noopener noreferrer"
        self.assertIn(nep.official_url, html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener noreferrer"', html)

    def test_bug1_policy_detail_fallback_when_url_unavailable(self):
        """Verify fallback badge & portal button when official document link is unavailable."""
        doc = PolicyDocument(
            title="Policy Without Direct Link Test",
            canonical_url=f"https://pib.gov.in/PressReleasePage.aspx?PRID=0000002_{int(datetime.now().timestamp())}",
            official_url=None,
            source_listing_url="https://testing.gov.in/portal",
            department="Department of Testing",
            document_type="POLICY",
            content="Policy content without direct document attachment.",
            content_hash="dummyhash123",
            first_detected_at=utc_now(),
            detected_at=utc_now(),
        )
        db.session.add(doc)
        db.session.commit()

        response = self.client.get(f"/policies/{doc.id}")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        # Fallback badge
        self.assertIn("Official document link unavailable", html)
        # Portal button
        self.assertIn("Source Portal", html)
        self.assertIn("https://testing.gov.in/portal", html)

    # ── BUG 2: AI Chatbot Policy Links ─────────────────────────────────────────
    def test_bug2_rag_sources_include_real_database_id_and_details(self):
        """Verify RAG response returns real database IDs, detail_url, category, and dept."""
        res = PolicyRAGEngine.answer_question("What is PM-KISAN scheme financial benefit?", lang="en")
        self.assertTrue(res["verified"])
        self.assertTrue(len(res["sources"]) > 0)

        source = res["sources"][0]
        self.assertIn("id", source)
        self.assertIsInstance(source["id"], int)
        self.assertTrue(source["id"] > 0)
        self.assertIn("title", source)
        self.assertIn("department", source)
        self.assertIn("category", source)
        self.assertIn("detail_url", source)
        self.assertEqual(source["detail_url"], f"/policies/{source['id']}")
        self.assertIn("official_url", source)

    def test_bug2_unverified_rag_question_has_no_fake_links(self):
        """Verify unverified question does not return fake links or hallucinated sources."""
        res = PolicyRAGEngine.answer_question("Random fictional alien spacecraft registration policy 99999", lang="en")
        self.assertFalse(res["verified"])
        self.assertEqual(res["sources"], [])
        self.assertEqual(res["citations"], [])
        self.assertIn("could not verify the answer", res["answer"])

    # ── BUG 3: News Appearing in All Policies ───────────────────────────────────
    def test_bug3_canonical_document_types_normalization(self):
        """Verify 12 canonical document types and exclusion classifications."""
        self.assertEqual(normalize_document_type("POLICY"), DOC_TYPE_POLICY)
        self.assertEqual(normalize_document_type("PRESS_RELEASE"), DOC_TYPE_PRESS_RELEASE)
        self.assertEqual(normalize_document_type("NEWS"), DOC_TYPE_NEWS)
        self.assertEqual(normalize_document_type("PIB"), DOC_TYPE_PRESS_RELEASE)
        self.assertIn(DOC_TYPE_PRESS_RELEASE, EXCLUDED_DOCUMENT_TYPES)
        self.assertIn(DOC_TYPE_NEWS, EXCLUDED_DOCUMENT_TYPES)

    def test_bug3_press_releases_and_news_excluded_from_all_policies(self):
        """Verify PRESS_RELEASE and NEWS documents are excluded from PolicyService.get_policies()."""
        # Ensure press release and news records exist in the database
        pr_count = PolicyDocument.query.filter(PolicyDocument.document_type.in_(EXCLUDED_DOCUMENT_TYPES)).count()
        self.assertTrue(pr_count >= 2, f"Expected at least 2 press release/news records in DB, found {pr_count}")

        # Fetch policies via service
        policies, meta = PolicyService.get_policies(filters={"status": "all"}, page=1, per_page=100)
        returned_types = {p["document_type"] for p in policies}

        # Press release and news must NOT be present
        self.assertNotIn("PRESS_RELEASE", returned_types)
        self.assertNotIn("NEWS", returned_types)
        self.assertNotIn("OTHER", returned_types)

        # Check API response
        api_res = self.client.get("/api/policies?per_page=100")
        self.assertEqual(api_res.status_code, 200)
        api_data = api_res.get_json()["data"]
        for p in api_data:
            self.assertNotIn(p["document_type"], ["PRESS_RELEASE", "NEWS"])
            self.assertNotEqual(p.get("classification_status"), "excluded_news")

    # ── BUG 4: New Policies and Updated Policies Filters ───────────────────────
    def test_bug4_filter_status_all_vs_new_vs_updated(self):
        """Verify status=all, status=new, and status=updated return distinct subsets."""
        all_policies, meta_all = PolicyService.get_policies(filters={"status": "all"}, per_page=100)
        new_policies, meta_new = PolicyService.get_policies(filters={"status": "new"}, per_page=100)
        updated_policies, meta_updated = PolicyService.get_policies(filters={"status": "updated"}, per_page=100)

        self.assertTrue(meta_all["total"] > 0)
        self.assertTrue(meta_new["total"] > 0)
        self.assertTrue(meta_updated["total"] > 0)

        # Updated policies must all have versions > 1 or recorded changes
        for p in updated_policies:
            doc = db.session.get(PolicyDocument, p["id"])
            has_multiple_versions = (doc.current_version or 1) > 1 or doc.versions.count() > 1
            has_changes = doc.changes.count() > 0
            self.assertTrue(
                has_multiple_versions or has_changes,
                f"Policy {p['id']} '{p['title']}' returned under status=updated but has no version history"
            )

        # New policies must have detected_at / first_detected_at within 14 days
        cutoff = utc_now() - timedelta(days=14)
        for p in new_policies:
            doc = db.session.get(PolicyDocument, p["id"])
            detected = doc.first_detected_at or doc.detected_at
            self.assertTrue(
                detected >= cutoff,
                f"Policy {p['id']} '{p['title']}' returned under status=new but detected_at is older than cutoff"
            )

    def test_bug4_api_status_parameters(self):
        """Verify API responds correctly to status=new and status=updated query parameters."""
        res_new = self.client.get("/api/policies?status=new")
        self.assertEqual(res_new.status_code, 200)
        data_new = res_new.get_json()
        self.assertTrue(data_new["success"])
        self.assertTrue(data_new["meta"]["total"] > 0)

        res_updated = self.client.get("/api/policies?status=updated")
        self.assertEqual(res_updated.status_code, 200)
        data_updated = res_updated.get_json()
        self.assertTrue(data_updated["success"])
        self.assertTrue(data_updated["meta"]["total"] > 0)

        # Backward compatibility with is_new=1 and is_modified=1
        res_is_new = self.client.get("/api/policies?is_new=1")
        self.assertEqual(res_is_new.status_code, 200)
        self.assertEqual(res_is_new.get_json()["meta"]["total"], data_new["meta"]["total"])

        res_is_modified = self.client.get("/api/policies?is_modified=1")
        self.assertEqual(res_is_modified.status_code, 200)
        self.assertEqual(res_is_modified.get_json()["meta"]["total"], data_updated["meta"]["total"])

    def test_bug4_combined_filtering_with_status(self):
        """Verify status parameter can be combined with category and search keywords."""
        res = self.client.get("/api/policies?status=new&category=education")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        for p in data["data"]:
            self.assertEqual(p["category"].lower(), "education")


if __name__ == "__main__":
    unittest.main()
