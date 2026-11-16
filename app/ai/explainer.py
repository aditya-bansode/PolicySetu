"""
PolicySetu — PolicyExplainer (Module 7)
=======================================
Generates plain-language explanations of policy amendments, version changes,
and clause updates in English, Hindi, and Marathi.
"""

import difflib
import logging
from typing import Any, Dict, List, Optional
from app.ai.llm_client import llm_client

logger = logging.getLogger(__name__)

DISCLAIMERS = {
    "en": "AI-generated explanation of policy changes. Not legal advice. Consult official gazette/notifications for authoritative text.",
    "hi": "नीतिगत परिवर्तनों का AI-जनरेटेड स्पष्टीकरण। यह कानूनी सलाह नहीं है। प्राधिकृत पाठ के लिए आधिकारिक राजपत्र/अधिसूचना देखें।",
    "mr": "धोरणातील बदलांचे AI द्वारे तयार केलेले स्पष्टीकरण. हा कायदेशीर सल्ला नाही. अधिकृत मजकुरासाठी कृपया अधिकृत राजपत्र किंवा शासन निर्णय पहावा."
}


class PolicyExplainer:
    """
    Explains differences between policy document versions in simple language.
    """

    @classmethod
    def explain_changes(
        cls,
        title: str,
        old_text: str,
        new_text: str,
        diff_summary: Optional[Dict[str, Any]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Explain the differences between old and new version of a document.
        """
        lang = language if language in ["en", "hi", "mr"] else "en"

        # Compute diff blocks if not provided or if diff_summary is not a dict
        if not diff_summary or not isinstance(diff_summary, dict):
            diff_summary = cls._compute_diff_summary(old_text, new_text)

        # Try LLM explanation if configured
        if llm_client.is_available():
            llm_result = cls._explain_with_llm(title, diff_summary, lang)
            if llm_result:
                return llm_result

        # Heuristic explanation
        return cls._generate_heuristic_explanation(title, diff_summary, lang)

    @classmethod
    def _compute_diff_summary(cls, old_text: str, new_text: str) -> Dict[str, Any]:
        """
        Extract added, removed, and modified clauses.
        """
        old_lines = [l.strip() for l in old_text.splitlines() if l.strip()]
        new_lines = [l.strip() for l in new_text.splitlines() if l.strip()]

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        added: List[str] = []
        removed: List[str] = []
        modified: List[Dict[str, str]] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "insert":
                for line in new_lines[j1:j2]:
                    if len(line) > 15:
                        added.append(line)
            elif tag == "delete":
                for line in old_lines[i1:i2]:
                    if len(line) > 15:
                        removed.append(line)
            elif tag == "replace":
                old_chunk = " ".join(old_lines[i1:i2])
                new_chunk = " ".join(new_lines[j1:j2])
                if len(old_chunk) > 15 or len(new_chunk) > 15:
                    modified.append({"from": old_chunk[:250], "to": new_chunk[:250]})

        return {
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "added_samples": added[:5],
            "removed_samples": removed[:5],
            "modified_samples": modified[:5],
        }

    @classmethod
    def _generate_heuristic_explanation(
        cls,
        title: str,
        diff_summary: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """
        Rule-based plain-language explanation of version differences.
        """
        added_cnt = diff_summary.get("added_count", 0)
        removed_cnt = diff_summary.get("removed_count", 0)
        modified_cnt = diff_summary.get("modified_count", 0)

        # Detect specific themes in added/modified clauses
        all_new_text = " ".join(diff_summary.get("added_samples", []) + [m.get("to", "") for m in diff_summary.get("modified_samples", [])]).lower()

        impact_points = []
        if any(w in all_new_text for w in ["deadline", "extended", "last date", "till"]):
            impact_points.append("Application deadlines or timeline schedules appear to have been revised or extended.")
        if any(w in all_new_text for w in ["rs.", "inr", "crore", "lakh", "subsidy", "amount", "financial"]):
            impact_points.append("Financial allocations, subsidies, or monetary criteria have been updated.")
        if any(w in all_new_text for w in ["eligibility", "criteria", "relaxed", "condition"]):
            impact_points.append("Beneficiary eligibility guidelines or application requirements have been modified.")
        if any(w in all_new_text for w in ["portal", "online", "application", "form", "aadhaar"]):
            impact_points.append("Administrative submission procedures or verification requirements have been adjusted.")

        if not impact_points:
            impact_points.append("Routine editorial updates, terminology clarifications, or clause renumbering.")

        # Multilingual explanations
        if language == "hi":
            summary = (
                f"{title} के नवीनतम संस्करण में {added_cnt} नए खंड जोड़े गए हैं, "
                f"{removed_cnt} पुराने खंड हटाए गए हैं, तथा {modified_cnt} खंडों में संशोधन किया गया है।"
            )
            impact_hi = [
                "समय-सीमा या आवेदन की तिथियों में संशोधन किया गया है।" if "deadline" in ip else
                "वित्तीय सहायता या पात्रता मानदंडों में बदलाव किया गया है।" if "financial" in ip or "eligibility" in ip else
                "प्रशासनिक प्रक्रिया को अद्यतन किया गया है।"
                for ip in impact_points
            ]
            key_takeaway = "नागरिकों को सलाह दी जाती है कि वे अपने लाभ या समय-सीमा से जुड़े अद्यतन नियमों का अवलोकन करें।"
            points = impact_hi
        elif language == "mr":
            summary = (
                f"{title} च्या नवीन आवृत्तीमध्ये {added_cnt} नवीन कलमे समाविष्ट करण्यात आली आहेत, "
                f"{removed_cnt} कलमे वगळण्यात आली आहेत, आणि {modified_cnt} कलमांमध्ये दुरुस्ती करण्यात आली आहे."
            )
            impact_mr = [
                "मुदतवाढ किंवा वेळापत्रकात सुधारणा करण्यात आली आहे." if "deadline" in ip else
                "आर्थिक सहाय्य किंवा पात्रता निकषांमध्ये बदल करण्यात आला आहे." if "financial" in ip or "eligibility" in ip else
                "प्रशासकीय प्रक्रियेमध्ये सुधारणा करण्यात आली आहे."
                for ip in impact_points
            ]
            key_takeaway = "लाभार्थ्यांनी सुधारित नियम व अंतिम मुदतीची नोंद घ्यावी."
            points = impact_mr
        else:
            summary = (
                f"The updated version of {title} includes {added_cnt} added clauses, "
                f"{removed_cnt} removed clauses, and {modified_cnt} modified provisions."
            )
            key_takeaway = "Stakeholders should review revised clauses for updated operational terms or deadlines."
            points = impact_points

        return {
            "title": title,
            "language": language,
            "summary_explanation": summary,
            "key_impact_points": points,
            "key_takeaway": key_takeaway,
            "added_count": added_cnt,
            "removed_count": removed_cnt,
            "modified_count": modified_cnt,
            "is_ai_interpretation": True,
            "disclaimer": DISCLAIMERS.get(language, DISCLAIMERS["en"]),
        }

    @classmethod
    def _explain_with_llm(
        cls,
        title: str,
        diff_summary: Dict[str, Any],
        language: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate explanation using LLM.
        """
        system_prompt = (
            "You are the PolicySetu Policy Amendment Explainer.\n"
            "Compare the two versions of the government policy and explain the changes in simple plain language.\n"
            f"Generate output in language: '{language}' (en=English, hi=Hindi, mr=Marathi).\n"
            "Respond ONLY with valid JSON having this schema:\n"
            "{\n"
            '  "summary_explanation": "Simple plain-language summary of what changed",\n'
            '  "key_impact_points": ["Point 1", "Point 2", ...],\n'
            '  "key_takeaway": "Actionable takeaway for beneficiaries"\n'
            "}\n"
            "Preserve all monetary figures, dates, and official reference numbers verbatim. Do not give legal advice."
        )

        user_prompt = (
            f"Policy: {title}\n\n"
            "DIFFERENCE SUMMARY (Untrusted Content):\n"
            "<untrusted_evidence_document>\n"
            f"Added clauses ({diff_summary.get('added_count', 0)}):\n" + "\n".join(diff_summary.get("added_samples", [])[:3]) + "\n\n"
            f"Removed clauses ({diff_summary.get('removed_count', 0)}):\n" + "\n".join(diff_summary.get("removed_samples", [])[:3]) + "\n\n"
            f"Modified clauses ({diff_summary.get('modified_count', 0)}):\n" + "\n".join([f"Old: {m.get('from')}\nNew: {m.get('to')}" for m in diff_summary.get("modified_samples", [])[:3]]) + "\n"
            "</untrusted_evidence_document>\n"
        )

        resp = llm_client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        if resp and isinstance(resp, dict):
            return {
                "title": title,
                "language": language,
                "summary_explanation": resp.get("summary_explanation", ""),
                "key_impact_points": resp.get("key_impact_points", []),
                "key_takeaway": resp.get("key_takeaway", ""),
                "added_count": diff_summary.get("added_count", 0),
                "removed_count": diff_summary.get("removed_count", 0),
                "modified_count": diff_summary.get("modified_count", 0),
                "is_ai_interpretation": True,
                "disclaimer": DISCLAIMERS.get(language, DISCLAIMERS["en"]),
            }

        return None
