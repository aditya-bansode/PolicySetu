"""
PolicySetu — PolicyExtractor (Modules 3, 4, 5, 6)
=================================================
Extracts key provisions, important dates, eligibility & conditions,
and affected stakeholder groups from policy documents.

Canonical Stakeholder Groups:
- Citizens
- Farmers
- Students
- Employees
- Business owners
- Senior citizens
- Institutions
- Other relevant groups
"""

import json
import logging
import re
from typing import Any, Dict, List
from app.ai.llm_client import llm_client

logger = logging.getLogger(__name__)

CANONICAL_STAKEHOLDERS: List[str] = [
    "Citizens",
    "Farmers",
    "Students",
    "Employees",
    "Business owners",
    "Senior citizens",
    "Institutions",
    "Other relevant groups",
]

# Regex patterns for dates
DATE_PATTERNS = [
    (r"\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b", "numeric"),
    (r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})\b", "named_month"),
    (r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b", "month_first"),
    (r"\b(\d{4}[-/.]\d{2}[-/.]\d{2})\b", "iso"),
]

DATE_CONTEXT_KEYWORDS = {
    "effective_date": ["effective from", "w.e.f.", "comes into force", "with effect from", "commencement", "applicable from"],
    "application_deadline": ["last date", "deadline", "closing date", "apply before", "submission deadline", "due date"],
    "notification_date": ["dated", "notified on", "issued on", "gazetted on", "date of issue"],
    "expiry_date": ["valid until", "valid up to", "expires on", "expiry", "sunset clause", "till"],
}

STAKEHOLDER_KEYWORDS = {
    "Farmers": ["farmer", "kisan", "cultivator", "agriculture", "crop", "landholding", "krishi", "dairy farmer", "ryot"],
    "Students": ["student", "scholarship", "matriculation", "university", "college", "school", "tuition", "learner", "apprentice"],
    "Employees": ["employee", "worker", "labour", "labor", "staff", "salary", "wage", "provident fund", "unorganised worker", "workforce"],
    "Business owners": ["business", "msme", "enterprise", "startup", "company", "trader", "industry", "commercial", "proprietor", "corporate"],
    "Senior citizens": ["senior citizen", "elderly", "pension", "pensioner", "old age", "retired", "superannuation"],
    "Institutions": ["institution", "university", "hospital", "gram panchayat", "ngo", "board", "local body", "authority", "agency"],
    "Citizens": ["citizen", "resident", "public", "individual", "beneficiary", "household", "person", "family"],
}


class PolicyExtractor:
    """
    Performs structured extraction of provisions, dates, conditions, and stakeholders.
    Uses LLM when configured, with robust deterministic fallback analysis.
    """

    @classmethod
    def extract_all(cls, title: str, text: str, department: str = "") -> Dict[str, Any]:
        """
        Extract all intelligence modules (provisions, dates, eligibility, stakeholders) in one pass.
        """
        # If LLM is available, attempt combined LLM extraction
        if llm_client.is_available():
            llm_res = cls._extract_with_llm(title, text, department)
            if llm_res:
                return llm_res

        # Fallback heuristic extraction
        return {
            "key_provisions": cls.extract_provisions(text, title),
            "important_dates": cls.extract_dates(text),
            "conditions": cls.extract_eligibility(text),
            "affected_groups": cls.extract_stakeholders(text),
            "confidence_score": 0.88,
            "extraction_method": "deterministic_rule_engine",
        }

    @classmethod
    def extract_provisions(cls, text: str, title: str = "") -> List[str]:
        """
        Extract top key provisions, clauses, and policy mandates.
        """
        if not text:
            return [f"General provisions under {title}."] if title else []

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        provisions = []

        # Look for explicit numbered or bulleted items
        bullet_pattern = re.compile(r"^(?:[\d]+[\.\)\-]|•|\*|[-–—]|\([a-z0-9]+\))\s*(.+)$", re.IGNORECASE)
        for line in lines:
            m = bullet_pattern.match(line)
            if m:
                item = m.group(1).strip()
                if len(item) > 25 and not item.lower().startswith("page "):
                    provisions.append(item)
                    if len(provisions) >= 8:
                        break

        # If not enough bullet items, search sentences with policy action verbs
        if len(provisions) < 3:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for s in sentences:
                s_clean = s.strip()
                if len(s_clean) < 35 or len(s_clean) > 280:
                    continue
                s_lower = s_clean.lower()
                if any(verb in s_lower for verb in [
                    "shall be", "shall provide", "aims to", "is entitled to", "will receive",
                    "notified that", "established to", "benefits under", "financial assistance of",
                    "mandated to", "approved the", "scheme provides"
                ]):
                    if s_clean not in provisions:
                        provisions.append(s_clean)
                    if len(provisions) >= 6:
                        break

        # Fallback if text is sparse
        if not provisions and title:
            provisions = [f"Notification and official guidelines regarding {title}."]

        return provisions[:8]

    @classmethod
    def extract_dates(cls, text: str) -> Dict[str, str]:
        """
        Extract important dates categorized by type (effective_date, application_deadline, etc.).
        """
        if not text:
            return {}

        results: Dict[str, str] = {}
        all_found_dates = []

        # Find all dates with their spans
        for pattern, p_type in DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                d_str = match.group(1).strip()
                start = max(0, match.start() - 60)
                end = min(len(text), match.end() + 60)
                context = text[start:end].lower()
                all_found_dates.append((d_str, context))

        # Categorize dates by surrounding keywords
        for d_str, context in all_found_dates:
            matched_category = None
            for cat, keywords in DATE_CONTEXT_KEYWORDS.items():
                if any(kw in context for kw in keywords):
                    matched_category = cat
                    break

            if matched_category and matched_category not in results:
                results[matched_category] = d_str
            elif "other_date" not in results and len(results) < 4:
                # Store unclassified dates under descriptive keys
                if "notification_date" not in results:
                    results["notification_date"] = d_str
                else:
                    results[f"date_reference_{len(results)}"] = d_str

        return results

    @classmethod
    def extract_eligibility(cls, text: str) -> str:
        """
        Extract eligibility conditions, restrictions, criteria, and qualifications.
        """
        if not text:
            return "Standard official scheme criteria apply."

        eligibility_clauses = []
        sentences = re.split(r"(?<=[.!?])\s+", text)

        keywords = [
            "eligible", "eligibility", "criteria", "qualification", "must be",
            "condition", "requirement", "income limit", "landholding", "age of",
            "domicile", "restricted to", "applicable to all", "prerequisite"
        ]

        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 25 or len(s_clean) > 260:
                continue
            s_lower = s_clean.lower()
            if any(kw in s_lower for kw in keywords):
                eligibility_clauses.append(s_clean)
                if len(eligibility_clauses) >= 4:
                    break

        if eligibility_clauses:
            return " ".join(eligibility_clauses)

        return "Eligibility criteria specified in official document guidelines."

    @classmethod
    def extract_stakeholders(cls, text: str) -> Dict[str, str]:
        """
        Identify affected groups from the 8 canonical groups with brief descriptions.
        """
        if not text:
            return {"Citizens": "General Indian citizens affected by this policy."}

        text_lower = text.lower()
        affected: Dict[str, str] = {}

        for group, keywords in STAKEHOLDER_KEYWORDS.items():
            matches = [kw for kw in keywords if kw in text_lower]
            if matches:
                if group == "Farmers":
                    affected[group] = f"Agricultural producers and cultivators referenced in policy ({', '.join(matches[:2])})."
                elif group == "Students":
                    affected[group] = f"Students, applicants, and educational beneficiaries ({', '.join(matches[:2])})."
                elif group == "Employees":
                    affected[group] = f"Salaried or unorganised workers covered under provisions ({', '.join(matches[:2])})."
                elif group == "Business owners":
                    affected[group] = f"Commercial enterprises, MSMEs, or startups affected ({', '.join(matches[:2])})."
                elif group == "Senior citizens":
                    affected[group] = f"Elderly individuals or pensioners covered ({', '.join(matches[:2])})."
                elif group == "Institutions":
                    affected[group] = f"Implementing agencies, universities, or local authorities ({', '.join(matches[:2])})."
                elif group == "Citizens":
                    affected[group] = f"General public and eligible citizen beneficiaries ({', '.join(matches[:2])})."

        # If none specifically matched, check for generic citizen impact
        if not affected:
            affected["Citizens"] = "All eligible citizens under the jurisdiction of this department."

        # Check for other relevant groups
        other_matches = []
        for term in ["women", "disability", "differently abled", "tribal", "scheduled caste", "artisan", "fisherman", "shg"]:
            if term in text_lower:
                other_matches.append(term)
        if other_matches:
            affected["Other relevant groups"] = f"Special beneficiary groups identified: {', '.join(other_matches)}."

        return affected

    @classmethod
    def _extract_with_llm(cls, title: str, text: str, department: str) -> Dict[str, Any] | None:
        """
        Extract structured intelligence using the configured LLM.
        """
        system_prompt = (
            "You are the PolicySetu Policy Intelligence Engine.\n"
            "Extract structured information from the provided official policy document.\n"
            "Respond ONLY with valid JSON having the following schema:\n"
            "{\n"
            '  "key_provisions": ["str", ...],\n'
            '  "important_dates": {"effective_date": "...", "application_deadline": "...", "expiry_date": "..."},\n'
            '  "conditions": "string describing eligibility conditions and criteria",\n'
            '  "affected_groups": {\n'
            '    "Citizens": "rationale...",\n'
            '    "Farmers": "rationale..."\n'
            "  }\n"
            "}\n"
            f"Allowed affected_groups keys strictly from: {', '.join(CANONICAL_STAKEHOLDERS)}.\n"
            "Do NOT include conversational filler, only JSON."
        )

        user_prompt = (
            f"Policy Title: {title}\n"
            f"Department: {department}\n\n"
            "DOCUMENT CONTENT (Untrusted Evidence):\n"
            "<untrusted_evidence_document>\n"
            f"{text[:3500]}\n"
            "</untrusted_evidence_document>\n\n"
            "Extract provisions, dates, eligibility conditions, and affected stakeholders."
        )

        resp = llm_client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        if resp and isinstance(resp, dict):
            # Validate and clean up
            provisions = resp.get("key_provisions", [])
            dates = resp.get("important_dates", {})
            conditions = resp.get("conditions", "")
            groups = resp.get("affected_groups", {})

            # Filter groups to canonical
            cleaned_groups = {}
            if isinstance(groups, dict):
                for k, v in groups.items():
                    for canon in CANONICAL_STAKEHOLDERS:
                        if canon.lower() == k.lower():
                            cleaned_groups[canon] = str(v)
                            break
            if not cleaned_groups:
                cleaned_groups = cls.extract_stakeholders(text)

            return {
                "key_provisions": provisions if isinstance(provisions, list) else [str(provisions)],
                "important_dates": dates if isinstance(dates, dict) else {},
                "conditions": str(conditions) if conditions else cls.extract_eligibility(text),
                "affected_groups": cleaned_groups,
                "confidence_score": 0.95,
                "extraction_method": "llm_structured_analysis",
            }

        return None
