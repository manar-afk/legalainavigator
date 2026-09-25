import re
from typing import List, Optional, Tuple
from ..models.query import OperationalMode, QueryCategory, IntentClassification, QueryRequest

# Keywords indicating statutory, regulatory, or external legal framework needs
EXTERNAL_LAW_KEYWORDS = [
    r"\bunder\s+([a-zA-Z\s]+)\s+law\b",
    r"\b([a-zA-Z\s]+)\s+law\b",
    r"\blegally\s+valid\b",
    r"\bvalid\b",
    r"\bvalidity\b",
    r"\blegality\b",
    r"\blawful\b",
    r"\bunlawful\b",
    r"\benforceable\b",
    r"\benforceability\b",
    r"\bstatutory\b",
    r"\blegislation\b",
    r"\bregulation\b",
    r"\bsection\s+\d+\s+of\b",
    r"\bact\b",
    r"\bcode\b",
    r"\bvalid\s+under\b",
    r"\btenancy\s+act\b",
    r"\brent\s+control\b",
    r"\bcontract\s+act\b",
    r"\blabor\s+code\b",
    r"\bemployment\s+act\b",
]

# Common explicit jurisdictions mentioned in queries
JURISDICTION_PATTERNS = [
    (r"\b(india|indian)\b", "India"),
    (r"\b(karnataka|bengaluru|bangalore)\b", "Karnataka, India"),
    (r"\b(california|ca)\b", "California, USA"),
    (r"\b(new\s+york|ny)\b", "New York, USA"),
    (r"\b(texas|tx)\b", "Texas, USA"),
    (r"\b(united\s+states|u\.s\.|usa|federal)\b", "United States (Federal)"),
    (r"\b(united\s+kingdom|uk|england)\b", "United Kingdom"),
]

# General concept patterns (definition / explanation of legal terms without needing external statutes)
CONCEPTUAL_PATTERNS = [
    r"(?i)^what\s+is\s+(an?|the)\s+([a-zA-Z\s\-]+clause|[a-zA-Z\s\-]+agreement|[a-zA-Z\s\-]+period|[a-zA-Z\s\-]+term)\??$",
    r"(?i)^explain\s+(an?|the)?\s*([a-zA-Z\s\-]+)\??$",
    r"(?i)^what\s+does\s+([a-zA-Z\s\-]+)\s+mean\??$",
    r"(?i)^what\s+are\s+liquidated\s+damages\??$",
    r"(?i)^what\s+is\s+force\s+majeure\??$",
    r"(?i)^what\s+is\s+indemnity\??$",
]

# Tactical litigation / legal advice requests
PROFESSIONAL_JUDGMENT_KEYWORDS = [
    r"\bshould\s+i\s+sue\b",
    r"\bfile\s+a\s+lawsuit\b",
    r"\bguarantee\s+i\s+will\s+win\b",
    r"\bwhat\s+court\s+will\s+decide\b",
    r"\brepresent\s+me\b",
    r"\bcan\s+you\s+be\s+my\s+lawyer\b",
]

# Comparison queries
COMPARISON_KEYWORDS = [
    r"\bcompare\b",
    r"\bwhat\s+changed\b",
    r"\bdifference\s+between\b",
    r"\bamendment\s+vs\b",
    r"\bversion\s+1\s+and\s+version\s+2\b",
]


class ModeRouterService:
    """
    Routes queries to Mode 1, Mode 2, or Mode 3 with dynamic reclassification,
    conceptual vs jurisdiction-dependent routing, and missing-jurisdiction detection.
    """

    @classmethod
    def extract_jurisdiction(cls, text: str, explicit_jurisdiction: Optional[str] = None) -> Optional[str]:
        if explicit_jurisdiction and explicit_jurisdiction.strip():
            return explicit_jurisdiction.strip()
        for pattern, canon_name in JURISDICTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return canon_name
        return None

    @classmethod
    def requires_statutory_or_external_law(cls, text: str) -> bool:
        lower = text.lower()
        for pattern in EXTERNAL_LAW_KEYWORDS:
            if re.search(pattern, lower):
                return True
        return False

    @classmethod
    def is_purely_conceptual(cls, text: str) -> bool:
        lower = text.lower().strip()
        for pattern in CONCEPTUAL_PATTERNS:
            if re.search(pattern, lower):
                # If it explicitly mentions a jurisdiction, it's not purely conceptual
                for j_pat, _ in JURISDICTION_PATTERNS:
                    if re.search(j_pat, lower):
                        return False
                return True
        # Common isolated legal concepts
        pure_terms = [
            "what is an indemnity clause",
            "what is a lock-in period",
            "what is force majeure",
            "what are liquidated damages",
            "what does severance mean",
            "what is a non-disclosure agreement",
            "what is an arbitration clause",
        ]
        return any(term in lower for term in pure_terms)

    @classmethod
    def classify_and_route(cls, request: QueryRequest) -> IntentClassification:
        query_text = request.query.strip()
        query_lower = query_text.lower()
        has_documents = len(request.doc_ids) > 0
        has_situation = request.situation is not None and bool(request.situation.raw_description.strip())

        # 1. Check for Out-of-Scope / Professional Legal Judgment
        for pattern in PROFESSIONAL_JUDGMENT_KEYWORDS:
            if re.search(pattern, query_lower):
                mode = OperationalMode.MODE_1_DOC_ONLY if has_documents else OperationalMode.MODE_3_GENERAL_NO_DOC
                return IntentClassification(
                    category=QueryCategory.G_PROFESSIONAL_JUDGMENT,
                    effective_mode=mode,
                    is_reclassified=False,
                    requires_external_law=False,
                    is_conceptual_only=False,
                    is_jurisdiction_missing=False,
                    confidence=0.98,
                    explanation="Request asks for tactical litigation advice or representation, which requires professional legal counsel."
                )

        from .jurisdiction_service import jurisdiction_service
        j_sig, j_state, _ = jurisdiction_service.resolve_jurisdiction(
            query=query_text,
            doc_ids=request.doc_ids,
            explicit_jurisdiction=request.jurisdiction
        )
        detected_jurisdiction = j_sig.jurisdiction_value if j_sig else None
        needs_external = cls.requires_statutory_or_external_law(query_text) or (cls.extract_jurisdiction(query_text, request.jurisdiction) is not None)

        # 2. Mode 3: General / No-Document Legal Information
        if not has_documents:
            # Check if pure conceptual question
            if cls.is_purely_conceptual(query_text) and not detected_jurisdiction:
                return IntentClassification(
                    category=QueryCategory.B_DOCUMENT_INTERPRETATION,
                    effective_mode=OperationalMode.MODE_3_GENERAL_NO_DOC,
                    is_reclassified=False,
                    requires_external_law=False,
                    is_conceptual_only=True,
                    is_jurisdiction_missing=False,
                    confidence=1.0,
                    explanation="General legal concept question. Can be explained in plain language without requiring external retrieval."
                )

            # Statutory or jurisdiction-specific question
            if needs_external:
                if detected_jurisdiction:
                    return IntentClassification(
                        category=QueryCategory.E_EXTERNAL_LEGAL_INFO,
                        effective_mode=OperationalMode.MODE_3_GENERAL_NO_DOC,
                        is_reclassified=False,
                        requires_external_law=True,
                        is_conceptual_only=False,
                        is_jurisdiction_missing=False,
                        target_jurisdiction=detected_jurisdiction,
                        retrieval_prepared=True,
                        retrieval_target_query=f"{query_text} [Jurisdiction: {detected_jurisdiction}]",
                        confidence=0.95,
                        explanation=f"Jurisdiction-specific question for {detected_jurisdiction}. Prepared for authoritative legal retrieval."
                    )
                else:
                    # Missing Jurisdiction!
                    return IntentClassification(
                        category=QueryCategory.F_INSUFFICIENT_INFO,
                        effective_mode=OperationalMode.MODE_3_GENERAL_NO_DOC,
                        is_reclassified=False,
                        requires_external_law=True,
                        is_conceptual_only=False,
                        is_jurisdiction_missing=True,
                        confidence=0.95,
                        explanation="Statutory rules and tenancy regulations vary substantially by state and country. A specific jurisdiction is required."
                    )

            # Fallback general query without document
            return IntentClassification(
                category=QueryCategory.B_DOCUMENT_INTERPRETATION,
                effective_mode=OperationalMode.MODE_3_GENERAL_NO_DOC,
                is_reclassified=False,
                requires_external_law=False,
                is_conceptual_only=True,
                is_jurisdiction_missing=False,
                confidence=0.9,
                explanation="Informational question handled via plain-language explanation."
            )

        # 3. Document Present: Mode 1 vs Mode 2
        # Check comparison first
        for pattern in COMPARISON_KEYWORDS:
            if re.search(pattern, query_lower) or len(request.doc_ids) > 1:
                return IntentClassification(
                    category=QueryCategory.C_DOCUMENT_COMPARISON,
                    effective_mode=OperationalMode.MODE_1_DOC_ONLY,
                    is_reclassified=False,
                    requires_external_law=False,
                    is_conceptual_only=False,
                    is_jurisdiction_missing=False,
                    confidence=0.95,
                    explanation="Comparison query between documents or versions."
                )

        # Check for DYNAMIC RECLASSIFICATION: Mode 1 -> Mode 2
        if needs_external:
            return IntentClassification(
                category=QueryCategory.E_EXTERNAL_LEGAL_INFO,
                effective_mode=OperationalMode.MODE_2_DOC_EXTERNAL,
                is_reclassified=True,
                reclassification_reason=(
                    "Question asks about statutory validity, governing law, or enforceability. "
                    "Dynamically reclassified from Mode 1 (Doc-Only) to Mode 2 (Doc + External Law) "
                    "to prevent misleading conclusions based solely on private agreement text."
                ),
                requires_external_law=True,
                is_conceptual_only=False,
                is_jurisdiction_missing=(detected_jurisdiction is None),
                target_jurisdiction=detected_jurisdiction,
                retrieval_prepared=True,
                retrieval_target_query=f"{query_text} [Document Reference: {request.doc_ids[0] if request.doc_ids else 'active'}]",
                confidence=0.95,
                explanation="Document question evaluated against external legal framework."
            )

        # Situation-Specific vs Document Factual (check whole words using word boundaries)
        situation_match = re.search(r"\b(my|i|me|mine|we|our|us|asking\s+me|told\s+me|wants\s+to|landlord\s+wants|leave\s+in)\b", query_lower)
        if has_situation or situation_match:
            return IntentClassification(
                category=QueryCategory.D_SITUATION_SPECIFIC,
                effective_mode=OperationalMode.MODE_1_DOC_ONLY,
                is_reclassified=False,
                requires_external_law=False,
                is_conceptual_only=False,
                is_jurisdiction_missing=False,
                confidence=0.95,
                explanation="Situation-aware question referencing specific events against uploaded agreement."
            )

        return IntentClassification(
            category=QueryCategory.A_DOCUMENT_FACTUAL,
            effective_mode=OperationalMode.MODE_1_DOC_ONLY,
            is_reclassified=False,
            requires_external_law=False,
            is_conceptual_only=False,
            is_jurisdiction_missing=False,
            confidence=0.95,
            explanation="Factual document question answered directly from uploaded contract provisions."
        )


mode_router = ModeRouterService()
