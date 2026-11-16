"""
PolicySetu — Test AI Intelligence System
=========================================
Comprehensive automated tests for all 8 AI intelligence modules:
1. Policy classification (12 canonical categories).
2. Simple-language multilingual summarization (EN, HI, MR) with entity preservation.
3. Key provision extraction.
4. Important dates extraction.
5. Eligibility and condition extraction.
6. Potentially affected stakeholder identification (8 canonical groups).
7. Policy change explanation.
8. 6-Step RAG question answering system (retrieval, passage scoring, prompt injection defense,
   citations, page/section references, and verified missing evidence refusal without hallucinations).
9. Multilingual i18n JSON files validation.
10. Flask API endpoints integration (/api/ai/ask, /api/ai/summarize).
"""

import json
import os
import unittest
from app import create_app
from app.extensions import db
from app.models import PolicyDocument, DocumentVersion, PolicyAnalysis, GovernmentSource
from app.ai.classifier import policy_classifier, CANONICAL_CATEGORIES
from app.ai.summarizer import policy_summarizer, AI_TRANSLATION_NOTICES
from app.ai.extractor import PolicyExtractor, CANONICAL_STAKEHOLDERS
from app.ai.explainer import PolicyExplainer
from app.ai.rag_engine import PolicyRAGEngine
from app.services.ai_service import AIService


class TestAIIntelligenceSystem(unittest.TestCase):
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

    # ── MODULE 1: POLICY CLASSIFICATION ──────────────────────────────────────────
    def test_01_classification_canonical_categories(self):
        """Test classification covers the 12 canonical categories."""
        self.assertEqual(len(CANONICAL_CATEGORIES), 12)
        expected = [
            "Agriculture", "Education", "Healthcare", "Employment and Labour",
            "Business and Finance", "Housing", "Social Welfare", "Transport",
            "Environment", "Law and Justice", "Public Administration", "General"
        ]
        self.assertListEqual(sorted(CANONICAL_CATEGORIES), sorted(expected))

    def test_02_classification_multilingual(self):
        """Test policy classification across English, Hindi, and Marathi inputs."""
        # English Agriculture
        res_agri = policy_classifier.classify(
            title="Pradhan Mantri Krishi Sinchayee Yojana Guidelines",
            text="Provides financial subsidy to cultivators, farmers and irrigation projects for crops.",
            department="Ministry of Agriculture & Farmers Welfare"
        )
        self.assertEqual(res_agri["category"], "Agriculture")
        self.assertGreaterEqual(res_agri["confidence"], 0.60)

        # Hindi Education
        res_edu = policy_classifier.classify(
            title="राष्ट्रीय शिक्षा नीति छात्रवृत्ति योजना",
            text="विश्वविद्यालय और स्कूल के विद्यार्थियों के लिए नई शिक्षा छात्रवृत्ति की घोषणा की गई।",
            department="शिक्षा मंत्रालय"
        )
        self.assertEqual(res_edu["category"], "Education")

        # Marathi Healthcare
        res_health = policy_classifier.classify(
            title="महात्मा जोतिराव फुले जन आरोग्य योजना सुधारणा",
            text="रुग्णालयात मोफत उपचार, औषधोपचार आणि आरोग्य विमा संरक्षण वाढविण्याबाबत शासन निर्णय.",
            department="सार्वजनिक आरोग्य विभाग"
        )
        self.assertEqual(res_health["category"], "Healthcare")

        # Business and Finance
        res_fin = policy_classifier.classify(
            title="Credit Guarantee Scheme for Micro and Small Enterprises",
            text="Collateral-free credit facility for MSME business units and startup enterprises.",
            department="Ministry of Micro, Small and Medium Enterprises"
        )
        self.assertEqual(res_fin["category"], "Business and Finance")

    # ── MODULE 2: SIMPLE-LANGUAGE SUMMARIZATION & ENTITY PRESERVATION ────────────
    def test_03_summarization_multilingual_and_entity_preservation(self):
        """Test multilingual summarization preserves monetary values, dates, and ref numbers."""
        sample_doc = (
            "Notification No. AGR/2026/894. The Ministry of Agriculture hereby announces "
            "an allocation of ₹6,000 per annum to smallholder farmers effective from 15-08-2026. "
            "All applications must be submitted before 31-12-2026 under PRID: 982341."
        )

        entities = policy_summarizer.extract_critical_entities(sample_doc)
        self.assertTrue(any("6,000" in val for val in entities["monetary_values"]))
        self.assertTrue(any("15-08-2026" in d or "31-12-2026" in d for d in entities["dates"]))
        self.assertTrue(any("AGR/2026/894" in r or "982341" in r for r in entities["references"]))

        # Check summaries in EN, HI, MR
        multi = policy_summarizer.summarize_multilingual(
            title="PM Kisan Financial Assistance",
            text=sample_doc,
            department="Ministry of Agriculture"
        )
        self.assertIn("en", multi)
        self.assertIn("hi", multi)
        self.assertIn("mr", multi)
        self.assertIn("Ministry of Agriculture", multi["en"])

        # Verify AI translation notice is present and explicit
        en_res = policy_summarizer.summarize("PM Kisan", sample_doc, language="en")
        hi_res = policy_summarizer.summarize("PM Kisan", sample_doc, language="hi")
        mr_res = policy_summarizer.summarize("PM Kisan", sample_doc, language="mr")

        self.assertTrue(en_res["is_ai_generated"])
        self.assertIn("AI-generated", en_res["disclaimer"])
        self.assertIn("AI-जनरेटेड", hi_res["disclaimer"])
        self.assertIn("AI-निर्मित", mr_res["disclaimer"])

    # ── MODULES 3, 4, 5, 6: INTELLIGENCE EXTRACTION ──────────────────────────────
    def test_04_provisions_and_dates_extraction(self):
        """Test extraction of key provisions and structured dates."""
        text = (
            "1. The scheme shall provide an interest subvention of 3% on short-term crop loans.\n"
            "2. Farmers shall be entitled to prompt repayment incentives up to ₹3,00,000.\n"
            "3. Digital verification through Aadhaar shall be mandated across all commercial banks.\n"
            "The notification is dated 01-04-2026 and comes into force with effect from 01-06-2026. "
            "The final application deadline is 31-10-2026."
        )

        provisions = PolicyExtractor.extract_provisions(text, "Crop Loan Subvention")
        self.assertGreaterEqual(len(provisions), 2)
        self.assertTrue(any("interest subvention" in p.lower() or "prompt repayment" in p.lower() for p in provisions))

        dates = PolicyExtractor.extract_dates(text)
        self.assertIn("application_deadline", dates)
        self.assertEqual(dates["application_deadline"], "31-10-2026")

    def test_05_eligibility_and_stakeholder_identification(self):
        """Test eligibility extraction and identification of canonical stakeholder groups."""
        text = (
            "Eligibility criteria: The applicant must be a resident cultivator possessing cultivable "
            "landholding not exceeding 2 hectares. Senior citizens aged 60 and above shall receive "
            "additional pension assistance. Micro business owners and registered MSME enterprises "
            "are also eligible to apply for processing unit grants."
        )

        eligibility = PolicyExtractor.extract_eligibility(text)
        self.assertIn("cultivable landholding", eligibility.lower())

        stakeholders = PolicyExtractor.extract_stakeholders(text)
        self.assertIn("Farmers", stakeholders)
        self.assertIn("Senior citizens", stakeholders)
        self.assertIn("Business owners", stakeholders)
        # Ensure all detected groups belong to canonical list
        for group in stakeholders.keys():
            self.assertIn(group, CANONICAL_STAKEHOLDERS)

    # ── MODULE 7: POLICY CHANGE EXPLANATION ──────────────────────────────────────
    def test_06_policy_change_explanation(self):
        """Test version change explanation between two versions of a policy."""
        old_text = "The subsidy amount is ₹25,000 for rural beneficiaries. Application deadline is 31-03-2026."
        new_text = "The subsidy amount is ₹35,000 for rural beneficiaries. Application deadline is extended till 30-06-2026. Online registration on the portal is mandatory."

        explanation = PolicyExplainer.explain_changes(
            title="Solar Pump Subsidy Guidelines",
            old_text=old_text,
            new_text=new_text,
            language="en"
        )

        self.assertIn("summary_explanation", explanation)
        self.assertTrue(explanation["is_ai_interpretation"])
        self.assertIn("disclaimer", explanation)
        self.assertGreater(len(explanation["key_impact_points"]), 0)

        # Marathi explanation
        exp_mr = PolicyExplainer.explain_changes(
            title="सौर कृषी पंप योजना",
            old_text=old_text,
            new_text=new_text,
            language="mr"
        )
        self.assertIn("नवीन", exp_mr["summary_explanation"])

    # ── MODULE 8: 6-STEP RAG QUESTION ANSWERING & AI SAFETY ──────────────────────
    def test_07_rag_system_grounded_answer_and_citations(self):
        """Test RAG system returns verified grounded answers with citations and page references."""
        # Find an existing policy in test DB or seed a test policy
        policy = PolicyDocument.query.first()
        if not policy:
            policy = PolicyDocument(
                title="National Renewable Energy Policy 2026",
                content="[Page 1] Section 2: Financial Assistance. The Ministry mandates a 40% capital subsidy for rooftop solar installation up to 3 kW capacity.",
                ai_summary="Subsidies for rooftop solar.",
                department="Ministry of New and Renewable Energy",
                jurisdiction="Union",
                canonical_url="https://mnre.gov.in/solar-2026",
                content_hash="hash12345"
            )
            db.session.add(policy)
            db.session.commit()

        # Query relevant to the policy
        res = PolicyRAGEngine.answer_question("solar rooftop capital subsidy financial assistance")
        self.assertTrue(res["verified"])
        self.assertGreater(res["confidence_score"], 0.5)
        self.assertGreater(len(res["sources"]), 0)
        self.assertGreater(len(res["citations"]), 0)
        # Check citations contain page or section reference
        top_citation = res["citations"][0]
        self.assertIn("page_reference", top_citation)
        self.assertIn("canonical_url", top_citation)

    def test_08_rag_system_missing_evidence_refusal(self):
        """Test RAG system explicitly refuses when evidence is absent, without hallucinating."""
        res = PolicyRAGEngine.answer_question("What is the extraterrestrial space alien quota for lunar farming?")
        self.assertFalse(res["verified"])
        self.assertEqual(res["confidence_score"], 0.0)
        self.assertEqual(len(res["sources"]), 0)
        self.assertEqual(len(res["citations"]), 0)
        self.assertIn("could not verify the answer", res["answer"].lower())

    def test_09_rag_system_multilingual_refusal(self):
        """Test missing evidence refusal in Hindi and Marathi."""
        res_hi = PolicyRAGEngine.answer_question("काल्पनिक अंतरिक्ष नीति क्या है?", language="hi")
        self.assertFalse(res_hi["verified"])
        self.assertIn("सत्यापित नहीं कर सकी", res_hi["answer"])

        res_mr = PolicyRAGEngine.answer_question("काल्पनिक परग्रह धोरण काय आहे?", language="mr")
        self.assertFalse(res_mr["verified"])
        self.assertIn("पडताळणी करू शकली नाही", res_mr["answer"])

    # ── MULTILINGUAL I18N VALIDATION ─────────────────────────────────────────────
    def test_10_i18n_translation_files(self):
        """Verify en.json, mr.json, and hi.json exist and contain required UI labels."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        i18n_dir = os.path.join(base_dir, "app", "i18n")

        for code in ["en", "mr", "hi"]:
            filepath = os.path.join(i18n_dir, f"{code}.json")
            self.assertTrue(os.path.exists(filepath), f"{code}.json must exist in app/i18n/")
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertIsInstance(data, dict)
                # Check essential nested keys
                self.assertIn("nav", data)
                self.assertIn("home", data["nav"])
                self.assertIn("policies", data["nav"])
                self.assertIn("ask_ai", data["nav"])
                self.assertIn("ask_ai", data)
                self.assertIn("policy_detail", data)

    # ── FLASK API INTEGRATION ────────────────────────────────────────────────────
    def test_11_api_ai_ask_endpoint(self):
        """Test POST /api/ai/ask endpoint."""
        # Valid query
        res = self.client.post("/api/ai/ask", json={"question": "What policies exist for farmers?", "language": "en"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertIn("question", data)
        self.assertIn("answer", data)
        self.assertIn("citations", data)

        # Empty query validation
        err_res = self.client.post("/api/ai/ask", json={"question": ""})
        self.assertEqual(err_res.status_code, 400)

    def test_12_api_ai_summarize_endpoint(self):
        """Test POST /api/ai/summarize endpoint."""
        policy = PolicyDocument.query.first()
        self.assertIsNotNone(policy, "Database should have at least one policy.")

        res = self.client.post("/api/ai/summarize", json={"policy_id": policy.id, "language": "hi"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["policy_id"], policy.id)
        self.assertIn("summary", data)
        self.assertIn("key_provisions", data)
        self.assertIn("important_dates", data)
        self.assertIn("affected_groups", data)
        self.assertEqual(data["language"], "hi")
        self.assertTrue(data["is_ai_translation"])


if __name__ == "__main__":
    unittest.main()
