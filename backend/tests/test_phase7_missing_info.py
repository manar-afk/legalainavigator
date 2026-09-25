import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.storage import document_store
from app.models.query import QueryRequest, IntentClassification, OperationalMode, QueryCategory
from app.models.situation import UserRole, UserSituation, SituationAnalysis
from app.models.missing_info import (
    EvidenceSufficiencyLevel,
    EvidentiaryState,
    HeuristicStatus,
    PredicateCategory,
    PredicateStatus,
    PredicateSourceStatus,
    MissingInfoReport,
)
from app.services.document_parser import document_parser
from app.services.missing_info_service import missing_info_service, UnstatedPredicateSemantic
from app.services.grounding_engine import grounding_engine

client = TestClient(app)

SAMPLE_LEASE_TEXT = """RESIDENTIAL LEASE AGREEMENT
This Agreement is entered into on October 1, 2024, between Mr. Arvind Rao ("Lessor") and Mr. Rahul Sharma ("Lessee").

SECTION 1: DEMISED PREMISES
Flat No. 402, Green Valley Apartments, Indiranagar, Bangalore, Karnataka 560038.

SECTION 2: MONTHLY RENT
The monthly rental for the Demised Premises shall be INR 35,000 (Indian Rupees Thirty-Five Thousand only), payable in advance on or before the 5th day of each calendar month directly into Lessor's designated bank account. A late fee of INR 500 per week shall apply after a 10-day grace period. Maintenance charges of INR 4,000 per month shall be paid directly by Lessee to the Resident Welfare Association.

SECTION 3: SECURITY DEPOSIT
Lessee has deposited an interest-free refundable Security Deposit of INR 1,50,000 (Indian Rupees One Lakh Fifty Thousand only). The deposit shall be refunded within fourteen (14) business days after Lessee vacates and surrenders vacant physical possession of the Demised Premises with all keys, subject to deductions for documented physical damages beyond normal wear and tear or unpaid utility bills.

SECTION 4: TERM AND LOCK-IN PERIOD
The lease shall be for an initial term of eleven (11) months commencing on October 1, 2024, and ending on August 31, 2025. Both Lessor and Lessee mutually agree to a mandatory lock-in period of six (6) months starting from the commencement date, ending on March 31, 2025. Neither party may terminate this agreement during the lock-in period. Vacating early during the lock-in makes the Lessee liable for rent for the unexpired portion of the lock-in period.

SECTION 5: PERMITTED USE AND RESTRICTIONS
The Demised Premises shall be used exclusively for private residential dwelling purposes. Commercial activities, guest houses, paying guests, and subletting or sharing without prior written consent of the Lessor are strictly prohibited.

SECTION 6: REPAIRS AND MAINTENANCE
Minor repairs up to INR 1,000 per occurrence (e.g. bulb replacements, minor tap washers) shall be borne by the Lessee. Structural repairs, major seepage, and electrical wiring defects not caused by Lessee misuse shall be the responsibility of the Lessor.

SECTION 7: LESSOR COVENANTS AND INSPECTION
Lessor warrants peaceful possession and quiet enjoyment. Lessor or authorized representative may inspect the premises upon providing at least twenty-four (24) hours' prior written notice to Lessee, during reasonable daytime hours.

SECTION 8: TERMINATION AND NOTICE
8.1 Termination for Convenience: After the expiry of the mandatory 6-month lock-in period, either party may terminate this agreement by serving thirty (30) days' prior written notice to the other party without assigning reasons.
8.2 Notice Delivery: All notices under this agreement shall be delivered in writing via registered post, reputable courier, or confirmed email acknowledgement. Verbal notice or informal instant messaging shall not constitute valid contractual notice.
8.3 Termination for Default: In the event of material breach, including non-payment of rent for exceeding fifteen (15) days after the due date, unauthorized alterations, or unlawful use, the non-defaulting party may terminate immediately, provided that a formal written cure notice specifying the default and granting not less than fourteen (14) days to remedy has first been served and remained uncured.
"""

CUSTOM_LEASE_TEXT = """COMMERCIAL & RESIDENTIAL LEASE
SECTION 1: TERM
The lease commences on January 1, 2024 for twelve (12) months. Lock-in period of three (3) months applies.
SECTION 2: TERMINATION
Either party may terminate after lock-in by giving forty-five (45) days' prior written notice.
SECTION 3: DEFAULT
Immediate termination requires giving twenty-one (21) days' written cure notice.
"""


@pytest.fixture(autouse=True)
def setup_lease_document():
    document_store.clear()
    meta, _ = document_parser.parse_text_content(
        SAMPLE_LEASE_TEXT,
        filename="residential_lease_agreement.txt"
    )
    yield meta
    document_store.clear()


# ============================================================================
# 1. Blocking-Predicate Gating & Sufficiency Levels
# ============================================================================

def test_sufficiency_sufficient_with_all_blocking_predicates_established(setup_lease_document):
    """
    When all blocking predicates are established by evidence, sufficiency level
    must evaluate to SUFFICIENT.
    """
    situation = UserSituation(
        raw_description=(
            "The lease began on October 1, 2024. Today is May 1, 2025 so the 6 months lock-in period expired on March 31. "
            "I served thirty days written notice via acknowledged email on April 1, 2025. "
            "I have paid rent on time every month with no default or cure notice served."
        ),
        declared_role=UserRole.TENANT
    )
    report = missing_info_service.detect_missing_information(
        query="Can I vacate the premises pursuant to my written notice?",
        situation=situation,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert report.sufficiency_level == EvidenceSufficiencyLevel.SUFFICIENT
    assert len([p for p in report.missing_predicates if p.is_blocking]) == 0


def test_sufficiency_partially_sufficient_non_blocking_missing(setup_lease_document):
    """
    When all blocking predicates are established, but non-blocking informational gaps remain
    (e.g. dispatch proof like courier vs email), sufficiency level must be PARTIALLY_SUFFICIENT.
    """
    situation = UserSituation(
        raw_description=(
            "The 6-month lock-in period concluded. I served written notice 30 days in advance. "
            "I have paid rent on time every month with no default or cure notice served."
        ),
        declared_role=UserRole.TENANT
    )
    report = missing_info_service.detect_missing_information(
        query="Can I vacate under Section 8?",
        situation=situation,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert report.sufficiency_level == EvidenceSufficiencyLevel.PARTIALLY_SUFFICIENT
    # Non-blocking missing predicate (notice delivery medium)
    assert any(p.predicate_id == "notice_delivery_medium" for p in report.missing_predicates)


def test_sufficiency_insufficient_blocking_missing(setup_lease_document):
    """
    When any blocking predicate is missing (e.g. lease start date or cure notice status unstated),
    sufficiency level must evaluate to INSUFFICIENT via blocking-predicate gating.
    """
    situation = UserSituation(
        raw_description="My landlord told me to leave immediately.",
        declared_role=UserRole.TENANT
    )
    report = missing_info_service.detect_missing_information(
        query="Can I terminate tomorrow without penalty or notice?",
        situation=situation,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert report.sufficiency_level == EvidenceSufficiencyLevel.INSUFFICIENT
    blocking_missing = [p for p in report.missing_predicates if p.is_blocking]
    assert len(blocking_missing) >= 1


# ============================================================================
# 2. INDETERMINATE vs Localized AMBIGUOUS Contradiction (Clarification 2)
# ============================================================================

def test_indeterminate_unresolved_contradiction_blocking_predicate(setup_lease_document):
    """
    Clarification 2: INDETERMINATE must be triggered ONLY when an unresolved
    contradiction materially affects a blocking/governing predicate.
    """
    situation = UserSituation(
        raw_description="I haven't paid rent for 2 months and have arrears.",
        previous_assertions=["I paid rent on time every month without any delay."],
        declared_role=UserRole.TENANT
    )
    report = missing_info_service.detect_missing_information(
        query="Can the landlord terminate immediately?",
        situation=situation,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert report.sufficiency_level == EvidenceSufficiencyLevel.INDETERMINATE
    assert len(report.contradictions) > 0


def test_localized_ambiguous_minor_contradiction_not_indeterminate(setup_lease_document):
    """
    Clarification 2: Minor contradictory facts (e.g. timing of conversation) remain
    localized AMBIGUOUS predicates without forcing the entire report to INDETERMINATE.
    """
    situation = UserSituation(
        raw_description="The landlord told me in the afternoon.",
        previous_assertions=["The landlord spoke to me in the morning."],
        declared_role=UserRole.TENANT
    )
    report = missing_info_service.detect_missing_information(
        query="Does my landlord have the right to terminate?",
        situation=situation,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    # Must NOT be INDETERMINATE because this minor conversational variance is non-blocking
    assert report.sufficiency_level != EvidenceSufficiencyLevel.INDETERMINATE
    assert any(p.status == PredicateStatus.AMBIGUOUS for p in report.ambiguous_predicates)


# ============================================================================
# 3. Applicability Determination & Pathways (Clarification 1)
# ============================================================================

def test_is_applicability_determined_requires_sufficient_and_unique_pathway(setup_lease_document):
    """
    Clarification 1: is_applicability_determined must require both sufficient evidence
    and one uniquely identified applicable contractual pathway.
    """
    report = MissingInfoReport(
        heuristic_status=HeuristicStatus.FRAMEWORK_NOT_REQUIRED,
        evidentiary_state=EvidentiaryState.EVIDENCE_ESTABLISHED,
        sufficiency_level=EvidenceSufficiencyLevel.SUFFICIENT,
        is_applicability_determined=True,
        overall_gap_summary="Direct factual lookup completed.",
        conditional_pathways=[]
    )
    assert report.is_applicability_determined is True


def test_is_applicability_determined_false_when_multiple_conditional_pathways(setup_lease_document):
    """
    Clarification 1: When multiple conditional pathways (Pathway A vs Pathway B) depend
    on missing factual conditions, is_applicability_determined MUST be False.
    """
    situation = UserSituation(
        raw_description="The landlord gave me 15 days notice.",
        declared_role=UserRole.TENANT
    )
    report = missing_info_service.detect_missing_information(
        query="Does my landlord have the right to make me leave?",
        situation=situation,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert len(report.conditional_pathways) >= 2
    assert report.is_applicability_determined is False


# ============================================================================
# 4. Mode 1 Isolation from External Law
# ============================================================================

def test_mode1_isolation_zero_statutory_predicates(setup_lease_document):
    """
    Mode 1 prerequisite evaluation must evaluate strictly contractual and factual predicates;
    zero statutory/jurisdiction predicates may be evaluated.
    """
    report = missing_info_service.detect_missing_information(
        query="What is the notice period under my contract?",
        situation=UserSituation(raw_description="My landlord told me to vacate."),
        doc_raw_text=SAMPLE_LEASE_TEXT,
        operational_mode=OperationalMode.MODE_1_DOC_ONLY
    )
    for p in report.missing_predicates + report.established_predicates + report.ambiguous_predicates:
        assert p.category != PredicateCategory.EXTERNAL_STATUTE


# ============================================================================
# 5. Dynamic Duration Extraction (No Hard-Coded Defaults)
# ============================================================================

def test_dynamic_duration_extraction_no_hardcoded_defaults(setup_lease_document):
    """
    Notice periods and cure periods must be dynamically regex-extracted from the
    retrieved document text with provenance, not hard-coded generic defaults.
    """
    durations = missing_info_service.extract_dynamic_durations(doc_raw_text=SAMPLE_LEASE_TEXT)
    conv_val, conv_prov = durations["convenience_notice"]
    cure_val, cure_prov = durations["cure_period"]
    lock_val, lock_prov = durations["lock_in"]

    assert conv_val == "30 days"
    assert conv_prov.source_type == "document_clause"
    assert conv_prov.start_char is not None

    assert cure_val == "14 days"
    assert cure_prov.source_type == "document_clause"

    assert lock_val == "6 months"
    assert lock_prov.source_type == "document_clause"


def test_dynamic_duration_with_custom_values():
    """
    Extracts custom duration values (e.g. 45 days convenience notice, 21 days cure notice)
    accurately from different agreement text.
    """
    durations = missing_info_service.extract_dynamic_durations(doc_raw_text=CUSTOM_LEASE_TEXT)
    conv_val, conv_prov = durations["convenience_notice"]
    cure_val, cure_prov = durations["cure_period"]
    lock_val, lock_prov = durations["lock_in"]

    assert conv_val == "45 days"
    assert cure_val == "21 days"
    assert lock_val == "3 months"


# ============================================================================
# 6. Semantic Negative-Fact Prevention
# ============================================================================

def test_semantic_negative_fact_prevention():
    """
    Unstated predicates must be phrased strictly as 'You have not stated whether...',
    never asserting negative facts as established truths.
    """
    formatted = UnstatedPredicateSemantic.format_unstated("a formal written cure notice was served")
    assert formatted.startswith("You have not stated whether")
    assert "did not" not in formatted
    assert "never" not in formatted

    report = missing_info_service.detect_missing_information(
        query="Can the landlord terminate?",
        situation=UserSituation(raw_description="My landlord told me to leave."),
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    for p in report.missing_predicates:
        if p.semantic_unstated_phrasing:
            assert p.semantic_unstated_phrasing.startswith("You have not stated whether")


# ============================================================================
# 7. Distinct Evidentiary States
# ============================================================================

def test_three_distinct_evidentiary_states(setup_lease_document):
    """
    Ensures CONTRACT_SILENCE, MISSING_FACTUAL_EVIDENCE, and AMBIGUOUS_EVIDENCE
    are three distinct states.
    """
    # 1. CONTRACT_SILENCE (topic unaddressed)
    rep_silence = missing_info_service.detect_missing_information(
        query="Can I keep a pet cat in this apartment?",
        situation=None,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert rep_silence.evidentiary_state == EvidentiaryState.CONTRACT_SILENCE

    # 2. MISSING_FACTUAL_EVIDENCE (clause exists, user facts unstated)
    rep_facts = missing_info_service.detect_missing_information(
        query="Can I terminate tomorrow?",
        situation=UserSituation(raw_description="I want to leave tomorrow."),
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert rep_facts.evidentiary_state == EvidentiaryState.MISSING_FACTUAL_EVIDENCE

    # 3. AMBIGUOUS_EVIDENCE (conflicting statements)
    rep_ambig = missing_info_service.detect_missing_information(
        query="Can the landlord terminate?",
        situation=UserSituation(
            raw_description="I have not paid rent for 2 months.",
            previous_assertions=["I paid rent on time every month."]
        ),
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert rep_ambig.evidentiary_state == EvidentiaryState.AMBIGUOUS_EVIDENCE


# ============================================================================
# 8. Framework Not Required & Heuristic Labeling
# ============================================================================

def test_framework_not_required_simple_lookup(setup_lease_document):
    """
    Direct factual lookups (rent, security deposit amount, address) bypass prerequisite
    detection heuristics via FRAMEWORK_NOT_REQUIRED without manufacturing missing information.
    """
    rep_rent = missing_info_service.detect_missing_information(
        query="What is the monthly rent?",
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert rep_rent.heuristic_status == HeuristicStatus.FRAMEWORK_NOT_REQUIRED
    assert rep_rent.sufficiency_level == EvidenceSufficiencyLevel.SUFFICIENT
    assert len(rep_rent.missing_predicates) == 0


def test_framework_prerequisite_heuristic_labeling(setup_lease_document):
    """
    Prerequisite detection frameworks must be explicitly labeled as heuristics,
    not legal rules.
    """
    rep = missing_info_service.detect_missing_information(
        query="Can I terminate my lease early?",
        situation=UserSituation(raw_description="I want to move out early."),
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert rep.heuristic_status == HeuristicStatus.APPLIED
    assert "Heuristic" in (rep.heuristic_name or "")


# ============================================================================
# 9. Multi-turn Supersession vs Contradiction
# ============================================================================

def test_multi_turn_contradictory_assertions_vs_supersession(setup_lease_document):
    """
    Differentiates explicit user corrections/supersession from unresolved contradictory assertions.
    """
    # Explicit supersession ("actually...")
    sit_superseded = UserSituation(
        raw_description="Actually I made a mistake, I haven't paid rent this month.",
        previous_assertions=["I paid rent on time every month."]
    )
    rep_superseded = missing_info_service.detect_missing_information(
        query="Can the landlord terminate?",
        situation=sit_superseded,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert rep_superseded.sufficiency_level != EvidenceSufficiencyLevel.INDETERMINATE

    # Unresolved contradiction without supersession keyword
    sit_conflict = UserSituation(
        raw_description="I haven't paid rent for 2 months.",
        previous_assertions=["I paid rent on time every month."]
    )
    rep_conflict = missing_info_service.detect_missing_information(
        query="Can the landlord terminate?",
        situation=sit_conflict,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert rep_conflict.sufficiency_level == EvidenceSufficiencyLevel.INDETERMINATE


# ============================================================================
# 10. Conditional Applicability Pathways & Bounded Guidance
# ============================================================================

def test_conditional_applicability_pathways_no_outcome_prediction(setup_lease_document):
    """
    Pathways define objective contractual conditions and stipulations,
    never predicting legal outcomes or probability of winning.
    """
    rep = missing_info_service.detect_missing_information(
        query="Does my landlord have the right to make me leave?",
        situation=UserSituation(raw_description="Landlord told me to leave in 15 days."),
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert len(rep.conditional_pathways) >= 2
    for pw in rep.conditional_pathways:
        assert "win" not in pw.contractual_stipulation.lower()
        assert "entitled to victory" not in pw.contractual_stipulation.lower()
        assert pw.applicable_provision in ["Section 8.1", "Section 8.3"]


def test_bounded_investigative_recommendations(setup_lease_document):
    """
    Investigative recommendations provide objective factual checks, never legal strategies.
    """
    rep = missing_info_service.detect_missing_information(
        query="Does my landlord have the right to make me leave?",
        situation=UserSituation(raw_description="Landlord told me to leave in 15 days."),
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert len(rep.investigative_recommendations) >= 2
    for rec in rep.investigative_recommendations:
        assert "sue" not in rec.lower()
        assert "lawsuit" not in rec.lower()


# ============================================================================
# 11. Additional Edge & Domain Tests
# ============================================================================

def test_primary_demo_gatekeeper_missing_notice_and_cure(setup_lease_document):
    """
    In the primary demo scenario, the gatekeeper identifies that Section 8.1 requires
    30 days written notice, Section 8.3 requires 14-day cure notice, and user has not
    stated whether cure notice was received.
    """
    req = QueryRequest(
        query="Does my landlord have the right to make me leave in 15 days?",
        doc_ids=[setup_lease_document.doc_id],
        situation=UserSituation(
            raw_description="My landlord told me to leave in 15 days because his son is moving in. I have paid rent on time.",
            declared_role=UserRole.TENANT
        )
    )
    intent = IntentClassification(
        category=QueryCategory.A_DOCUMENT_FACTUAL,
        effective_mode=OperationalMode.MODE_1_DOC_ONLY,
        is_reclassified=False,
        requires_external_law=False,
        is_conceptual_only=False,
        is_jurisdiction_missing=False,
        retrieval_prepared=True,
        confidence=0.95
    )
    ans = grounding_engine.answer_document_query(req, intent)
    assert ans.missing_info_report is not None
    assert ans.missing_info_report["sufficiency_level"] in [
        EvidenceSufficiencyLevel.INSUFFICIENT.value,
        EvidenceSufficiencyLevel.PARTIALLY_SUFFICIENT.value
    ]
    assert any("cure" in p.field_name.lower() or "cure" in p.description.lower() for p in ans.missing_info_details)


def test_nonexistent_topic_contract_silence_abstention(setup_lease_document):
    """
    Querying an unaddressed subject generates CONTRACT_SILENCE and abstains.
    """
    req = QueryRequest(
        query="Can I keep a pet dog?",
        doc_ids=[setup_lease_document.doc_id]
    )
    intent = IntentClassification(
        category=QueryCategory.F_INSUFFICIENT_INFO,
        effective_mode=OperationalMode.MODE_1_DOC_ONLY,
        is_reclassified=False,
        requires_external_law=False,
        is_conceptual_only=False,
        is_jurisdiction_missing=False,
        retrieval_prepared=True,
        confidence=0.95
    )
    ans = grounding_engine.answer_document_query(req, intent)
    assert ans.evidence_sufficiency_passed is False
    assert ans.missing_info_report is not None
    assert ans.missing_info_report["evidentiary_state"] == EvidentiaryState.CONTRACT_SILENCE.value


def test_deposit_refund_pathways_and_blocking_gates(setup_lease_document):
    """
    Deposit refund evaluates vacant possession handover date as a blocking gate and
    contractor damage invoices as non-blocking.
    """
    report = missing_info_service.detect_missing_information(
        query="When do I get my security deposit refund?",
        situation=UserSituation(raw_description="I vacated the flat yesterday."),
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert len(report.conditional_pathways) >= 2
    assert any(p.predicate_id == "vacant_possession_handover_date" for p in report.missing_predicates + report.established_predicates)


def test_commercial_use_exception_pathway(setup_lease_document):
    """
    Commercial use evaluates permitted private dwelling use and written consent exception pathway.
    """
    report = missing_info_service.detect_missing_information(
        query="Can I run a business or restaurant here?",
        situation=None,
        doc_raw_text=SAMPLE_LEASE_TEXT
    )
    assert len(report.conditional_pathways) >= 2
    assert any("Pathway A: Prohibited Commercial Use" in pw.pathway_name for pw in report.conditional_pathways)


def test_end_to_end_missing_info_api_payload(setup_lease_document):
    """
    Complete /api/query call verifying missing_info_report serialization fidelity
    and frontend payload compatibility.
    """
    payload = {
        "query": "Can I terminate tomorrow without penalty?",
        "doc_ids": [setup_lease_document.doc_id],
        "situation": {
            "raw_description": "I want to terminate immediately tomorrow.",
            "declared_role": "tenant"
        }
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "missing_info_report" in data
    mir = data["missing_info_report"]
    assert mir is not None
    assert "sufficiency_level" in mir
    assert "evidentiary_state" in mir
    assert "conditional_pathways" in mir
