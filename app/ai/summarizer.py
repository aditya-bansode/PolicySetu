"""
PolicySetu — Simple-Language Multilingual Summarizer (Module 2)
==============================================================
Transforms bureaucratic government notifications and gazettes into clear,
plain-language explanations in English, Marathi, and Hindi.

Preserves strictly:
- Government department names
- Legal terminology
- Monetary values (₹, INR, Crore, Lakh)
- Dates and deadlines
- Eligibility conditions
- Official document references (PRID, GR code)

Clearly indicates that summaries are AI-generated; never claims official documents
themselves are officially translated.
"""

import re
import json
import logging
from typing import Dict, Any, Optional
from app.ai.llm_client import LLMClient, llm_client

logger = logging.getLogger("policysetu.ai.summarizer")

AI_TRANSLATION_NOTICES = {
    "en": "Note: This is an AI-generated summary and interpretation of the official document. The official government publication remains authoritative.",
    "hi": "सूचना: यह आधिकारिक दस्तावेज का AI-जनरेटेड सारांश और अनुवाद है। मूल आधिकारिक सरकारी राजपत्र ही प्रामाणिक माना जाएगा।",
    "mr": "सूचना: हा अधिकृत दस्तऐवजाचा AI-निर्मित सारांश व अनुवाद आहे. मूळ अधिकृत सरकारी शासन निर्णयच अंतिम व प्रामाणिक मानला जाईल.",
}


class PolicySummarizer:
    """
    Multilingual summarization engine for English, Marathi, and Hindi.
    """

    def __init__(self, client: Optional[LLMClient] = None):
        self.llm = client or llm_client

    @staticmethod
    def extract_critical_entities(text: str) -> Dict[str, list]:
        """
        Extract monetary figures, dates, and official references that MUST be preserved.
        """
        # Currency / amounts
        money_matches = re.findall(
            r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?(?:\s*(?:crore|lakh|thousand|cr|k))?",
            text,
            flags=re.IGNORECASE,
        )

        # Dates
        date_matches = re.findall(
            r"\b(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",
            text,
            flags=re.IGNORECASE,
        )

        # Reference numbers / GR numbers / PRIDs
        ref_matches = re.findall(
            r"\b(?:PRID\s*[:\-]?\s*\d+|GR\s*No\.?\s*[:\-]?\s*[\w\d\-_/]+|Notification\s*No\.?\s*[:\-]?\s*[\w\d\-_/]+)\b",
            text,
            flags=re.IGNORECASE,
        )

        return {
            "monetary_values": list(set(money_matches[:5])),
            "dates": list(set(date_matches[:5])),
            "references": list(set(ref_matches[:5])),
        }

    def summarize(
        self,
        title: str,
        text: str,
        department: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Generate a plain-language summary in target language (en, hi, mr).
        """
        lang = language if language in ("en", "hi", "mr") else "en"
        entities = self.extract_critical_entities(f"{title} {text}")

        # 1. Attempt LLM generation if configured
        if self.llm.is_configured():
            lang_names = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
            target_lang = lang_names.get(lang, "English")

            prompt = (
                f"Summarize the following Indian government policy document in plain, accessible {target_lang}.\n"
                f"CRITICAL REQUIREMENTS:\n"
                f"- Write in simple language avoiding unnecessary bureaucratic jargon.\n"
                f"- Preserve exact department name: '{department or 'Government of India'}'\n"
                f"- Preserve all monetary amounts, numerical quotas, dates, and official reference codes.\n"
                f"- State clearly what the policy provides and who benefits.\n\n"
                f"Document Title: {title}\n"
                f"Department: {department or 'N/A'}\n"
                f"Text Excerpt: {text[:2500]}\n\n"
                f"Summary in {target_lang}:"
            )
            llm_summary = self.llm.generate(prompt)
            if llm_summary and len(llm_summary.strip()) > 40:
                return {
                    "language": lang,
                    "summary": llm_summary.strip(),
                    "is_ai_generated": True,
                    "disclaimer": AI_TRANSLATION_NOTICES[lang],
                    "preserved_entities": entities,
                    "method": "llm",
                }

        # 2. Resilient Deterministic Civic-Tech Summarizer
        clean_first_para = text.strip().split("\n\n")[0] if text else title
        clean_first_para = re.sub(r"\s+", " ", clean_first_para)[:350].strip()

        if lang == "hi":
            summary = (
                f"यह नीति '{department or 'भारत सरकार'}' द्वारा जारी की गई है: {title}। "
                f"इसका मुख्य उद्देश्य नागरिकों और संबंधित हितधारकों को नीतिगत लाभ और दिशा-निर्देश प्रदान करना है। "
                f"महत्वपूर्ण विवरण: {clean_first_para}."
            )
        elif lang == "mr":
            summary = (
                f"हे अधिकृत धोरण '{department or 'महाराष्ट्र शासन'}' द्वारे निर्गमित करण्यात आले आहे: {title}. "
                f"या निर्णयान्वये संबंधित नागरिक व घटकांना विहित तरतुदी व प्रशासकीय मार्गदर्शक तत्त्वे लागू करण्यात आली आहेत. "
                f"प्रमुख तपशील: {clean_first_para}."
            )
        else:
            summary = (
                f"Issued by {department or 'the Government'}: '{title}'. "
                f"This policy sets forth official guidelines and public entitlements for eligible stakeholders. "
                f"Overview: {clean_first_para}."
            )

        return {
            "language": lang,
            "summary": summary,
            "is_ai_generated": True,
            "disclaimer": AI_TRANSLATION_NOTICES[lang],
            "preserved_entities": entities,
            "method": "deterministic",
        }

    def summarize_multilingual(
        self,
        title: str,
        text: str,
        department: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate summaries in all 3 supported languages: EN, HI, MR.
        """
        return {
            "en": self.summarize(title, text, department, language="en")["summary"],
            "hi": self.summarize(title, text, department, language="hi")["summary"],
            "mr": self.summarize(title, text, department, language="mr")["summary"],
        }


# Module singleton
policy_summarizer = PolicySummarizer()
