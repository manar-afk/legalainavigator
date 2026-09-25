"""
Domain models for Phase 7: Missing Information Engine.
Defines evidence sufficiency levels, prerequisite predicate status,
provenance attribution, conditional applicability pathways, and comprehensive gap reporting.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .query import OperationalMode


class EvidenceSufficiencyLevel(str, Enum):
    SUFFICIENT = "sufficient"                      # All blocking predicates established
    PARTIALLY_SUFFICIENT = "partially_sufficient"  # Blocking established, non-blocking informational gaps exist
    INSUFFICIENT = "insufficient"                  # One or more blocking predicates missing
    INDETERMINATE = "indeterminate"                # Unresolved contradiction materially affects a blocking/governing predicate


class EvidentiaryState(str, Enum):
    CONTRACT_SILENCE = "contract_silence"                  # Document contains no clause governing the subject
    MISSING_FACTUAL_EVIDENCE = "missing_factual_evidence"  # Clause exists, but user factual predicates unstated
    AMBIGUOUS_EVIDENCE = "ambiguous_evidence"              # Contradictory contract clauses or conflicting user assertions
    EVIDENCE_ESTABLISHED = "evidence_established"          # Relevant evidence present and unambiguous


class HeuristicStatus(str, Enum):
    APPLIED = "applied"
    FRAMEWORK_NOT_REQUIRED = "framework_not_required"      # Simple lookup or general query; no heuristic needed


class PredicateCategory(str, Enum):
    DOCUMENT_DATE = "document_date"
    FACTUAL_EVENT = "factual_event"
    NOTICE_RECEIPT = "notice_receipt"
    CONTRACTUAL_PROVISION = "contractual_provision"
    PARTY_CONSENT = "party_consent"
    EXTERNAL_STATUTE = "external_statute"                  # Strictly Mode 2 only!


class PredicateStatus(str, Enum):
    ESTABLISHED = "established"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    NOT_APPLICABLE = "not_applicable"


class PredicateSourceStatus(str, Enum):
    DOCUMENT_PROVEN = "document_proven"
    USER_ASSERTED = "user_asserted"
    UNSTATED = "unstated"
    CONTRADICTORY_SIGNALS = "contradictory_signals"


class PredicateProvenance(BaseModel):
    source_type: str  # "document_clause", "user_assertion", "external_statute", "heuristic_template"
    source_ref: Optional[str] = None  # e.g. "Section 8.1 (residential_lease_agreement.txt)"
    exact_quote: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    extracted_value: Optional[str] = None  # e.g. "30 days", "14 days", "6 months"
    source_description: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.source_description:
            self.source_description = self.source_ref or self.source_type

class MissingPredicateItem(BaseModel):
    predicate_id: str
    label: str
    category: PredicateCategory
    is_blocking: bool
    status: PredicateStatus
    source_status: PredicateSourceStatus
    mode_applicability: List[OperationalMode] = [
        OperationalMode.MODE_1_DOC_ONLY,
        OperationalMode.MODE_2_DOC_EXTERNAL
    ]
    why_it_matters: str
    impact_on_pathway: Dict[str, str] = Field(default_factory=dict)
    suggested_investigation: str
    provenance: Optional[PredicateProvenance] = None
    semantic_unstated_phrasing: Optional[str] = None
    description: Optional[str] = None
    predicate_name: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.predicate_name:
            self.predicate_name = self.label or self.predicate_id
        if not self.description:
            self.description = self.semantic_unstated_phrasing or self.suggested_investigation

class ConditionalApplicabilityPathway(BaseModel):
    pathway_name: str  # e.g. "Pathway A: Termination for Convenience"
    factual_condition: str  # e.g. "If no uncured material default occurred and lock-in period has concluded"
    applicable_provision: str  # e.g. "Section 8.1"
    contractual_stipulation: str  # Dynamically extracted terms (e.g. "thirty (30) days' prior written notice")
    evidence_required_to_confirm: List[str] = Field(default_factory=list)


class MissingInfoReport(BaseModel):
    heuristic_status: HeuristicStatus
    heuristic_name: Optional[str] = None
    evidentiary_state: EvidentiaryState
    sufficiency_level: EvidenceSufficiencyLevel
    established_predicates: List[MissingPredicateItem] = Field(default_factory=list)
    missing_predicates: List[MissingPredicateItem] = Field(default_factory=list)
    ambiguous_predicates: List[MissingPredicateItem] = Field(default_factory=list)
    conditional_pathways: List[ConditionalApplicabilityPathway] = Field(default_factory=list)
    overall_gap_summary: str
    is_applicability_determined: bool  # True ONLY if sufficiency_level == SUFFICIENT and exactly 1 unique pathway identified
    contradictions: List[str] = Field(default_factory=list)
    investigative_recommendations: List[str] = Field(default_factory=list)
    query_text: Optional[str] = None
