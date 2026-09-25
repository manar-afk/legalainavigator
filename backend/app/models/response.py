from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .document import EvidenceSource
from .query import OperationalMode, QueryCategory


class EvidenceSnippet(BaseModel):
    """Detailed traceable evidence snippet for UI highlighting."""
    snippet_id: str
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    quote: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    source_type: str = "document"  # "document", "user_fact", "statute"
    effective_date: Optional[str] = None


class MissingInfoItem(BaseModel):
    """An explicit factual or legal gap that prevents certain conclusion."""
    field_name: str
    description: str
    why_it_matters: str
    framework_context: Optional[str] = None  # e.g., "Lease Termination Framework"
    is_blocking: bool = False
    category: Optional[str] = None
    impact_on_pathway: Optional[Dict[str, str]] = None
    suggested_investigation: Optional[str] = None


class InconsistencyItem(BaseModel):
    """A detected conflict between clauses or across document versions."""
    topic: str
    description: str
    clause_a_ref: str
    clause_a_text: str
    clause_b_ref: str
    clause_b_text: str
    neutral_advisory: str = "Please verify which provision governs your situation."


class GroundedAnswer(BaseModel):
    """Comprehensive grounded response adhering to knowledge hierarchy & strict fact separation."""
    # Strict 5-way Information Separation
    document_facts: List[str] = Field(
        default_factory=list,
        description="Direct factual provisions extracted from the document."
    )
    user_provided_facts: List[str] = Field(
        default_factory=list,
        description="Facts stated by the user, treated as subjective unverified assertions."
    )
    external_law: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Authoritative statutory/regulatory provisions and currency info."
    )
    plain_language_interpretation: str = Field(
        ...,
        description="Plain-language informational explanation of how provisions connect."
    )
    uncertainty_and_gaps: List[str] = Field(
        default_factory=list,
        description="Identified ambiguities, missing dates, or prerequisites."
    )

    # User-facing structured sections (Section 9 of Product Spec)
    answer: str = Field(
        ...,
        description="Short direct answer using measured, non-definitive language."
    )
    what_the_document_says: Optional[str] = Field(
        default=None,
        description="Verbatim or paraphrased excerpt from the relevant provision."
    )
    what_this_means_in_plain_language: str = Field(
        ...,
        description="Jargon-free explanation."
    )
    why_it_matters_to_your_situation: Optional[str] = Field(
        default=None,
        description="Connection to stated user facts without declaring outcomes."
    )
    what_is_unclear_or_missing: Optional[str] = Field(
        default=None,
        description="Explicitly identified factual or documentary gaps."
    )
    what_to_check_next: List[str] = Field(
        default_factory=list,
        description="Informational preparation steps, dates to verify, or documents to find."
    )

    # Traceable evidence & diagnostics
    sources: List[EvidenceSnippet] = Field(default_factory=list)
    judicial_precedents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Verified court judgments with complete judicial metadata."
    )
    failure_uncertainty_state: Optional[str] = Field(
        default=None,
        description="Mode 2 failure or uncertainty state if applicable."
    )
    jurisdiction_signal: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Evaluated jurisdiction signal provenance."
    )
    document_law_relationships: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Neutral 4-stage comparison between contract clause and statutory standard."
    )
    situation_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Extracted semantic situation analysis and role context."
    )
    missing_info_report: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Comprehensive Phase 7 Missing Information Report with pathways and blocking-predicate gating."
    )
    missing_info_details: List[MissingInfoItem] = Field(default_factory=list)
    inconsistencies: List[InconsistencyItem] = Field(default_factory=list)
    neutral_labels: List[str] = Field(
        default_factory=list,
        description="Neutral tags: Important, Review, Potential Inconsistency, Unclear, Missing Information, Requires Professional Review."
    )
    operational_mode: OperationalMode = OperationalMode.MODE_1_DOC_ONLY
    query_category: QueryCategory = QueryCategory.A_DOCUMENT_FACTUAL
    evidence_sufficiency_passed: bool = True
    professional_review_recommended: bool = False
