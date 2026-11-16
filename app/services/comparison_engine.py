"""
PolicySetu — Policy Version Comparison Engine
=============================================
Performs semantic, clause-by-clause diffing between document versions.
Detects added, removed, and modified clauses with page references.
Prevents false-positive updates caused solely by transient website timestamp changes.
"""

import re
import difflib
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("policysetu.comparison_engine")


class PolicyComparisonEngine:
    """
    Clause-level comparison engine for legal and policy documents.
    """

    # Patterns indicating transient web timestamps that should be ignored for content hash diffing
    TIMESTAMP_PATTERNS = [
        re.compile(r"(?:last\s*updated|modified|generated|printed|accessed|retrieved|current\s*as\s*of)\s*:\s*[^\n\r]+", re.IGNORECASE),
        re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b"),
        re.compile(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s+\d{1,2}:\d{2}(?:\s*(?:AM|PM))?\b", re.IGNORECASE),
        re.compile(r"Page\s+\d+\s+of\s+\d+", re.IGNORECASE),
    ]

    SECTION_HEADING_PATTERNS = [
        re.compile(r"^(?:Section|Article|Clause|Rule|Chapter|Part|Schedule|Annexure|Appendix)\s+[\dA-Za-z\.\-]+.*", re.IGNORECASE),
        re.compile(r"^(?:शासन\s*निर्णय|प्रस्तावना|परिशिष्ट|महत्वाचे\s*मुद्दे).*", re.UNICODE),
        re.compile(r"^\d+[\.\)]\s+[A-Za-z\u0900-\u097F].*"),
    ]

    @classmethod
    def normalize_for_comparison(cls, text: str) -> str:
        """
        Normalize text for meaningful difference check by stripping volatile
        timestamps, footers, and redundant line breaks.
        """
        if not text:
            return ""
        clean = text
        for p in cls.TIMESTAMP_PATTERNS:
            clean = p.sub("", clean)

        # Normalize line endings and multiple spaces
        lines = [re.sub(r"[ \t]+", " ", l).strip() for l in clean.splitlines()]
        # Remove empty lines
        non_empty = [l for l in lines if l]
        return "\n".join(non_empty)

    @classmethod
    def has_meaningful_difference(cls, old_text: str, new_text: str) -> bool:
        """
        Determine if there is a substantive content difference between two text versions,
        ignoring cosmetic timestamp or footer alterations.
        """
        norm_old = cls.normalize_for_comparison(old_text)
        norm_new = cls.normalize_for_comparison(new_text)

        if norm_old == norm_new:
            return False

        # Calculate character-level or token-level similarity
        matcher = difflib.SequenceMatcher(None, norm_old, norm_new)
        similarity = matcher.ratio()

        # If similarity is 1.0 (identical normalized content), no meaningful difference
        return similarity < 0.9999

    @classmethod
    def segment_into_clauses(cls, text: str) -> List[Dict[str, Any]]:
        """
        Segment a policy document into structured clauses, paragraphs, and sections
        with detectable headings and page references.
        """
        if not text:
            return []

        clauses: List[Dict[str, Any]] = []
        lines = text.splitlines()

        current_heading = "General Provisions"
        current_lines: List[str] = []
        current_page = 1
        clause_index = 1

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            # Check for embedded page marker (e.g. "[Page 2]" or "--- Page 2 ---")
            page_match = re.search(r"\[Page\s+(\d+)\]|---\s*Page\s+(\d+)\s*---", trimmed, re.IGNORECASE)
            if page_match:
                current_page = int(page_match.group(1) or page_match.group(2))
                continue

            # Check if this line is a section heading
            is_heading = False
            for p in cls.SECTION_HEADING_PATTERNS:
                if p.match(trimmed) and len(trimmed) < 120:
                    is_heading = True
                    break

            if is_heading:
                # Flush existing clause
                if current_lines:
                    clause_text = " ".join(current_lines).strip()
                    if len(clause_text) > 15:
                        clauses.append({
                            "index": clause_index,
                            "section": current_heading,
                            "text": clause_text,
                            "page": current_page,
                        })
                        clause_index += 1
                    current_lines = []
                current_heading = trimmed
            else:
                current_lines.append(trimmed)

        # Flush trailing clause
        if current_lines:
            clause_text = " ".join(current_lines).strip()
            if len(clause_text) > 15:
                clauses.append({
                    "index": clause_index,
                    "section": current_heading,
                    "text": clause_text,
                    "page": current_page,
                })

        # If document had no structured headings, split into paragraphs
        if len(clauses) <= 1 and "\n\n" in text:
            clauses = []
            paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 15]
            for idx, p in enumerate(paragraphs):
                clauses.append({
                    "index": idx + 1,
                    "section": f"Clause {idx + 1}",
                    "text": p,
                    "page": 1,
                })

        return clauses

    @classmethod
    def compare(
        cls,
        old_text: str,
        new_text: str,
        v1_num: int = 1,
        v2_num: int = 2
    ) -> Dict[str, Any]:
        """
        Compare two versions of a policy document:
        Detects added clauses, removed clauses, and modified clauses with page numbers.
        """
        old_clauses = cls.segment_into_clauses(old_text)
        new_clauses = cls.segment_into_clauses(new_text)

        meaningful_change = cls.has_meaningful_difference(old_text, new_text)

        if not meaningful_change:
            return {
                "identical": True,
                "meaningful_change": False,
                "v1_num": v1_num,
                "v2_num": v2_num,
                "diff_summary": f"Version {v1_num} and Version {v2_num} are substantively identical. Only minor whitespace or timestamp variations detected.",
                "added_clauses": [],
                "removed_clauses": [],
                "modified_clauses": [],
                "changed_sections": [],
                "additions_count": 0,
                "deletions_count": 0,
                "unified_diff": "",
            }

        # Align clauses using SequenceMatcher
        old_texts = [c["text"] for c in old_clauses]
        new_texts = [c["text"] for c in new_clauses]

        matcher = difflib.SequenceMatcher(None, old_texts, new_texts)
        opcodes = matcher.get_opcodes()

        added_clauses: List[Dict[str, Any]] = []
        removed_clauses: List[Dict[str, Any]] = []
        modified_clauses: List[Dict[str, Any]] = []
        changed_sections: set = set()

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                continue

            elif tag == "replace":
                # Pairwise comparison to see if it's an amended clause or complete replacement
                old_slice = old_clauses[i1:i2]
                new_slice = new_clauses[j1:j2]

                # Match by section name or position
                for o_c in old_slice:
                    matched_new = None
                    for n_c in new_slice:
                        if n_c["section"] == o_c["section"] or difflib.SequenceMatcher(None, o_c["text"], n_c["text"]).ratio() > 0.4:
                            matched_new = n_c
                            break

                    if matched_new:
                        sim = round(difflib.SequenceMatcher(None, o_c["text"], matched_new["text"]).ratio(), 2)
                        sec_name = matched_new["section"] if matched_new["section"] != "General Provisions" else o_c["section"]
                        modified_clauses.append({
                            "section": sec_name,
                            "before": o_c["text"],
                            "after": matched_new["text"],
                            "page": matched_new.get("page") or o_c.get("page", 1),
                            "similarity": sim,
                        })
                        changed_sections.add(sec_name)
                    else:
                        removed_clauses.append({
                            "section": o_c["section"],
                            "text": o_c["text"],
                            "page": o_c.get("page", 1),
                        })
                        changed_sections.add(o_c["section"])

                for n_c in new_slice:
                    if not any(m["after"] == n_c["text"] for m in modified_clauses):
                        added_clauses.append({
                            "section": n_c["section"],
                            "text": n_c["text"],
                            "page": n_c.get("page", 1),
                        })
                        changed_sections.add(n_c["section"])

            elif tag == "delete":
                for o_c in old_clauses[i1:i2]:
                    removed_clauses.append({
                        "section": o_c["section"],
                        "text": o_c["text"],
                        "page": o_c.get("page", 1),
                    })
                    changed_sections.add(o_c["section"])

            elif tag == "insert":
                for n_c in new_clauses[j1:j2]:
                    added_clauses.append({
                        "section": n_c["section"],
                        "text": n_c["text"],
                        "page": n_c.get("page", 1),
                    })
                    changed_sections.add(n_c["section"])

        # Compute line-by-line unified diff
        lines1 = old_text.splitlines(keepends=True)
        lines2 = new_text.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            lines1, lines2,
            fromfile=f"Version {v1_num}",
            tofile=f"Version {v2_num}",
            lineterm=""
        ))

        additions_cnt = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        deletions_cnt = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        # Narrative Summary of Changes
        summary_parts = []
        if modified_clauses:
            summary_parts.append(f"{len(modified_clauses)} clause(s) modified")
        if added_clauses:
            summary_parts.append(f"{len(added_clauses)} new clause(s) added")
        if removed_clauses:
            summary_parts.append(f"{len(removed_clauses)} clause(s) repealed or removed")

        diff_summary = (
            f"Amendment from Version {v1_num} to Version {v2_num}: " +
            (", ".join(summary_parts) if summary_parts else "Minor textual edits detected.") +
            f". Key updates affect: {', '.join(sorted(changed_sections)[:4])}."
        )

        return {
            "identical": False,
            "meaningful_change": True,
            "v1_num": v1_num,
            "v2_num": v2_num,
            "diff_summary": diff_summary,
            "added_clauses": added_clauses,
            "removed_clauses": removed_clauses,
            "modified_clauses": modified_clauses,
            "changed_sections": sorted(list(changed_sections)),
            "additions_count": additions_cnt,
            "deletions_count": deletions_cnt,
            "unified_diff": "".join(diff_lines),
        }
