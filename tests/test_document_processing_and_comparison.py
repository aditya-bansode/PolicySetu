"""
PolicySetu — Document Processing & Version Comparison Test Suite
================================================================
Comprehensive automated tests covering:
1. PyMuPDF PDF extraction (text, pages, metadata, headings, tables)
2. PDF Edge cases (empty, corrupted, encrypted, scanned/OCR required)
3. HTML semantic extraction and boilerplate stripping
4. Deduplicated file storage
5. Meaningful content difference vs cosmetic timestamp changes
6. Clause-by-clause diffing (added, removed, modified clauses with page references)
7. End-to-end DocumentProcessingService workflow
"""

import os
import shutil
import unittest
import datetime
import pymupdf

from app import create_app
from app.extensions import db
from app.models.source import GovernmentSource
from app.models.document import PolicyDocument, DocumentVersion, PolicyChange
from app.models.analysis import PolicyAnalysis
from app.storage.document_storage import DocumentStorageManager
from app.extractors.pdf_extractor import PDFExtractor
from app.extractors.html_extractor import HTMLExtractor
from app.extractors.document_extractor import DocumentExtractor
from app.services.comparison_engine import PolicyComparisonEngine
from app.services.document_processing_service import DocumentProcessingService


class TestDocumentStorage(unittest.TestCase):
    """Test deduplicated local document storage."""

    def setUp(self):
        self.test_dir = os.path.join("data", "test_storage")
        os.makedirs(self.test_dir, exist_ok=True)
        self.manager = DocumentStorageManager(base_storage_dir=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_save_and_deduplicate_storage(self):
        """Verify files with identical SHA-256 reuse storage path without duplicate writes."""
        content = b"%PDF-1.6 Sample Policy Content\nSection 1: Guidelines."
        
        # First save
        res1 = self.manager.save_document(content, filename_hint="policy.pdf", source_id=1)
        self.assertFalse(res1["is_duplicate"])
        self.assertTrue(os.path.exists(res1["file_path"]))
        self.assertEqual(res1["file_size"], len(content))

        # Second save of identical bytes
        res2 = self.manager.save_document(content, filename_hint="policy_copy.pdf", source_id=1)
        self.assertTrue(res2["is_duplicate"])
        self.assertEqual(res1["file_path"], res2["file_path"])
        self.assertEqual(res1["content_hash"], res2["content_hash"])

    def test_02_empty_bytes_raises_error(self):
        """Cannot save 0-byte document."""
        with self.assertRaises(ValueError):
            self.manager.save_document(b"", filename_hint="empty.pdf")


class TestPDFExtraction(unittest.TestCase):
    """Test PyMuPDF extraction across normal, corrupted, encrypted, and scanned PDFs."""

    def _create_sample_pdf(self) -> bytes:
        """Create a multi-page PDF with metadata, headings, tables, and clauses."""
        doc = pymupdf.open()
        doc.set_metadata({
            "title": "National Green Energy Policy 2026",
            "author": "Ministry of Power",
            "subject": "Renewable Energy Transition",
        })

        # Page 1
        page1 = doc.new_page()
        page1.insert_text(
            (50, 60),
            "National Green Energy Policy 2026\n"
            "Section 1: Preliminary Provisions\n"
            "This policy establishes renewable energy quotas for commercial entities.\n"
            "Clause 1.1: Scope and Applicability\n"
            "Applies to all heavy manufacturing units exceeding 100kW grid demand.\n",
            fontsize=12
        )

        # Page 2
        page2 = doc.new_page()
        page2.insert_text(
            (50, 60),
            "Section 2: Financial Incentives and Capital Subsidies\n"
            "Eligible green units shall receive a 35 percent direct capital subsidy on rooftop solar installations.\n"
            "Clause 2.1: Disqualification Criteria\n"
            "Entities with unresolved environmental penalty proceedings are strictly ineligible.\n",
            fontsize=12
        )

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_03_extract_normal_pdf(self):
        """Extract full text, page numbers, metadata, and headings using PyMuPDF."""
        pdf_bytes = self._create_sample_pdf()
        res = PDFExtractor.extract(pdf_bytes)

        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["page_count"], 2)
        self.assertFalse(res["ocr_required"])
        self.assertEqual(res["metadata"]["title"], "National Green Energy Policy 2026")
        self.assertEqual(res["metadata"]["author"], "Ministry of Power")

        # Verify page mapping
        self.assertEqual(len(res["pages"]), 2)
        self.assertEqual(res["pages"][0]["page_number"], 1)
        self.assertIn("Section 1", res["pages"][0]["text"])
        self.assertEqual(res["pages"][1]["page_number"], 2)
        self.assertIn("Section 2", res["pages"][1]["text"])

        # Verify headings detection
        headings_text = [h["text"] for h in res["headings"]]
        self.assertTrue(any("Section 1" in h for h in headings_text))
        self.assertTrue(any("Section 2" in h for h in headings_text))

    def test_04_handle_empty_pdf(self):
        """Empty buffer returns clean empty status without crashing."""
        res = PDFExtractor.extract(b"")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "empty")
        self.assertEqual(res["page_count"], 0)

    def test_05_handle_corrupted_pdf(self):
        """Corrupted/invalid byte stream returns corrupted status."""
        garbage_bytes = b"Random string without PDF magic header or trailer."
        res = PDFExtractor.extract(garbage_bytes)
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "corrupted")
        self.assertIn("Corrupted", res["error"])

    def test_06_handle_encrypted_pdf(self):
        """Password-protected encrypted PDF is detected and marked encrypted."""
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Classified Policy Notification")
        # Encrypt with owner and user password
        perm = pymupdf.PDF_PERM_ACCESSIBILITY
        doc.save(
            "test_encrypted.pdf",
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="OwnerPass123",
            user_pw="SecretPass123",
            permissions=perm
        )
        doc.close()

        with open("test_encrypted.pdf", "rb") as f:
            enc_bytes = f.read()
        os.remove("test_encrypted.pdf")

        res = PDFExtractor.extract(enc_bytes)
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "encrypted")
        self.assertTrue(res.get("is_encrypted"))

    def test_07_detect_scanned_pdf_and_mark_ocr_required(self):
        """PDF with pages but missing native digital text is marked as scanned with OCR required."""
        # Create PDF page with no text (e.g. blank page representing scanned bitmap image)
        doc = pymupdf.open()
        page = doc.new_page()  # 0 text chars
        scanned_bytes = doc.tobytes()
        doc.close()

        res = PDFExtractor.extract(scanned_bytes)
        self.assertTrue(res["success"])
        self.assertTrue(res["ocr_required"])
        self.assertEqual(res["ocr_status"], "pending_ocr")
        self.assertIn("OCR extraction required", res["ocr_message"])


class TestHTMLExtraction(unittest.TestCase):
    """Test HTML semantic extraction and boilerplate cleaning."""

    def test_08_extract_html_content_and_metadata(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cabinet Decision on Semiconductor Subsidy</title>
            <meta name="description" content="Official cabinet press release regarding fabrication plant incentives.">
            <meta name="author" content="Press Information Bureau">
        </head>
        <body>
            <nav><a href="/">Home</a><a href="/login">Login</a></nav>
            <header>Government Portal Header</header>
            <main>
                <h1>Cabinet Approves Semiconductor Mission Expansion</h1>
                <p>The Union Cabinet has approved an outlay of INR 76,000 Crore for design-linked incentives.</p>
                <h2>Key Provisions</h2>
                <ul>
                    <li>50 percent fiscal support for silicon wafer fabs.</li>
                    <li>Support for compound semiconductors and advanced packaging.</li>
                </ul>
                <table>
                    <tr><th>Component</th><th>Outlay (INR Cr)</th></tr>
                    <tr><td>Silicon Fabs</td><td>40,000</td></tr>
                    <tr><td>Design Linked</td><td>10,000</td></tr>
                </table>
            </main>
            <footer>Copyright 2026 Government of India. All rights reserved.</footer>
            <script>console.log("analytics tracking");</script>
        </body>
        </html>
        """
        res = HTMLExtractor.extract(html)
        self.assertTrue(res["success"])
        self.assertEqual(res["metadata"]["title"], "Cabinet Decision on Semiconductor Subsidy")
        self.assertIn("76,000 Crore", res["text"])
        # Boilerplate check: nav, footer, script stripped
        self.assertNotIn("analytics tracking", res["text"])
        self.assertNotIn("Copyright 2026 Government of India", res["text"])
        self.assertNotIn("Home", res["text"])

        # Headings check
        h_texts = [h["text"] for h in res["headings"]]
        self.assertIn("Cabinet Approves Semiconductor Mission Expansion", h_texts)
        self.assertIn("Key Provisions", h_texts)

        # Tables check
        self.assertEqual(len(res["tables"]), 1)
        self.assertEqual(res["tables"][0]["row_count"], 3)


class TestComparisonEngine(unittest.TestCase):
    """Test clause-level comparison and meaningful difference verification."""

    def test_09_meaningful_difference_ignores_website_timestamp_changes(self):
        """Do not label a document as updated merely because its website timestamp changed."""
        v1_text = (
            "National Solar Policy\n"
            "Last Updated: 2026-09-01T12:00:00Z\n"
            "Section 1: Subsidy Rate\n"
            "Subsidy is fixed at 30 percent for residential units."
        )
        # Only the timestamp changed on the website
        v2_text = (
            "National Solar Policy\n"
            "Last Updated: 2026-11-15T16:45:00Z\n"
            "Section 1: Subsidy Rate\n"
            "Subsidy is fixed at 30 percent for residential units."
        )

        has_diff = PolicyComparisonEngine.has_meaningful_difference(v1_text, v2_text)
        self.assertFalse(has_diff)

        comp = PolicyComparisonEngine.compare(v1_text, v2_text, v1_num=1, v2_num=2)
        self.assertTrue(comp["identical"])
        self.assertFalse(comp["meaningful_change"])
        self.assertEqual(len(comp["modified_clauses"]), 0)

    def test_10_clause_level_diff_detects_added_removed_and_modified(self):
        """Detect added, removed, and modified clauses with page numbers."""
        v1_text = (
            "[Page 1]\n"
            "Section 1: Scope\n"
            "Applies to micro and small rural enterprises.\n\n"
            "[Page 2]\n"
            "Section 2: Capital Assistance\n"
            "Eligible units receive 25 percent capital subsidy.\n\n"
            "[Page 3]\n"
            "Section 3: Sunset Clause\n"
            "This scheme shall terminate on 31 December 2026."
        )

        v2_text = (
            "[Page 1]\n"
            "Section 1: Scope\n"
            "Applies to micro, small, and medium rural enterprises.\n\n"
            "[Page 2]\n"
            "Section 2: Capital Assistance\n"
            "Eligible units receive 40 percent capital subsidy with interest subvention.\n\n"
            "[Page 2]\n"
            "Section 4: Priority Lending Quota\n"
            "Scheduled commercial banks shall earmark 15 percent quota for women-led units."
        )

        comp = PolicyComparisonEngine.compare(v1_text, v2_text, v1_num=1, v2_num=2)
        self.assertFalse(comp["identical"])
        self.assertTrue(comp["meaningful_change"])

        # 1. Modified Clauses (Section 1 and Section 2)
        mod_sections = [m["section"] for m in comp["modified_clauses"]]
        self.assertTrue(any("Section 1" in s for s in mod_sections))
        self.assertTrue(any("Section 2" in s for s in mod_sections))

        # Check page reference on Section 2
        sec2_mod = next(m for m in comp["modified_clauses"] if "Section 2" in m["section"])
        self.assertEqual(sec2_mod["page"], 2)
        self.assertIn("25 percent", sec2_mod["before"])
        self.assertIn("40 percent", sec2_mod["after"])

        # 2. Added Clause (Section 4)
        add_sections = [a["section"] for a in comp["added_clauses"]]
        self.assertTrue(any("Section 4" in s for s in add_sections))
        sec4_add = next(a for a in comp["added_clauses"] if "Section 4" in a["section"])
        self.assertEqual(sec4_add["page"], 2)
        self.assertIn("women-led units", sec4_add["text"])

        # 3. Removed Clause (Section 3 Sunset Clause was deleted)
        rem_sections = [r["section"] for r in comp["removed_clauses"]]
        self.assertTrue(any("Section 3" in s for s in rem_sections))
        sec3_rem = next(r for r in comp["removed_clauses"] if "Section 3" in r["section"])
        self.assertEqual(sec3_rem["page"], 3)


class TestDocumentProcessingIntegration(unittest.TestCase):
    """End-to-end integration tests using DocumentProcessingService with SQLite."""

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
        self.storage_dir = os.path.join("data", "test_processing_storage")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.service = DocumentProcessingService(DocumentStorageManager(self.storage_dir))

        self.source = GovernmentSource(
            name="MNRE Official",
            base_url="https://mnre.gov.in",
            jurisdiction="Central Government",
            department="Renewable Energy",
            source_type="portal",
            enabled=True
        )
        db.session.add(self.source)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        PolicyAnalysis.query.delete()
        PolicyChange.query.delete()
        DocumentVersion.query.delete()
        PolicyDocument.query.delete()
        GovernmentSource.query.delete()
        db.session.commit()
        if os.path.exists(self.storage_dir):
            shutil.rmtree(self.storage_dir, ignore_errors=True)

    def test_11_process_pdf_and_create_version_history(self):
        """Ingest version 1 PDF, followed by amended version 2 PDF; verify version bump and PolicyChange."""
        canonical_url = "https://mnre.gov.in/policies/wind-solar-hybrid-2026.pdf"

        # 1. Create Version 1 PDF
        doc1 = pymupdf.open()
        p1 = doc1.new_page()
        p1.insert_text(
            (50, 50),
            "National Wind-Solar Hybrid Policy\n"
            "Section 1: Capacity Requirement\n"
            "Minimum rated capacity for hybrid project shall be 50 MW.",
            fontsize=12
        )
        pdf1_bytes = doc1.tobytes()
        doc1.close()

        # Ingest v1
        res1 = self.service.process_document(
            content_bytes=pdf1_bytes,
            filename_hint="wind_hybrid_v1.pdf",
            canonical_url=canonical_url,
            title="National Wind-Solar Hybrid Policy",
            source_id=self.source.id,
            category="Energy"
        )
        self.assertEqual(res1["action"], "created")
        self.assertEqual(res1["version_number"], 1)

        # 2. Ingest amended Version 2 PDF
        doc2 = pymupdf.open()
        p2 = doc2.new_page()
        p2.insert_text(
            (50, 50),
            "National Wind-Solar Hybrid Policy\n"
            "Section 1: Capacity Requirement\n"
            "Minimum rated capacity for hybrid project shall be reduced to 25 MW.\n"
            "Section 2: Storage Mandate\n"
            "Must integrate battery energy storage of 10 MW for 2 hours.",
            fontsize=12
        )
        pdf2_bytes = doc2.tobytes()
        doc2.close()

        res2 = self.service.process_document(
            content_bytes=pdf2_bytes,
            filename_hint="wind_hybrid_v2.pdf",
            canonical_url=canonical_url,
            source_id=self.source.id,
        )
        self.assertEqual(res2["action"], "modified")
        self.assertEqual(res2["version_number"], 2)

        # Query database to confirm records
        pol = PolicyDocument.query.filter_by(canonical_url=canonical_url).first()
        self.assertIsNotNone(pol)
        self.assertEqual(pol.versions.count(), 2)
        self.assertEqual(pol.changes.count(), 1)

        change = pol.changes.first()
        self.assertEqual(change.change_type, "modified")
        self.assertIn("Capacity Requirement", change.change_description)


if __name__ == "__main__":
    unittest.main()
