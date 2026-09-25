"""Phase 10 Automated Pytest Suite: 14 Benchmark Evaluation Cases & Cloud Readiness."""

import pytest
from app.evaluation.runner import EvaluationRunner
from app.evaluation.benchmark_cases import BENCHMARK_CASES, BenchmarkCase
from app.evaluation.metrics import BenchmarkScorecard
from app.core.storage import document_store


@pytest.fixture(autouse=True)
def clean_store():
    document_store.clear()
    yield
    document_store.clear()


@pytest.fixture(scope="module")
def runner():
    return EvaluationRunner()


def get_case_by_id(case_id: int) -> BenchmarkCase:
    for c in BENCHMARK_CASES:
        if c.case_id == case_id:
            return c
    raise ValueError(f"Case {case_id} not found in BENCHMARK_CASES")


def test_case_01_simple_factual_question(runner):
    case = get_case_by_id(1)
    res = runner.run_case(case)
    assert res.passed, f"Case 1 failed: {res.failure_reasons}"
    assert res.retrieval_accuracy >= 0.90
    assert not res.hallucination_detected


def test_case_02_multi_clause_reasoning(runner):
    case = get_case_by_id(2)
    res = runner.run_case(case)
    assert res.passed, f"Case 2 failed: {res.failure_reasons}"
    assert res.retrieval_accuracy >= 0.80
    assert not res.hallucination_detected


def test_case_03_situation_specific_notice(runner):
    case = get_case_by_id(3)
    res = runner.run_case(case)
    assert res.passed, f"Case 3 failed: {res.failure_reasons}"
    assert res.grounding_fidelity >= 0.80
    assert not res.hallucination_detected


def test_case_04_document_comparison_amendment(runner):
    case = get_case_by_id(4)
    res = runner.run_case(case)
    assert res.passed, f"Case 4 failed: {res.failure_reasons}"
    assert res.contradiction_detection_correct


def test_case_05_unverified_relationship_conflict(runner):
    case = get_case_by_id(5)
    res = runner.run_case(case)
    assert res.passed, f"Case 5 failed: {res.failure_reasons}"
    assert res.contradiction_detection_correct
    assert res.diagnostic_details.get("true_contradictions") == 0


def test_case_06_missing_information_gatekeeper(runner):
    case = get_case_by_id(6)
    res = runner.run_case(case)
    assert res.passed, f"Case 6 failed: {res.failure_reasons}"
    assert res.missing_info_gatekeeper_correct
    assert res.diagnostic_details.get("unstated_predicates_count", 0) > 0


def test_case_07_nonexistent_clause_contract_silence(runner):
    case = get_case_by_id(7)
    res = runner.run_case(case)
    assert res.passed, f"Case 7 failed: {res.failure_reasons}"
    assert res.appropriate_abstention
    assert not res.hallucination_detected


def test_case_08_document_plus_external_law_mode2(runner):
    case = get_case_by_id(8)
    res = runner.run_case(case)
    assert res.passed, f"Case 8 failed: {res.failure_reasons}"
    assert not res.hallucination_detected


def test_case_09_ambiguous_question_subjective_fairness(runner):
    case = get_case_by_id(9)
    res = runner.run_case(case)
    assert res.passed, f"Case 9 failed: {res.failure_reasons}"
    assert res.appropriate_abstention


def test_case_10_professional_advice_boundary(runner):
    case = get_case_by_id(10)
    res = runner.run_case(case)
    assert res.passed, f"Case 10 failed: {res.failure_reasons}"
    assert not res.hallucination_detected


def test_case_11_adversarial_prompt_injection(runner):
    case = get_case_by_id(11)
    res = runner.run_case(case)
    assert res.passed, f"Case 11 failed: {res.failure_reasons}"
    assert not res.hallucination_detected


def test_case_12_long_document_needle_retrieval(runner):
    case = get_case_by_id(12)
    res = runner.run_case(case)
    assert res.passed, f"Case 12 failed: {res.failure_reasons}"
    assert res.retrieval_accuracy >= 0.85
    assert not res.hallucination_detected


def test_case_13_general_legal_concept_mode3(runner):
    case = get_case_by_id(13)
    res = runner.run_case(case)
    assert res.passed, f"Case 13 failed: {res.failure_reasons}"
    assert not res.hallucination_detected


def test_case_14_jurisdiction_specific_general_law_mode3(runner):
    case = get_case_by_id(14)
    res = runner.run_case(case)
    assert res.passed, f"Case 14 failed: {res.failure_reasons}"
    assert res.appropriate_abstention


def test_full_evaluation_suite_aggregation(runner):
    """Verifies that the entire 14-case benchmark achieves 100% pass rate and 0% hallucination."""
    scorecard: BenchmarkScorecard = runner.run_all()
    assert scorecard.total_cases == 14
    assert scorecard.passed_cases == 14
    assert scorecard.pass_rate_pct == 100.0
    assert scorecard.hallucination_rate_pct == 0.0
    assert scorecard.avg_grounding_fidelity >= 0.85
    assert len(scorecard.to_markdown()) > 500


def test_api_evaluation_endpoint():
    """Verifies that GET /api/evaluation/run returns 403 when disabled or key invalid, and 200 when authorized."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.core.config import settings

    client = TestClient(app)

    # 1. Disabled by default -> returns 403
    orig_enabled = settings.ENABLE_EVALUATION_ENDPOINT
    orig_key = settings.EVALUATION_KEY
    try:
        settings.ENABLE_EVALUATION_ENDPOINT = False
        resp_disabled = client.get("/api/evaluation/run")
        assert resp_disabled.status_code == 403, f"Expected 403 when disabled, got {resp_disabled.status_code}"

        # 2. Enabled but requiring key
        settings.ENABLE_EVALUATION_ENDPOINT = True
        settings.EVALUATION_KEY = "test-secret-key-123"

        # Missing key -> 403
        resp_nokey = client.get("/api/evaluation/run")
        assert resp_nokey.status_code == 403, f"Expected 403 with missing key, got {resp_nokey.status_code}"

        # Invalid key -> 403
        resp_badkey = client.get("/api/evaluation/run", headers={"X-Evaluation-Key": "wrong-key"})
        assert resp_badkey.status_code == 403, f"Expected 403 with bad key, got {resp_badkey.status_code}"

        # Valid key -> 200
        resp_auth = client.get("/api/evaluation/run", headers={"X-Evaluation-Key": "test-secret-key-123"})
        assert resp_auth.status_code == 200
        data = resp_auth.json()
        assert data["total_cases"] == 14
        assert data["passed_cases"] == 14
        assert data["pass_rate_pct"] == 100.0
        assert data["hallucination_rate_pct"] == 0.0
        assert "Benchmark Evaluation Scorecard" in data.get("markdown_report", "") or len(data.get("case_results", [])) == 14
    finally:
        settings.ENABLE_EVALUATION_ENDPOINT = orig_enabled
        settings.EVALUATION_KEY = orig_key


