from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    TENANT = "tenant"
    LANDLORD = "landlord"
    EMPLOYEE = "employee"
    EMPLOYER = "employer"
    CUSTOMER = "customer"
    SERVICE_PROVIDER = "service_provider"
    BORROWER = "borrower"
    LENDER = "lender"
    BUYER = "buyer"
    SELLER = "seller"
    GENERAL = "general"


class RoleResolutionStatus(str, Enum):
    DECLARED_BY_USER = "declared_by_user"                  # Explicitly selected by user
    INFERRED_HIGH_CONFIDENCE = "inferred_high_confidence"  # Clear semantic relationship (>= 0.85)
    INFERRED_LOW_CONFIDENCE = "inferred_low_confidence"    # Ambiguous signals (< 0.85)
    UNRESOLVED_CONFLICT = "unresolved_conflict"            # Declared role conflicts with narrative
    ROLE_NEUTRAL = "role_neutral"                          # General or fallback without bias


class FactStatus(str, Enum):
    USER_ASSERTED = "user_asserted"                  # Stated by user, unverified externally
    NOT_STATED = "not_stated"                        # Material factual predicate unstated
    DOCUMENT_SUPPORTED = "document_supported"        # Matches contract clause text
    DOCUMENT_CONTRADICTED = "document_contradicted"  # In direct tension with contract clause
    UNRESOLVED = "unresolved"                        # Inconclusive alignment


class DiscrepancyType(str, Enum):
    DIFFERENCE = "difference"                      # Variance without direct conflict
    POTENTIAL_CONFLICT = "potential_conflict"      # Stated demand departs from standard covenant
    CONTRADICTION = "contradiction"                # Incompatible claims
    INSUFFICIENT_INFORMATION = "insufficient_information"


class TimelineAnchor(BaseModel):
    """Normalized temporal entity with provenance tracking."""
    raw_value: str
    normalized_value: Optional[str] = None
    event_type: str  # "notice_period", "lock_in_duration", "commencement_date"
    source: str = "user_assertion"  # "user_assertion" | "uploaded_document"
    confidence: float = 1.0


class FinancialEntity(BaseModel):
    """Financial amount with strict source tracking."""
    raw_value: str
    numeric_amount: Optional[float] = None
    currency: Optional[str] = "INR"
    item_type: str = "rent"  # "rent", "security_deposit", "late_fee", "repair_cap"
    source: str = "user_assertion"  # "user_assertion" | "uploaded_document" | "both"
    confidence: float = 1.0


class SituationFactItem(BaseModel):
    """An asserted or evaluated situation fact with turn-based supersession."""
    fact_id: str
    assertion_text: str
    fact_status: FactStatus = FactStatus.USER_ASSERTED
    turn_index: int = 1
    is_superseded: bool = False
    superseded_by: Optional[str] = None
    superseded_reason: Optional[str] = None


class UserSituation(BaseModel):
    """User-provided subjective situation context."""
    raw_description: str = Field(
        ...,
        description="The user's description of what is happening in their own natural language."
    )
    declared_role: Optional[UserRole] = Field(
        default=None,
        description="User's role if explicitly selected or confirmed."
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="User-stated jurisdiction (city, state, country) if specified."
    )
    turn_index: int = 1
    previous_assertions: List[str] = Field(default_factory=list)


class SituationAnalysis(BaseModel):
    """Extracted situation entities, semantic roles, and fact-covenant alignments."""
    declared_role: Optional[UserRole] = None
    inferred_role: UserRole = Field(
        default=UserRole.GENERAL,
        description="Role inferred from context or semantic transaction."
    )
    role_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    role_evidence: Optional[str] = Field(
        default=None,
        description="Semantic excerpt justifying role inference."
    )
    role_resolution_status: RoleResolutionStatus = RoleResolutionStatus.ROLE_NEUTRAL
    counterparty_role: Optional[UserRole] = None
    counterparty_name: Optional[str] = None
    stated_facts: List[SituationFactItem] = Field(default_factory=list)
    timeline_anchors: List[TimelineAnchor] = Field(default_factory=list)
    financial_elements: List[FinancialEntity] = Field(default_factory=list)
    core_legal_topic: str = Field(default="general")
    discrepancy_signals: List[Dict[str, Any]] = Field(default_factory=list)
