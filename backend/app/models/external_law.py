from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LegalSourceType(str, Enum):
    ACT_PRIMARY_LEGISLATION = "act_primary_legislation"
    RULE_REGULATION = "rule_regulation"
    GOVERNMENT_NOTIFICATION = "government_notification"
    OFFICIAL_GAZETTE = "official_gazette"
    COURT_JUDGMENT = "court_judgment"


class SourceCurrencyStatus(str, Enum):
    IN_FORCE = "in_force"
    AMENDED = "amended"
    REPEALED = "repealed"
    SUPERSEDED = "superseded"
    SOURCE_CURRENTNESS_UNVERIFIED = "source_currentness_unverified"


class FailureUncertaintyState(str, Enum):
    # Full Abstention States
    JURISDICTION_MISSING = "jurisdiction_missing"
    AUTHORITATIVE_SOURCE_NOT_FOUND = "authoritative_source_not_found"
    SOURCE_CURRENTNESS_UNVERIFIED = "source_currentness_unverified"
    INSUFFICIENT_DOCUMENT_CONTEXT = "insufficient_document_context"
    # Flag and Continue Cautiously States
    JURISDICTION_CONFLICT = "jurisdiction_conflict"
    LEGAL_APPLICABILITY_UNCERTAIN = "legal_applicability_uncertain"
    CONFLICTING_AUTHORITIES = "conflicting_authorities"


class HandlingMode(str, Enum):
    ABSTAIN = "abstain"
    FLAG_AND_CONTINUE = "flag_and_continue"


class PrecedentialScope(str, Enum):
    NATIONAL_SUPREME_COURT = "national_supreme_court"  # Binding nationwide under Art 141 (India)
    STATE_TERRITORIAL_HIGH_COURT = "state_territorial_high_court"  # Precedential within state jurisdiction
    PERSUASIVE_OTHER_HIGH_COURT = "persuasive_other_high_court"    # Persuasive authority
    DISTINGUISHED_PRECEDENT = "distinguished_precedent"
    OVERRULED_PRECEDENT = "overruled_precedent"
    UNVERIFIED_SCOPE = "unverified_scope"


class JurisdictionSignal(BaseModel):
    """Signal indicating jurisdiction origin and evidence."""
    signal_source: str  # "query", "document", "user_situation"
    jurisdiction_value: str
    evidence_text: Optional[str] = None
    confidence: float = 1.0


class AuthoritativeLegalSource(BaseModel):
    """
    Verified primary statute, rule, notification, or gazette record.
    Currency and metadata MUST represent a verified source record, not LLM inference.
    """
    source_id: str
    jurisdiction: str                       # e.g., "India", "Karnataka, India"
    source_type: LegalSourceType
    title: str                              # e.g., "The Indian Contract Act, 1872"
    issuing_authority: str                  # e.g., "Legislative Department, Ministry of Law and Justice, Government of India"
    section_provision: str                  # e.g., "Section 27"
    provision_title: Optional[str] = None   # e.g., "Agreement in restraint of trade, void"
    official_url: str                       # e.g., "https://www.indiacode.nic.in/handle/123456789/2187"
    retrieval_date: str                     # ISO date string e.g., "2026-09-22"
    enactment_date: Optional[str] = None    # e.g., "1872-04-25"
    effective_date: Optional[str] = None    # e.g., "1872-09-01"
    last_amendment_date: Optional[str] = None  # e.g., "2018-05-04"
    currentness_status: SourceCurrencyStatus
    verification_status: str                # e.g., "verified_official_record"
    exact_retrieved_text: str               # Verbatim statutory text
    source_locator_version_info: str        # e.g., "Act No. 9 of 1872 as modified up to 1st September 2024"
    provenance_notes: str                   # Reference record provenance
    is_authoritative: bool = True


class JudicialPrecedentSource(BaseModel):
    """
    Verified judicial decision interpreting statutory provisions.
    Precedential scope and status MUST be verified from official registry records.
    """
    precedent_id: str
    case_name: str                          # e.g., "Percept D'Mark (India) (P) Ltd. v. Zaheer Khan"
    court: str                              # e.g., "Supreme Court of India"
    court_level: str                        # "Apex Court / Supreme Court"
    decision_date: str                      # e.g., "2006-03-22"
    citation: str                           # e.g., "(2006) 4 SCC 227"
    bench_strength: Optional[str] = None    # e.g., "Division Bench (2 Judges)"
    binding_status: str                     # "Binding nationwide under Art. 141 Constitution of India"
    precedential_scope: PrecedentialScope
    status_verification: str                # "Verified from official Supreme Court of India law reports"
    relevant_provision: str                 # e.g., "Section 27, Indian Contract Act, 1872"
    relevant_paragraph_section: str         # e.g., "Paragraphs 56-64"
    verbatim_excerpt: str
    discussion_summary: str                 # Objective judicial analysis without declaring conclusions
    official_registry_url: Optional[str] = None
    provenance_notes: str                   # Reference provenance


class DocumentLawRelationship(BaseModel):
    """Structured neutral 4-stage comparison between private agreement and public law."""
    document_clause_ref: str
    document_clause_text: str
    statutory_provision_ref: str
    statutory_provision_text: str
    judicial_discussion: Optional[str] = None
    factors_and_uncertainties: List[str] = Field(default_factory=list)
    relationship_explanation: str
