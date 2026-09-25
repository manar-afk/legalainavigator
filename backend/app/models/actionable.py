"""
Domain models for Phase 9: Actionable Outputs Generator & Professional Consultation Brief.
Strict synthesis layer over Phase 1-8 engines.
Enforces complete source-type-specific provenance, role-resolution preservation,
neutral supervisory labeling, deterministic checklist priority, and strict non-re-reasoning boundary.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

from .situation import UserRole, RoleResolutionStatus
from .comparison import PartyRole, LegalTriggerType, ClauseEvidence, DocumentVersionMeta
from .external_law import AuthoritativeLegalSource


class ActionableSourceType(str, Enum):
    # 5 Evidentiary Types
    DOCUMENT_PROVISION = "document_provision"        # Grounded in contract text
    USER_ASSERTION = "user_assertion"                # Stated by user in situation narrative
    EXTERNAL_LAW = "external_law"                    # Grounded in Phase 5 authoritative statute (Mode 2 only)
    GATEKEEPER_DERIVED = "gatekeeper_derived"        # Grounded in Phase 7 missing predicate or pathway
    COMPARISON_DERIVED = "comparison_derived"        # Grounded in Phase 8 amendment or contradiction
    # 1 Non-Evidentiary Type
    SYNTHESIZED_PREPARATION = "synthesized_prep"    # Derived preparation task; NOT evidentiary authority!


class ActionableItemProvenance(BaseModel):
    source_type: ActionableSourceType
    source_ref: str                                  # e.g. "Section 8.1", "User Narrative Line 1", "TPA s.106", "Predicate notice_written"
    document_id: Optional[str] = None                # Required for DOCUMENT_PROVISION; None for USER_ASSERTION / SYNTHESIZED_PREPARATION
    document_name: Optional[str] = None
    section_or_title: Optional[str] = None
    exact_quote: Optional[str] = None                # Required for DOCUMENT_PROVISION; None for SYNTHESIZED_PREPARATION
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class ActionableLabel(str, Enum):
    IMPORTANT = "important"
    REVIEW = "review"
    POTENTIAL_INCONSISTENCY = "potential_inconsistency"
    UNCLEAR = "unclear"
    MISSING_INFORMATION = "missing_information"
    REQUIRES_PROFESSIONAL_REVIEW = "requires_professional_review"


class CovenantClassification(str, Enum):
    OBLIGATION = "obligation"                        # Mandatory duty imposed on a party
    RIGHT = "right"                                  # Entitlement or option exercisable by a party
    RESTRICTION = "restriction"                      # Negative covenant / prohibition
    FINANCIAL_PAYMENT = "financial_payment"          # Monetary obligation (rent, deposit, maintenance)
    PROCEDURAL_NOTICE = "procedural_notice"          # Notice delivery mechanism and timeline
    DEADLINE = "deadline"                            # Fixed temporal milestone or cure period


class DocumentDescribedCovenantItem(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    covenant_type: CovenantClassification
    title: str
    summary_description: str
    obligated_party: PartyRole
    beneficiary_party: PartyRole
    trigger_type: LegalTriggerType = LegalTriggerType.UNCLASSIFIED
    neutral_label: ActionableLabel = ActionableLabel.IMPORTANT
    clause_evidence: ClauseEvidence
    associated_deadline: Optional[str] = None
    is_conditional: bool = False
    condition_precedent: Optional[str] = None
    provenance: ActionableItemProvenance
    origin_reference_id: Optional[str] = None        # Traceability pointer to Phase 4/8 clause
    advisory_boundary: str = (
        "This entry describes what the identified document provision states. "
        "It does not independently determine legal validity, enforceability, or the existence of an enforceable legal right."
    )


class ChecklistCategory(str, Enum):
    DOCUMENT_GATHERING = "document_gathering"        # Locating missing contracts, notices, addenda
    FACTUAL_VERIFICATION = "factual_verification"    # Confirming dispatch dates, payment receipts
    TIMELINE_CONFIRMATION = "timeline_confirmation"  # Establishing occupancy start, cure period dates
    QUESTIONS_TO_CLARIFY = "questions_to_clarify"    # Clarifications needed before legal consultation


class ChecklistPriority(str, Enum):
    BLOCKING = "blocking"                            # Derived strictly from Phase 7 blocking predicates or inquiry-relevant Phase 8 true contradictions
    STANDARD = "standard"                            # General non-blocking evidentiary preparation


class ActionableChecklistItem(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: ChecklistCategory
    task_description: str
    rationale: str
    priority: ChecklistPriority
    provenance: ActionableItemProvenance             # Complete provenance; validated according to source_type
    origin_reference_id: Optional[str] = None        # Traceability pointer to Phase 7/8 entity
    status: str = "pending"                          # "pending" | "completed"


class LawyerQuestionItem(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str
    context_rationale: str
    origin_phase: str                                # e.g. "Phase 7 Missing Predicate", "Phase 8 Contradiction"
    origin_reference_id: Optional[str] = None        # Traceability pointer (e.g. predicate_id, difference_id)
    supporting_evidence_refs: List[ActionableItemProvenance] = Field(default_factory=list)
    neutral_label: ActionableLabel = ActionableLabel.REQUIRES_PROFESSIONAL_REVIEW


class ReviewFlagItem(BaseModel):
    flag_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: ActionableLabel
    title: str
    neutral_explanation: str                         # Strictly bounded; zero legal risk predictions
    origin_reference_id: Optional[str] = None        # Traceability pointer (e.g. difference_id, predicate_id)
    supporting_evidence: Optional[ActionableItemProvenance] = None


class RoleResolutionProfile(BaseModel):
    declared_role: Optional[UserRole] = None
    inferred_role: Optional[UserRole] = None         # Exact inferred state from Phase 6; NO synthetic default to GENERAL!
    role_confidence: Optional[float] = None
    role_evidence: List[str] = Field(default_factory=list)
    role_resolution_status: RoleResolutionStatus
    role_uncertainty_note: Optional[str] = None


class ProfessionalConsultationBrief(BaseModel):
    brief_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str
    client_situation_summary: str
    role_profile: RoleResolutionProfile              # Preserves complete Phase 6 role semantics & uncertainty without synthetic fallback
    governing_documents: List[DocumentVersionMeta]
    key_contractual_provisions: List[ClauseEvidence]
    targeted_questions_for_counsel: List[LawyerQuestionItem]
    missing_facts_to_clarify: List[str]              # From Phase 7 gatekeeper unstated predicates
    identified_inconsistencies_and_review_flags: List[ReviewFlagItem] # Strictly neutral labels; NO risk scores
    plain_language_overview: str
    operational_mode: str = "mode_1_doc_only"
    external_statutory_context: Optional[List[AuthoritativeLegalSource]] = None # Typed Phase 5 model!
    disclaimer: str = (
        "IMPORTANT NOTICE: This consultation brief was automatically generated by the Legal Information "
        "Navigator as an informational preparation aid for consultation with a qualified legal professional. "
        "It does not constitute legal representation, legal advice, or formal legal opinions. "
        "All provisions, dates, and claims should be independently verified by legal counsel."
    )


class ActionableOutputsContainer(BaseModel):
    container_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    consultation_brief: ProfessionalConsultationBrief
    covenants_matrix: List[DocumentDescribedCovenantItem]
    preparation_checklist: List[ActionableChecklistItem]
    markdown_brief_text: str


class ActionableGenerateRequest(BaseModel):
    doc_ids: List[str] = Field(default_factory=list)
    situation_description: Optional[str] = None
    declared_role: Optional[UserRole] = None
    comparison_doc_id: Optional[str] = None
    query_text: Optional[str] = None
    operational_mode: str = "mode_1_doc_only"
