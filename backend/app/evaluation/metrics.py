"""Metrics computation engine for Legal Information Navigator evaluation harness.

Evaluates 10 core metrics across the 14 benchmark evaluation archetypes:
1. Retrieval Recall
2. Retrieval Specificity
3. Evidence Grounding Fidelity
4. Citation Precision & Span Accuracy
5. Answer Accuracy & Semantic Correctness
6. Structural Completeness
7. Hallucination Rate (0.0% invariant on evidence-requiring claims)
8. Appropriate Abstention & Boundary Enforcement
9. Missing-Information Gatekeeper Accuracy
10. Contradiction & Unverified Relationship Detection
Plus Latency tracking (mean, median, p95).
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import statistics
from pydantic import BaseModel, Field


class ClaimCategory(str, Enum):
    DOCUMENT_GROUNDED_CLAIM = "DOCUMENT_GROUNDED_CLAIM"
    USER_ASSERTION = "USER_ASSERTION"
    EXTERNAL_LAW_CLAIM = "EXTERNAL_LAW_CLAIM"
    GENERAL_CONCEPT_EXPLANATION = "GENERAL_CONCEPT_EXPLANATION"
    PROCESS_PREPARATION_STATEMENT = "PROCESS_PREPARATION_STATEMENT"
    UNCERTAINTY_ABSTENTION = "UNCERTAINTY_ABSTENTION"


class EvaluatedClaim(BaseModel):
    text: str
    category: ClaimCategory
    requires_evidence: bool
    is_grounded: bool = True
    grounding_source: Optional[str] = None
    violation_detail: Optional[str] = None


class CaseEvaluationResult(BaseModel):
    case_id: int
    archetype: str
    mode: str
    passed: bool
    retrieval_accuracy: float = 1.0       # Retrieval Recall
    retrieval_specificity: float = 1.0    # Negative retrieval / precision
    grounding_fidelity: float = 1.0       # Grounding ratio on claims requiring evidence
    answer_accuracy: float = 1.0          # Semantic & factual accuracy
    citation_precision: float = 1.0       # Span & section precision
    completeness: float = 1.0             # Structural completeness
    hallucination_detected: bool = False  # True if any claim requiring evidence lacks grounding
    appropriate_abstention: bool = True   # True if boundary / silence respected
    missing_info_gatekeeper_correct: bool = True # Missing info detection
    contradiction_detection_correct: bool = True # Contradiction & conflict detection
    latency_ms: float = 0.0
    failure_reasons: List[str] = Field(default_factory=list)
    diagnostic_details: Dict[str, Any] = Field(default_factory=dict)
    evaluated_claims: List[EvaluatedClaim] = Field(default_factory=list)


class BenchmarkScorecard(BaseModel):
    total_cases: int = 14
    passed_cases: int = 0
    failed_cases: int = 0
    pass_rate_pct: float = 0.0
    avg_retrieval_accuracy: float = 0.0
    avg_retrieval_specificity: float = 1.0
    avg_grounding_fidelity: float = 0.0
    avg_answer_accuracy: float = 0.0
    avg_citation_precision: float = 0.0
    avg_completeness: float = 0.0
    hallucination_rate_pct: float = 0.0
    abstention_accuracy_pct: float = 0.0
    missing_info_accuracy_pct: float = 0.0
    contradiction_accuracy_pct: float = 0.0
    avg_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    markdown_report: str = ""
    case_results: List[CaseEvaluationResult] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Formats the scorecard into a clean GitHub Flavored Markdown table."""
        lines = [
            "# Benchmark Evaluation Scorecard (14 Archetypes) — Revision 2",
            "",
            f"**Overall Pass Rate**: {self.passed_cases}/{self.total_cases} ({self.pass_rate_pct:.1f}%)",
            f"**Hallucination Rate**: {self.hallucination_rate_pct:.1f}% (Evidence-Requiring Claims Invariant)",
            f"**Average Grounding Fidelity**: {self.avg_grounding_fidelity * 100:.1f}%",
            f"**Average Retrieval Recall**: {self.avg_retrieval_accuracy * 100:.1f}%",
            f"**Average Retrieval Specificity**: {self.avg_retrieval_specificity * 100:.1f}%",
            f"**Average Latency**: {self.avg_latency_ms:.1f} ms (Median: {self.median_latency_ms:.1f} ms, p95: {self.p95_latency_ms:.1f} ms)",
            "",
            "| # | Archetype | Mode | Status | Recall | Specificity | Grounding | Accuracy | Hallucination | Latency |",
            "|---|-----------|------|--------|--------|-------------|-----------|----------|---------------|---------|"
        ]

        for res in self.case_results:
            status_emoji = "✅ PASS" if res.passed else "❌ FAIL"
            halluc_str = "None (0%)" if not res.hallucination_detected else "DETECTED"
            lines.append(
                f"| {res.case_id} | {res.archetype} | `{res.mode}` | {status_emoji} | "
                f"{res.retrieval_accuracy*100:.0f}% | {res.retrieval_specificity*100:.0f}% | "
                f"{res.grounding_fidelity*100:.0f}% | {res.answer_accuracy*100:.0f}% | "
                f"{halluc_str} | {res.latency_ms:.1f}ms |"
            )

        if self.failed_cases > 0:
            lines.append("")
            lines.append("### Diagnostic Failures")
            for res in self.case_results:
                if not res.passed:
                    lines.append(f"- **Case {res.case_id} ({res.archetype})**: {'; '.join(res.failure_reasons)}")

        return "\n".join(lines)


def aggregate_scorecard(results: List[CaseEvaluationResult]) -> BenchmarkScorecard:
    """Aggregates individual case evaluation results into a comprehensive scorecard."""
    total = len(results)
    if total == 0:
        return BenchmarkScorecard()

    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    pass_rate = (passed / total) * 100.0

    avg_retrieval = sum(r.retrieval_accuracy for r in results) / total
    avg_specificity = sum(r.retrieval_specificity for r in results) / total
    avg_grounding = sum(r.grounding_fidelity for r in results) / total
    avg_accuracy = sum(r.answer_accuracy for r in results) / total
    avg_citation = sum(r.citation_precision for r in results) / total
    avg_completeness = sum(r.completeness for r in results) / total

    # Hallucination rate on claims requiring evidence across all cases
    all_claims = [c for r in results for c in r.evaluated_claims]
    ev_claims = [c for c in all_claims if c.requires_evidence]
    if ev_claims:
        ungrounded_claims = [c for c in ev_claims if not c.is_grounded]
        halluc_rate = (len(ungrounded_claims) / len(ev_claims)) * 100.0
    else:
        hallucination_count = sum(1 for r in results if r.hallucination_detected)
        halluc_rate = (hallucination_count / total) * 100.0

    abstention_cases = [r for r in results if "abstention" in r.diagnostic_details or r.case_id in (7, 9, 14)]
    abstention_acc = (
        (sum(1 for r in abstention_cases if r.appropriate_abstention) / len(abstention_cases) * 100.0)
        if abstention_cases else 100.0
    )

    missing_cases = [r for r in results if r.case_id == 6]
    missing_acc = (
        (sum(1 for r in missing_cases if r.missing_info_gatekeeper_correct) / len(missing_cases) * 100.0)
        if missing_cases else 100.0
    )

    contradiction_cases = [r for r in results if r.case_id in (4, 5)]
    contradiction_acc = (
        (sum(1 for r in contradiction_cases if r.contradiction_detection_correct) / len(contradiction_cases) * 100.0)
        if contradiction_cases else 100.0
    )

    latencies = [r.latency_ms for r in results]
    avg_latency = statistics.mean(latencies) if latencies else 0.0
    median_latency = statistics.median(latencies) if latencies else 0.0
    if len(latencies) >= 2:
        sorted_latencies = sorted(latencies)
        idx_95 = int(0.95 * (len(sorted_latencies) - 1))
        p95_latency = sorted_latencies[idx_95]
    else:
        p95_latency = avg_latency

    card = BenchmarkScorecard(
        total_cases=total,
        passed_cases=passed,
        failed_cases=failed,
        pass_rate_pct=pass_rate,
        avg_retrieval_accuracy=avg_retrieval,
        avg_retrieval_specificity=avg_specificity,
        avg_grounding_fidelity=avg_grounding,
        avg_answer_accuracy=avg_accuracy,
        avg_citation_precision=avg_citation,
        avg_completeness=avg_completeness,
        hallucination_rate_pct=halluc_rate,
        abstention_accuracy_pct=abstention_acc,
        missing_info_accuracy_pct=missing_acc,
        contradiction_accuracy_pct=contradiction_acc,
        avg_latency_ms=avg_latency,
        median_latency_ms=median_latency,
        p95_latency_ms=p95_latency,
        case_results=results,
    )
    card.markdown_report = card.to_markdown()
    return card
