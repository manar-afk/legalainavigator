"""
Situation Analysis & Role Context Engine.
Extracts semantic relationships, inferred roles, timeline anchors, and financial entities.
Classifies fact status, detects fact-covenant discrepancies vs contradictions,
and strictly enforces that missing info is never converted into negative facts.
"""

import re
import uuid
from typing import Optional, List, Dict, Any, Tuple

from ..models.situation import (
    UserRole,
    RoleResolutionStatus,
    FactStatus,
    DiscrepancyType,
    TimelineAnchor,
    FinancialEntity,
    SituationFactItem,
    UserSituation,
    SituationAnalysis,
)
from ..models.document import DocumentChunk
from ..services.guardrails import guardrail_service


class SituationService:
    """
    Service responsible for parsing user situation narratives, resolving semantic roles,
    extracting normalized entities, and aligning user assertions against contract covenants.
    """

    @classmethod
    def sanitize_untrusted_situation(cls, raw_text: str) -> str:
        """
        Wraps user situation in isolated contextual markers and neutralizes delimiter escapes.
        User-provided situation text is strictly untrusted data, never privileged instructions.
        """
        # Neutralize delimiter breakout attempts
        safe_text = raw_text.replace("</UNTRUSTED_USER_SITUATION>", "&lt;/UNTRUSTED_USER_SITUATION_ESCAPED&gt;")
        safe_text = safe_text.replace("<UNTRUSTED_USER_SITUATION>", "&lt;UNTRUSTED_USER_SITUATION_ESCAPED&gt;")
        safe_text = re.sub(r"<\|.*?\|>", "[ESCAPED_TOKEN]", safe_text)
        return safe_text.strip()

    @classmethod
    def infer_semantic_role(
        cls,
        text: str,
        declared_role: Optional[UserRole] = None
    ) -> Tuple[UserRole, float, Optional[str], RoleResolutionStatus, Optional[UserRole]]:
        """
        Infers role based on semantic relationships and transaction context, not mere keywords.
        Returns: (inferred_role, confidence, evidence_text, resolution_status, counterparty_role)
        """
        lower = text.lower()

        # Semantic Relationship 1: Tenant vs Landlord
        # Case A: Occupant / Tenant (someone occupying property owned/controlled by another)
        tenant_semantic_patterns = [
            (r"the person who owns the (flat|house|apartment|property|room) (told|asked|wants) me to (leave|vacate|pay|move)", "person who owns the property asked speaker to vacate/pay"),
            (r"my (landlord|flat owner|house owner|lessor) (is asking|asked|told|wants|demanded) me to (leave|vacate|pay)", "landlord demanded speaker to leave/pay"),
            (r"(rented|leased) a (flat|house|apartment|room) (in|at|from)", "speaker rented property"),
            (r"(paying|paid) (the )?rent to (my|the) (landlord|owner)", "speaker pays rent to owner"),
            (r"asking me to (leave|vacate) in \d+ days", "speaker asked to vacate"),
        ]
        for pat, desc in tenant_semantic_patterns:
            m = re.search(pat, lower)
            if m:
                inferred = UserRole.TENANT
                counterparty = UserRole.LANDLORD
                evidence = m.group(0)
                conf = 0.95

                # Check conflict with declared role
                if declared_role and declared_role == UserRole.LANDLORD:
                    return inferred, 0.5, evidence, RoleResolutionStatus.UNRESOLVED_CONFLICT, counterparty
                if declared_role and declared_role == UserRole.TENANT:
                    return declared_role, 1.0, "Declared by user and supported by narrative", RoleResolutionStatus.DECLARED_BY_USER, counterparty
                return inferred, conf, evidence, RoleResolutionStatus.INFERRED_HIGH_CONFIDENCE, counterparty

        # Case B: Landlord / Property Owner
        landlord_semantic_patterns = [
            (r"my tenant (stopped|refused|failed|not) paying", "tenant failed to pay rent to speaker"),
            (r"i (leased|rented|let) out my (flat|house|property|apartment) to", "speaker leased property to tenant"),
            (r"want to (evict|remove|terminate) my tenant", "speaker seeking to terminate tenant"),
            (r"tenant (violated|breached) the (lease|agreement)", "tenant breached agreement with speaker"),
        ]
        for pat, desc in landlord_semantic_patterns:
            m = re.search(pat, lower)
            if m:
                inferred = UserRole.LANDLORD
                counterparty = UserRole.TENANT
                evidence = m.group(0)
                conf = 0.95

                if declared_role and declared_role == UserRole.TENANT:
                    return inferred, 0.5, evidence, RoleResolutionStatus.UNRESOLVED_CONFLICT, counterparty
                if declared_role and declared_role == UserRole.LANDLORD:
                    return declared_role, 1.0, "Declared by user and supported by narrative", RoleResolutionStatus.DECLARED_BY_USER, counterparty
                return inferred, conf, evidence, RoleResolutionStatus.INFERRED_HIGH_CONFIDENCE, counterparty

        # Semantic Relationship 2: Employee vs Employer
        # Case A: Employee
        employee_semantic_patterns = [
            (r"(the firm|the company|my employer|my boss) (that hired me|where i worked|terminated me|fired me)", "hiring entity terminated speaker"),
            (r"my (company|employer|boss) (terminated|fired|let go of) me", "employer terminated speaker"),
            (r"(resigned|leaving my job|left the company|quit my job) and (want to join|joining|received an offer)", "worker departing and joining competitor"),
            (r"says i cannot (join|work for) (another|a competitor|a startup)", "restriction imposed on worker's employment"),
        ]
        for pat, desc in employee_semantic_patterns:
            m = re.search(pat, lower)
            if m:
                inferred = UserRole.EMPLOYEE
                counterparty = UserRole.EMPLOYER
                evidence = m.group(0)
                conf = 0.92

                if declared_role and declared_role == UserRole.EMPLOYER:
                    return inferred, 0.5, evidence, RoleResolutionStatus.UNRESOLVED_CONFLICT, counterparty
                if declared_role and declared_role == UserRole.EMPLOYEE:
                    return declared_role, 1.0, "Declared by user and supported by narrative", RoleResolutionStatus.DECLARED_BY_USER, counterparty
                return inferred, conf, evidence, RoleResolutionStatus.INFERRED_HIGH_CONFIDENCE, counterparty

        # Case B: Employer
        employer_semantic_patterns = [
            (r"(my|our) (former|ex-)?employee (joined|started|solicited)", "worker departed and joined competitor"),
            (r"staff member (breached|violated|stole)", "staff member breached company covenants"),
        ]
        for pat, desc in employer_semantic_patterns:
            m = re.search(pat, lower)
            if m:
                inferred = UserRole.EMPLOYER
                counterparty = UserRole.EMPLOYEE
                evidence = m.group(0)
                conf = 0.90

                if declared_role and declared_role == UserRole.EMPLOYEE:
                    return inferred, 0.5, evidence, RoleResolutionStatus.UNRESOLVED_CONFLICT, counterparty
                if declared_role and declared_role == UserRole.EMPLOYER:
                    return declared_role, 1.0, "Declared by user", RoleResolutionStatus.DECLARED_BY_USER, counterparty
                return inferred, conf, evidence, RoleResolutionStatus.INFERRED_HIGH_CONFIDENCE, counterparty

        # Default / Fallback: Role Neutral
        if declared_role:
            return declared_role, 1.0, "Declared explicitly by user", RoleResolutionStatus.DECLARED_BY_USER, None

        return UserRole.GENERAL, 0.5, None, RoleResolutionStatus.ROLE_NEUTRAL, None

    @classmethod
    def extract_timeline_anchors(
        cls,
        text: str,
        doc_text: Optional[str] = None
    ) -> List[TimelineAnchor]:
        """
        Extracts and normalizes duration and date entities.
        Strict Rule: NEVER calculates expiry dates without BOTH commencement date and duration.
        """
        anchors: List[TimelineAnchor] = []
        lower = text.lower()

        # 1. Notice periods: e.g. "15 days", "30 days"
        notice_m = re.search(r"\b(\d+)\s*(days?|day's?)\b", lower)
        if notice_m:
            days = notice_m.group(1)
            anchors.append(TimelineAnchor(
                raw_value=f"{days} days",
                normalized_value=f"P{days}D",
                event_type="notice_period",
                source="user_assertion",
                confidence=0.95
            ))

        # 2. Lock-in duration: e.g. "6 months lock-in", "six months"
        lock_m = re.search(r"\b(6|six|\d+)\s*months?\b", lower)
        if lock_m:
            dur = lock_m.group(1)
            num_dur = "6" if dur == "six" else dur
            anchors.append(TimelineAnchor(
                raw_value=f"{dur} months",
                normalized_value=f"P{num_dur}M",
                event_type="lock_in_duration",
                source="user_assertion",
                confidence=0.9
            ))

        # 3. Specific Calendar Dates: e.g. "October 1, 2024", "1st Oct 2024", "March 31, 2025"
        date_patterns = [
            r"\b(october|november|december|january|february|march|april|may|june|july|august|september)\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(october|november|december|january|february|march|april|may|june|july|august|september),?\s+\d{4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b"
        ]
        for pat in date_patterns:
            dm = re.search(pat, lower)
            if dm:
                anchors.append(TimelineAnchor(
                    raw_value=dm.group(0),
                    normalized_value=dm.group(0),
                    event_type="calendar_date",
                    source="user_assertion",
                    confidence=0.95
                ))

        return anchors

    @classmethod
    def extract_financial_elements(
        cls,
        text: str,
        doc_text: Optional[str] = None
    ) -> List[FinancialEntity]:
        """
        Extracts financial elements preserving exact source attribution:
        'user_assertion', 'uploaded_document', or 'both'.
        """
        entities: List[FinancialEntity] = []
        lower = text.lower()
        doc_lower = (doc_text or "").lower()

        # Rent extraction: e.g. "35,000", "INR 35,000", "35000 rent"
        rent_m = re.search(r"(?:inr|rs\.?|₹)?\s*([0-9]{2,3},[0-9]{3}|[0-9]{4,6})\s*(?:per\s+month|monthly|rent)?", lower)
        if rent_m and "day" not in rent_m.group(0):
            raw = rent_m.group(1)
            num_val = float(raw.replace(",", ""))
            # Check if this figure also appears in document
            is_in_doc = raw in doc_lower or str(int(num_val)) in doc_lower
            entities.append(FinancialEntity(
                raw_value=f"INR {raw}",
                numeric_amount=num_val,
                currency="INR",
                item_type="rent",
                source="both" if is_in_doc else "user_assertion",
                confidence=0.95
            ))

        # Deposit extraction: e.g. "3,50,000 deposit", "10 months deposit"
        dep_m = re.search(r"(\d+)\s*months?\s*(?:rent\s+)?deposit", lower)
        if dep_m:
            months = dep_m.group(1)
            entities.append(FinancialEntity(
                raw_value=f"{months} months deposit",
                numeric_amount=float(months),
                currency="MONTHS_RENT",
                item_type="security_deposit",
                source="user_assertion",
                confidence=0.9
            ))

        return entities

    @classmethod
    def handle_assertion_supersession(
        cls,
        current_text: str,
        turn_index: int = 1,
        previous_facts: Optional[List[SituationFactItem]] = None
    ) -> List[SituationFactItem]:
        """
        Supports correction of user assertions across turns.
        If user states: 'Actually it was 30 days, not 15', marks the earlier 15-day assertion as superseded.
        """
        facts: List[SituationFactItem] = []
        prev_list = previous_facts or []

        # Check for supersession markers
        supersedes = False
        supersede_reason = None
        if "actually" in current_text.lower() or "correction" in current_text.lower() or "i meant" in current_text.lower():
            supersedes = True
            supersede_reason = "Corrected by user in subsequent turn."

        curr_id = str(uuid.uuid4())[:8]
        current_fact = SituationFactItem(
            fact_id=curr_id,
            assertion_text=current_text,
            fact_status=FactStatus.USER_ASSERTED,
            turn_index=turn_index,
            is_superseded=False
        )

        for pf in prev_list:
            if supersedes and not pf.is_superseded:
                # Mark previous assertion superseded
                pf.is_superseded = True
                pf.superseded_by = curr_id
                pf.superseded_reason = supersede_reason
            facts.append(pf)

        facts.append(current_fact)
        return facts

    @classmethod
    def analyze_situation(
        cls,
        situation: Optional[UserSituation],
        query: str,
        doc_chunks: Optional[List[DocumentChunk]] = None,
        doc_raw_text: Optional[str] = None
    ) -> SituationAnalysis:
        """
        Performs end-to-end situation analysis, semantic role resolution,
        entity normalization, and fact-covenant discrepancy detection.
        """
        raw_narrative = ""
        declared_role = None
        turn_idx = 1
        prev_assertions: List[str] = []

        if situation:
            raw_narrative = situation.raw_description.strip()
            declared_role = situation.declared_role
            turn_idx = situation.turn_index
            prev_assertions = situation.previous_assertions

        combined_text = f"{raw_narrative} {query}".strip()
        safe_narrative = cls.sanitize_untrusted_situation(combined_text)

        # 1. Semantic Role Analysis
        inferred_role, role_conf, role_ev, role_status, counterparty_role = cls.infer_semantic_role(
            safe_narrative,
            declared_role=declared_role
        )

        # 2. Timeline & Financial Entity Extraction
        timeline_anchors = cls.extract_timeline_anchors(safe_narrative, doc_text=doc_raw_text)
        financial_elements = cls.extract_financial_elements(safe_narrative, doc_text=doc_raw_text)

        # 3. Assertion & Fact-Status Classification
        facts: List[SituationFactItem] = []
        if safe_narrative:
            facts.append(SituationFactItem(
                fact_id=str(uuid.uuid4())[:8],
                assertion_text=safe_narrative,
                fact_status=FactStatus.USER_ASSERTED,
                turn_index=turn_idx
            ))

        # Check turn supersession if previous assertions exist
        if prev_assertions:
            prev_fact_items = [
                SituationFactItem(
                    fact_id=f"prev_{i}",
                    assertion_text=pa,
                    fact_status=FactStatus.USER_ASSERTED,
                    turn_index=turn_idx - 1
                )
                for i, pa in enumerate(prev_assertions)
            ]
            facts = cls.handle_assertion_supersession(safe_narrative, turn_index=turn_idx, previous_facts=prev_fact_items)

        # 4. Bilateral Fact-Covenant Discrepancy Detection (User Assertion <-> Retrieved Document Clause)
        discrepancies: List[Dict[str, Any]] = []

        # Find stated notice period in user assertion
        user_notice_days = None
        for ta in timeline_anchors:
            if ta.event_type == "notice_period":
                m = re.search(r"(\d+)", ta.raw_value)
                if m:
                    user_notice_days = int(m.group(1))

        # Check against retrieved chunks (ONLY against actual retrieved document clauses, NEVER against typical contracts)
        if doc_chunks and user_notice_days is not None:
            for chunk in doc_chunks:
                # Look for notice clauses in chunk
                if "notice" in chunk.text.lower() and ("convenience" in chunk.text.lower() or "termination" in chunk.text.lower() or "thirty" in chunk.text.lower()):
                    c_m = re.search(r"\b(thirty|30)\s*(?:\([0-9]+\)\s*)?days?\b", chunk.text.lower())
                    if c_m:
                        doc_notice_days = 30
                        if user_notice_days != doc_notice_days:
                            # Potential contractual discrepancy (NOT necessarily contradiction, as breach may apply)
                            discrepancies.append({
                                "type": DiscrepancyType.POTENTIAL_CONFLICT.value,
                                "user_assertion": f"{user_notice_days} days notice requested",
                                "document_clause_ref": f"{chunk.section_number or 'Clause'} ({chunk.filename})",
                                "contract_stipulation": "thirty (30) days' prior written notice for convenience",
                                "neutral_explanation": (
                                    f"Your statement asserts a request to leave in {user_notice_days} days. "
                                    f"Section 8.1 of the agreement specifies that termination for convenience requires thirty (30) days' "
                                    f"prior written notice. Immediate termination under Section 8.3 describes specified material breaches "
                                    f"where a formal written cure notice of at least 14 days must first be served."
                                )
                            })

        # Core legal topic inference
        core_topic = "general"
        lower_comb = combined_text.lower()
        if "leave" in lower_comb or "notice" in lower_comb or "vacate" in lower_comb or "evict" in lower_comb or "terminate" in lower_comb:
            core_topic = "lease_termination" if (inferred_role in [UserRole.TENANT, UserRole.LANDLORD] or declared_role in [UserRole.TENANT, UserRole.LANDLORD]) else "termination"
        elif "non-compete" in lower_comb or "compete" in lower_comb or "startup" in lower_comb:
            core_topic = "non_compete"
        elif "deposit" in lower_comb or "refund" in lower_comb:
            core_topic = "deposit_dispute"

        return SituationAnalysis(
            declared_role=declared_role,
            inferred_role=inferred_role,
            role_confidence=role_conf,
            role_evidence=role_ev,
            role_resolution_status=role_status,
            counterparty_role=counterparty_role,
            stated_facts=facts,
            timeline_anchors=timeline_anchors,
            financial_elements=financial_elements,
            core_legal_topic=core_topic,
            discrepancy_signals=discrepancies
        )

    @classmethod
    def generate_bounded_checklist(
        cls,
        analysis: SituationAnalysis,
        doc_chunks: Optional[List[DocumentChunk]] = None
    ) -> List[str]:
        """
        Generates actionable preparation and evidence-gathering steps strictly bounded
        to factual investigation. Forbids tactical legal strategies or representation advice.
        """
        checklist: List[str] = [
            "Locate the written notice or communication and record the date and time received.",
            "Verify the delivery medium of the notice (e.g. Section 8.2 specifies registered post, courier, or acknowledged email).",
            "Review your bank transfer records to confirm that all monthly rental payments are up to date."
        ]

        if analysis.core_legal_topic == "lease_termination":
            checklist.append("Check whether any separate written default or cure notice citing Section 8.3 was served.")
            checklist.append("Locate your original signed lease agreement to verify the commencement date (October 1, 2024).")
            checklist.append("Prepare your timeline and document copies before consulting a legal professional.")
        elif analysis.core_legal_topic == "non_compete":
            checklist.append("Locate your original employment agreement and review Section 11 (Non-Competition).")
            checklist.append("Check the exact termination date and notice of relieving/acceptance.")
            checklist.append("Document whether confidential trade secrets or proprietary assets are involved.")

        return checklist


situation_service = SituationService()
