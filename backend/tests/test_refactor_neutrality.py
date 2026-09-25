"""
Refactor Neutrality & Dynamic Extraction Verification Test Suite (15 Tests).
Validates:
1. Evidence-bound dynamic extraction pipeline (exact source-span verification, semantic query association).
2. Domain neutrality (employment, NDA, vendor contracts - no hardcoded landlord/tenant assumptions).
3. Contract silence invariants (no synthetic 6-month lock-in defaults, clean abstention).
4. Query-semantic value differentiation (salary vs bonus, rent vs deposit).
5. Thin orchestrator endpoint POST /api/v1/navigate across 0, 1, and 2+ document scenarios.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.storage import document_store
from app.services.document_parser import document_parser
from app.services.grounding_engine import grounding_engine
from app.services.mode_router import mode_router
from app.models.query import QueryRequest, OperationalMode, QueryCategory
from app.models.situation import UserSituation, UserRole
from app.models.navigate import NavigateRequest, UnifiedNavigationResponse


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    document_store.clear()
    yield
    document_store.clear()


@pytest.fixture
def employment_contract():
    text = (
        "EMPLOYMENT AGREEMENT\n\n"
        "SECTION 1: APPOINTMENT AND DUTIES\n"
        "The Company hereby employs the Employee as Senior Software Architect.\n\n"
        "SECTION 2: REMUNERATION AND COMPENSATION\n"
        "2.1 Fixed Salary: The Company shall pay the Employee a fixed basic annual salary of INR 18,00,000/- "
        "payable in equal monthly installments on the last working day of each calendar month.\n"
        "2.2 Signing Bonus: The Employee shall receive a one-time joining bonus of INR 2,00,000/- upon successful completion of onboarding.\n\n"
        "SECTION 3: TERMINATION AND RESIGNATION\n"
        "3.1 Notice Period: Either party may terminate this employment agreement by serving sixty (60) days' prior written notice to the other party.\n"
        "3.2 Termination for Cause: The Company may terminate employment immediately without notice in the event of gross misconduct or material breach.\n\n"
        "SECTION 4: GOVERNING LAW\n"
        "This agreement is governed by the laws of India and subject to the jurisdiction of courts in New Delhi."
    )
    meta, _ = document_parser.parse_text_content(text, filename="employment_agreement.txt")
    return meta


@pytest.fixture
def nda_contract():
    text = (
        "NON-DISCLOSURE AGREEMENT\n\n"
        "SECTION 1: CONFIDENTIAL INFORMATION\n"
        "The Recipient agrees to hold all Technical Data and Business Plans strictly confidential.\n\n"
        "SECTION 2: DURATION OF OBLIGATIONS\n"
        "The obligations of confidentiality under this Agreement shall survive for a period of two (2) years "
        "from the date of disclosure.\n\n"
        "SECTION 3: REMEDIES AND JURISDICTION\n"
        "This Agreement shall be construed under the laws of Singapore."
    )
    meta, _ = document_parser.parse_text_content(text, filename="confidentiality_nda.txt")
    return meta


@pytest.fixture
def lease_contract():
    text = (
        "RESIDENTIAL LEASE AGREEMENT\n\n"
        "SECTION 1: DEMISED PREMISES\n"
        "Flat No. 402, Indiranagar, Bangalore.\n\n"
        "SECTION 2: MONTHLY RENT\n"
        "The Lessee shall pay a monthly rent of INR 35,000/- in advance on or before the 5th day of each month.\n\n"
        "SECTION 3: SECURITY DEPOSIT\n"
        "The Lessee has deposited a refundable security deposit of INR 1,50,000/-.\n"
        "The deposit shall be refunded within fourteen (14) days after vacating.\n\n"
        "SECTION 4: LOCK-IN PERIOD\n"
        "The parties agree to a mandatory lock-in period of 6 months from the commencement date.\n\n"
        "SECTION 5: TERMINATION\n"
        "After expiry of lock-in, either party may terminate by serving thirty (30) days' prior written notice."
    )
    meta, _ = document_parser.parse_text_content(text, filename="residential_lease.txt")
    return meta


# ---------------------------------------------------------------------------
# Tests 1-7: Evidence-Bound Dynamic Extraction & Semantic Association
# ---------------------------------------------------------------------------

def test_01_non_lease_employment_salary_extraction(employment_contract):
    """Verifies that an employment salary is dynamically extracted with exact figures and no lease terms."""
    req = QueryRequest(query="What is my salary under the employment agreement?", doc_ids=[employment_contract.doc_id])
    intent = mode_router.classify_and_route(req)
    ans = grounding_engine.answer_document_query(req, intent)

    assert "18,00,000" in ans.answer or "18,00,000" in ans.plain_meaning
    assert "2.1" in ans.answer or "2" in ans.answer
    assert "landlord" not in ans.answer.lower()
    assert "tenant" not in ans.answer.lower()
    assert len(ans.sources) > 0
    assert any("18,00,000" in s.quote for s in ans.sources)


def test_02_non_lease_employment_notice_period(employment_contract):
    """Verifies that employment notice period of 60 days is extracted and does NOT default to 30 days."""
    req = QueryRequest(query="What is the notice period required to terminate or resign?", doc_ids=[employment_contract.doc_id])
    intent = mode_router.classify_and_route(req)
    ans = grounding_engine.answer_document_query(req, intent)

    assert "sixty (60) days" in ans.answer or "60" in ans.answer or "sixty" in ans.answer.lower()
    assert "3.1" in ans.answer or "3" in ans.answer
    assert "thirty (30) days" not in ans.answer
    assert "section 8" not in ans.answer.lower()


def test_03_lock_in_absence_returns_neutral_silence(employment_contract):
    """Verifies that a contract without lock-in returns exact neutral silence and never defaults to 6 months."""
    req = QueryRequest(query="Is there any lock-in period in this contract?", doc_ids=[employment_contract.doc_id])
    intent = mode_router.classify_and_route(req)
    ans = grounding_engine.answer_document_query(req, intent)

    assert "No lock-in provision was identified in the available document evidence." in ans.answer
    assert "6 months" not in ans.answer
    assert "six months" not in ans.answer.lower()


def test_04_missing_monetary_concept_abstains_cleanly(nda_contract):
    """Verifies that asking for rent/salary in an NDA returns a clean absence statement without invented figures."""
    req = QueryRequest(query="What is the monthly rent or security deposit?", doc_ids=[nda_contract.doc_id])
    intent = mode_router.classify_and_route(req)
    ans = grounding_engine.answer_document_query(req, intent)

    assert "No rent amount was identified in the available document evidence." in ans.answer or \
           "No security deposit amount was identified in the available document evidence." in ans.answer
    assert "35,00,0" not in ans.answer
    assert "1,50,000" not in ans.answer


def test_05_missing_jurisdiction_abstains_with_clarification():
    """Verifies that a general legal query without jurisdiction clarifies missing jurisdiction instead of fabricating rules."""
    req = QueryRequest(query="What is the mandatory notice period for residential evictions?", doc_ids=[])
    resp = client.post("/api/v1/navigate", json={"query": req.query, "doc_ids": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["jurisdiction_note"] is not None or "jurisdiction" in (data["what_is_unclear_or_missing"] or "").lower()


def test_06_query_semantic_differentiation_salary_vs_bonus(employment_contract):
    """Verifies query-semantic association differentiates between salary (18L) and signing bonus (2L)."""
    # Query for salary
    req_sal = QueryRequest(query="What is my basic fixed salary?", doc_ids=[employment_contract.doc_id])
    ans_sal = grounding_engine.answer_document_query(req_sal, mode_router.classify_and_route(req_sal))
    assert "18,00,000" in ans_sal.answer
    assert "2,00,000" not in ans_sal.answer

    # Query for bonus
    req_bon = QueryRequest(query="What is the signing bonus or joining bonus?", doc_ids=[employment_contract.doc_id])
    ans_bon = grounding_engine.answer_document_query(req_bon, mode_router.classify_and_route(req_bon))
    assert "2,00,000" in ans_bon.answer
    assert "18,00,000" not in ans_bon.answer


def test_07_query_semantic_differentiation_rent_vs_deposit(lease_contract):
    """Verifies query-semantic association differentiates between monthly rent (35k) and deposit (1.5L)."""
    # Query for rent
    req_rent = QueryRequest(query="What is the monthly rent?", doc_ids=[lease_contract.doc_id])
    ans_rent = grounding_engine.answer_document_query(req_rent, mode_router.classify_and_route(req_rent))
    assert "35,000" in ans_rent.answer
    assert "1,50,000" not in ans_rent.answer

    # Query for deposit
    req_dep = QueryRequest(query="What is the security deposit amount and refund timeline?", doc_ids=[lease_contract.doc_id])
    ans_dep = grounding_engine.answer_document_query(req_dep, mode_router.classify_and_route(req_dep))
    assert "1,50,000" in ans_dep.answer
    assert "35,000" not in ans_dep.answer
    assert "fourteen (14) days" in ans_dep.answer or "14" in ans_dep.answer


# ---------------------------------------------------------------------------
# Tests 8-15: Unified Orchestrator /api/v1/navigate Endpoint Invariants
# ---------------------------------------------------------------------------

def test_08_unified_navigate_endpoint_mode1_single_doc(employment_contract):
    """Tests POST /api/v1/navigate with a single employment document."""
    payload = {
        "query": "What is my notice period and what must I do to resign?",
        "doc_ids": [employment_contract.doc_id],
        "declared_role": "Employee"
    }
    resp = client.post("/api/v1/navigate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "employee" in (data["inferred_role"] or "").lower()
    assert len(data["sources"]) > 0
    assert len(data["actionable_checklist"]) > 0
    assert data["comparative_analysis"] is None
    assert data["diagnostics"]["doc_count"] == 1
    assert data["diagnostics"]["effective_mode"] == "mode_1_doc_only"


def test_09_unified_navigate_endpoint_mode2_external_law(lease_contract):
    """Tests POST /api/v1/navigate when a query touches both contract and statutory law."""
    payload = {
        "query": "Does the Transfer of Property Act require 15 days or 30 days notice to terminate?",
        "doc_ids": [lease_contract.doc_id],
        "jurisdiction": "Karnataka, India"
    }
    resp = client.post("/api/v1/navigate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["diagnostics"]["effective_mode"] == "mode_2_doc_external"
    assert data["governing_legal_framework"] is not None
    assert len(data["governing_legal_framework"]) > 0
    assert data["diagnostics"]["has_external_law"] is True


def test_10_unified_navigate_endpoint_mode3_general_no_doc():
    """Tests POST /api/v1/navigate with 0 documents for general legal knowledge."""
    payload = {
        "query": "What is an unstamped lease agreement under Indian Evidence Law?",
        "doc_ids": [],
        "jurisdiction": "Delhi, India"
    }
    resp = client.post("/api/v1/navigate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["diagnostics"]["effective_mode"] == "mode_3_general_no_doc"
    assert data["diagnostics"]["doc_count"] == 0
    assert "No document was provided" in data["what_the_document_says"]
    assert len(data["answer"]) > 50


def test_11_unified_navigate_endpoint_multi_doc_comparison():
    """Tests POST /api/v1/navigate with 2 documents automatically populates comparative analysis."""
    from tests.test_phase8_contradiction_comparison import SAMPLE_BASE_LEASE, SAMPLE_SELECTIVE_AMENDMENT
    meta_a, _ = document_parser.parse_text_content(SAMPLE_BASE_LEASE, filename="base_lease.txt")
    meta_b, _ = document_parser.parse_text_content(SAMPLE_SELECTIVE_AMENDMENT, filename="amendment.txt")

    payload = {
        "query": "What changed in the monthly rent between the two agreements?",
        "doc_ids": [meta_a.doc_id, meta_b.doc_id]
    }
    resp = client.post("/api/v1/navigate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["diagnostics"]["doc_count"] == 2
    assert data["comparative_analysis"] is not None
    assert len(data["comparative_analysis"]["differences"]) > 0


def test_12_unified_navigate_pasted_content_support():
    """Tests POST /api/v1/navigate with pasted_content when no file was uploaded."""
    pasted_text = (
        "CONSULTING SERVICES AGREEMENT\n\n"
        "SECTION 1: SCOPE\n"
        "Consultant shall provide AI architecture advisory services.\n\n"
        "SECTION 2: COMPENSATION\n"
        "Client shall pay Consultant a fixed retainer of USD 12,000 per month.\n\n"
        "SECTION 3: TERMINATION\n"
        "Either party may terminate upon thirty (30) days written notice."
    )
    payload = {
        "query": "What is the monthly retainer fee?",
        "pasted_content": pasted_text,
        "doc_ids": []
    }
    resp = client.post("/api/v1/navigate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "12,000" in data["answer"] or "12,000" in data["what_this_means_in_plain_language"]
    assert data["diagnostics"]["doc_count"] >= 1
    assert len(data["sources"]) > 0


def test_13_unified_navigate_role_perspective_formatting(employment_contract):
    """Tests that declared perspective is applied to the plain language summary."""
    payload = {
        "query": "Can the company fire me without notice?",
        "doc_ids": [employment_contract.doc_id],
        "declared_role": "Employee"
    }
    resp = client.post("/api/v1/navigate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "Employee" in data["summary_and_perspective"]
    assert "Section 3" in data["what_the_document_says"] or "notice" in data["answer"].lower()


def test_14_vendor_nda_non_lease_contract(nda_contract):
    """Tests non-disclosure agreement duration extraction without tenancy assumptions."""
    payload = {
        "query": "How long do the confidentiality obligations last?",
        "doc_ids": [nda_contract.doc_id]
    }
    resp = client.post("/api/v1/navigate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "two (2) years" in data["answer"] or "two (2) years" in data["what_the_document_says"] or "two" in data["answer"].lower()
    assert "tenant" not in data["answer"].lower()
    assert "landlord" not in data["answer"].lower()


def test_15_diagnostics_contain_internal_machinery_without_leaking(employment_contract):
    """Tests that diagnostics contain internal engine metadata while top-level fields are user-centric."""
    payload = {
        "query": "What are my termination notice covenants?",
        "doc_ids": [employment_contract.doc_id],
        "situation_description": "I received an offer from another company and want to resign."
    }
    resp = client.post("/api/v1/navigate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Diagnostics contains internal metadata
    assert "effective_mode" in data["diagnostics"]
    assert "category" in data["diagnostics"]
    assert "evidence_sufficiency_passed" in data["diagnostics"]
    assert "latency_ms" in data["diagnostics"]

    # Top-level fields are user-facing product fields
    assert "summary_and_perspective" in data
    assert "what_the_document_says" in data
    assert "what_this_means_in_plain_language" in data
    assert "actionable_checklist" in data
    assert data["consultation_brief_markdown"] is not None
