from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class DocumentRelationshipStatus(str, Enum):
    EXPRESS_AMENDMENT_REFERENCED = "express_amendment_referenced"      # Doc B explicitly cites Doc A and amends specific sections
    FULL_RESTATEMENT_REPLACEMENT = "full_restatement_replacement"      # Doc B states it amends and restates Doc A in its entirety
    CONFIRMED_CO_APPLICABLE = "confirmed_co_applicable"                # Concurrent co-active agreements governing same transaction without precedence clause
    UNVERIFIED_RELATIONSHIP = "unverified_relationship"                # No express link detected; relationship unverified (DO NOT assume standalone)
    INTRA_DOCUMENT_COVENANTS = "intra_document_covenants"              # Internal clauses within a single document
    CONFIRMED_STANDALONE = "confirmed_standalone"                      # Affirmatively confirmed separate by user/metadata


class DocumentRole(str, Enum):
    BASE_AGREEMENT = "base_agreement"
    AMENDMENT_ADDENDUM = "amendment_addendum"
    RESTATEMENT = "restatement"
    SIDE_LETTER = "side_letter"
    CO_APPLICABLE_AGREEMENT = "co_applicable_agreement"
    UNLINKED_DOCUMENT = "unlinked_document"
    SINGLE_DOCUMENT = "single_document"


class ExecutionStatus(str, Enum):
    VERIFIED_SIGNED = "verified_signed"
    BLANK_OR_UNSIGNED = "blank_or_unsigned"
    DATED_UNVERIFIED_SIGNATURE = "dated_unverified_signature"
    UNDATED = "undated"


class PartyRole(str, Enum):
    TENANT_LESSEE = "tenant_lessee"
    LANDLORD_LESSOR = "landlord_lessor"
    EMPLOYEE = "employee"
    EMPLOYER = "employer"
    MUTUAL_BOTH = "mutual_both"
    UNSPECIFIED = "unspecified"


class LegalTriggerType(str, Enum):
    UNCLASSIFIED = "unclassified"                       # Default! Never assumed silently; preserves semantic comparison and uncertainty
    CONVENIENCE_NO_FAULT = "convenience_no_fault"       # Early termination without cause
    DEFAULT_MATERIAL_BREACH = "default_material_breach" # Non-payment, breach of use, cure notices
    EXPIRATION_TERM = "expiration_term"                 # Natural end of lease term, renewal window
    LOCK_IN_COMPLIANCE = "lock_in_compliance"           # Mandatory occupancy period
    FINANCIAL_PAYMENT = "financial_payment"             # Base rent, maintenance, deposit
    PREMISES_USE = "premises_use"                       # Permitted residential use, subletting bar
    REPAIR_MAINTENANCE = "repair_maintenance"           # Structural vs day-to-day repair duties
    DISPUTE_FORUM = "dispute_forum"                     # Jurisdiction, arbitration seat


class ChangeType(str, Enum):
    MODIFICATION = "modification"                       # Existing covenant modified in value/scope
    ADDITION = "addition"                               # New covenant/restriction in Doc B not in Doc A
    OMITTED_UNMODIFIED = "omitted_unmodified"           # Unaddressed in partial amendment; base lease remains operative
    OMITTED_FROM_RESTATEMENT = "omitted_from_restatement" # Absent from restatement with no equivalent (not labeled express deletion)
    EXPRESS_DELETION = "express_deletion"               # Clause explicitly repealed/deleted in text
    REPHRASING = "rephrasing"                           # Stylistic rewording without semantic alteration
    POTENTIAL_CONFLICT_UNVERIFIED = "potential_conflict_unverified" # Conflicting text detected across unverified relationship (not a true contradiction)
    INTERNAL_INCONSISTENCY = "internal_inconsistency"   # True established contradiction under confirmed context (intra-doc or co-applicable)


class MaterialityLevel(str, Enum):
    MATERIAL = "material"                               # Substantively alters legal duties, liabilities, or timelines
    NON_MATERIAL = "non_material"                       # Stylistic, formatting, or trivial administrative tweak
    INDETERMINATE_MATERIALITY = "indeterminate"         # Materiality dependent on unstated factual context


class ReconciliationStatus(str, Enum):
    RECONCILED_TEMPORAL = "reconciled_temporal"         # Sequential time windows (e.g. Lock-in vs Post-Lock-in)
    RECONCILED_SUBORDINATION = "reconciled_subordination" # Express precedence clause ('Notwithstanding...', 'Subject to...')
    RECONCILED_ACTOR_ASYMMETRY = "reconciled_actor_asymmetry" # Different parties have different rights/obligations
    RECONCILED_EXPRESS_AMENDMENT = "reconciled_express_amendment" # Doc B explicitly updates Doc A with stated effective date
    CONFLICTING_UNVERIFIED_RELATIONSHIP = "conflicting_unverified_relationship" # Conflicting text detected across documents with unverified relationship (NOT an irreconcilable contradiction)
    IRRECONCILABLE_CONTRADICTION = "irreconcilable_contradiction" # True established contradiction under confirmed applicable context (intra-doc or confirmed co-applicable)


class MetadataProvenance(BaseModel):
    field_name: str                                     # e.g. "document_title", "execution_date", "integration_clause"
    extracted_value: str
    exact_quote: str
    char_start: int
    char_end: int
    doc_id: str


class DocumentVersionMeta(BaseModel):
    doc_id: str
    doc_name: str
    document_title: str
    document_role: DocumentRole = DocumentRole.SINGLE_DOCUMENT
    title_provenance: Optional[MetadataProvenance] = None
    execution_date: Optional[str] = None
    execution_date_provenance: Optional[MetadataProvenance] = None
    effective_date: Optional[str] = None
    effective_date_provenance: Optional[MetadataProvenance] = None
    parties_named: List[str] = Field(default_factory=list)
    parties_provenance: List[MetadataProvenance] = Field(default_factory=list)
    execution_status: ExecutionStatus = ExecutionStatus.UNDATED
    signature_provenance: Optional[MetadataProvenance] = None
    referenced_agreements: List[Dict[str, str]] = Field(default_factory=list)
    referenced_agreements_provenance: List[MetadataProvenance] = Field(default_factory=list)
    has_integration_clause: bool = False
    integration_clause_text: Optional[str] = None
    integration_clause_provenance: Optional[MetadataProvenance] = None


class ClauseEvidence(BaseModel):
    doc_id: str
    doc_name: str
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    exact_quote: str
    char_start: int
    char_end: int
    extracted_value: Optional[str] = None
    obligated_party: PartyRole = PartyRole.UNSPECIFIED
    beneficiary_party: PartyRole = PartyRole.UNSPECIFIED
    trigger_type: LegalTriggerType = LegalTriggerType.UNCLASSIFIED  # Strict default!
    trigger_uncertainty_note: Optional[str] = None                 # Preserves legal uncertainty


class ComparisonDifferenceItem(BaseModel):
    difference_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dimension: str                         # e.g. "TERMINATION_NOTICE", "PAYMENT_FINANCIAL"
    trigger_type: LegalTriggerType = LegalTriggerType.UNCLASSIFIED
    change_type: ChangeType                # Independent: MODIFICATION, ADDITION, OMITTED_UNMODIFIED, POTENTIAL_CONFLICT_UNVERIFIED, etc.
    materiality: MaterialityLevel          # Independent: MATERIAL, NON_MATERIAL
    title: str
    doc_a_clause: Optional[ClauseEvidence] = None
    doc_b_clause: Optional[ClauseEvidence] = None
    reconciliation_status: ReconciliationStatus
    reconciliation_explanation: str
    bounded_textual_impact: str            # Strictly bounded to textual/operational duties; NO litigation tactics
    uncertainty_disclosure: Optional[str] = None # Discloses trigger/interpretive uncertainty
    non_definitive_guidance: str = "Please verify which version governs your situation."


class ContradictionDiagnosticItem(BaseModel):
    contradiction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    trigger_type: LegalTriggerType
    actor_role: PartyRole
    provision_a: ClauseEvidence
    provision_b: ClauseEvidence
    conflict_analysis: str
    why_unreconciled: str
    co_applicability_context: Optional[str] = None # e.g. "Confirmed co-applicable agreements with no order-of-precedence clause"
    non_definitive_guidance: str = (
        "Potential internal inconsistency: Within the confirmed operative document context, "
        "these provisions specify conflicting mandates under the same conditions. "
        "Please verify which provision applies with a qualified legal professional."
    )


class ComparisonRequest(BaseModel):
    doc_id_a: str
    doc_id_b: Optional[str] = None         # If None, evaluates intra-document contradictions in doc_id_a
    focus_dimension: Optional[str] = None  # Optional dimension filter
    user_situation: Optional[str] = None   # Optional narrative context
    operational_mode: str = "mode_1_doc_only"
    co_applicable_override: Optional[bool] = None # Affirmatively declare co-applicable concurrent agreements


class ComparisonResult(BaseModel):
    comparison_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_a_meta: DocumentVersionMeta
    doc_b_meta: Optional[DocumentVersionMeta] = None
    relationship_status: DocumentRelationshipStatus
    summary_of_changes: str
    total_differences_analyzed: int = 0
    material_modifications_count: int = 0
    true_contradictions_count: int = 0         # ONLY increments for established true contradictions (0 for unverified relationship!)
    unverified_conflicts_count: int = 0        # Increments for conflicting provisions across unverified relationship
    additions_count: int = 0
    omitted_unmodified_count: int = 0
    omitted_from_restatement_count: int = 0
    express_deletions_count: int = 0
    differences: List[ComparisonDifferenceItem] = Field(default_factory=list)
    contradictions: List[ContradictionDiagnosticItem] = Field(default_factory=list) # Only contains confirmed true contradictions
    non_definitive_advisory: str = (
        "This comparison analyzes textual and operational differences between the provided documents. "
        "The system does not provide legal representation, nor does it adjudicate which provision legally controls. "
        "Please verify execution dates, signatures, and governing priority with a qualified legal professional."
    )


# Backwards compatibility aliases
ClauseDiff = ComparisonDifferenceItem
DocumentComparison = ComparisonResult

