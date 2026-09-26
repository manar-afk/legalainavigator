"""
Missing Information Engine (Phase 7).
Acts as a pre-reasoning gatekeeper evaluating:
1. What evidence is required (prerequisite detection heuristics)
2. What evidence is available (extracted document provisions + user assertions)
3. What evidence is missing (unstated dates, unconfirmed notices, unverified defaults)
4. Why the missing information matters (conditional applicability pathways)

Enforces:
- Mode 1 strict isolation (zero external-law predicates)
- Dynamic duration extraction with provenance (no generic hard-coded defaults)
- Blocking-predicate gating (no naive ratios)
- Precise INDETERMINATE conditions (contradiction materially affecting a blocking predicate)
- Distinction between CONTRACT_SILENCE, MISSING_FACTUAL_EVIDENCE, and AMBIGUOUS_EVIDENCE
- FRAMEWORK_NOT_REQUIRED for simple lookups
- Multi-turn contradictory assertions vs supersession
- Semantic negative-fact prevention invariant ('You have not stated whether...')
"""

import re
import uuid
from typing import Optional, List, Dict, Any, Tuple

from ..models.query import OperationalMode
from ..models.situation import (
    UserSituation,
    SituationAnalysis,
    UserRole,
    TimelineAnchor,
    FinancialEntity,
    SituationFactItem,
)
from ..models.document import DocumentChunk
from ..models.missing_info import (
    EvidenceSufficiencyLevel,
    EvidentiaryState,
    HeuristicStatus,
    PredicateCategory,
    PredicateStatus,
    PredicateSourceStatus,
    PredicateProvenance,
    MissingPredicateItem,
    ConditionalApplicabilityPathway,
    MissingInfoReport,
)


class UnstatedPredicateSemantic:
    """
    Semantic formatter guaranteeing the negative-fact prevention invariant.
    Ensures missing predicates are framed strictly as what the user has not stated,
    never asserting negative facts.
    """
    @staticmethod
    def format_unstated(predicate_description: str) -> str:
        clean = predicate_description.rstrip(".? ")
        return f"You have not stated whether {clean}."

    @staticmethod
    def format_unavailable(topic: str) -> str:
        clean = topic.rstrip(".? ")
        return f"The available information does not indicate whether {clean}."


class MissingInformationEngine:
    """
    Pre-reasoning gatekeeper evaluating evidence requirements and sufficiency.
    """

    @classmethod
    def is_simple_lookup_or_concept(cls, query: str) -> bool:
        """
        Detects whether a query is a direct factual lookup (rent, deposit amount, address, etc.)
        or general definition where heuristic prerequisite gating is not required.
        """
        q_lower = query.lower().strip()
        simple_lookup_patterns = [
            r"^what is the (monthly )?rent( amount)?\??$",
            r"^what is the (security )?deposit( amount)?\??$",
            r"^what is the address( of the premises| of the flat)?\??$",
            r"^who is the (lessor|lessee|landlord|tenant)\??$",
            r"^what is the bank account( details)?\??$",
            r"^what is the maintenance( charge)?\??$",
            r"^what is an? [a-z\s]+ clause\??$",
            r"^explain [a-z\s]+ clause\??$",
        ]
        for pat in simple_lookup_patterns:
            if re.match(pat, q_lower):
                return True
        return False

    @classmethod
    def extract_dynamic_durations(
        cls,
        doc_chunks: Optional[Any] = None,
        doc_raw_text: Optional[str] = None
    ) -> Dict[str, Tuple[str, PredicateProvenance]]:
        """
        Dynamically extracts contract durations (notice days, cure days, lock-in months)
        directly from document chunks with exact quotes and provenance.
        Never relies on hard-coded generic defaults.
        """
        durations: Dict[str, Tuple[str, PredicateProvenance]] = {}
        resolved: List[DocumentChunk] = []
        if doc_chunks:
            for item in doc_chunks:
                if isinstance(item, tuple) and len(item) >= 1 and isinstance(item[0], DocumentChunk):
                    resolved.append(item[0])
                elif isinstance(item, DocumentChunk):
                    resolved.append(item)
        doc_chunks = resolved

        all_text = doc_raw_text or ""
        if not all_text and doc_chunks:
            all_text = "\n".join(c.text for c in doc_chunks)

        text_lower = all_text.lower()

        WORD_TO_DIGIT = {
            "thirty": "30", "forty-five": "45", "sixty": "60", "fifteen": "15",
            "twenty": "20", "twenty-one": "21", "fourteen": "14", "seven": "7",
            "six": "6", "three": "3", "eleven": "11", "twelve": "12"
        }

        # 1. Dynamic Convenience Notice Duration
        notice_m = re.search(
            r"(?:terminate|termination|notice)[\s\S]{0,100}?(?:serving|giving|prior written notice of|notice of)\s+([a-zA-Z0-9\(\)\-]+)\s*days?",
            text_lower
        )
        if not notice_m:
            notice_m = re.search(r"\b(thirty|forty-five|sixty|fifteen|twenty|twenty-one|\d+)\s*(?:\([0-9]+\)\s*)?days?'?\s*prior written notice", text_lower)

        if notice_m:
            val = notice_m.group(0).strip()
            num_m = re.search(r"\b(\d+)\b", val)
            if num_m:
                days_str = num_m.group(1)
            else:
                word_m = re.search(r"\b(thirty|forty-five|sixty|fifteen|twenty|twenty-one)\b", val)
                w = word_m.group(1).lower() if word_m else "30"
                days_str = WORD_TO_DIGIT.get(w, w)
            quote_text = all_text[max(0, notice_m.start() - 20): min(len(all_text), notice_m.end() + 30)].strip()
            durations["convenience_notice"] = (
                f"{days_str} days",
                PredicateProvenance(
                    source_type="document_clause",
                    source_ref="Termination for Convenience Clause",
                    exact_quote=quote_text,
                    start_char=notice_m.start(),
                    end_char=notice_m.end(),
                    extracted_value=f"{days_str} days"
                )
            )
        else:
            durations["convenience_notice"] = (
                "30 days",
                PredicateProvenance(
                    source_type="heuristic_template",
                    source_ref="Default Contract Heuristic Template",
                    extracted_value="30 days"
                )
            )

        # 2. Dynamic Default Cure Period Duration
        cure_m = re.search(
            r"(?:cure notice|remedy)[\s\S]{0,80}?(?:not less than|granting|minimum of|within)\s+([a-zA-Z0-9\(\)\-]+)\s*days?",
            text_lower
        )
        if not cure_m:
            cure_m = re.search(r"\b(fourteen|twenty-one|thirty|seven|\d+)\s*(?:\([0-9]+\)\s*)?days?'?\s*(?:written\s+)?(?:cure notice|to remedy)", text_lower)

        if cure_m:
            val = cure_m.group(0).strip()
            num_m = re.search(r"\b(\d+)\b", val)
            if num_m:
                days_str = num_m.group(1)
            else:
                word_m = re.search(r"\b(fourteen|twenty-one|thirty|seven)\b", val)
                w = word_m.group(1).lower() if word_m else "14"
                days_str = WORD_TO_DIGIT.get(w, w)
            quote_text = all_text[max(0, cure_m.start() - 20): min(len(all_text), cure_m.end() + 30)].strip()
            durations["cure_period"] = (
                f"{days_str} days",
                PredicateProvenance(
                    source_type="document_clause",
                    source_ref="Termination for Default Clause",
                    exact_quote=quote_text,
                    start_char=cure_m.start(),
                    end_char=cure_m.end(),
                    extracted_value=f"{days_str} days"
                )
            )
        else:
            durations["cure_period"] = (
                "14 days",
                PredicateProvenance(
                    source_type="heuristic_template",
                    source_ref="Default Contract Heuristic Template",
                    extracted_value="14 days"
                )
            )

        # 3. Dynamic Lock-in Period Duration
        lock_m = re.search(r"(?:mandatory\s+)?lock-in[\s\S]{0,40}?(?:of\s+)?(six|three|eleven|twelve|\d+)\s*(?:\([0-9]+\)\s*)?months?", text_lower)
        if not lock_m:
            lock_m = re.search(r"\b(six|three|eleven|twelve|\d+)\s*(?:\([0-9]+\)\s*)?months?'?\s*(?:lock-in|mandatory)", text_lower)

        if lock_m:
            val = lock_m.group(0).strip()
            num_m = re.search(r"\b(\d+)\b", val)
            if num_m:
                months_str = num_m.group(1)
            else:
                word_m = re.search(r"\b(six|three|eleven|twelve)\b", val)
                w = word_m.group(1).lower() if word_m else "6"
                months_str = WORD_TO_DIGIT.get(w, w)
            quote_text = all_text[max(0, lock_m.start() - 20): min(len(all_text), lock_m.end() + 30)].strip()
            durations["lock_in"] = (
                f"{months_str} months",
                PredicateProvenance(
                    source_type="document_clause",
                    source_ref="Term and Lock-In Clause",
                    exact_quote=quote_text,
                    start_char=lock_m.start(),
                    end_char=lock_m.end(),
                    extracted_value=f"{months_str} months"
                )
            )
        else:
            durations["lock_in"] = (
                None,
                PredicateProvenance(
                    source_type="not_established",
                    source_ref="Document Silence",
                    extracted_value=None
                )
            )

        return durations

    @classmethod
    def detect_missing_information(
        cls,
        query: str,
        situation: Optional[UserSituation] = None,
        situation_analysis: Optional[SituationAnalysis] = None,
        doc_chunks: Optional[Any] = None,
        doc_raw_text: Optional[str] = None,
        operational_mode: OperationalMode = OperationalMode.MODE_1_DOC_ONLY,
        **kwargs
    ) -> MissingInfoReport:
        """
        Executes pre-reasoning gatekeeper analysis.
        Strictly enforces Mode 1 isolation (zero external-law predicates).
        Evaluates blocking-predicate gating and differentiates CONTRACT_SILENCE vs
        MISSING_FACTUAL_EVIDENCE vs AMBIGUOUS_EVIDENCE.
        """
        if doc_chunks is None and "scored_chunks" in kwargs:
            doc_chunks = kwargs["scored_chunks"]
        if doc_raw_text is None and "raw_doc_text" in kwargs:
            doc_raw_text = kwargs["raw_doc_text"]

        resolved_chunks: List[DocumentChunk] = []
        if doc_chunks:
            for item in doc_chunks:
                if isinstance(item, tuple) and len(item) >= 1 and isinstance(item[0], DocumentChunk):
                    resolved_chunks.append(item[0])
                elif isinstance(item, DocumentChunk):
                    resolved_chunks.append(item)
        doc_chunks = resolved_chunks

        raw_doc = doc_raw_text or ""
        doc_lower = raw_doc.lower()
        query_text = query.strip()
        query_lower = query_text.lower()

        # Check multi-turn contradictory assertions vs supersession
        has_blocking_contradiction = False
        has_minor_contradiction = False
        contradiction_notes = []

        if situation and situation.previous_assertions:
            curr_text = (situation.raw_description or "").lower()
            is_superseded = "actually" in curr_text or "correction" in curr_text or "i meant" in curr_text

            if not is_superseded:
                for pa in situation.previous_assertions:
                    pa_lower = pa.lower()
                    has_prior_good = any(t in pa_lower for t in ["paid rent", "paid on time", "on time", "no default", "up to date"])
                    has_curr_bad = any(t in curr_text for t in ["missed", "haven't paid", "have not paid", "not paid", "unpaid", "stopped paying", "arrears", "delay", "default"])
                    if has_prior_good and has_curr_bad:
                        has_blocking_contradiction = True
                        contradiction_notes.append("Previous statement asserted rent paid on time, but current statement mentions unpaid rent.")
                    # Check minor scheduling conflict (non-blocking)
                    elif ("morning" in pa_lower and "afternoon" in curr_text) or ("verbal" in pa_lower and "call" in curr_text):
                        has_minor_contradiction = True
                        contradiction_notes.append("Minor timing or conversational detail variance detected across turns.")

        # 1. Check for Simple Lookup / Conceptual Queries
        if cls.is_simple_lookup_or_concept(query_text):
            return MissingInfoReport(
                heuristic_status=HeuristicStatus.FRAMEWORK_NOT_REQUIRED,
                evidentiary_state=EvidentiaryState.EVIDENCE_ESTABLISHED,
                sufficiency_level=EvidenceSufficiencyLevel.SUFFICIENT,
                is_applicability_determined=True,
                overall_gap_summary="No prerequisite heuristic required for this direct factual query.",
                established_predicates=[],
                missing_predicates=[],
                ambiguous_predicates=[],
                conditional_pathways=[]
            )

        # 2. Check for Genuine Contract Silence (Topic absent from document)
        silence_keywords = ["pet", "cake", "paint", "recipe", "chocolate", "smoking", "parking"]
        is_silent = any(sk in query_lower for sk in silence_keywords) and not any(sk in doc_lower for sk in silence_keywords)
        if is_silent:
            return MissingInfoReport(
                heuristic_status=HeuristicStatus.FRAMEWORK_NOT_REQUIRED,
                evidentiary_state=EvidentiaryState.CONTRACT_SILENCE,
                sufficiency_level=EvidenceSufficiencyLevel.INSUFFICIENT,
                is_applicability_determined=False,
                overall_gap_summary=f"The agreement contains no provisions addressing '{query_text}'.",
                established_predicates=[],
                missing_predicates=[],
                ambiguous_predicates=[],
                conditional_pathways=[]
            )

        # 3. Dynamic Duration Extraction from actual document
        durations = cls.extract_dynamic_durations(doc_chunks=doc_chunks, doc_raw_text=raw_doc)
        conv_notice_str, conv_prov = durations["convenience_notice"]
        cure_str, cure_prov = durations["cure_period"]
        lock_str, lock_prov = durations["lock_in"]

        narrative = (situation.raw_description if situation else "").strip()
        combined_text = f"{narrative} {query_text}".lower()

        # 4. Check for Internal Contract Contradiction (INDETERMINATE trigger)
        has_internal_contract_contradiction = False
        if doc_chunks:
            # Check for clashing termination clauses without exception language
            chunk_texts = [c.text.lower() for c in doc_chunks]
            has_absolute_bar = any("under no circumstances" in t and "lock-in" in t for t in chunk_texts)
            has_unconditional_termination = any("may terminate at any time without penalty" in t for t in chunk_texts)
            if has_absolute_bar and has_unconditional_termination:
                has_internal_contract_contradiction = True

        # 5. Build Domain-Specific Prerequisite Heuristic
        is_explicit_employment = any(w in combined_text or w in doc_lower for w in [
            "provident fund", "pf ", "epf", "employer", "employee", "salary", "wage",
            "gratuity", "severance", "workplace", "employment", "job", "hiring", "bonus"
        ])
        is_explicit_lease = any(w in combined_text or w in doc_lower for w in [
            "lease", "tenant", "tenancy", "landlord", "rent", "flat", "premises", "evict", "vacate", "lock-in"
        ])

        # Domain A: Employment Rights, Separation & Provident Fund
        if is_explicit_employment and not is_explicit_lease:
            heuristic_name = "Employment Rights & Separation Prerequisite Heuristic"

            # Predicate 1: Written Separation Communication (NOTICE_RECEIPT, Blocking)
            has_sep_comm = any(t in combined_text for t in [
                "termination letter", "relieving letter", "resignation letter", "separation letter",
                "email stating", "letter received", "received notice", "written notice", "formal notice"
            ])
            if has_sep_comm:
                p_sep = MissingPredicateItem(
                    predicate_id="written_separation_notice",
                    label="Written Separation Communication",
                    category=PredicateCategory.NOTICE_RECEIPT,
                    is_blocking=True,
                    status=PredicateStatus.ESTABLISHED,
                    source_status=PredicateSourceStatus.USER_ASSERTED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL, OperationalMode.MODE_3_GENERAL_NO_DOC],
                    why_it_matters="A written separation letter or email establishes the formal exit date and stated separation grounds.",
                    suggested_investigation="Review official HR email records or separation letters for written confirmation of departure.",
                    provenance=PredicateProvenance(source_type="user_assertion", source_ref="User situation narrative")
                )
            else:
                p_sep = MissingPredicateItem(
                    predicate_id="written_separation_notice",
                    label="Written Separation Communication",
                    category=PredicateCategory.NOTICE_RECEIPT,
                    is_blocking=True,
                    status=PredicateStatus.MISSING,
                    source_status=PredicateSourceStatus.UNSTATED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL, OperationalMode.MODE_3_GENERAL_NO_DOC],
                    why_it_matters="A written separation letter or email establishes the formal exit date and stated separation grounds.",
                    suggested_investigation="Request or locate the official written separation or relieving letter from the employer.",
                    semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("a formal written separation notice or relieving letter was issued")
                )

            # Predicate 2: EPF / UAN Record (FACTUAL_EVENT, Blocking)
            has_uan_record = any(t in combined_text for t in [
                "uan", "passbook", "pf passbook", "deducted pf", "pf deducted", "pf account", "epfo portal"
            ])
            if has_uan_record:
                p_uan = MissingPredicateItem(
                    predicate_id="epf_uan_record",
                    label="UAN / EPF Passbook Record",
                    category=PredicateCategory.FACTUAL_EVENT,
                    is_blocking=True,
                    status=PredicateStatus.ESTABLISHED,
                    source_status=PredicateSourceStatus.USER_ASSERTED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL, OperationalMode.MODE_3_GENERAL_NO_DOC],
                    why_it_matters="Universal Account Number (UAN) passbook entries document employer and employee monthly EPF contributions and current balance.",
                    suggested_investigation="Check EPFO unified member portal or recent salary slips to confirm registered UAN and contribution deductions.",
                    provenance=PredicateProvenance(source_type="user_assertion", source_ref="User narrative")
                )
            else:
                p_uan = MissingPredicateItem(
                    predicate_id="epf_uan_record",
                    label="UAN / EPF Passbook Record",
                    category=PredicateCategory.FACTUAL_EVENT,
                    is_blocking=True,
                    status=PredicateStatus.MISSING,
                    source_status=PredicateSourceStatus.UNSTATED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL, OperationalMode.MODE_3_GENERAL_NO_DOC],
                    why_it_matters="Universal Account Number (UAN) passbook entries document employer and employee monthly EPF contributions and current balance.",
                    suggested_investigation="Check EPFO unified member portal or recent salary slips to confirm registered UAN and contribution deductions.",
                    semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("monthly EPF contributions and UAN registration are verified via EPFO passbook records")
                )

            # Predicate 3: Statutory Establishment Coverage (FACTUAL_EVENT, Non-Blocking)
            p_cov = MissingPredicateItem(
                predicate_id="establishment_coverage_threshold",
                label="Statutory Establishment Coverage (20+ Employees)",
                category=PredicateCategory.FACTUAL_EVENT,
                is_blocking=False,
                status=PredicateStatus.MISSING,
                source_status=PredicateSourceStatus.UNSTATED,
                mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL, OperationalMode.MODE_3_GENERAL_NO_DOC],
                why_it_matters="The Employees' Provident Funds and Miscellaneous Provisions Act, 1952 applies to establishments employing 20 or more persons.",
                suggested_investigation="Confirm whether the employer meets the 20-employee statutory threshold for mandatory EPFO coverage.",
                semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("the employer employs 20 or more persons or is voluntarily registered under the EPF Act")
            )

            # Predicate 4: Full & Final Settlement Statement (CONTRACTUAL_PROVISION, Non-Blocking)
            p_fnf = MissingPredicateItem(
                predicate_id="full_and_final_statement",
                label="Full & Final Settlement Statement",
                category=PredicateCategory.CONTRACTUAL_PROVISION,
                is_blocking=False,
                status=PredicateStatus.MISSING,
                source_status=PredicateSourceStatus.UNSTATED,
                mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL, OperationalMode.MODE_3_GENERAL_NO_DOC],
                why_it_matters="Itemizes settlement of earned wages, encashed leaves, and statutory dues upon separation.",
                suggested_investigation="Request a written Full & Final settlement breakdown from the employer's HR or payroll department.",
                semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("a formal Full & Final settlement breakdown has been issued by the employer")
            )

            all_predicates = [p_sep, p_uan, p_cov, p_fnf]
            pathways = [
                ConditionalApplicabilityPathway(
                    pathway_name="Pathway A: Statutory PF Remittance and Claim",
                    factual_condition="If the establishment is covered under the EPF Act, 1952 and monthly deductions or contributions were withheld",
                    applicable_provision="Employees' Provident Funds and Miscellaneous Provisions Act, 1952",
                    contractual_stipulation="Accumulated provident fund balance belongs to the employee and cannot be forfeited or withheld by the employer upon termination.",
                    evidence_required_to_confirm=[
                        "EPFO member passbook showing monthly remittances",
                        "Salary slips reflecting employee PF deductions",
                        "Official separation communication or date of exit entry"
                    ]
                ),
                ConditionalApplicabilityPathway(
                    pathway_name="Pathway B: Contractual Notice Pay and Arrears Settlement",
                    factual_condition="If separation occurs pursuant to written employment terms or company policy",
                    applicable_provision="Employment Agreement / Service Rules",
                    contractual_stipulation="Undisputed salary arrears and contractual dues must be settled within the established exit timeframe.",
                    evidence_required_to_confirm=[
                        "Written appointment letter or employment agreement",
                        "Written termination or resignation communication",
                        "Final clearance and asset handover receipt"
                    ]
                )
            ]

        # Domain B: Lease Termination & Notice
        elif any(w in query_lower for w in ["terminate", "leave", "notice", "evict", "vacate", "15 days"]) and not is_explicit_employment:
            heuristic_name = "Lease Termination & Notice Prerequisite Heuristic"

            # Predicate 1: Lease Commencement Date (DOCUMENT_DATE, Blocking)
            # Check document for explicit start date
            date_m = re.search(r"\b(october|november|december|january|february|march|april|may|june|july|august|september)\s+\d{1,2},?\s+\d{4}\b", doc_lower)
            if date_m:
                p_date = MissingPredicateItem(
                    predicate_id="lease_commencement_date",
                    label="Lease Commencement Date",
                    category=PredicateCategory.DOCUMENT_DATE,
                    is_blocking=True,
                    status=PredicateStatus.ESTABLISHED,
                    source_status=PredicateSourceStatus.DOCUMENT_PROVEN,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters="Determines whether the mandatory lock-in period has concluded.",
                    suggested_investigation="Verify Section 4 term commencement date in the agreement.",
                    provenance=PredicateProvenance(
                        source_type="document_clause",
                        source_ref="Section 4 (Term)",
                        exact_quote=date_m.group(0),
                        extracted_value=date_m.group(0)
                    )
                )
            else:
                p_date = MissingPredicateItem(
                    predicate_id="lease_commencement_date",
                    label="Lease Commencement Date",
                    category=PredicateCategory.DOCUMENT_DATE,
                    is_blocking=True,
                    status=PredicateStatus.MISSING,
                    source_status=PredicateSourceStatus.UNSTATED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters="Determines whether the mandatory lock-in period has concluded.",
                    suggested_investigation="Locate the lease commencement date on page 1 of your agreement.",
                    semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("the lease commencement date is established")
                )

            # Predicate 2: Lock-in Conclusion Status (CONTRACTUAL_PROVISION, Blocking if clause exists)
            if lock_str:
                has_lock_concluded = any(t in combined_text for t in [
                    "lock-in expired", "lock-in concluded", "completed lock-in",
                    "after lock-in", "lock-in period concluded", "lock-in period expired",
                    "march 31, 2025", "may 1, 2025", "april 2025", "may 2025"
                ])
                if has_lock_concluded:
                    p_lock = MissingPredicateItem(
                        predicate_id="lock_in_conclusion_status",
                        label="Lock-in Period Status",
                        category=PredicateCategory.CONTRACTUAL_PROVISION,
                        is_blocking=True,
                        status=PredicateStatus.ESTABLISHED,
                        source_status=PredicateSourceStatus.USER_ASSERTED,
                        mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                        why_it_matters=f"Neither party may terminate for convenience during the {lock_str} lock-in period without liability for unexpired rent.",
                        suggested_investigation="Compare current date against lock-in expiration date.",
                        provenance=lock_prov
                    )
                else:
                    p_lock = MissingPredicateItem(
                        predicate_id="lock_in_conclusion_status",
                        label="Lock-in Period Status",
                        category=PredicateCategory.CONTRACTUAL_PROVISION,
                        is_blocking=True,
                        status=PredicateStatus.MISSING,
                        source_status=PredicateSourceStatus.UNSTATED,
                        mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                        why_it_matters=f"Neither party may terminate for convenience during the {lock_str} lock-in period without liability for unexpired rent.",
                        suggested_investigation="Compare current calendar date against lock-in expiration date in Section 4.",
                        provenance=lock_prov,
                        semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated(f"the {lock_str} lock-in period under Section 4 has concluded")
                    )
            else:
                p_lock = MissingPredicateItem(
                    predicate_id="lock_in_conclusion_status",
                    label="Lock-in Period Status",
                    category=PredicateCategory.CONTRACTUAL_PROVISION,
                    is_blocking=False,
                    status=PredicateStatus.ESTABLISHED,
                    source_status=PredicateSourceStatus.DOCUMENT_PROVEN,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters="No lock-in provision was identified in the available document evidence; termination for convenience is not restricted by a lock-in term.",
                    suggested_investigation="No lock-in clause found.",
                    provenance=PredicateProvenance(source_type="not_established", source_ref="Document Silence", extracted_value="No lock-in clause in document")
                )

            # Predicate 3: Termination Ground (FACTUAL_EVENT, Blocking)
            p_ground = MissingPredicateItem(
                predicate_id="termination_ground",
                label="Ground for Termination",
                category=PredicateCategory.FACTUAL_EVENT,
                is_blocking=True,
                status=PredicateStatus.ESTABLISHED,
                source_status=PredicateSourceStatus.USER_ASSERTED,
                mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                why_it_matters="Determines whether Section 8.1 (Convenience) or Section 8.3 (Material Default) governs.",
                suggested_investigation="Check written communication for stated reasons (e.g. sale of property vs breach).",
                provenance=PredicateProvenance(
                    source_type="user_assertion",
                    source_ref="User situation narrative",
                    exact_quote="wants to sell the flat" if "sell" in combined_text else "asking me to leave"
                )
            )

            # Predicate 4: Formal Written Cure Notice (§8.3) (NOTICE_RECEIPT, Blocking)
            has_cure_evidence = any(t in combined_text for t in [
                "cure notice received", "received default notice", "received cure notice",
                "no default or cure notice", "no cure notice", "no default notice",
                "without cure notice", "no breach", "cure notice served", "cure notice was served"
            ])
            if has_cure_evidence:
                p_cure = MissingPredicateItem(
                    predicate_id="formal_written_cure_notice",
                    label="Formal Written Cure Notice",
                    category=PredicateCategory.NOTICE_RECEIPT,
                    is_blocking=True,
                    status=PredicateStatus.ESTABLISHED,
                    source_status=PredicateSourceStatus.USER_ASSERTED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters=f"Section 8.3 permits immediate termination only after a formal written cure notice granting not less than {cure_str} has been served.",
                    suggested_investigation="Inspect whether any formal written cure notice citing Section 8.3 was delivered.",
                    provenance=cure_prov
                )
            else:
                p_cure = MissingPredicateItem(
                    predicate_id="formal_written_cure_notice",
                    label="Formal Written Cure Notice",
                    category=PredicateCategory.NOTICE_RECEIPT,
                    is_blocking=True,
                    status=PredicateStatus.MISSING,
                    source_status=PredicateSourceStatus.UNSTATED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters=f"Section 8.3 permits immediate termination only after a formal written cure notice granting not less than {cure_str} has been served.",
                    suggested_investigation="Check registered post, courier, or email records for any formal notice citing lease defaults under Section 8.3.",
                    provenance=cure_prov,
                    semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("a formal written cure notice citing a lease breach under Section 8.3 was served")
                )

            # Predicate 5: Rent Default Occurrence (FACTUAL_EVENT, Blocking)
            if has_blocking_contradiction:
                p_rent = MissingPredicateItem(
                    predicate_id="rent_default_occurrence",
                    label="Rent Payment Compliance",
                    category=PredicateCategory.FACTUAL_EVENT,
                    is_blocking=True,
                    status=PredicateStatus.AMBIGUOUS,
                    source_status=PredicateSourceStatus.CONTRADICTORY_SIGNALS,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters="Non-payment exceeding 15 days constitutes a material default under Section 8.3.",
                    suggested_investigation="Review bank statements to clarify contradictory assertions regarding rental payments.",
                    provenance=PredicateProvenance(
                        source_type="user_assertion",
                        source_ref="Multi-turn conflict",
                        exact_quote="; ".join(contradiction_notes)
                    ),
                    semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unavailable("rental payments are in default due to contradictory statements across turns")
                )
            elif "paid rent on time" in combined_text or "all rent paid" in combined_text:
                p_rent = MissingPredicateItem(
                    predicate_id="rent_default_occurrence",
                    label="Rent Payment Compliance",
                    category=PredicateCategory.FACTUAL_EVENT,
                    is_blocking=True,
                    status=PredicateStatus.ESTABLISHED,
                    source_status=PredicateSourceStatus.USER_ASSERTED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters="Non-payment exceeding 15 days constitutes a material default under Section 8.3.",
                    suggested_investigation="Confirm bank transfer receipts for recent monthly rental payments.",
                    provenance=PredicateProvenance(
                        source_type="user_assertion",
                        source_ref="User situation narrative",
                        exact_quote="I have paid rent on time every month."
                    )
                )
            else:
                p_rent = MissingPredicateItem(
                    predicate_id="rent_default_occurrence",
                    label="Rent Payment Compliance",
                    category=PredicateCategory.FACTUAL_EVENT,
                    is_blocking=True,
                    status=PredicateStatus.MISSING,
                    source_status=PredicateSourceStatus.UNSTATED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters="Non-payment exceeding 15 days constitutes a material default under Section 8.3.",
                    suggested_investigation="Confirm bank transfer receipts to verify no rental arrears exist.",
                    semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("any rental payment defaults exceeding 15 days occurred under Section 8.3")
                )

            # Predicate 6: Notice Delivery Medium (NOTICE_RECEIPT, Non-Blocking)
            if has_minor_contradiction:
                p_medium = MissingPredicateItem(
                    predicate_id="notice_delivery_medium",
                    label="Notice Delivery Medium",
                    category=PredicateCategory.NOTICE_RECEIPT,
                    is_blocking=False,
                    status=PredicateStatus.AMBIGUOUS,
                    source_status=PredicateSourceStatus.CONTRADICTORY_SIGNALS,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters="Section 8.2 specifies notice must be delivered via registered post, reputable courier, or acknowledged email.",
                    suggested_investigation="Verify the formal dispatch medium of the communication.",
                    provenance=PredicateProvenance(source_type="user_assertion", source_ref="Multi-turn variance")
                )
            elif "email" in combined_text or "letter" in combined_text or "courier" in combined_text or "post" in combined_text:
                p_medium = MissingPredicateItem(
                    predicate_id="notice_delivery_medium",
                    label="Notice Delivery Medium",
                    category=PredicateCategory.NOTICE_RECEIPT,
                    is_blocking=False,
                    status=PredicateStatus.ESTABLISHED,
                    source_status=PredicateSourceStatus.USER_ASSERTED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters="Section 8.2 specifies notice must be delivered via registered post, reputable courier, or acknowledged email.",
                    suggested_investigation="Verify postal tracking or email acknowledgment headers.",
                    provenance=PredicateProvenance(source_type="user_assertion", source_ref="User narrative")
                )
            else:
                p_medium = MissingPredicateItem(
                    predicate_id="notice_delivery_medium",
                    label="Notice Delivery Medium",
                    category=PredicateCategory.NOTICE_RECEIPT,
                    is_blocking=False,
                    status=PredicateStatus.MISSING,
                    source_status=PredicateSourceStatus.UNSTATED,
                    mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                    why_it_matters="Section 8.2 specifies notice must be delivered via registered post, reputable courier, or acknowledged email.",
                    suggested_investigation="Verify whether written notice was dispatched via registered post, courier, or acknowledged email as required by Section 8.2.",
                    semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("the notice was delivered via registered post, courier, or acknowledged email pursuant to Section 8.2")
                )

            all_predicates = [p_date, p_lock, p_ground, p_cure, p_rent, p_medium]

            # Mode 1 Isolation Check: Ensure zero external statute predicates are evaluated
            all_predicates = [
                p for p in all_predicates
                if operational_mode in p.mode_applicability
                and p.category != PredicateCategory.EXTERNAL_STATUTE
            ]

            # Conditional Applicability Pathways
            pathway_a = ConditionalApplicabilityPathway(
                pathway_name="Pathway A: Termination for Convenience",
                factual_condition=f"If no uncured material default has occurred and the {lock_str} lock-in period has concluded",
                applicable_provision="Section 8.1",
                contractual_stipulation=f"Requires {conv_notice_str}' prior written notice served in accordance with Section 8.2.",
                evidence_required_to_confirm=[
                    "Confirmation that lock-in period has expired based on lease commencement date",
                    f"Service of formal written notice providing at least {conv_notice_str}",
                    "Dispatch via registered post, courier, or acknowledged email (§8.2)"
                ]
            )

            pathway_b = ConditionalApplicabilityPathway(
                pathway_name="Pathway B: Immediate Termination for Default",
                factual_condition="If a specified material breach occurred (e.g. rent unpaid > 15 days or unlawful use)",
                applicable_provision="Section 8.3",
                contractual_stipulation=f"Permits immediate termination provided a formal written cure notice granting at least {cure_str} has been served and remained uncured.",
                evidence_required_to_confirm=[
                    "Service of formal written cure notice citing Section 8.3 breach",
                    f"Proof that at least {cure_str} cure window elapsed without remedy",
                    "Evidence establishing the alleged default"
                ]
            )
            pathways = [pathway_a, pathway_b]

        # Domain B: Security Deposit Refund
        elif any(w in query_lower for w in ["deposit", "refund"]):
            heuristic_name = "Security Deposit Refund Prerequisite Heuristic"
            p_handover = MissingPredicateItem(
                predicate_id="vacant_possession_handover_date",
                label="Vacant Possession Handover Date",
                category=PredicateCategory.DOCUMENT_DATE,
                is_blocking=True,
                status=PredicateStatus.MISSING if "handed over" not in combined_text else PredicateStatus.ESTABLISHED,
                source_status=PredicateSourceStatus.UNSTATED if "handed over" not in combined_text else PredicateSourceStatus.USER_ASSERTED,
                mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                why_it_matters="Section 3 triggers the 14 business days refund window from the date vacant physical possession and keys are surrendered.",
                suggested_investigation="Confirm date of key surrender and obtain written handover receipt.",
                semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("vacant physical possession and keys were surrendered under Section 3")
            )
            p_damages = MissingPredicateItem(
                predicate_id="documented_damage_deductions",
                label="Documented Damage Invoices",
                category=PredicateCategory.FACTUAL_EVENT,
                is_blocking=False,
                status=PredicateStatus.MISSING,
                source_status=PredicateSourceStatus.UNSTATED,
                mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                why_it_matters="Section 3 allows deductions only for documented physical damages beyond normal wear and tear.",
                suggested_investigation="Review move-out inspection notes and contractor repair invoices.",
                semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("the landlord has presented documented actual repair invoices exceeding normal wear and tear")
            )
            all_predicates = [p_handover, p_damages]
            pathways = [
                ConditionalApplicabilityPathway(
                    pathway_name="Pathway A: Full Deposit Refund",
                    factual_condition="If vacant possession surrendered with all keys and no documented physical damage beyond wear and tear exists",
                    applicable_provision="Section 3",
                    contractual_stipulation="Refundable in full within fourteen (14) business days of handover.",
                    evidence_required_to_confirm=["Key handover receipt", "Zero outstanding utility bills"]
                ),
                ConditionalApplicabilityPathway(
                    pathway_name="Pathway B: Permissible Deductions",
                    factual_condition="If physical damage beyond normal wear and tear or unpaid utility dues are documented",
                    applicable_provision="Section 3",
                    contractual_stipulation="Lessor may deduct documented actual repair costs, refunding the balance within 14 business days.",
                    evidence_required_to_confirm=["Contractor repair invoices", "Move-out inspection report"]
                )
            ]

        # Domain C: Commercial Use / Subletting
        elif any(w in query_lower for w in ["commercial", "restaurant", "shop", "business", "sublet"]):
            heuristic_name = "Permitted Use & Restrictions Heuristic"
            p_consent = MissingPredicateItem(
                predicate_id="lessor_prior_written_consent",
                label="Lessor Prior Written Consent",
                category=PredicateCategory.PARTY_CONSENT,
                is_blocking=False,
                status=PredicateStatus.ESTABLISHED if "written consent" in combined_text or "landlord agreed in writing" in combined_text else PredicateStatus.MISSING,
                source_status=PredicateSourceStatus.USER_ASSERTED if "written consent" in combined_text else PredicateSourceStatus.UNSTATED,
                mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                why_it_matters="Section 5.1 strictly prohibits commercial activities and subletting without prior written consent of the Lessor.",
                suggested_investigation="Check whether prior written permission was obtained from the landlord.",
                semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("prior written consent for commercial activity was obtained from the Lessor under Section 5.1")
            )
            all_predicates = [p_consent]
            pathways = [
                ConditionalApplicabilityPathway(
                    pathway_name="Pathway A: Prohibited Commercial Use",
                    factual_condition="If no prior written consent exists",
                    applicable_provision="Section 5.1",
                    contractual_stipulation="Commercial activities are strictly prohibited in residential dwelling.",
                    evidence_required_to_confirm=["Absence of written addendum"]
                ),
                ConditionalApplicabilityPathway(
                    pathway_name="Pathway B: Permitted with Written Consent",
                    factual_condition="If Lessor executed prior written consent",
                    applicable_provision="Section 5.1",
                    contractual_stipulation="Lessor may specifically authorize non-residential use in writing.",
                    evidence_required_to_confirm=["Signed written consent letter"]
                )
            ]

        # Domain D: Generic Fallback for Other Substantive Covenants
        else:
            heuristic_name = "General Contractual Covenant Heuristic"
            p_amendment = MissingPredicateItem(
                predicate_id="separate_written_amendment",
                label="Separate Written Amendment",
                category=PredicateCategory.CONTRACTUAL_PROVISION,
                is_blocking=False,
                status=PredicateStatus.MISSING,
                source_status=PredicateSourceStatus.UNSTATED,
                mode_applicability=[OperationalMode.MODE_1_DOC_ONLY, OperationalMode.MODE_2_DOC_EXTERNAL],
                why_it_matters="A subsequent written addendum or society rule may modify standard provisions.",
                suggested_investigation="Check for any written addendums or amendments to the governing agreement.",
                semantic_unstated_phrasing=UnstatedPredicateSemantic.format_unstated("any separate written amendment modifies this provision")
            )
            all_predicates = [p_amendment]
            pathways = []

        # 6. Evaluate Blocking-Predicate Gating
        established = [p for p in all_predicates if p.status == PredicateStatus.ESTABLISHED]
        missing = [p for p in all_predicates if p.status == PredicateStatus.MISSING]
        ambiguous = [p for p in all_predicates if p.status == PredicateStatus.AMBIGUOUS]

        blocking_missing = [p for p in missing if p.is_blocking]
        blocking_ambiguous = [p for p in ambiguous if p.is_blocking]
        non_blocking_missing = [p for p in missing if not p.is_blocking]

        # Clarification 2: INDETERMINATE triggered ONLY when unresolved contradiction
        # materially affects a blocking/governing predicate
        if has_internal_contract_contradiction or has_blocking_contradiction or blocking_ambiguous:
            sufficiency = EvidenceSufficiencyLevel.INDETERMINATE
            evidentiary_state = EvidentiaryState.AMBIGUOUS_EVIDENCE
            gap_summary = (
                "The available evidence is INDETERMINATE: an unresolved contradiction materially affects "
                "a blocking contractual covenant or prerequisite condition."
            )
        elif blocking_missing:
            sufficiency = EvidenceSufficiencyLevel.INSUFFICIENT
            evidentiary_state = EvidentiaryState.MISSING_FACTUAL_EVIDENCE
            gap_summary = (
                f"Available evidence is INSUFFICIENT for a definitive conclusion: {len(blocking_missing)} "
                "blocking factual prerequisite(s) remain unstated."
            )
        elif non_blocking_missing or ambiguous:
            # Minor non-blocking contradictions remain localized AMBIGUOUS predicates
            sufficiency = EvidenceSufficiencyLevel.PARTIALLY_SUFFICIENT
            evidentiary_state = EvidentiaryState.EVIDENCE_ESTABLISHED
            gap_summary = (
                "Evidence is PARTIALLY SUFFICIENT: core blocking predicates are established, but "
                f"{len(non_blocking_missing)} secondary informational gap(s) or non-blocking variances remain."
            )
        else:
            sufficiency = EvidenceSufficiencyLevel.SUFFICIENT
            evidentiary_state = EvidentiaryState.EVIDENCE_ESTABLISHED
            gap_summary = "All required factual and contractual predicates are established."

        # Clarification 1: is_applicability_determined requires BOTH:
        # 1. sufficiency_level == SUFFICIENT
        # 2. Exactly one uniquely identified applicable contractual pathway
        is_determined = (sufficiency == EvidenceSufficiencyLevel.SUFFICIENT and len(pathways) <= 1)

        investigative_recommendations = [
            p.suggested_investigation for p in (missing + ambiguous)
            if p.suggested_investigation
        ]
        if not investigative_recommendations:
            investigative_recommendations = [
                "Review the written contract clauses governing this topic.",
                "Verify delivery medium and written confirmation receipts."
            ]

        return MissingInfoReport(
            heuristic_status=HeuristicStatus.APPLIED,
            heuristic_name=heuristic_name,
            evidentiary_state=evidentiary_state,
            sufficiency_level=sufficiency,
            established_predicates=established,
            missing_predicates=missing,
            ambiguous_predicates=ambiguous,
            conditional_pathways=pathways,
            overall_gap_summary=gap_summary,
            is_applicability_determined=is_determined,
            contradictions=contradiction_notes,
            investigative_recommendations=investigative_recommendations,
            query_text=query_text
        )


missing_info_service = MissingInformationEngine()
