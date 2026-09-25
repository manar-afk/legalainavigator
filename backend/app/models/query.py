from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from .situation import UserSituation


class OperationalMode(str, Enum):
    MODE_1_DOC_ONLY = "mode_1_doc_only"          # Document-only Q&A (Web OFF by default)
    MODE_2_DOC_EXTERNAL = "mode_2_doc_external"  # Document + External Law (Conditional Web ON)
    MODE_3_GENERAL_NO_DOC = "mode_3_general_no_doc"  # General / No-Document Legal Info


class QueryCategory(str, Enum):
    A_DOCUMENT_FACTUAL = "document_factual"
    B_DOCUMENT_INTERPRETATION = "document_interpretation"
    C_DOCUMENT_COMPARISON = "document_comparison"
    D_SITUATION_SPECIFIC = "situation_specific"
    E_EXTERNAL_LEGAL_INFO = "external_legal_info"
    F_INSUFFICIENT_INFO = "insufficient_info"
    G_PROFESSIONAL_JUDGMENT = "professional_judgment"


class QueryRequest(BaseModel):
    """Incoming user query payload."""
    query: str = Field(..., description="The user's direct question.")
    situation: Optional[UserSituation] = Field(
        default=None,
        description="Optional situation description stated by the user."
    )
    doc_ids: List[str] = Field(
        default_factory=list,
        description="IDs of currently loaded documents."
    )
    requested_mode: Optional[OperationalMode] = Field(
        default=None,
        description="Requested mode, or None to auto-route."
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Jurisdiction filter if specified (e.g. California, Karnataka, India)."
    )


class IntentClassification(BaseModel):
    """Result of intent parsing and mode routing."""
    category: QueryCategory
    effective_mode: OperationalMode
    is_reclassified: bool = False
    reclassification_reason: Optional[str] = None
    requires_external_law: bool = False
    is_conceptual_only: bool = True
    is_jurisdiction_missing: bool = False
    target_jurisdiction: Optional[str] = None
    retrieval_prepared: bool = False
    retrieval_target_query: Optional[str] = None
    confidence: float = 1.0
    explanation: Optional[str] = None
