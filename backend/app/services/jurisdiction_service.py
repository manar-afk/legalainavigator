"""
Jurisdiction Signal Resolver & Conflict Detector.
Treats jurisdiction as an evaluated signal from query, document, or user situation.
Detects jurisdiction conflicts and triggers explicit failure/uncertainty states.
Never silently assumes India or any other default jurisdiction.
"""

import re
from typing import Optional, Tuple, List
from ..models.external_law import JurisdictionSignal, FailureUncertaintyState
from ..core.storage import document_store


# Canonical recognized jurisdiction patterns
KNOWN_JURISDICTIONS = [
    (r"\b(himachal\s+pradesh|hp)\b", "Himachal Pradesh, India"),
    (r"\b(karnataka|bengaluru|bangalore)\b", "Karnataka, India"),
    (r"\b(maharashtra|mumbai|bombay|pune)\b", "Maharashtra, India"),
    (r"\b(delhi|new\s+delhi|ncr)\b", "Delhi, India"),
    (r"\b(tamil\s+nadu|chennai|madras)\b", "Tamil Nadu, India"),
    (r"\b(telangana|hyderabad)\b", "Telangana, India"),
    (r"\b(west\s+bengal|kolkata|calcutta)\b", "West Bengal, India"),
    (r"\b(india|indian|republic\s+of\s+india)\b", "India"),
    (r"\b(california|ca)\b", "California, USA"),
    (r"\b(new\s+york|ny)\b", "New York, USA"),
    (r"\b(texas|tx)\b", "Texas, USA"),
    (r"\b(united\s+states|u\.s\.|usa|federal)\b", "United States (Federal)"),
    (r"\b(united\s+kingdom|uk|england)\b", "United Kingdom"),
]

# Patterns for extracting governing law clauses inside documents
GOVERNING_LAW_SECTION_PATTERNS = [
    r"(?i)(governing\s+law|jurisdiction|dispute\s+resolution)[\s\S]{0,300}?(laws\s+of\s+[a-zA-Z\s,]+|courts\s+(?:in|at)\s+[a-zA-Z\s,]+)",
    r"(?i)shall\s+be\s+governed\s+by\s+and\s+construed\s+in\s+accordance\s+with\s+the\s+laws\s+of\s+([a-zA-Z\s,]+)",
    r"(?i)courts\s+(?:in|at)\s+([a-zA-Z\s,]+)\s+shall\s+have\s+exclusive\s+jurisdiction",
]


class JurisdictionService:
    """
    Evaluates jurisdiction signals across query, document text, and situation context.
    Detects conflicts and enforces explicit abstention when missing.
    """

    @classmethod
    def extract_from_query(cls, query: str) -> Optional[JurisdictionSignal]:
        q_lower = query.lower()
        for pat, canon_name in KNOWN_JURISDICTIONS:
            m = re.search(pat, q_lower)
            if m:
                return JurisdictionSignal(
                    signal_source="query",
                    jurisdiction_value=canon_name,
                    evidence_text=m.group(0),
                    confidence=0.95
                )
        return None

    @classmethod
    def extract_from_document(cls, doc_id: str) -> Optional[JurisdictionSignal]:
        raw_text = document_store.get_raw_text(doc_id)
        if not raw_text:
            return None

        # Look specifically in governing law clauses
        for chunk in document_store.get_chunks(doc_id):
            sec_title = (chunk.section_title or "").lower()
            if "governing law" in sec_title or "jurisdiction" in sec_title or "dispute resolution" in sec_title:
                text_lower = chunk.text.lower()
                for pat, canon_name in KNOWN_JURISDICTIONS:
                    m = re.search(pat, text_lower)
                    if m:
                        return JurisdictionSignal(
                            signal_source="document",
                            jurisdiction_value=canon_name,
                            evidence_text=f"{chunk.section_number or 'Governing Law Clause'}: {chunk.text.strip()[:180]}",
                            confidence=0.9
                        )

        # Fallback search across entire document text for governing law patterns
        for pat, canon_name in KNOWN_JURISDICTIONS:
            if re.search(r"(?i)(governing\s+law|jurisdiction)[\s\S]{0,150}" + pat, raw_text):
                return JurisdictionSignal(
                    signal_source="document",
                    jurisdiction_value=canon_name,
                    evidence_text=f"Extracted from document governing law context: {canon_name}",
                    confidence=0.85
                )

        return None

    @classmethod
    def extract_from_situation(cls, explicit_jurisdiction: Optional[str]) -> Optional[JurisdictionSignal]:
        if not explicit_jurisdiction or not explicit_jurisdiction.strip():
            return None
        val = explicit_jurisdiction.strip()
        for pat, canon_name in KNOWN_JURISDICTIONS:
            if re.search(pat, val.lower()):
                return JurisdictionSignal(
                    signal_source="user_situation",
                    jurisdiction_value=canon_name,
                    evidence_text=val,
                    confidence=0.9
                )
        return JurisdictionSignal(
            signal_source="user_situation",
            jurisdiction_value=val,
            evidence_text=val,
            confidence=0.75
        )

    @classmethod
    def resolve_jurisdiction(
        cls,
        query: str,
        doc_ids: Optional[List[str]] = None,
        explicit_jurisdiction: Optional[str] = None
    ) -> Tuple[Optional[JurisdictionSignal], Optional[FailureUncertaintyState], Optional[str]]:
        """
        Resolves effective jurisdiction.
        Returns: (resolved_signal, failure_or_uncertainty_state, advisory_message)
        """
        query_sig = cls.extract_from_query(query)
        sit_sig = cls.extract_from_situation(explicit_jurisdiction)

        doc_sig = None
        if doc_ids:
            for d_id in doc_ids:
                d_sig = cls.extract_from_document(d_id)
                if d_sig:
                    doc_sig = d_sig
                    break

        # Check for Jurisdiction Conflict (e.g. Document says Karnataka, Query asks about Himachal Pradesh)
        if query_sig and doc_sig:
            q_val = query_sig.jurisdiction_value.lower()
            d_val = doc_sig.jurisdiction_value.lower()

            # Compatible if identical, or if one is the generic nation (India) and the other is a state within it
            is_compatible = (
                q_val == d_val
                or q_val.strip() == "india"
                or d_val.strip() == "india"
            )
            # If two distinct states or jurisdictions differ, it's an explicit conflict
            if not is_compatible:
                conflict_msg = (
                    f"Jurisdiction conflict detected: The uploaded agreement designates {doc_sig.jurisdiction_value} "
                    f"({doc_sig.evidence_text[:100]}...), whereas your question inquires about {query_sig.jurisdiction_value}. "
                    "The system will not silently choose one jurisdiction over the other. Please clarify which law governs."
                )
                return (
                    query_sig,
                    FailureUncertaintyState.JURISDICTION_CONFLICT,
                    conflict_msg
                )

        # Prioritize explicit query signal, then situation, then document governing law
        if query_sig:
            return query_sig, None, None
        if sit_sig:
            return sit_sig, None, None
        if doc_sig:
            return doc_sig, None, None

        # Neither query, situation, nor document specified a jurisdiction
        missing_msg = (
            "Jurisdiction missing: A specific jurisdiction is required to evaluate statutory enforceability. "
            "Neither your question, your stated situation, nor the uploaded document specifies a governing jurisdiction. "
            "Because statutory rules vary substantially, the system will not guess or assume a default jurisdiction."
        )
        return None, FailureUncertaintyState.JURISDICTION_MISSING, missing_msg


jurisdiction_service = JurisdictionService()
