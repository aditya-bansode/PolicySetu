"""
PolicySetu — Policy Classifier
==============================
Classifies policy documents into the 12 canonical PolicySetu categories:
1. Agriculture
2. Education
3. Healthcare
4. Employment and Labour
5. Business and Finance
6. Housing
7. Social Welfare
8. Transport
9. Environment
10. Law and Justice
11. Public Administration
12. General
"""

import re
import json
import logging
from typing import Dict, Any, Optional
from app.ai.llm_client import LLMClient

logger = logging.getLogger("policysetu.ai.classifier")

CANONICAL_CATEGORIES = [
    "Agriculture",
    "Education",
    "Healthcare",
    "Employment and Labour",
    "Business and Finance",
    "Housing",
    "Social Welfare",
    "Transport",
    "Environment",
    "Law and Justice",
    "Public Administration",
    "General",
]

TAXONOMY_KEYWORDS = {
    "Agriculture": [
        "agriculture", "farmer", "kisan", "crop", "mandi", "irrigation", "fertilizer",
        "krishi", "harvest", "dairy", "poultry", "horticulture", "pm-kisan",
        "कृषी", "शेतकरी", "पिक", "बियाणे", "शेती", "पशुसंवर्धन", "सिंचन",
        "कृषि", "किसान", "फसल", "उर्वरक", "मंडी"
    ],
    "Education": [
        "education", "school", "college", "university", "student", "scholarship",
        "curriculum", "cbse", "ugc", "teacher", "literacy", "exam", "higher education",
        "शिक्षण", "शाळा", "महाविद्यालय", "विद्यार्थी", "शिष्यवृत्ती", "अभ्यासक्रम",
        "विद्यालय", "छात्र", "शिक्षा", "अध्यापक"
    ],
    "Healthcare": [
        "health", "hospital", "ayushman", "medical", "medicine", "doctor",
        "disease", "vaccine", "clinical", "pharma", "wellness", "nurse",
        "आरोग्य", "रुग्णालय", "वैद्यकीय", "औषध", "लस", "आयुष्मान",
        "स्वास्थ्य", "चिकित्सा", "अस्पताल", "दवा", "रोग"
    ],
    "Employment and Labour": [
        "employment", "labour", "worker", "job", "wage", "provident fund",
        "epfo", "esic", "unemployment", "apprentice", "gig worker", "salary",
        "रोजगार", "कामगार", "वेतन", "कर्मचारी", "भविष्य निर्वाह",
        "श्रम", "मजदूर", "नौकरी", "भत्ता"
    ],
    "Business and Finance": [
        "tax", "gst", "msme", "finance", "banking", "subsidy", "credit", "loan",
        "commerce", "industry", "investment", "fdi", "tariff", "sebi", "rbi",
        "उद्योग", "वित्त", "बँक", "कर्ज", "कर", "व्यापार", "गुंतवणूक",
        "व्यापार", "ऋण", "वित्तीय", "ब्याज", "निगम"
    ],
    "Housing": [
        "housing", "pmay", "awas", "slum", "residential", "flat", "tenement",
        "urban development", "real estate", "rera",
        "घरकुल", "गृहनिर्माण", "झोपडपट्टी", "रहिवासी",
        "आवास", "मकान", "बस्ती", "भूखंड"
    ],
    "Social Welfare": [
        "welfare", "pension", "divyang", "disability", "tribal", "sc/st",
        "minority", "women", "child", "senior citizen", "destitute", "widow",
        "कल्याण", "पेन्शन", "दिव्यांग", "महिला व बाल", "सामाजिक न्याय", "ज्येष्ठ नागरिक",
        "पेंशन", "कल्याणकारी", "निःशक्त", "महिला एवं बाल"
    ],
    "Transport": [
        "transport", "railway", "highway", "metro", "bus", "road", "traffic",
        "aviation", "port", "shipping", "motor vehicle", "nhai",
        "वाहतूक", "रेल्वे", "महामार्ग", "रस्ता", "विमानतळ",
        "परिवहन", "सड़क", "रेलवे", "यातायात", "पोत"
    ],
    "Environment": [
        "environment", "pollution", "forest", "wildlife", "solar", "green",
        "renewable", "climate", "carbon", "water conservation", "emission",
        "पर्यावरण", "प्रदूषण", "वन", "सौर", "हरित", "हवामान",
        "जलवायु", "जंगल", "नवीकरणीय", "प्रदूषण नियंत्रण"
    ],
    "Law and Justice": [
        "law", "justice", "court", "act", "ordinance", "judiciary", "legal",
        "penal", "tribunal", "advocate", "bar council", "constitution",
        "कायदा", "न्याय", "न्यायालय", "अधिनियम", "कायदेशीर",
        "विधि", "कानून", "अदालत", "न्यायिक"
    ],
    "Public Administration": [
        "administration", "gazette", "governance", "civil service", "cadre",
        "transfer", "recruitment", "official notification", "departmental", "ias",
        "प्रशासन", "सेवा", "संवर्ग", "कार्यालय", "अधिकारी", "बदली", "शासन निर्णय",
        "प्रशासनिक", "संवर्ग", "राजपत्र", "कार्मिक"
    ],
}


class PolicyClassifier:
    """
    Classifies a policy document into one of the 12 canonical categories.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def classify(self, title: str, text: str = "", department: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify document title, text excerpt, and department into a canonical category.
        """
        combined_text = f"{title}\n{department or ''}\n{text[:1000]}".strip()

        # 1. Attempt classification with LLM if configured
        if self.llm.is_configured():
            prompt = (
                f"Classify the following government policy into EXACTLY ONE of these categories:\n"
                f"{', '.join(CANONICAL_CATEGORIES)}\n\n"
                f"Document Details:\n"
                f"Title: {title}\n"
                f"Department: {department or 'N/A'}\n"
                f"Content Excerpt: {text[:400]}\n\n"
                f"Return JSON strictly formatted as: {{\"category\": \"CategoryName\", \"confidence\": 0.95}}"
            )
            raw = self.llm.generate(prompt)
            if raw:
                try:
                    match = re.search(r"\{.*?\}", raw, re.DOTALL)
                    if match:
                        data = json.loads(match.group(0))
                        cat = data.get("category")
                        if cat in CANONICAL_CATEGORIES:
                            return {
                                "category": cat,
                                "confidence": float(data.get("confidence", 0.95)),
                                "method": "llm",
                            }
                except Exception:
                    pass

        # 2. Resilient Taxonomy Heuristics Fallback (Supports EN, HI, MR)
        clean_lower = combined_text.lower()
        scores: Dict[str, int] = {cat: 0 for cat in CANONICAL_CATEGORIES}

        # Department weight is prioritized
        dept_lower = (department or "").lower()
        for cat, keywords in TAXONOMY_KEYWORDS.items():
            for kw in keywords:
                if kw in dept_lower:
                    scores[cat] += 4
                if kw in clean_lower:
                    scores[cat] += 1

        best_cat = "General"
        max_score = 0
        for cat, sc in scores.items():
            if sc > max_score:
                max_score = sc
                best_cat = cat

        confidence = min(0.95, 0.50 + (max_score * 0.08)) if max_score > 0 else 0.50

        return {
            "category": best_cat,
            "confidence": round(confidence, 2),
            "method": "taxonomy",
        }


# Module singleton
policy_classifier = PolicyClassifier()
