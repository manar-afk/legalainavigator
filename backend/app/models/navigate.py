from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from .query import OperationalMode, QueryCategory
from .response import EvidenceSnippet
from .comparison import ComparisonResult
from .actionable import DocumentDescribedCovenantItem, ActionableChecklistItem, ProfessionalConsultationBrief


class NavigateRequest(BaseModel):
    query: Optional[str] = Field(
        default="",
        description="The user's direct question, situation narrative, or legal topic."
    )
    situation_description: Optional[str] = Field(
        default="",
        description="Optional detailed factual narrative of what occurred."
    )
    declared_role: Optional[str] = Field(
        default=None,
        description="User perspective (e.g. Tenant, Landlord, Employee, Employer, Client, Contractor)."
    )
    doc_ids: List[str] = Field(
        default_factory=list,
        description="IDs of documents attached to the request (0, 1, or multiple)."
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Applicable jurisdiction (city, state, or country) if known."
    )
    pasted_content: Optional[str] = Field(
        default=None,
        description="Optional pasted agreement text if no document file was uploaded."
    )
    requested_mode: Optional[OperationalMode] = Field(
        default=None,
        description="Optional explicit operational mode, or None to determine dynamically."
    )


class UnifiedNavigationResponse(BaseModel):
    summary_and_perspective: str = Field(
        ...,
        description="Plain-language direct answer tailored to the user's situation and inferred perspective."
    )
    answer: str = Field(
        ...,
        description="Substantive legal and contractual answer."
    )
    inferred_role: Optional[str] = Field(
        default=None,
        description="Inferred or declared perspective (e.g. Tenant, Employee, Contractor)."
    )
    what_the_document_says: str = Field(
        ...,
        description="Verbatim excerpts, clause numbers, and textual facts from uploaded documents."
    )
    what_this_means_in_plain_language: str = Field(
        ...,
        description="Neutral, objective translation of complex contractual terms into plain language."
    )
    why_it_matters: Optional[str] = Field(
        default=None,
        description="Contextual explanation of how this provision affects the user's situation."
    )
    sources: List[EvidenceSnippet] = Field(
        default_factory=list,
        description="Verbatim clause citations with document IDs, section numbers, and exact character spans."
    )
    comparative_analysis: Optional[ComparisonResult] = Field(
        default=None,
        description="Cross-document diffs, material modifications, additions, and contradictions."
    )
    governing_legal_framework: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Statutory provisions, default statutory notice rules, and jurisdiction notes."
    )
    jurisdiction_note: Optional[str] = Field(
        default=None,
        description="Jurisdiction status or prompt if jurisdiction is missing."
    )
    what_is_unclear_or_missing: Optional[str] = Field(
        default=None,
        description="Factual gaps, unstated timelines, contract silence, or missing jurisdiction."
    )
    uncertainties: List[str] = Field(
        default_factory=list,
        description="Specific caveats, preconditions, or unestablished facts."
    )
    actionable_checklist: List[str] = Field(
        default_factory=list,
        description="Bounded, non-tactical investigative steps and records to preserve."
    )
    covenants_matrix: Optional[List[DocumentDescribedCovenantItem]] = Field(
        default=None,
        description="Extracted bilateral rights and obligations matrix."
    )
    consultation_brief_markdown: Optional[str] = Field(
        default=None,
        description="Complete formatted markdown export for attorney consultation."
    )
    diagnostics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Internal telemetry, mode classification, category code, sufficiency status, latency."
    )
