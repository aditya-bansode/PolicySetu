"""
PolicySetu — Unit & Integration Test Suite for Monitoring Engine & Adapters
===========================================================================
Tests every adapter (PIB, Maharashtra GR, India Code, e-Gazette) and the
10-step document detection pipeline.
"""

import os
import unittest
import datetime
from unittest.mock import MagicMock, patch

from app import create_app
from app.extensions import db
from app.models.source import GovernmentSource
from app.models.document import PolicyDocument, DocumentVersion, PolicyChange
from app.models.analysis import PolicyAnalysis
from app.models.monitoring import MonitoringLog

from app.adapters.base_adapter import BaseSourceAdapter
from app.adapters.pib_adapter import PIBSourceAdapter
from app.adapters.maharashtra_gr_adapter import MaharashtraGRAdapter
from app.adapters.india_code_adapter import IndiaCodeAdapter
from app.adapters.egazette_adapter import EGazetteAdapter
from app.adapters.registry import get_adapter, get_all_registered_adapters
from app.services.monitoring_engine import PolicyMonitoringEngine
from app.utils.helpers import hash_content, utc_now


class TestSourceAdapters(unittest.TestCase):
    """Unit tests for every government source adapter."""

    def test_01_base_adapter_canonical_url_normalization(self):
        """Verify URL normalization strips tracking params, fragments, and redundant ports."""
        raw_url = "HTTPS://PIB.gov.in:443/AllRel.aspx?utm_source=twitter&utm_medium=social&lang=1#heading"
        normalized = BaseSourceAdapter.normalize_canonical_url(raw_url)
        self.assertEqual(normalized, "https://pib.gov.in/AllRel.aspx?lang=1")

        url_with_trailing = "https://gr.maharashtra.gov.in/1145/Government-Resolutions/"
        self.assertEqual(BaseSourceAdapter.normalize_canonical_url(url_with_trailing), "https://gr.maharashtra.gov.in/1145/Government-Resolutions")

    def test_02_pib_adapter_date_parsing_and_isolation(self):
        """Verify PIB date parsing never invents dates."""
        adapter = PIBSourceAdapter()

        # Valid date string
        dt = adapter._parse_publication_date("प्रविष्टि तिथि: 15 NOV 2026 3:31PM by PIB Delhi")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 11)
        self.assertEqual(dt.day, 15)

        # Unparseable date string: MUST NOT invent date
        none_dt = adapter._parse_publication_date("Invalid date token without numbers")
        self.assertIsNone(none_dt)

        empty_dt = adapter._parse_publication_date("")
        self.assertIsNone(empty_dt)

    def test_03_pib_adapter_mock_listing_and_parsing(self):
        """Verify PIB listing HTML parsing and document extraction."""
        adapter = PIBSourceAdapter()
        mock_html = b"""
        <html><body>
            <a href="/PressReleaseDetail.aspx?PRID=999901">PM Launches Digital Mission</a>
            <a href="/PressReleaseDetail.aspx?PRID=999902">Cabinet Approves Agri Scheme</a>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.content = mock_html
        mock_resp.status_code = 200

        with patch.object(adapter, "safe_get", return_value=mock_resp):
            items = adapter.fetch_recent_documents(limit=5)
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0]["prid"], "999901")
            self.assertEqual(items[0]["title"], "PM Launches Digital Mission")

    def test_04_maharashtra_gr_date_parsing_and_categorization(self):
        """Verify Maharashtra GR date parsing (DD-MM-YYYY) and category heuristics."""
        adapter = MaharashtraGRAdapter()

        dt = adapter._parse_gr_date("13-11-2026")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.day, 13)
        self.assertEqual(dt.month, 11)
        self.assertEqual(dt.year, 2026)

        # Invalid date: never invent date
        self.assertIsNone(adapter._parse_gr_date("not-a-date"))

        # Category heuristics
        doc = adapter.parse_document({
            "title": "यंत्रमाग योजना",
            "department": "उद्योग, ऊर्जा व कामगार विभाग",
            "gr_code": "202611130001",
            "gr_date_str": "13-11-2026",
            "pdf_url": "https://gr.maharashtra.gov.in/Site/Upload/GR/202611130001.pdf"
        })
        self.assertEqual(doc["category"], "Commerce & Industry")
        self.assertEqual(doc["language"], "mr")
        self.assertEqual(doc["jurisdiction"], "State Government")

    def test_05_india_code_adapter_diagnostics(self):
        """Verify India Code adapter clearly marks SPA/auth restriction and does not claim access."""
        adapter = IndiaCodeAdapter()
        health = adapter.check_health()
        self.assertFalse(health["is_healthy"])
        self.assertEqual(health["status"], "inaccessible")
        self.assertIn("Angular SPA", health["message"])

        # Fetch returns empty list without crashing
        docs = adapter.fetch_recent_documents()
        self.assertEqual(len(docs), 0)

    def test_06_egazette_adapter_diagnostics(self):
        """Verify e-Gazette adapter clearly marks ASP.NET session state requirement."""
        adapter = EGazetteAdapter()
        health = adapter.check_health()
        self.assertFalse(health["is_healthy"])
        self.assertEqual(health["status"], "inaccessible")
        self.assertIn("ASP.NET session", health["message"])

        docs = adapter.fetch_recent_documents()
        self.assertEqual(len(docs), 0)

    def test_07_adapter_registry_lookup(self):
        """Verify central registry correctly maps aliases and identifiers."""
        self.assertIsInstance(get_adapter("pib"), PIBSourceAdapter)
        self.assertIsInstance(get_adapter("Press Information Bureau"), PIBSourceAdapter)
        self.assertIsInstance(get_adapter("maharashtra_gr"), MaharashtraGRAdapter)
        self.assertIsInstance(get_adapter("Maharashtra Govt. Resolutions"), MaharashtraGRAdapter)
        self.assertIsInstance(get_adapter("india_code"), IndiaCodeAdapter)
        self.assertIsInstance(get_adapter("egazette"), EGazetteAdapter)
        self.assertIsNone(get_adapter("non_existent_source_12345"))


class TestMonitoringEnginePipeline(unittest.TestCase):
    """Integration tests for the 10-step document detection and versioning engine."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.app_context.pop()

    def setUp(self):
        # Create test source
        self.test_source = GovernmentSource(
            name="Test PIB Portal",
            base_url="https://pib.gov.in",
            jurisdiction="Central Government",
            department="Ministry of Agriculture",
            source_type="pib",
            enabled=True
        )
        db.session.add(self.test_source)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        PolicyAnalysis.query.delete()
        PolicyChange.query.delete()
        DocumentVersion.query.delete()
        PolicyDocument.query.delete()
        MonitoringLog.query.delete()
        GovernmentSource.query.delete()
        db.session.commit()


    def test_08_new_document_detection_creates_version_1(self):
        """Step 6 & 9: Verify detection of a new document creates DocumentVersion 1."""
        engine = PolicyMonitoringEngine()

        mock_doc = {
            "title": "National Green Hydrogen Standard 2026",
            "url": "https://pib.gov.in/PressReleaseDetail.aspx?PRID=888801",
            "department": "Ministry of New and Renewable Energy",
            "jurisdiction": "Central Government",
            "state": None,
            "document_type": "policy",
            "category": "Energy",
            "publication_date": datetime.datetime(2026, 11, 15, 12, 0),
            "content": "Official Green Hydrogen standard defined with 2kg CO2/kg H2 threshold.",
            "language": "en",
        }

        # Mock adapter
        mock_adapter = MagicMock(spec=BaseSourceAdapter)
        mock_adapter.check_health.return_value = {"is_healthy": True, "status": "active"}
        mock_adapter.fetch_recent_documents.return_value = [mock_doc]
        mock_adapter.normalize_canonical_url.side_effect = lambda u: u
        mock_adapter.parse_document.return_value = mock_doc

        with patch("app.services.monitoring_engine.get_adapter", return_value=mock_adapter):
            res = engine.scan_source(self.test_source.id)
            self.assertTrue(res["success"])
            self.assertEqual(res["new_documents"], 1)

            # Query database
            doc = PolicyDocument.query.filter_by(canonical_url="https://pib.gov.in/PressReleaseDetail.aspx?PRID=888801").first()
            self.assertIsNotNone(doc)
            self.assertEqual(doc.title, "National Green Hydrogen Standard 2026")

            # Check version 1
            versions = DocumentVersion.query.filter_by(document_id=doc.id).all()
            self.assertEqual(len(versions), 1)
            self.assertEqual(versions[0].version_number, 1)
            self.assertEqual(versions[0].content_hash, hash_content(mock_doc["content"]))

    def test_09_duplicate_detection_does_not_create_version(self):
        """Step 4: Verify identical content leaves versions unchanged."""
        engine = PolicyMonitoringEngine()

        mock_doc = {
            "title": "Existing National Standard",
            "url": "https://pib.gov.in/PressReleaseDetail.aspx?PRID=888802",
            "department": "Ministry of Power",
            "jurisdiction": "Central Government",
            "state": None,
            "document_type": "policy",
            "category": "Energy",
            "publication_date": datetime.datetime(2026, 11, 15, 10, 0),
            "content": "Existing unmodified standard text.",
            "language": "en",
        }

        mock_adapter = MagicMock(spec=BaseSourceAdapter)
        mock_adapter.check_health.return_value = {"is_healthy": True, "status": "active"}
        mock_adapter.fetch_recent_documents.return_value = [mock_doc]
        mock_adapter.normalize_canonical_url.side_effect = lambda u: u
        mock_adapter.parse_document.return_value = mock_doc

        with patch("app.services.monitoring_engine.get_adapter", return_value=mock_adapter):
            # First pass: creates document
            res1 = engine.scan_source(self.test_source.id)
            self.assertEqual(res1["new_documents"], 1)

            # Second pass: identical content
            res2 = engine.scan_source(self.test_source.id)
            self.assertEqual(res2["new_documents"], 0)
            self.assertEqual(res2["unchanged_documents"], 1)

            doc = PolicyDocument.query.filter_by(canonical_url=mock_doc["url"]).first()
            self.assertEqual(doc.versions.count(), 1)

    def test_10_modified_document_creates_version_2_and_policy_change(self):
        """Step 7: Verify modified content creates version 2 and logs a PolicyChange record."""
        engine = PolicyMonitoringEngine()

        initial_doc = {
            "title": "Solar Subsidy Scheme Guidelines",
            "url": "https://pib.gov.in/PressReleaseDetail.aspx?PRID=888803",
            "department": "Ministry of Power",
            "jurisdiction": "Central Government",
            "state": None,
            "document_type": "guidelines",
            "category": "Energy",
            "publication_date": datetime.datetime(2026, 11, 15, 10, 0),
            "content": "Original guidelines: Subsidy rate is 40 percent.",
            "language": "en",
        }

        mock_adapter = MagicMock(spec=BaseSourceAdapter)
        mock_adapter.check_health.return_value = {"is_healthy": True, "status": "active"}
        mock_adapter.normalize_canonical_url.side_effect = lambda u: u

        with patch("app.services.monitoring_engine.get_adapter", return_value=mock_adapter):
            # Phase 1: Ingest original
            mock_adapter.fetch_recent_documents.return_value = [initial_doc]
            mock_adapter.parse_document.return_value = initial_doc
            res1 = engine.scan_source(self.test_source.id)
            self.assertEqual(res1["new_documents"], 1)

            # Phase 2: Upstream publishes modified guidelines
            modified_doc = dict(initial_doc)
            modified_doc["content"] = "Amended guidelines: Subsidy rate is now 60 percent for rural households."
            mock_adapter.fetch_recent_documents.return_value = [modified_doc]
            mock_adapter.parse_document.return_value = modified_doc

            res2 = engine.scan_source(self.test_source.id)
            self.assertEqual(res2["modified_documents"], 1)

            # Verify database has 2 versions and 1 change record
            doc = PolicyDocument.query.filter_by(canonical_url=initial_doc["url"]).first()
            self.assertEqual(doc.versions.count(), 2)
            self.assertEqual(doc.changes.count(), 1)

            change = doc.changes.first()
            self.assertEqual(change.change_type, "modified")
            self.assertIn("promoted to version 2", change.change_description.lower())

    def test_11_fault_isolation_continues_monitoring_on_failure(self):
        """Verify that when one source fails, other sources are not aborted."""
        # Create second source
        s2 = GovernmentSource(
            name="Working Second Source",
            base_url="https://pib.gov.in",
            jurisdiction="Central Government",
            source_type="pib",
            enabled=True
        )
        db.session.add(s2)
        db.session.commit()

        engine = PolicyMonitoringEngine()

        def mock_scan_source(sid, max_items=15):
            if sid == self.test_source.id:
                return {"success": False, "source": "Failing Source", "status": "failed", "error": "Simulated Network Drop"}
            return {"success": True, "source": "Working Second Source", "status": "success", "new_documents": 2, "documents_found": 2}

        with patch.object(engine, "scan_source", side_effect=mock_scan_source):
            summary = engine.scan_all_sources()
            self.assertEqual(summary["sources_scanned"], 2)
            self.assertEqual(summary["new_documents_detected"], 2)


if __name__ == "__main__":
    unittest.main()
