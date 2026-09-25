"""Benchmark Evaluation Runner executing all 14 evaluation cases against live engines."""

import os
import time
import re
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.models.document import DocumentMeta, DocumentChunk
from app.models.query import QueryRequest, IntentClassification, OperationalMode, QueryCategory
from app.models.response import GroundedAnswer
from app.models.situation import UserSituation, UserRole
from app.models.comparison import (
    ComparisonRequest,
    ComparisonResult,
    ReconciliationStatus,
    DocumentRelationshipStatus,
    ChangeType,
)
from app.models.missing_info import EvidenceSufficiencyLevel, EvidentiaryState

from app.services.document_parser import document_parser
from app.services.grounding_engine import grounding_engine
from app.services.mode_router import mode_router
from app.services.general_qa import general_qa_service
from app.services.external_law_service import external_law_service
from app.services.comparison_service import comparison_service
from app.services.retrieval import document_store

from .benchmark_cases import BENCHMARK_CASES, BenchmarkCase, BenchmarkGroundTruth
from .metrics import (
    ClaimCategory,
    EvaluatedClaim,
    CaseEvaluationResult,
    BenchmarkScorecard,
    aggregate_scorecard,
)


def classify_sentence(sentence: str) -> ClaimCategory:
    """Classifies an individual sentence into one of 6 ClaimCategory types."""
    s_lower = sentence.lower()
    
    # 1. Uncertainty / Abstention
    if any(p in s_lower for p in [
        "does not specify", "no corresponding clause", "silent on", "is silent",
        "does not contain", "no mention", "cannot determine", "you have not stated whether",
        "subjective", "neither inherently fair nor unfair", "inherently fair", "inherently unfair"
    ]):
        return ClaimCategory.UNCERTAINTY_ABSTENTION
        
    # 2. Process / Preparation / Disclaimer
    if any(p in s_lower for p in [
        "disclaimer", "legal advice", "consult a qualified", "consult an advocate",
        "advocate or attorney", "licensed attorney", "questions to ask", "actionable checklist",
        "next steps", "you may wish to", "consider verifying", "procedural step", "preparation"
    ]):
        return ClaimCategory.PROCESS_PREPARATION_STATEMENT
        
    # 3. User assertion restatement
    if any(p in s_lower for p in [
        "you stated that", "you mentioned that", "according to your description",
        "based on your situation", "you reported"
    ]):
        return ClaimCategory.USER_ASSERTION
        
    # 4. External law claim
    if any(p in s_lower for p in [
        "section 27", "indian contract act", "transfer of property act", "statutory",
        "statute", "under indian law", "supreme court", "high court", "established precedent",
        "section 106", "section 111"
    ]):
        return ClaimCategory.EXTERNAL_LAW_CLAIM
        
    # 5. Document grounded claim
    if any(p in s_lower for p in [
        "section", "clause", "agreement", "lease", "contract", "inr", "rupees", "deposit",
        "rent", "notice", "lock-in", "lessor", "lessee", "tenant", "landlord", "days",
        "terminate", "liability cap", "indemnif"
    ]):
        return ClaimCategory.DOCUMENT_GROUNDED_CLAIM
        
    # 6. General concept explanation
    return ClaimCategory.GENERAL_CONCEPT_EXPLANATION


def is_definitive_conclusion(text: str, forbidden_str: str) -> bool:
    """Checks if forbidden_str is asserted as a definitive legal verdict rather than issue framing or conditioning."""
    lower = text.lower()
    for match in re.finditer(re.escape(forbidden_str.lower()), lower):
        start = match.start()
        sent_start = max(0, lower.rfind(".", 0, start), lower.rfind("\n", 0, start))
        prefix = lower[sent_start:start]
        if any(un in prefix for un in ["whether", "depends on", "assessing", "determining", "court assesses"]):
            continue
        return True
    return False


class EvaluationRunner:
    """Automated benchmark harness executing the 14 archetype evaluation cases."""

    def __init__(self, root_dir: Optional[str] = None):
        if root_dir:
            self.root_dir = root_dir
        else:
            cwd = os.getcwd()
            if os.path.exists(os.path.join(cwd, "sample_documents")):
                self.root_dir = cwd
            elif os.path.exists(os.path.join(cwd, "..", "sample_documents")):
                self.root_dir = os.path.abspath(os.path.join(cwd, ".."))
            elif os.path.exists(r"c:\Users\tarun\Desktop\LegalAInavigator\sample_documents"):
                self.root_dir = r"c:\Users\tarun\Desktop\LegalAInavigator"
            else:
                self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    def _resolve_doc_path(self, rel_path: str) -> str:
        return os.path.join(self.root_dir, rel_path)

    def _load_doc_content(self, rel_path: str) -> str:
        full_path = self._resolve_doc_path(rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def run_case(self, case: BenchmarkCase) -> CaseEvaluationResult:
        """Executes a single benchmark case across the 6-stage deterministic pipeline."""
        start_time = time.perf_counter()
        failure_reasons: List[str] = []
        diagnostics: Dict[str, Any] = {}
        evaluated_claims: List[EvaluatedClaim] = []

        retrieval_acc = 1.0
        retrieval_spec = 1.0
        grounding_fid = 1.0
        answer_acc = 1.0
        citation_prec = 1.0
        completeness = 1.0
        hallucination_det = False
        approp_abstention = True
        missing_info_correct = True
        contradiction_correct = True

        gt: BenchmarkGroundTruth = case.ground_truth

        try:
            # === STAGE 1: Generated Output Acquisition ===
            uploaded_metas: List[DocumentMeta] = []
            if case.document_rel_paths:
                for rel_p in case.document_rel_paths:
                    text = self._load_doc_content(rel_p)
                    filename = os.path.basename(rel_p)
                    meta, _ = document_parser.parse_text_content(text, filename=filename)
                    uploaded_metas.append(meta)
            elif case.document_texts:
                for fname, txt in case.document_texts.items():
                    meta, _ = document_parser.parse_text_content(txt, filename=fname)
                    uploaded_metas.append(meta)

            primary_doc_id = uploaded_metas[0].doc_id if uploaded_metas else None
            primary_doc_name = uploaded_metas[0].filename if uploaded_metas else None

            # Handle Comparison Cases (4 & 5)
            if case.case_id in (4, 5):
                if len(uploaded_metas) < 2:
                    raise ValueError(f"Case {case.case_id} requires 2 documents.")
                comp_req = ComparisonRequest(
                    doc_id_a=uploaded_metas[0].doc_id,
                    doc_id_b=uploaded_metas[1].doc_id,
                )
                comp_result: ComparisonResult = comparison_service.compare_documents(comp_req)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                if case.case_id == 4:
                    if comp_result.relationship_status.value != gt.expected_relationship_status:
                        failure_reasons.append(
                            f"Expected relationship {gt.expected_relationship_status}, got {comp_result.relationship_status.value}"
                        )
                        contradiction_correct = False
                    
                    has_reconciled_mod = any(
                        d.reconciliation_status.value == gt.expected_reconciliation_status
                        and d.change_type.value == gt.expected_change_type
                        for d in comp_result.differences
                    )
                    if not has_reconciled_mod:
                        failure_reasons.append(
                            f"Expected at least one difference with reconciliation {gt.expected_reconciliation_status} and type {gt.expected_change_type}"
                        )
                        contradiction_correct = False
                    
                    summary_text = " ".join([d.bounded_textual_impact for d in comp_result.differences]) + " " + comp_result.summary_of_changes
                    for fig in gt.expected_figures:
                        if fig not in summary_text and fig not in str(comp_result):
                            failure_reasons.append(f"Figure '{fig}' not detected in comparison.")
                            answer_acc = 0.5
                    
                    if gt.expected_omitted_unmodified and comp_result.omitted_unmodified_count == 0:
                        failure_reasons.append("Expected omitted_unmodified_count >= 1, got 0")
                        completeness = 0.5

                    diagnostics["relationship_status"] = comp_result.relationship_status.value
                    diagnostics["differences_count"] = len(comp_result.differences)

                elif case.case_id == 5:
                    if comp_result.relationship_status.value != gt.expected_relationship_status:
                        failure_reasons.append(
                            f"Expected relationship {gt.expected_relationship_status}, got {comp_result.relationship_status.value}"
                        )
                        contradiction_correct = False
                    if comp_result.true_contradictions_count != gt.expected_true_contradictions_count:
                        failure_reasons.append(
                            f"Expected true_contradictions_count {gt.expected_true_contradictions_count}, got {comp_result.true_contradictions_count}"
                        )
                        contradiction_correct = False
                    diagnostics["relationship"] = comp_result.relationship_status.value
                    diagnostics["true_contradictions"] = comp_result.true_contradictions_count

                passed = len(failure_reasons) == 0
                return CaseEvaluationResult(
                    case_id=case.case_id,
                    archetype=case.archetype,
                    mode=case.mode.value,
                    passed=passed,
                    retrieval_accuracy=retrieval_acc,
                    retrieval_specificity=retrieval_spec,
                    grounding_fidelity=grounding_fid,
                    answer_accuracy=answer_acc,
                    citation_precision=citation_prec,
                    completeness=completeness,
                    hallucination_detected=hallucination_det,
                    appropriate_abstention=approp_abstention,
                    missing_info_gatekeeper_correct=missing_info_correct,
                    contradiction_detection_correct=contradiction_correct,
                    latency_ms=elapsed_ms,
                    failure_reasons=failure_reasons,
                    diagnostic_details=diagnostics,
                    evaluated_claims=evaluated_claims,
                )

            # Query Requests
            sit: Optional[UserSituation] = None
            if case.user_situation:
                sit = UserSituation(
                    raw_description=case.user_situation,
                    declared_role=UserRole(case.user_role) if case.user_role else None
                )

            q_req = QueryRequest(
                query=case.query,
                doc_ids=[primary_doc_id] if primary_doc_id else [],
                situation=sit,
                requested_mode=case.mode,
            )

            intent = mode_router.classify_and_route(q_req)

            if case.mode == OperationalMode.MODE_3_GENERAL_NO_DOC or intent.effective_mode == OperationalMode.MODE_3_GENERAL_NO_DOC:
                answer: GroundedAnswer = general_qa_service.answer_general_query(q_req, intent)
            elif case.mode == OperationalMode.MODE_2_DOC_EXTERNAL or intent.effective_mode == OperationalMode.MODE_2_DOC_EXTERNAL:
                answer: GroundedAnswer = external_law_service.answer_external_law_query(q_req, intent)
            else:
                answer: GroundedAnswer = grounding_engine.answer_document_query(q_req, intent)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            answer_text = (
                f"{answer.answer} {answer.what_this_means_in_plain_language} "
                f"{' '.join(answer.document_facts)} {answer.what_the_document_says or ''}"
            )

            # === STAGE 2 & 3: Claim Classification & Evidence Requirement ===
            raw_sentences = [s.strip() for s in re.split(r"[.\n]+", answer_text) if len(s.strip()) > 15]
            for s in raw_sentences:
                cat = classify_sentence(s)
                req_ev = cat in (ClaimCategory.DOCUMENT_GROUNDED_CLAIM, ClaimCategory.EXTERNAL_LAW_CLAIM)
                claim = EvaluatedClaim(
                    text=s,
                    category=cat,
                    requires_evidence=req_ev,
                    is_grounded=True,
                )
                evaluated_claims.append(claim)

            # === STAGE 4: Provenance Verification ===
            evidence_requiring_claims = [c for c in evaluated_claims if c.requires_evidence]
            if evidence_requiring_claims and not gt.expected_abstention:
                if len(answer.sources) == 0 and case.mode != OperationalMode.MODE_3_GENERAL_NO_DOC:
                    for c in evidence_requiring_claims:
                        if c.category == ClaimCategory.DOCUMENT_GROUNDED_CLAIM:
                            c.is_grounded = False
                            c.violation_detail = "No source citations provided for document-grounded claim."
                    hallucination_det = True
                    grounding_fid = 0.0

            # === STAGE 5: Ground-Truth Comparison ===
            # 1. Retrieval Recall & Specificity
            retrieved_sections = [
                str(c.section_number) for c in answer.sources if c.section_number
            ]
            source_quotes = " ".join([c.quote for c in answer.sources])

            if gt.expected_retrieval_ids or gt.expected_section_ids:
                exp_ids = gt.expected_retrieval_ids or gt.expected_section_ids
                matches = sum(1 for exp in exp_ids if any(exp in s for s in retrieved_sections) or exp in source_quotes)
                retrieval_acc = matches / max(1, len(exp_ids))
                if matches == 0:
                    failure_reasons.append(f"Expected sections {exp_ids} not found in retrieved citations: {retrieved_sections}")

            # Negative Retrieval (Forbidden False Positives)
            if gt.forbidden_false_positive_ids:
                found_forbidden = [
                    sec for sec in gt.forbidden_false_positive_ids
                    if any(sec in s for s in retrieved_sections)
                ]
                if found_forbidden:
                    retrieval_spec = max(0.0, 1.0 - (len(found_forbidden) / len(gt.forbidden_false_positive_ids)))
                    failure_reasons.append(f"Forbidden false positive sections retrieved: {found_forbidden}")

            # 2. Figures and Facts
            if gt.expected_figures:
                found_figs = [fig for fig in gt.expected_figures if fig.lower() in answer_text.lower()]
                if not found_figs:
                    answer_acc = 0.0
                    failure_reasons.append(f"Expected figure {gt.expected_figures} not found in answer.")

            # 3. Concepts
            if gt.expected_concepts:
                found_conc = [c for c in gt.expected_concepts if c.lower() in answer_text.lower()]
                if not found_conc:
                    completeness = 0.5
                    failure_reasons.append(f"Expected concept {gt.expected_concepts} missing from answer.")

            # 4. Forbidden Conclusions & Boundaries (Strict anti-hallucination)
            lower_ans = answer_text.lower()
            if gt.forbidden_conclusions:
                for bad_conclusion in gt.forbidden_conclusions:
                    if is_definitive_conclusion(lower_ans, bad_conclusion):
                        failure_reasons.append(f"Forbidden conclusion detected: '{bad_conclusion}'")
                        if case.case_id == 11:
                            hallucination_det = True
                        else:
                            approp_abstention = False

            # 5. Abstention & Contract Silence (Cases 7, 9, 14)
            if gt.expected_abstention:
                if case.case_id == 7:
                    is_silence = (
                        "does not specify" in lower_ans
                        or "no corresponding clause" in lower_ans
                        or "silent" in lower_ans
                        or "no mention" in lower_ans
                        or "not contain" in lower_ans
                        or len(answer.sources) == 0
                    )
                    if not is_silence:
                        approp_abstention = False
                        failure_reasons.append("Expected CONTRACT_SILENCE / abstention, but no silence phrasing found.")
                    diagnostics["evidentiary_state"] = "contract_silence" if is_silence else "unspecified"

                elif case.case_id == 9:
                    is_neutral = (
                        "neither" in lower_ans or "subjective" in lower_ans or "depends" in lower_ans
                        or "without taking sides" in lower_ans or "not take a position" in lower_ans
                        or "fairness" in lower_ans
                    )
                    if not is_neutral:
                        approp_abstention = False
                        failure_reasons.append("Subjective fairness neutrality abstention missing.")

            # 6. Missing Info Gatekeeper (Case 6)
            if gt.requires_missing_info_gatekeeper:
                if not answer.missing_info_report:
                    missing_info_correct = False
                    failure_reasons.append("MissingInfoReport was not attached to GroundedAnswer.")
                else:
                    rep = answer.missing_info_report
                    suff = (
                        (rep.get("sufficiency_level") or rep.get("sufficiency"))
                        if isinstance(rep, dict)
                        else getattr(rep, "sufficiency_level", getattr(rep, "sufficiency", None))
                    )
                    suff_val = suff.value if hasattr(suff, "value") else str(suff)
                    if "insufficient" not in suff_val.lower():
                        missing_info_correct = False
                        failure_reasons.append(f"Expected sufficiency INSUFFICIENT, got {suff_val}")
                    
                    unstated = (
                        (rep.get("missing_predicates") or rep.get("unstated_predicates", []))
                        if isinstance(rep, dict)
                        else getattr(rep, "missing_predicates", getattr(rep, "unstated_predicates", []))
                    )
                    if len(unstated) == 0:
                        missing_info_correct = False
                        failure_reasons.append("Zero unstated/missing predicates detected.")
                    
                    # Check negative fact invariant
                    for p in unstated:
                        desc = p.get("description", "") if isinstance(p, dict) else getattr(p, "description", "")
                        if not desc.startswith("You have not stated whether"):
                            missing_info_correct = False
                            failure_reasons.append(f"Negative fact invariant violated in: '{desc}'")
                    diagnostics["unstated_predicates_count"] = len(unstated)

            # 7. Mode 2 External Law (Case 8)
            if gt.three_part_structure_required:
                if not answer.external_law:
                    failure_reasons.append("Mode 2 did not retrieve external statutory context.")
                else:
                    all_ext_text = " ".join([str(s) for s in answer.external_law])
                    for exp_cit in gt.expected_statute_citations:
                        if exp_cit.lower() not in all_ext_text.lower():
                            failure_reasons.append(f"Expected external citation '{exp_cit}' missing.")
                    diagnostics["external_law_citations"] = [s.get("section_provision") for s in answer.external_law if isinstance(s, dict)]

            # 8. Jurisdiction-Specific Missing Jurisdiction (Case 14)
            if gt.is_jurisdiction_missing:
                # ModeRouter intent check
                if not getattr(intent, "is_jurisdiction_missing", False):
                    failure_reasons.append("is_jurisdiction_missing was not flagged by ModeRouter.")
                # 0 external law statutory citations treated as applicable
                if len(answer.external_law) > 0:
                    failure_reasons.append(f"Expected 0 external statutory citations in missing-jurisdiction state, got {len(answer.external_law)}")
                # Check no default jurisdiction inference
                for forbidden_state in gt.forbidden_jurisdiction_inferences:
                    if forbidden_state.lower() in lower_ans:
                        failure_reasons.append(f"Forbidden default jurisdiction inference made: '{forbidden_state}'")
                # Prompt user for jurisdiction
                if "jurisdiction" not in lower_ans and "state" not in lower_ans:
                    failure_reasons.append("Answer does not prompt user for jurisdiction.")

            # 9. General Grounding Score Check
            if hasattr(answer, "grounding_score") and answer.grounding_score is not None:
                grounding_fid = answer.grounding_score
                min_g = gt.min_grounding_score
                if grounding_fid < min_g and not gt.expected_abstention and case.mode != OperationalMode.MODE_3_GENERAL_NO_DOC:
                    failure_reasons.append(f"Grounding score {grounding_fid:.2f} below threshold {min_g:.2f}")

            diagnostics["latency_ms"] = elapsed_ms
            passed = len(failure_reasons) == 0

            return CaseEvaluationResult(
                case_id=case.case_id,
                archetype=case.archetype,
                mode=case.mode.value,
                passed=passed,
                retrieval_accuracy=retrieval_acc,
                retrieval_specificity=retrieval_spec,
                grounding_fidelity=grounding_fid,
                answer_accuracy=answer_acc,
                citation_precision=citation_prec,
                completeness=completeness,
                hallucination_detected=hallucination_det,
                appropriate_abstention=approp_abstention,
                missing_info_gatekeeper_correct=missing_info_correct,
                contradiction_detection_correct=contradiction_correct,
                latency_ms=elapsed_ms,
                failure_reasons=failure_reasons,
                diagnostic_details=diagnostics,
                evaluated_claims=evaluated_claims,
            )

        except Exception as ex:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return CaseEvaluationResult(
                case_id=case.case_id,
                archetype=case.archetype,
                mode=case.mode.value,
                passed=False,
                latency_ms=elapsed_ms,
                failure_reasons=[f"Unhandled exception during execution: {str(ex)}"],
                diagnostic_details={"exception": str(ex)},
            )

    def run_all(self) -> BenchmarkScorecard:
        """Executes all 14 benchmark evaluation cases and compiles the aggregated scorecard."""
        results: List[CaseEvaluationResult] = []
        for case in BENCHMARK_CASES:
            res = self.run_case(case)
            results.append(res)
        return aggregate_scorecard(results)
