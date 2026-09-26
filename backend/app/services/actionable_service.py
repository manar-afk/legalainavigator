"""
Service implementation for Phase 9: Actionable Outputs Generator & Professional Consultation Brief.
Strict synthesis layer over Phase 1-8 engines.
Does NOT independently re-reason, manufacture new legal predicates, or predict court outcomes.
Enforces complete source-type-specific provenance, role resolution preservation,
neutral supervisory labeling, deterministic checklist priority, and strict non-re-reasoning boundary.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import re
import uuid

from ..models.situation import (
    UserRole,
    UserSituation,
    RoleResolutionStatus,
    SituationAnalysis,
    TimelineAnchor,
    FinancialEntity,
)
from ..models.comparison import (
    PartyRole,
    LegalTriggerType,
    ClauseEvidence,
    DocumentVersionMeta,
    ComparisonResult,
    ComparisonDifferenceItem,
    ContradictionDiagnosticItem,
    ReconciliationStatus,
    ComparisonRequest,
)
from ..models.missing_info import (
    MissingInfoReport,
    MissingPredicateItem,
    EvidenceSufficiencyLevel,
    EvidentiaryState,
)
from ..models.query import OperationalMode
from ..models.external_law import AuthoritativeLegalSource
from ..models.actionable import (
    ActionableSourceType,
    ActionableItemProvenance,
    ActionableLabel,
    CovenantClassification,
    DocumentDescribedCovenantItem,
    ChecklistCategory,
    ChecklistPriority,
    ActionableChecklistItem,
    LawyerQuestionItem,
    ReviewFlagItem,
    RoleResolutionProfile,
    ProfessionalConsultationBrief,
    ActionableOutputsContainer,
    ActionableGenerateRequest,
)

from .situation_service import situation_service
from .missing_info_service import missing_info_service
from .comparison_service import comparison_service
from .document_parser import document_store


class ActionableService:
    """
    Synthesizes Phase 1-8 outputs into audit-grade, evidence-linked actionable artifacts:
    1. Professional Consultation Brief
    2. Document-Described Covenants Matrix
    3. Deterministic Actionable Preparation Checklist
    4. Markdown Brief Text for Export
    """

    def generate_actionable_outputs(
        self,
        doc_ids: List[str],
        situation_description: Optional[str] = None,
        declared_role: Optional[UserRole] = None,
        comparison_doc_id: Optional[str] = None,
        query_text: Optional[str] = None,
        operational_mode: str = "mode_1_doc_only",
        precomputed_situation: Optional[SituationAnalysis] = None,
        precomputed_missing_info: Optional[MissingInfoReport] = None,
        precomputed_comparison: Optional[ComparisonResult] = None,
        external_law_sources: Optional[List[AuthoritativeLegalSource]] = None,
    ) -> ActionableOutputsContainer:
        """
        Main synthesis pipeline.
        Consumes established Phase 4-8 entities and formats actionable outputs without re-reasoning.
        """
        # Step 1: Resolve Document Texts & Metadata
        doc_a_id = doc_ids[0] if doc_ids else None
        governing_docs: List[DocumentVersionMeta] = []
        doc_a_name = None
        doc_a_text = ""
        doc_b_obj = None

        if doc_a_id:
            doc_a_obj = document_store.get_document(doc_a_id)
            doc_a_name = doc_a_obj.filename if doc_a_obj else f"{doc_a_id}.txt"
            doc_a_text = document_store.get_raw_text(doc_a_id) or ""
            meta_a = comparison_service.extract_document_version_meta(doc_a_id, doc_a_name, doc_a_text)
            governing_docs.append(meta_a)

            doc_b_obj = document_store.get_document(comparison_doc_id) if comparison_doc_id else None
            if doc_b_obj and comparison_doc_id:
                doc_b_text = document_store.get_raw_text(comparison_doc_id) or ""
                meta_b = comparison_service.extract_document_version_meta(doc_b_obj.doc_id, doc_b_obj.filename, doc_b_text)
                governing_docs.append(meta_b)

        # Step 2: Resolve Situation & Role Profile (Phase 6)
        user_sit: Optional[UserSituation] = None
        if precomputed_situation:
            sit_analysis = precomputed_situation
        else:
            if situation_description or declared_role:
                user_sit = UserSituation(
                    raw_description=situation_description or "",
                    declared_role=declared_role,
                )
            sit_analysis = situation_service.analyze_situation(
                situation=user_sit,
                query=query_text or "",
                doc_raw_text=doc_a_text,
            )

        role_profile = self._build_role_profile(sit_analysis)

        # Step 3: Resolve Comparison Context (Phase 8)
        comparison_result: Optional[ComparisonResult] = precomputed_comparison
        if not comparison_result and doc_a_id:
            if doc_b_obj:
                comparison_result = comparison_service.compare_documents(
                    ComparisonRequest(
                        doc_id_a=doc_a_id,
                        doc_id_b=doc_b_obj.doc_id,
                        operational_mode=operational_mode,
                    )
                )
            elif doc_a_text:
                comparison_result = comparison_service.compare_documents(
                    ComparisonRequest(
                        doc_id_a=doc_a_id,
                        doc_id_b=None,
                        operational_mode=operational_mode,
                    )
                )

        # Step 4: Resolve Missing Info & Gatekeeper Context (Phase 7)
        missing_info_report: Optional[MissingInfoReport] = precomputed_missing_info
        if not missing_info_report:
            op_mode = OperationalMode.MODE_2_DOC_EXTERNAL if operational_mode == "mode_2_doc_external" else (
                OperationalMode.MODE_3_GENERAL_NO_DOC if operational_mode == "mode_3_general_no_doc" or not doc_a_id else OperationalMode.MODE_1_DOC_ONLY
            )
            missing_info_report = missing_info_service.detect_missing_information(
                query=query_text or "What are the termination requirements?",
                situation=user_sit,
                situation_analysis=sit_analysis,
                doc_raw_text=doc_a_text,
                operational_mode=op_mode,
            )

        # Step 5: Extract Document-Described Covenants Matrix
        covenants_matrix: List[DocumentDescribedCovenantItem] = []
        if doc_a_id and doc_a_text:
            covenants_matrix = self._build_covenants_matrix(
                doc_id=doc_a_id,
                doc_name=doc_a_name or f"{doc_a_id}.txt",
                doc_text=doc_a_text,
                comparison_result=comparison_result,
            )

        # Step 6: Formulate Evidence-Linked Curated Questions for Counsel
        targeted_questions = self._build_lawyer_questions(
            missing_info_report=missing_info_report,
            comparison_result=comparison_result,
            covenants_matrix=covenants_matrix,
            operational_mode=operational_mode,
            external_law_sources=external_law_sources,
        )

        # Step 7: Formulate Neutral Review Flags (Section 14 labels only, zero risk scores)
        review_flags = self._build_review_flags(
            missing_info_report=missing_info_report,
            comparison_result=comparison_result,
            covenants_matrix=covenants_matrix,
            role_profile=role_profile,
        )

        # Step 8: Build Deterministic Preparation Checklist
        checklist = self._build_actionable_checklist(
            missing_info_report=missing_info_report,
            comparison_result=comparison_result,
            governing_docs=governing_docs,
            query_text=query_text or "",
            covenants_matrix=covenants_matrix,
        )

        # Step 9: Synthesize Plain-Language Overview (with Mode 2 3-part separation if applicable)
        plain_overview = self._synthesize_plain_language_overview(
            covenants_matrix=covenants_matrix,
            missing_info_report=missing_info_report,
            comparison_result=comparison_result,
            operational_mode=operational_mode,
            external_law_sources=external_law_sources,
        )

        # Step 10: Extract Missing Facts to Clarify from Gatekeeper
        missing_facts = [
            f"You have not stated {p.description.lower() if p.description else (p.label or p.predicate_id)} ({p.suggested_investigation or 'Clarify with evidence'})."
            for p in missing_info_report.missing_predicates
            if p.status.value in ["missing", "unstated", "ambiguous"]
        ] if missing_info_report else []

        # Key contractual provisions with character provenance
        key_provisions: List[ClauseEvidence] = [c.clause_evidence for c in covenants_matrix]

        # Mode 2 external statutory context
        external_context: Optional[List[AuthoritativeLegalSource]] = (
            external_law_sources if operational_mode == "mode_2_doc_external" and external_law_sources else None
        )

        safe_summary = (
            situation_service.sanitize_untrusted_situation(situation_description.strip())
            if situation_description and situation_description.strip()
            else "User has not provided an explicit situation narrative."
        )

        # Build Consultation Brief
        consultation_brief = ProfessionalConsultationBrief(
            generated_at=datetime.now(timezone.utc).isoformat(),
            client_situation_summary=safe_summary,
            role_profile=role_profile,
            governing_documents=governing_docs,
            key_contractual_provisions=key_provisions,
            targeted_questions_for_counsel=targeted_questions,
            missing_facts_to_clarify=missing_facts,
            identified_inconsistencies_and_review_flags=review_flags,
            plain_language_overview=plain_overview,
            operational_mode=operational_mode,
            external_statutory_context=external_context,
        )

        # Generate Exportable Markdown
        markdown_text = self._format_markdown_brief(
            brief=consultation_brief,
            covenants=covenants_matrix,
            checklist=checklist,
        )

        return ActionableOutputsContainer(
            consultation_brief=consultation_brief,
            covenants_matrix=covenants_matrix,
            preparation_checklist=checklist,
            markdown_brief_text=markdown_text,
        )

    # =========================================================================
    # INTERNAL BUILDERS (SYNTHESIS ONLY - ZERO INDEPENDENT RE-REASONING)
    # =========================================================================

    def _build_role_profile(self, sit_analysis: SituationAnalysis) -> RoleResolutionProfile:
        """
        Preserves exact Phase 6 role semantics and uncertainty.
        Never defaults inferred_role to synthetic GENERAL if none was inferred.
        """
        inferred = None
        if sit_analysis.role_resolution_status != RoleResolutionStatus.ROLE_NEUTRAL:
            if sit_analysis.inferred_role and sit_analysis.inferred_role != UserRole.GENERAL:
                inferred = sit_analysis.inferred_role

        status = sit_analysis.role_resolution_status
        if sit_analysis.declared_role == UserRole.GENERAL and inferred is None and status == RoleResolutionStatus.DECLARED_BY_USER:
            status = RoleResolutionStatus.ROLE_NEUTRAL

        uncertainty_note = None
        if status == RoleResolutionStatus.UNRESOLVED_CONFLICT:
            uncertainty_note = (
                "Role conflict detected between declared role and situation narrative. "
                "Phase 9 preserves this uncertainty and does not assume a governing role. "
                "Please clarify the exact legal relationship with legal counsel."
            )
        elif status == RoleResolutionStatus.INFERRED_LOW_CONFIDENCE:
            uncertainty_note = "Role inference has low confidence. Please verify your role."

        return RoleResolutionProfile(
            declared_role=sit_analysis.declared_role,
            inferred_role=inferred,
            role_confidence=sit_analysis.role_confidence,
            role_evidence=[sit_analysis.role_evidence] if isinstance(sit_analysis.role_evidence, str) and sit_analysis.role_evidence else (sit_analysis.role_evidence if isinstance(sit_analysis.role_evidence, list) else []),
            role_resolution_status=status,
            role_uncertainty_note=uncertainty_note,
        )

    def _build_covenants_matrix(
        self,
        doc_id: str,
        doc_name: str,
        doc_text: str,
        comparison_result: Optional[ComparisonResult],
    ) -> List[DocumentDescribedCovenantItem]:
        """
        Builds matrix of Document-Described Covenants.
        Explicitly frames items as textually described, not legally adjudicated.
        """
        items: List[DocumentDescribedCovenantItem] = []
        raw_clauses = comparison_service.extract_clause_evidences(doc_id, doc_name, doc_text)

        for cl in raw_clauses:
            # Classify covenant type
            cov_type = CovenantClassification.OBLIGATION
            title = cl.section_title
            label = ActionableLabel.IMPORTANT
            condition = None
            is_cond = False
            deadline = None

            if cl.trigger_type == LegalTriggerType.FINANCIAL_PAYMENT:
                cov_type = CovenantClassification.FINANCIAL_PAYMENT
                title = f"Payment Covenant: {cl.section_title}"
            elif cl.trigger_type == LegalTriggerType.CONVENIENCE_NO_FAULT:
                cov_type = CovenantClassification.RIGHT
                title = "Termination for Convenience (No-Fault)"
                deadline = f"Advance Notice: {cl.extracted_value}" if cl.extracted_value else None
            elif cl.trigger_type == LegalTriggerType.DEFAULT_MATERIAL_BREACH:
                cov_type = CovenantClassification.PROCEDURAL_NOTICE
                title = "Default & Material Breach Procedure"
                deadline = f"Cure Period: {cl.extracted_value}" if cl.extracted_value else None
                is_cond = True
                condition = "Upon uncured default or non-payment"
            elif cl.trigger_type == LegalTriggerType.LOCK_IN_COMPLIANCE:
                cov_type = CovenantClassification.RESTRICTION
                title = "Mandatory Lock-in Period Restriction"
                deadline = f"Duration: {cl.extracted_value}" if cl.extracted_value else None
            elif cl.trigger_type == LegalTriggerType.UNCLASSIFIED:
                cov_type = CovenantClassification.OBLIGATION
                label = ActionableLabel.UNCLEAR

            prov = ActionableItemProvenance(
                source_type=ActionableSourceType.DOCUMENT_PROVISION,
                source_ref=f"{cl.section_number} ({doc_name})",
                document_id=doc_id,
                document_name=doc_name,
                section_or_title=cl.section_title,
                exact_quote=cl.exact_quote,
                char_start=cl.char_start,
                char_end=cl.char_end,
            )

            desc = f"Section {cl.section_number} textually states: \"{cl.exact_quote}\""

            items.append(
                DocumentDescribedCovenantItem(
                    covenant_type=cov_type,
                    title=title,
                    summary_description=desc,
                    obligated_party=cl.obligated_party,
                    beneficiary_party=cl.beneficiary_party,
                    trigger_type=cl.trigger_type,
                    neutral_label=label,
                    clause_evidence=cl,
                    associated_deadline=deadline,
                    is_conditional=is_cond,
                    condition_precedent=condition,
                    provenance=prov,
                    origin_reference_id=f"{doc_id}:{cl.section_number}",
                )
            )

        return items

    def _build_lawyer_questions(
        self,
        missing_info_report: Optional[MissingInfoReport],
        comparison_result: Optional[ComparisonResult],
        covenants_matrix: List[DocumentDescribedCovenantItem],
        operational_mode: str,
        external_law_sources: Optional[List[AuthoritativeLegalSource]],
    ) -> List[LawyerQuestionItem]:
        """
        Formulates curated questions for counsel with backward traceability pointers.
        Every question maps directly to an established Phase 4-8 entity.
        """
        questions: List[LawyerQuestionItem] = []

        # 1. Questions from Phase 7 Missing Predicates
        if missing_info_report:
            for pred in missing_info_report.missing_predicates:
                if pred.status.value in ["missing", "unstated", "ambiguous"]:
                    pred_name = pred.label or pred.predicate_id
                    prov = ActionableItemProvenance(
                        source_type=ActionableSourceType.GATEKEEPER_DERIVED,
                        source_ref=f"Phase 7 Predicate: {pred_name}",
                        document_id=pred.provenance.source_ref if pred.provenance else None,
                        exact_quote=pred.provenance.exact_quote if pred.provenance else None,
                        char_start=pred.provenance.start_char if pred.provenance else None,
                        char_end=pred.provenance.end_char if pred.provenance else None,
                    )
                    questions.append(
                        LawyerQuestionItem(
                            question_text=f"How does the lack of verified factual evidence regarding '{pred_name}' affect the applicability of governing contractual terms?",
                            context_rationale=f"The gatekeeper flagged '{pred_name}' as {pred.status.value}. Contractual prerequisites require verification.",
                            origin_phase="Phase 7 Missing Information Gatekeeper",
                            origin_reference_id=pred.predicate_id,
                            supporting_evidence_refs=[prov],
                            neutral_label=ActionableLabel.MISSING_INFORMATION if pred.is_blocking else ActionableLabel.REVIEW,
                        )
                    )

            # Questions from Phase 7 Pathways
            for idx, path in enumerate(missing_info_report.conditional_pathways):
                path_ref = path.applicable_provision or f"Pathway_{idx+1}"
                questions.append(
                    LawyerQuestionItem(
                        question_text=f"Under our factual circumstances, does the situation fall under '{path.pathway_name}' ({path_ref})?",
                        context_rationale=f"Pathway '{path.pathway_name}' requires satisfying condition: {path.factual_condition}.",
                        origin_phase="Phase 7 Conditional Applicability Pathway",
                        origin_reference_id=f"pathway_{idx+1}",
                        supporting_evidence_refs=[
                            ActionableItemProvenance(
                                source_type=ActionableSourceType.GATEKEEPER_DERIVED,
                                source_ref=f"Pathway: {path.pathway_name}",
                            )
                        ],
                        neutral_label=ActionableLabel.REVIEW,
                    )
                )

        # 2. Questions from Phase 8 Contradictions & Differences
        if comparison_result:
            for diag in comparison_result.contradictions:
                prov_a = ActionableItemProvenance(
                    source_type=ActionableSourceType.COMPARISON_DERIVED,
                    source_ref=f"{diag.provision_a.section_number} ({diag.provision_a.doc_name})",
                    document_id=diag.provision_a.doc_id,
                    exact_quote=diag.provision_a.exact_quote,
                    char_start=diag.provision_a.char_start,
                    char_end=diag.provision_a.char_end,
                )
                prov_b = ActionableItemProvenance(
                    source_type=ActionableSourceType.COMPARISON_DERIVED,
                    source_ref=f"{diag.provision_b.section_number} ({diag.provision_b.doc_name})",
                    document_id=diag.provision_b.doc_id,
                    exact_quote=diag.provision_b.exact_quote,
                    char_start=diag.provision_b.char_start,
                    char_end=diag.provision_b.char_end,
                )
                questions.append(
                    LawyerQuestionItem(
                        question_text=f"Given that {diag.provision_a.section_number} specifies {diag.provision_a.extracted_value} while {diag.provision_b.section_number} specifies {diag.provision_b.extracted_value}, which mandate legally controls under governing rules of contract construction?",
                        context_rationale=diag.conflict_analysis,
                        origin_phase="Phase 8 Contradiction Engine",
                        origin_reference_id=diag.contradiction_id,
                        supporting_evidence_refs=[prov_a, prov_b],
                        neutral_label=ActionableLabel.POTENTIAL_INCONSISTENCY,
                    )
                )

            # Unverified relationship question if applicable
            if comparison_result.relationship_status.value == "unverified_relationship":
                questions.append(
                    LawyerQuestionItem(
                        question_text="The relationship between the provided agreements is textually unlinked. Can you confirm whether Document B supersedes, supplements, or operates independently of Document A?",
                        context_rationale="No express amendment cross-reference, integration clause, or restatement intent was textually detected.",
                        origin_phase="Phase 8 Document Relationship Engine",
                        origin_reference_id="rel_unverified",
                        supporting_evidence_refs=[
                            ActionableItemProvenance(
                                source_type=ActionableSourceType.COMPARISON_DERIVED,
                                source_ref="Relationship: UNVERIFIED_RELATIONSHIP",
                            )
                        ],
                        neutral_label=ActionableLabel.REQUIRES_PROFESSIONAL_REVIEW,
                    )
                )

        # 3. Questions from Phase 5 External Law (Mode 2 only!)
        if operational_mode == "mode_2_doc_external" and external_law_sources:
            for law in external_law_sources:
                prov_law = ActionableItemProvenance(
                    source_type=ActionableSourceType.EXTERNAL_LAW,
                    source_ref=f"{law.title}, {law.section_provision}",
                    exact_quote=law.exact_retrieved_text[:200] if law.exact_retrieved_text else None,
                )
                questions.append(
                    LawyerQuestionItem(
                        question_text=f"Does {law.section_provision} of {law.title} override or limit the contractual notice timeline in our jurisdiction ({law.jurisdiction})?",
                        context_rationale=f"Mode 2 identified statutory provision: {law.section_provision}. Local statutory tenancy mandates may imply mandatory protections.",
                        origin_phase="Phase 5 External Law Engine",
                        origin_reference_id=law.source_id,
                        supporting_evidence_refs=[prov_law],
                        neutral_label=ActionableLabel.REQUIRES_PROFESSIONAL_REVIEW,
                    )
                )

        # 4. Questions from Covenants with Unclassified Triggers
        for cov in covenants_matrix:
            if cov.trigger_type == LegalTriggerType.UNCLASSIFIED:
                questions.append(
                    LawyerQuestionItem(
                        question_text=f"What is the precise legal effect of {cov.clause_evidence.section_number} given its non-standard operational condition?",
                        context_rationale=f"The clause condition could not be conclusively categorized into standard convenience or default templates.",
                        origin_phase="Phase 4/8 Clause Interpretation",
                        origin_reference_id=cov.origin_reference_id,
                        supporting_evidence_refs=[cov.provenance],
                        neutral_label=ActionableLabel.UNCLEAR,
                    )
                )

        return questions

    def _build_review_flags(
        self,
        missing_info_report: Optional[MissingInfoReport],
        comparison_result: Optional[ComparisonResult],
        covenants_matrix: List[DocumentDescribedCovenantItem],
        role_profile: RoleResolutionProfile,
    ) -> List[ReviewFlagItem]:
        """
        Builds Neutral Review Flags strictly restricted to Section 14 neutral labels.
        ZERO risk scores, exposure claims, or predictions!
        """
        flags: List[ReviewFlagItem] = []

        # Role conflict review flag
        if role_profile.role_resolution_status == RoleResolutionStatus.UNRESOLVED_CONFLICT:
            flags.append(
                ReviewFlagItem(
                    label=ActionableLabel.UNCLEAR,
                    title="Role Resolution Uncertainty",
                    neutral_explanation="There is a discrepancy between the declared user role and the relationship described in the factual narrative. Clarification is recommended.",
                    origin_reference_id="role_conflict",
                    supporting_evidence=ActionableItemProvenance(
                        source_type=ActionableSourceType.USER_ASSERTION,
                        source_ref="User Situation Narrative",
                    ),
                )
            )

        # Phase 8 contradiction review flags
        if comparison_result:
            for diag in comparison_result.contradictions:
                flags.append(
                    ReviewFlagItem(
                        label=ActionableLabel.POTENTIAL_INCONSISTENCY,
                        title=f"Potential Inconsistency: {diag.title}",
                        neutral_explanation=f"Textual conflict detected between {diag.provision_a.section_number} ({diag.provision_a.extracted_value}) and {diag.provision_b.section_number} ({diag.provision_b.extracted_value}). Please verify with counsel.",
                        origin_reference_id=diag.contradiction_id,
                        supporting_evidence=ActionableItemProvenance(
                            source_type=ActionableSourceType.COMPARISON_DERIVED,
                            source_ref=f"{diag.provision_a.section_number} vs {diag.provision_b.section_number}",
                        ),
                    )
                )

            if comparison_result.unverified_conflicts_count > 0:
                flags.append(
                    ReviewFlagItem(
                        label=ActionableLabel.POTENTIAL_INCONSISTENCY,
                        title="Unverified Document Relationship Conflict",
                        neutral_explanation="The agreements contain conflicting terms but no express amendment link or integration clause was found. Their governing priority is unverified.",
                        origin_reference_id="unverified_conflict",
                        supporting_evidence=ActionableItemProvenance(
                            source_type=ActionableSourceType.COMPARISON_DERIVED,
                            source_ref="Relationship: UNVERIFIED_RELATIONSHIP",
                        ),
                    )
                )

        # Phase 7 missing blocking predicate flags
        if missing_info_report:
            for pred in missing_info_report.missing_predicates:
                if pred.is_blocking and pred.status.value in ["missing", "unstated"]:
                    pred_name = pred.label or pred.predicate_id
                    flags.append(
                        ReviewFlagItem(
                            label=ActionableLabel.MISSING_INFORMATION,
                            title=f"Missing Factual Precondition: {pred_name}",
                            neutral_explanation=f"Contractual applicability cannot be determined until evidence regarding '{pred_name}' is established.",
                            origin_reference_id=pred.predicate_id,
                            supporting_evidence=ActionableItemProvenance(
                                source_type=ActionableSourceType.GATEKEEPER_DERIVED,
                                source_ref=f"Phase 7 Predicate: {pred_name}",
                            ),
                        )
                    )

        # Lock-in compliance flag
        for cov in covenants_matrix:
            if cov.trigger_type == LegalTriggerType.LOCK_IN_COMPLIANCE:
                flags.append(
                    ReviewFlagItem(
                        label=ActionableLabel.IMPORTANT,
                        title=f"Important Covenant: {cov.title}",
                        neutral_explanation="Agreement specifies a mandatory lock-in period. Early convenience termination is textually prohibited during this window.",
                        origin_reference_id=cov.origin_reference_id,
                        supporting_evidence=cov.provenance,
                    )
                )

        return flags

    def _build_actionable_checklist(
        self,
        missing_info_report: Optional[MissingInfoReport],
        comparison_result: Optional[ComparisonResult],
        governing_docs: List[DocumentVersionMeta],
        query_text: str,
        covenants_matrix: List[DocumentDescribedCovenantItem],
    ) -> List[ActionableChecklistItem]:
        """
        Builds deterministic preparation checklist.
        Priority is strictly BLOCKING (gatekeeper blocking predicate or inquiry-relevant contradiction)
        or STANDARD. Never uses subjective importance rankings.
        """
        checklist: List[ActionableChecklistItem] = []

        # 1. Tasks from Phase 7 Missing Predicates
        if missing_info_report:
            for pred in missing_info_report.missing_predicates:
                if pred.status.value in ["missing", "unstated", "ambiguous"]:
                    priority = ChecklistPriority.BLOCKING if pred.is_blocking else ChecklistPriority.STANDARD
                    pred_name = pred.label or pred.predicate_id
                    task_desc = pred.description or pred.suggested_investigation or f"Clarify {pred_name}"
                    prov = ActionableItemProvenance(
                        source_type=ActionableSourceType.GATEKEEPER_DERIVED,
                        source_ref=f"Predicate: {pred_name}",
                        document_id=pred.provenance.source_ref if pred.provenance else None,
                        exact_quote=pred.provenance.exact_quote if pred.provenance else None,
                        char_start=pred.provenance.start_char if pred.provenance else None,
                        char_end=pred.provenance.end_char if pred.provenance else None,
                    )
                    checklist.append(
                        ActionableChecklistItem(
                            category=ChecklistCategory.FACTUAL_VERIFICATION,
                            task_description=f"Establish whether: {task_desc}",
                            rationale=f"Gatekeeper identified this prerequisite as {pred.status.value}; required to evaluate contractual applicability.",
                            priority=priority,
                            provenance=prov,
                            origin_reference_id=pred.predicate_id,
                        )
                    )

        # 2. Tasks from Phase 8 Contradictions (Inquiry-Relevance Gated!)
        if comparison_result:
            for diag in comparison_result.contradictions:
                # Gating: is the contradiction materially relevant to current query/pathway?
                is_relevant = False
                query_lower = query_text.lower()
                diag_lower = (diag.title + " " + diag.conflict_analysis).lower()

                notice_terms = ["notice", "terminate", "vacate", "leave", "evict", "end"]
                rent_terms = ["rent", "pay", "money", "deposit", "financial", "fee"]

                if any(t in query_lower for t in notice_terms) and any(t in diag_lower for t in notice_terms):
                    is_relevant = True
                elif any(t in query_lower for t in rent_terms) and any(t in diag_lower for t in rent_terms):
                    is_relevant = True
                elif not query_text.strip():
                    is_relevant = True

                priority = ChecklistPriority.BLOCKING if is_relevant else ChecklistPriority.STANDARD
                prov = ActionableItemProvenance(
                    source_type=ActionableSourceType.COMPARISON_DERIVED,
                    source_ref=f"Contradiction: {diag.title}",
                    document_id=diag.provision_a.doc_id,
                    exact_quote=diag.provision_a.exact_quote,
                    char_start=diag.provision_a.char_start,
                    char_end=diag.provision_a.char_end,
                )
                checklist.append(
                    ActionableChecklistItem(
                        category=ChecklistCategory.QUESTIONS_TO_CLARIFY,
                        task_description=f"Clarify conflicting terms between {diag.provision_a.section_number} and {diag.provision_b.section_number}",
                        rationale=f"Both clauses specify incompatible mandates ({diag.provision_a.extracted_value} vs {diag.provision_b.extracted_value}).",
                        priority=priority,
                        provenance=prov,
                        origin_reference_id=diag.contradiction_id,
                    )
                )

        # 3. Document Gathering Task
        for meta in governing_docs:
            if meta.execution_status.value in ["blank_or_unsigned", "dated_unverified_signature", "undated"]:
                checklist.append(
                    ActionableChecklistItem(
                        category=ChecklistCategory.DOCUMENT_GATHERING,
                        task_description=f"Locate a fully executed, signed, and dated copy of '{meta.doc_name}'",
                        rationale=f"Document execution status is currently recorded as '{meta.execution_status.value}'. Unsigned documents require verification.",
                        priority=ChecklistPriority.STANDARD,
                        provenance=ActionableItemProvenance(
                            source_type=ActionableSourceType.DOCUMENT_PROVISION,
                            source_ref=f"Execution Status ({meta.doc_name})",
                            document_id=meta.doc_id,
                            document_name=meta.doc_name,
                        ),
                        origin_reference_id=f"exec_{meta.doc_id}",
                    )
                )

        # 4. Purely Synthesized Preparation Instructions (Explicitly marked SYNTHESIZED_PREPARATION)
        checklist.append(
            ActionableChecklistItem(
                category=ChecklistCategory.DOCUMENT_GATHERING,
                task_description="Compile all written notices, payment transfer receipts, and email correspondence into a chronological folder.",
                rationale="Having dated records organized chronologically assists legal counsel in reviewing notice compliance.",
                priority=ChecklistPriority.STANDARD,
                provenance=ActionableItemProvenance(
                    source_type=ActionableSourceType.SYNTHESIZED_PREPARATION,
                    source_ref="synthesized_procedural_step",
                ),
                origin_reference_id="synth_prep_chrono_folder",
            )
        )
        checklist.append(
            ActionableChecklistItem(
                category=ChecklistCategory.QUESTIONS_TO_CLARIFY,
                task_description="Preserve all written communications, payment or contribution records, and note key communication dates.",
                rationale="Provides counsel with an immediate chronological factual record and verified supporting documentation.",
                priority=ChecklistPriority.STANDARD,
                provenance=ActionableItemProvenance(
                    source_type=ActionableSourceType.SYNTHESIZED_PREPARATION,
                    source_ref="synthesized_procedural_step",
                ),
                origin_reference_id="synth_prep_print_brief",
            )
        )

        return checklist

    def _synthesize_plain_language_overview(
        self,
        covenants_matrix: List[DocumentDescribedCovenantItem],
        missing_info_report: Optional[MissingInfoReport],
        comparison_result: Optional[ComparisonResult],
        operational_mode: str,
        external_law_sources: Optional[List[AuthoritativeLegalSource]],
    ) -> str:
        """
        Synthesizes plain-language summary.
        In Mode 2, enforces 3-part structured separation:
        Part A: What the document says
        Part B: What the authoritative external statute says
        Part C: What remains uncertain regarding legal applicability
        """
        if operational_mode == "mode_2_doc_external" and external_law_sources:
            part_a_clauses = [f"- Section {c.clause_evidence.section_number}: {c.summary_description}" for c in covenants_matrix[:3]]
            part_a = "### Part A: What the Provided Agreement States\n" + ("\n".join(part_a_clauses) if part_a_clauses else "- No specific agreement clauses were extracted.")

            part_b_statutes = [f"- {s.title} ({s.section_provision}): {s.exact_retrieved_text[:180]}..." for s in external_law_sources]
            part_b = "### Part B: What Authoritative External Statutes State\n" + "\n".join(part_b_statutes)

            statute_titles = ", ".join(dict.fromkeys(s.title for s in external_law_sources if s.title)) or "statutory rules"
            part_c = (
                "### Part C: Uncertainty & Questions for Legal Review\n"
                f"- Whether governing statutory provisions ({statute_titles}) supersede contractual notice terms.\n"
                "- Whether statutory notice protections require specific dispatch formats under local rules."
            )
            return f"{part_a}\n\n{part_b}\n\n{part_c}"

        # Standard Mode 1 or Mode 3 Synthesis
        if not covenants_matrix:
            return "This assessment is based on the factual situation provided and applicable legal principles (no contract document was attached)."

        lines = [
            "This summary synthesizes the textual provisions governing your situation based on the uploaded agreement:",
        ]
        for c in covenants_matrix:
            lines.append(f"- **{c.title}** ({c.clause_evidence.section_number}): {c.summary_description}")

        if comparison_result and comparison_result.total_differences_analyzed > 0:
            lines.append(f"\n**Document Version Context**: {comparison_result.summary_of_changes}")

        return "\n".join(lines)

    def _format_markdown_brief(
        self,
        brief: ProfessionalConsultationBrief,
        covenants: List[DocumentDescribedCovenantItem],
        checklist: List[ActionableChecklistItem],
    ) -> str:
        """
        Generates a clean, professionally formatted Markdown document ready to export/download.
        """
        lines = [
            "# Professional Legal Consultation Brief",
            f"**Generated On**: {brief.generated_at}  ",
            "",
            "> [!IMPORTANT]",
            f"> {brief.disclaimer}",
            "",
            "---",
            "",
            "## 1. Client Situation & Role Profile",
            f"**Client Situation Summary**:\n> {brief.client_situation_summary}",
            "",
            f"- **Declared Role**: `{brief.role_profile.declared_role or 'Unspecified'}`",
            f"- **Inferred Role**: `{brief.role_profile.inferred_role or 'Unresolved / Neutral'}`",
            f"- **Resolution Status**: `{brief.role_profile.role_resolution_status.value}`",
        ]

        if brief.role_profile.role_uncertainty_note:
            lines.append(f"> [!WARNING]\n> **Role Uncertainty**: {brief.role_profile.role_uncertainty_note}")

        lines.extend([
            "",
            "## 2. Governing Documents & Execution Status",
        ])
        if brief.governing_documents:
            for doc in brief.governing_documents:
                lines.append(f"- **{doc.doc_name}** (`{doc.doc_id}`): Role = `{doc.document_role.value}`, Status = `{doc.execution_status.value}`")
        else:
            lines.append("- *No document was provided for textual analysis.*")

        lines.extend([
            "",
            "## 3. Document-Described Covenants Matrix",
            "*Note: The following entries describe what the contract text states. They do not constitute an independent legal determination of enforceability.*",
            "",
        ])
        if covenants:
            lines.append("| Covenant Title | Party Obligated | Trigger Type | Stated Requirement / Quote |")
            lines.append("|---|---|---|---|")
            for cov in covenants:
                quote_clean = cov.clause_evidence.exact_quote.replace("\n", " ").replace("|", "\\|")[:90]
                lines.append(f"| **{cov.title}** | `{cov.obligated_party.value}` | `{cov.trigger_type.value}` | {quote_clean}... |")
        else:
            lines.append("*No contractual provisions were extracted (no document provided).*")

        lines.extend([
            "",
            "## 4. Key Questions for Legal Counsel",
        ])
        for idx, q in enumerate(brief.targeted_questions_for_counsel, 1):
            lines.append(f"### Q{idx}. {q.question_text}")
            lines.append(f"- **Context**: {q.context_rationale}")
            lines.append(f"- **Origin**: {q.origin_phase}")
            if q.supporting_evidence_refs:
                ev_str = ", ".join([f"`{e.source_ref}`" for e in q.supporting_evidence_refs])
                lines.append(f"- **Supporting Evidence Pointers**: {ev_str}")
            lines.append("")

        lines.extend([
            "## 5. Missing Factual Information to Clarify",
        ])
        if brief.missing_facts_to_clarify:
            for mf in brief.missing_facts_to_clarify:
                lines.append(f"- [ ] {mf}")
        else:
            lines.append("- *No material blocking factual preconditions were flagged as unstated.*")

        lines.extend([
            "",
            "## 6. Identified Inconsistencies & Review Flags",
        ])
        if brief.identified_inconsistencies_and_review_flags:
            for rf in brief.identified_inconsistencies_and_review_flags:
                lines.append(f"- **[{rf.label.value.upper()}] {rf.title}**: {rf.neutral_explanation}")
        else:
            lines.append("- *No internal contradictions or unverified conflicts identified.*")

        lines.extend([
            "",
            "## 7. Actionable Preparation Checklist",
        ])
        for item in checklist:
            p_tag = "**[BLOCKING]** " if item.priority == ChecklistPriority.BLOCKING else ""
            lines.append(f"- [ ] {p_tag}{item.task_description}  \n  *Rationale*: {item.rationale} (`Source: {item.provenance.source_type.value}`)")

        lines.extend([
            "",
            "---",
            "*Prepared using the Legal Information Navigator synthesis engine.*",
        ])

        return "\n".join(lines)


actionable_service = ActionableService()
