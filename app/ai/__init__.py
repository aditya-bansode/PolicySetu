"""
PolicySetu — AI Intelligence Package
====================================
Subsystem providing:
1. Policy classification (12 canonical categories)
2. Simple-language summarization (EN, MR, HI)
3. Key provision extraction
4. Important dates extraction
5. Eligibility and condition extraction
6. Affected stakeholder identification
7. Policy change explanation
8. RAG Question Answering system
"""

from app.ai.llm_client import llm_client, LLMClient
from app.ai.classifier import policy_classifier, PolicyClassifier, CANONICAL_CATEGORIES
from app.ai.summarizer import policy_summarizer, PolicySummarizer
from app.ai.extractor import PolicyExtractor, CANONICAL_STAKEHOLDERS
from app.ai.explainer import PolicyExplainer
from app.ai.rag_engine import PolicyRAGEngine

__all__ = [
    "llm_client",
    "LLMClient",
    "policy_classifier",
    "PolicyClassifier",
    "CANONICAL_CATEGORIES",
    "policy_summarizer",
    "PolicySummarizer",
    "PolicyExtractor",
    "CANONICAL_STAKEHOLDERS",
    "PolicyExplainer",
    "PolicyRAGEngine",
]
