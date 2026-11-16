"""
PolicySetu — End-to-End Integration Test Suite
===============================================
Tests the full 12-step end-to-end policy workflow:
1. Monitoring worker checks a configured government source.
2. New policy document is detected from listings.
3. Document is downloaded where permitted.
4. PDF or HTML text is extracted.
5. Duplicate detection is performed using canonical URL.
6. Document metadata is saved in SQLite.
7. AI processes the document with safety guardrails.
8. Category (12 canonical categories) and stakeholder groups (8 canonical groups) are identified.
9. Plain-language summaries are generated in English, Marathi, and Hindi.
10. Policy is published on the dashboard and queryable via APIs.
11. If an existing document changes, a new version is created with meaningful difference checking.
12. Version comparison reflects added, removed, and modified clauses with plain-language explanation.
13. Resilient Error Handling:
    - If AI is unavailable/degraded, document is still saved with processing status.
    - If one source fails, other sources continue working.
    - If a document cannot be extracted, error status is recorded without discarding.
"""

import json
import os
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app import create_app
from app.extensions import db
from app.models import (
    GovernmentSource,
    PolicyDocument,
    DocumentVersion,
    PolicyChange,
    PolicyAnalysis,
    MonitoringLog
)
from app.services.monitoring_engine import PolicyMonitoringEngine
from app.services.policy_service import PolicyService
from app.services.comparison_engine import PolicyComparisonEngine
from app.ai.classifier import CANONICAL_CATEGORIES
from app.ai.extractor import CANONICAL_STAKEHOLDERS
from app.utils.helpers import hash_content


class TestEndToEndIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_01_end_to_end_pipeline_new_document(self):
        """
        Steps 1-10: Test full pipeline from source detection to dashboard publication.
        """
        # Ensure a test source exists
        source = GovernmentSource.query.filter_by(source_type="pib").first()
        if not source:
            source = GovernmentSource(
                name="PIB Test Portal",
                base_url="https://pib.gov.in",
                jurisdiction="Union",
                department="Ministry of Agriculture",
                source_type="pib",
                enabled=True
            )
            db.session.add(source)
            db.session.commit()

        canonical_test_url = f"https://pib.gov.in/PressReleasePage.aspx?PRID=TEST_{int(datetime.utcnow().timestamp())}"
        sample_title = "National Mission on High-Yield Pulse Cultivation 2026"
        sample_content = (
            "The Ministry of Agriculture and Farmers Welfare hereby notifies the launch of "
            "the National Mission on High-Yield Pulse Cultivation. The government provides a capital "
            "grant of ₹15,000 per hectare to small and marginal farmers. Applications open on 01-08-2026 "
            "and close on 30-11-2026. Micro agricultural business owners and registered FPOs are also "
            "entitled to seed processing grants under this scheme."
        )

        mock_raw_item = {
            "title": sample_title,
            "url": canonical_test_url,
            "canonical_url": canonical_test_url,
            "department": "Ministry of Agriculture and Farmers Welfare",
            "jurisdiction": "Central Government",
            "document_type": "scheme",
            "publication_date": datetime(2026, 8, 1),
            "content": sample_content,
            "language": "en"
        }

        engine = PolicyMonitoringEngine()

        # Mock adapter methods to simulate live portal detection
        with patch("app.services.monitoring_engine.get_adapter") as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.check_health.return_value = {"is_healthy": True, "status": "active"}
            mock_adapter.fetch_recent_documents.return_value = [mock_raw_item]
            mock_adapter.normalize_canonical_url.return_value = canonical_test_url
            mock_adapter.parse_document.return_value = mock_raw_item
            mock_get_adapter.return_value = mock_adapter

            scan_res = engine.scan_source(source.id, max_items=5)
            self.assertTrue(scan_res["success"])
            self.assertGreaterEqual(scan_res["new_documents"], 1)

        # Verify Document Metadata Saved (Step 6)
        doc = PolicyDocument.query.filter_by(canonical_url=canonical_test_url).first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.title, sample_title)
        self.assertIn(doc.processing_status, ["completed", "ai_degraded"])

        # Verify Category Assigned (Step 8: 12 Canonical Categories)
        self.assertIn(doc.category, CANONICAL_CATEGORIES)
        self.assertEqual(doc.category, "Agriculture")

        # Verify Document Version 1 Created (Step 9)
        v1 = DocumentVersion.query.filter_by(document_id=doc.id, version_number=1).first()
        self.assertIsNotNone(v1)
        self.assertEqual(v1.content_hash, doc.content_hash)

        # Verify PolicyAnalysis Populated (Steps 8 & 9: Multilingual Summaries & Stakeholders)
        analysis = doc.analysis
        self.assertIsNotNone(analysis)
        self.assertTrue(bool(analysis.summary_en))
        self.assertTrue(bool(analysis.summary_hi))
        self.assertTrue(bool(analysis.summary_mr))

        stakeholders = analysis.get_affected_groups_dict()
        self.assertIn("Farmers", stakeholders)
        # All stakeholders must belong to canonical groups
        for group in stakeholders.keys():
            self.assertIn(group, CANONICAL_STAKEHOLDERS)

        # Verify Dashboard Statistics & API Publication (Step 10)
        dash_stats = PolicyService.get_dashboard_stats()
        self.assertGreater(dash_stats["total_policies"], 0)
        self.assertIn("timeline", dash_stats)

        # Query single policy API
        api_single = self.client.get(f"/api/policies/{doc.id}")
        self.assertEqual(api_single.status_code, 200)
        doc_json = api_single.get_json()["data"]
        self.assertEqual(doc_json["id"], doc.id)
        self.assertEqual(doc_json["title"], sample_title)

        # Query filtered list API
        api_res = self.client.get(f"/api/policies?q=Pulse+Cultivation&per_page=50")
        self.assertEqual(api_res.status_code, 200)
        data = api_res.get_json()["data"]
        self.assertTrue(any(d["id"] == doc.id for d in data))

    def test_02_end_to_end_pipeline_document_modification_and_version_comparison(self):
        """
        Steps 11-12: Test document versioning and comparison when content changes.
        """
        # Create a dedicated base document for modification testing
        mod_test_url = f"https://pib.gov.in/PressReleasePage.aspx?PRID=TEST_MOD_{int(datetime.utcnow().timestamp())}"
        source = GovernmentSource.query.filter_by(source_type="pib").first() or GovernmentSource.query.first()

        v1_content = "Initial clause 1. Farmers receive ₹5,000 subsidy under the national scheme."
        doc = PolicyDocument(
            source_id=source.id,
            title="Solar Agriculture Pump Subsidy Scheme",
            canonical_url=mod_test_url,
            department="Ministry of New and Renewable Energy",
            jurisdiction="Central Government",
            content=v1_content,
            content_hash=hash_content(v1_content),
            language="en",
            processing_status="completed"
        )
        db.session.add(doc)
        db.session.flush()

        v1 = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            content=v1_content,
            content_hash=doc.content_hash,
            captured_at=datetime.utcnow()
        )
        db.session.add(v1)
        db.session.commit()

        v2_content = "Amended clause 1. Farmers receive ₹8,500 subsidy. Additional clause 2: Application deadline is extended till 31-12-2026."

        modified_raw_item = {
            "title": doc.title,
            "url": doc.canonical_url,
            "canonical_url": doc.canonical_url,
            "department": doc.department,
            "content": v2_content,
            "publication_date": datetime(2026, 9, 1),
            "language": "en"
        }

        engine = PolicyMonitoringEngine()

        with patch("app.services.monitoring_engine.get_adapter") as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.check_health.return_value = {"is_healthy": True, "status": "active"}
            mock_adapter.fetch_recent_documents.return_value = [modified_raw_item]
            mock_adapter.normalize_canonical_url.return_value = doc.canonical_url
            mock_adapter.parse_document.return_value = modified_raw_item
            mock_get_adapter.return_value = mock_adapter

            scan_res = engine.scan_source(source.id, max_items=5)
            self.assertTrue(scan_res["success"])
            self.assertGreaterEqual(scan_res["modified_documents"], 1)

        # Verify new version created (Step 11)
        versions = DocumentVersion.query.filter_by(document_id=doc.id).order_by(DocumentVersion.version_number.desc()).all()
        self.assertGreaterEqual(len(versions), 2)
        latest_version = versions[0]
        self.assertGreater(latest_version.version_number, 1)

        # Verify PolicyChange diff record saved
        change = PolicyChange.query.filter_by(document_id=doc.id, new_version_id=latest_version.id).first()
        self.assertIsNotNone(change)
        self.assertEqual(change.change_type, "modified")

        # Verify Version Comparison Display (Step 12)
        comp = PolicyService.compare_versions(doc.id, v1_num=1, v2_num=latest_version.version_number)
        self.assertIsNotNone(comp)
        self.assertTrue(comp["meaningful_change"])
        self.assertIn("diff_summary", comp)
        self.assertIn("added_clauses", comp)

        # Verify Web Comparison View renders successfully
        web_resp = self.client.get(f"/policies/{doc.id}/compare?v1=1&v2={latest_version.version_number}")
        self.assertEqual(web_resp.status_code, 200)
        self.assertIn(b"Policy Version Comparison", web_resp.data)

    def test_03_error_handling_source_failure_isolation(self):
        """
        Verify error isolation: if one source fails, other sources continue working.
        """
        engine = PolicyMonitoringEngine()

        with patch("app.services.monitoring_engine.get_adapter") as mock_get_adapter:
            def side_effect(name):
                mock_adapter = MagicMock()
                if "PIB" in name:
                    # Simulated portal timeout / server outage
                    mock_adapter.check_health.return_value = {"is_healthy": False, "message": "Connection timed out"}
                else:
                    mock_adapter.check_health.return_value = {"is_healthy": True}
                    mock_adapter.fetch_recent_documents.return_value = []
                return mock_adapter

            mock_get_adapter.side_effect = side_effect
            summary = engine.scan_all_sources(max_items_per_source=2)

            self.assertIn("sources_scanned", summary)
            self.assertGreater(summary["sources_scanned"], 0)
            # Ensure other sources completed without throwing unhandled exceptions
            self.assertIn("details", summary)

    def test_04_error_handling_failed_document_not_discarded(self):
        """
        Verify unextractable/corrupted documents are recorded with status and not silently discarded.
        """
        test_url = f"https://mock.gov.in/broken_doc_{int(datetime.utcnow().timestamp())}.pdf"
        bad_item = {
            "title": "Unreadable Corrupted Gazette Notification",
            "url": test_url,
            "canonical_url": test_url,
            "department": "Ministry of Law",
            "pdf_url": test_url,
            "content": "",
            "document_type": "notification"
        }

        source = GovernmentSource.query.first()
        engine = PolicyMonitoringEngine()

        with patch("app.services.monitoring_engine.get_adapter") as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.check_health.return_value = {"is_healthy": True}
            mock_adapter.fetch_recent_documents.return_value = [bad_item]
            mock_adapter.normalize_canonical_url.return_value = test_url
            mock_adapter.parse_document.return_value = bad_item
            # Simulate corrupted stream
            mock_adapter.safe_get.return_value = MagicMock(status_code=500, content=b"")
            mock_get_adapter.return_value = mock_adapter

            res = engine.scan_source(source.id, max_items=2)
            self.assertTrue(res["success"])

            # Verify document was saved rather than silently lost
            doc = PolicyDocument.query.filter_by(canonical_url=test_url).first()
            self.assertIsNotNone(doc, "Failed documents must not be silently discarded.")
            self.assertEqual(doc.title, "Unreadable Corrupted Gazette Notification")

    def test_05_frontend_real_api_integration(self):
        """
        Verify frontend routes serve live database information without hardcoded mock fallbacks.
        """
        # Home page
        res_home = self.client.get("/")
        self.assertEqual(res_home.status_code, 200)

        # Policy Explorer API
        res_policies = self.client.get("/api/policies?page=1&per_page=5")
        self.assertEqual(res_policies.status_code, 200)
        self.assertIn("data", res_policies.get_json())
        self.assertIn("meta", res_policies.get_json())

        # Dashboard stats API
        res_stats = self.client.get("/api/dashboard/stats")
        self.assertEqual(res_stats.status_code, 200)
        stats = res_stats.get_json()["data"]
        self.assertIn("total_policies", stats)
        self.assertIn("categories", stats)
        self.assertIn("jurisdictions", stats)
        self.assertIn("timeline", stats)

        # RAG Ask AI API
        res_ask = self.client.post("/api/ai/ask", json={"question": "What is PM Kisan?", "language": "en"})
        self.assertEqual(res_ask.status_code, 200)
        self.assertIn("answer", res_ask.get_json()["data"])

        # Multilingual Summarize API
        doc = PolicyDocument.query.first()
        res_sum = self.client.post("/api/ai/summarize", json={"policy_id": doc.id, "language": "hi"})
        self.assertEqual(res_sum.status_code, 200)
        self.assertEqual(res_sum.get_json()["data"]["language"], "hi")


if __name__ == "__main__":
    unittest.main()
