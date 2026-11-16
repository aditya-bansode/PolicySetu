"""
Unit and integration tests for Maharashtra MahaDBT Scholarship Integration in PolicySetu.
"""
import unittest
from app import create_app, db
from app.models.document import PolicyDocument
from app.models.scholarship import ScholarshipScheme
from app.services.scholarship_service import ScholarshipService, VERIFIED_MAHADBT_SCHEMES
from app.adapters.mahadbt_adapter import MahaDBTAdapter
from app.ai.rag_engine import PolicyRAGEngine

class TestMahaDBTIntegration(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_verified_schemes_catalog_integrity(self):
        """Ensure all verified schemes have required fields and proper MahaDBT 2.0 guidelines links."""
        self.assertGreaterEqual(len(VERIFIED_MAHADBT_SCHEMES), 10)
        for scheme in VERIFIED_MAHADBT_SCHEMES:
            self.assertIn("scheme_name", scheme)
            self.assertIn("department", scheme)
            self.assertEqual(scheme["jurisdiction"], "Maharashtra")
            self.assertEqual(scheme["category"], "Education")
            self.assertEqual(scheme["academic_year"], "2026-27")
            self.assertIn("mahadbt", scheme["official_scheme_url"])
            self.assertIn("mahadbt2.maharashtra.gov.in", scheme["official_guidelines_url"])
            self.assertTrue(any(status in scheme["application_status"] for status in ["Active", "Open", "Upcoming"]))

    def test_seed_and_database_persistence(self):
        """Test seeding verified schemes into the database."""
        service = ScholarshipService()
        result = service.seed_all_verified_scholarships()
        self.assertGreaterEqual(result["total_schemes"], 10)

        # Check DB count
        scholarships = ScholarshipScheme.query.all()
        self.assertEqual(len(scholarships), result["total_schemes"])

        # Verify linked policy documents
        for s in scholarships:
            self.assertIsNotNone(s.policy_document_id)
            doc = PolicyDocument.query.get(s.policy_document_id)
            self.assertIsNotNone(doc)
            self.assertEqual(doc.jurisdiction, "Maharashtra")
            self.assertEqual(doc.category, "Education")
            self.assertEqual(doc.document_type.upper(), "SCHEME")
            
            # Check serialized dict has enriched scholarship info
            doc_dict = doc.to_dict()
            self.assertTrue(doc_dict.get("is_scholarship"))
            self.assertEqual(doc_dict.get("academic_year"), "2026-27")
            self.assertIsNotNone(doc_dict.get("eligibility_criteria"))
            self.assertIn("mahadbt", doc_dict.get("official_scheme_url", ""))

    def test_policy_filtering_by_maharashtra_and_education(self):
        """Verify schemes appear in All Policies when filtered by Education and Maharashtra."""
        service = ScholarshipService()
        service.seed_all_verified_scholarships()

        res = self.client.get('/api/policies?jurisdiction=Maharashtra&category=Education&type=Scheme')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        policies = data["data"]
        self.assertGreaterEqual(len(policies), 10)

        titles = [p["title"] for p in policies]
        self.assertTrue(any("Eklavya" in t for t in titles))
        self.assertTrue(any("Post-Matric" in t for t in titles))

    def test_keyword_search_for_scholarships(self):
        """Verify searching for specific scholarships works via the search API."""
        service = ScholarshipService()
        service.seed_all_verified_scholarships()

        # Search for Eklavya
        res = self.client.get('/api/policies?q=Eklavya')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        policies = data["data"]
        self.assertGreaterEqual(len(policies), 1)
        self.assertIn("Eklavya", policies[0]["title"])

        # Search for Post-Matric
        res2 = self.client.get('/api/policies?q=Post-Matric')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2["success"])
        policies2 = data2["data"]
        self.assertGreaterEqual(len(policies2), 1)

    def test_scholarship_api_endpoints(self):
        """Test GET /api/scholarships and GET /api/scholarships/<id>."""
        service = ScholarshipService()
        service.seed_all_verified_scholarships()

        res = self.client.get('/api/scholarships')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        scholarships = data["data"]
        self.assertGreaterEqual(len(scholarships), 10)

        first_id = scholarships[0]["id"]
        res_detail = self.client.get(f'/api/scholarships/{first_id}')
        self.assertEqual(res_detail.status_code, 200)
        detail_data = res_detail.get_json()
        self.assertTrue(detail_data["success"])
        self.assertEqual(detail_data["data"]["id"], first_id)
        self.assertEqual(detail_data["data"]["academic_year"], "2026-27")

    def test_mahadbt_adapter_instantiation_and_discovery(self):
        """Test MahaDBT adapter functions cleanly."""
        adapter = MahaDBTAdapter()
        self.assertEqual(adapter.source_code, "mahadbt")
        self.assertEqual(adapter.source_name, "MahaDBT Scholarship Portal")
        # Test discovery runs safely
        results = adapter.fetch_recent_documents(limit=5)
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 5)
        for r in results:
            self.assertEqual(r["jurisdiction"], "Maharashtra")
            self.assertEqual(r["category"], "Education")

    def test_rag_answering_on_mahadbt_queries(self):
        """Verify RAG engine accurately answers MahaDBT scholarship questions with citations."""
        service = ScholarshipService()
        service.seed_all_verified_scholarships()

        rag = PolicyRAGEngine()

        # Query 1: Department providing Eklavya Scholarship
        ans1 = rag.answer_question("Which department provides Eklavya scholarship?")
        self.assertTrue(ans1["verified"])
        self.assertTrue("Higher Education" in ans1["answer"] or "DHE" in ans1["answer"])
        self.assertGreaterEqual(len(ans1["citations"]), 1)

        # Query 2: Eligibility for Eklavya Scholarship
        ans2 = rag.answer_question("Who is eligible for Eklavya Scholarship?")
        self.assertTrue(ans2["verified"])
        self.assertTrue(any(w in ans2["answer"] for w in ["Arts", "Law", "Commerce", "Science", "60%"]))

        # Query 3: Where to apply
        ans3 = rag.answer_question("Where can I apply for Maharashtra MahaDBT scholarships?")
        self.assertTrue(ans3["verified"])
        self.assertIn("mahadbt2.maharashtra.gov.in", ans3["answer"])


if __name__ == '__main__':
    unittest.main()
