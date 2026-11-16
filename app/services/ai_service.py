"""
PolicySetu — AIService
======================
Natural language processing, RAG answering grounded strictly in official documents,
multilingual policy summarization (English, Hindi, Marathi), structured intelligence
extraction, and version change explanations.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.models import PolicyDocument, PolicyAnalysis
from app.extensions import db
from app.ai.classifier import policy_classifier, CANONICAL_CATEGORIES
from app.ai.summarizer import policy_summarizer
from app.ai.extractor import PolicyExtractor, CANONICAL_STAKEHOLDERS
from app.ai.explainer import PolicyExplainer
from app.ai.rag_engine import PolicyRAGEngine

logger = logging.getLogger(__name__)

DISCLAIMERS = {
    "en": (
        "This is an AI-generated explanation based on official government documents. "
        "It is not legal advice. Always refer to the official source for authoritative information."
    ),
    "hi": (
        "यह आधिकारिक सरकारी दस्तावेजों पर आधारित AI-जनरेटेड स्पष्टीकरण है। "
        "यह कानूनी सलाह नहीं है। आधिकारिक जानकारी के लिए हमेशा सरकारी स्रोत देखें।"
    ),
    "mr": (
        "हे अधिकृत सरकारी दस्तऐवजांवर आधारित AI द्वारे तयार केलेले स्पष्टीकरण आहे. "
        "हा कायदेशीर सल्ला नाही. अधिकृत माहितीसाठी नेहमी मूळ सरकारी स्त्रोताचा संदर्भ घ्यावा."
    )
}


class AIService:
    """
    Unified AI service layer delegating to specialized engines:
    - RAG Question Answering (PolicyRAGEngine)
    - Multilingual Plain-Language Summarization (PolicySummarizer)
    - Policy Classification into 12 Categories (PolicyClassifier)
    - Intelligence Extraction (PolicyExtractor: provisions, dates, eligibility, stakeholders)
    - Version Change Explanation (PolicyExplainer)
    """

    @classmethod
    def ask(cls, question: str, language: str = "en", history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Retrieval-Augmented Generation (RAG) Q&A answering grounded strictly in official documents.
        Follows the 6-step RAG workflow:
        1. Retrieve relevant stored policy documents
        2. Find relevant passages with page/section references
        3. Pass retrieved evidence to LLM with prompt injection defense
        4. Generate a concise answer in requested language
        5. Return citations to the original document
        6. Include page or section references
        """
        return PolicyRAGEngine.answer_question(question=question, language=language, history=history)

    @classmethod
    def summarize(cls, policy_id: int, language: str = "en") -> Optional[Dict[str, Any]]:
        """
        Retrieve or compute a multilingual summary and structured intelligence for a policy.
        """
        doc = db.session.get(PolicyDocument, policy_id)
        if not doc:
            return None

        lang = language if language in ["en", "hi", "mr"] else "en"
        analysis = doc.analysis

        # If analysis does not exist or has missing summaries, generate them
        if not analysis or not analysis.summary_mr or not analysis.summary_hi:
            text_content = doc.content or doc.ai_summary or doc.title
            
            # Generate summaries in 3 languages
            summaries = policy_summarizer.summarize_multilingual(
                title=doc.title,
                text=text_content,
                department=doc.department or ""
            )

            # Extract structured intelligence
            extracted = PolicyExtractor.extract_all(
                title=doc.title,
                text=text_content,
                department=doc.department or ""
            )

            if not analysis:
                analysis = PolicyAnalysis(
                    document_id=doc.id,
                    summary_en=summaries.get("en", doc.ai_summary or doc.title),
                    summary_hi=summaries.get("hi", doc.ai_summary or doc.title),
                    summary_mr=summaries.get("mr", doc.ai_summary or doc.title),
                    key_provisions=json.dumps(extracted.get("key_provisions", []), ensure_ascii=False),
                    important_dates=json.dumps(extracted.get("important_dates", {}), ensure_ascii=False),
                    conditions=extracted.get("conditions", "Standard official scheme criteria apply."),
                    affected_groups=json.dumps(extracted.get("affected_groups", {}), ensure_ascii=False),
                    confidence_score=extracted.get("confidence_score", 0.92)
                )
                db.session.add(analysis)
            else:
                analysis.summary_en = summaries.get("en", analysis.summary_en)
                analysis.summary_hi = summaries.get("hi", analysis.summary_hi)
                analysis.summary_mr = summaries.get("mr", analysis.summary_mr)
                if not analysis.key_provisions or analysis.key_provisions == "[]":
                    analysis.key_provisions = json.dumps(extracted.get("key_provisions", []), ensure_ascii=False)
                if not analysis.important_dates or analysis.important_dates == "{}":
                    analysis.important_dates = json.dumps(extracted.get("important_dates", {}), ensure_ascii=False)
                if not analysis.conditions:
                    analysis.conditions = extracted.get("conditions", "")
                if not analysis.affected_groups or analysis.affected_groups == "{}":
                    analysis.affected_groups = json.dumps(extracted.get("affected_groups", {}), ensure_ascii=False)

            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error persisting policy analysis for document {doc.id}: {e}")

        # Select summary for requested language
        if lang == "hi":
            summary = analysis.summary_hi or doc.ai_summary
        elif lang == "mr":
            summary = analysis.summary_mr or doc.ai_summary
        else:
            summary = analysis.summary_en or doc.ai_summary

        return {
            "policy_id": doc.id,
            "title": doc.title,
            "language": lang,
            "summary": summary,
            "key_provisions": analysis.get_key_provisions_list(),
            "important_dates": analysis.get_important_dates_dict(),
            "affected_groups": analysis.get_affected_groups_dict(),
            "conditions": analysis.conditions,
            "confidence_score": analysis.confidence_score,
            "is_ai_translation": lang in ["hi", "mr"],
            "translation_notice": (
                "AI-generated translation of policy summary. The official source document remains in its published language."
                if lang in ["hi", "mr"] else ""
            ),
            "disclaimer": DISCLAIMERS.get(lang, DISCLAIMERS["en"]),
        }

    @classmethod
    def classify_policy(cls, title: str, text: str = "", department: str = "") -> Dict[str, Any]:
        """Classify policy into 12 canonical categories."""
        return policy_classifier.classify(title=title, text=text, department=department)

    @classmethod
    def extract_intelligence(cls, title: str, text: str, department: str = "") -> Dict[str, Any]:
        """Extract provisions, dates, eligibility conditions, and stakeholders."""
        return PolicyExtractor.extract_all(title=title, text=text, department=department)

    @classmethod
    def explain_changes(
        cls,
        title: str,
        old_text: str,
        new_text: str,
        diff_summary: Optional[Dict[str, Any]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Explain policy amendments between versions in simple language."""
        return PolicyExplainer.explain_changes(
            title=title,
            old_text=old_text,
            new_text=new_text,
            diff_summary=diff_summary,
            language=language
        )
