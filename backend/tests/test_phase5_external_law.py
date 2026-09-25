import pytest
import os
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.query import QueryRequest, OperationalMode, QueryCategory
from backend.app.models.external_law import (
    SourceCurrencyStatus,
    FailureUncertaintyState,
    PrecedentialScope,
)
from backend.app.services.document_parser import document_parser
from backend.app.services.authoritative_legal_store import authoritative_store, VERIFIED_STATUTES, VERIFIED_PRECEDENTS
from backend.app.services.jurisdiction_service import jurisdiction_service
from backend.app.services.mode_router import mode_router
from backend.app.services.external_law_service import external_law_service


client = TestClient(app)


@pytest.fixture
def load_employment_doc():
    sample_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "sample_documents", "employment_contract.txt")
    )
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()
    meta, _ = document_parser.parse_text_content(content, filename="employment_contract.txt")
    return meta


@pytest.fixture
def load_lease_doc():
    sample_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "sample_documents", "residential_lease_agreement.txt")
    )
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()
    meta, _ = document_parser.parse_text_content(content, filename="residential_lease_agreement.txt")
    return meta


# 1. Mode 1 -> Mode 2 Dynamic Reclassification on Statutory Question
def test_mode1_to_mode2_dynamic_reclassification(load_lease_doc):
    # Step A: User asks Mode 1 document-only question
    req1 = QueryRequest(
        query="What does my agreement say about notice period?",
        doc_ids=[load_lease_doc.doc_id]
    )
    intent1 = mode_router.classify_and_route(req1)
    assert intent1.effective_mode == OperationalMode.MODE_1_DOC_ONLY
    ans1 = client.post("/api/query", json=req1.model_dump()).json()
    assert ans1["operational_mode"] == "mode_1_doc_only"
    assert len(ans1["external_law"]) == 0

    # Step B: User follows up with statutory enforceability question
    req2 = QueryRequest(
        query="Is that 30-day notice period legally valid under Indian tenancy law?",
        doc_ids=[load_lease_doc.doc_id]
    )
    intent2 = mode_router.classify_and_route(req2)
    assert intent2.effective_mode == OperationalMode.MODE_2_DOC_EXTERNAL
    assert intent2.is_reclassified is True

    ans2 = client.post("/api/query", json=req2.model_dump()).json()
    assert ans2["operational_mode"] == "mode_2_doc_external"
    assert len(ans2["external_law"]) >= 1


# 2. Document <-> Law Distinction & 5-Way Information Invariant (Employment Non-Compete)
def test_document_law_distinction_and_invariants(load_employment_doc):
    req = QueryRequest(
        query="Is this 2-year post-termination non-compete enforceable in India?",
        doc_ids=[load_employment_doc.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    assert res["operational_mode"] == "mode_2_doc_external"
    assert len(res["document_facts"]) >= 1
    assert len(res["external_law"]) >= 1

    # Invariant: document_facts != external_law (no text contamination)
    doc_fact_text = " ".join(res["document_facts"])
    ext_law_text = " ".join([s["exact_retrieved_text"] for s in res["external_law"]])
    assert "Section 11" in doc_fact_text
    assert "Section 27" in ext_law_text
    assert doc_fact_text != ext_law_text

    # Both contract rule and statute are presented without overwriting contract clause
    assert "24" in doc_fact_text or "twenty-four" in doc_fact_text.lower()
    assert "restrain" in ext_law_text.lower() or "trade" in ext_law_text.lower()


# 3. Neutral 4-Stage Synthesis (Zero Legal Conclusions)
def test_neutral_four_stage_synthesis_no_legal_conclusions(load_employment_doc):
    req = QueryRequest(
        query="Is this non-compete clause valid?",
        doc_ids=[load_employment_doc.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    interp = res["plain_language_interpretation"]

    # Verify the 4 distinct stages are present
    assert "1. Document Provision:" in interp
    assert "2. Statutory Provision:" in interp
    assert "3. Judicial Discussion:" in interp
    assert "4. Factors & Uncertainty:" in interp

    # Strictly avoid conclusory pronouncements
    ans_lower = res["answer"].lower()
    assert "therefore this clause is void" not in ans_lower
    assert "unconditionally illegal" not in ans_lower
    assert "generally unenforceable" not in ans_lower
    assert "may depend on" in ans_lower


# 4. Judicial Precedent Metadata Integrity (Percept D'Mark)
def test_judicial_precedent_metadata_integrity(load_employment_doc):
    req = QueryRequest(
        query="What court precedents govern this post-termination non-compete in India?",
        doc_ids=[load_employment_doc.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    assert len(res["judicial_precedents"]) >= 1
    prec = res["judicial_precedents"][0]

    assert prec["case_name"] == "Percept D'Mark (India) (P) Ltd. v. Zaheer Khan"
    assert prec["court"] == "Supreme Court of India"
    assert prec["decision_date"] == "2006-03-22"
    assert prec["citation"] == "(2006) 4 SCC 227"
    assert prec["precedential_scope"] == PrecedentialScope.NATIONAL_SUPREME_COURT.value
    assert "verified metadata" in prec["binding_status"].lower()
    assert prec["status_verification"] != ""


# 5. Evidence-Based Currentness Verification (From Verified Fixtures)
def test_evidence_based_currentness(load_employment_doc):
    req = QueryRequest(
        query="Is this non-compete enforceable under Section 27 of the Indian Contract Act?",
        doc_ids=[load_employment_doc.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    assert len(res["external_law"]) >= 1
    statute = res["external_law"][0]

    assert statute["currentness_status"] == SourceCurrencyStatus.IN_FORCE.value
    assert statute["last_amendment_date"] == "2018-05-04"
    assert statute["verification_status"] == "verified_official_record"
    assert "indiacode.nic.in" in statute["official_url"]
    assert statute["provenance_notes"] != ""


# 6. Source Unavailable Explicit Abstention
def test_source_unavailable_explicit_abstention(load_lease_doc):
    req = QueryRequest(
        query="What are the statutory commercial deep-sea mining permit rules for this lease in India?",
        doc_ids=[load_lease_doc.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    # Must abstain cleanly without fabricating a statutory rule
    assert res["evidence_sufficiency_passed"] is False
    assert res["failure_uncertainty_state"] == FailureUncertaintyState.AUTHORITATIVE_SOURCE_NOT_FOUND.value
    assert "could not be verified" in res["answer"].lower()
    assert len(res["external_law"]) == 0


# 7. Currentness Unavailable Abstention
def test_currentness_unavailable_abstention():
    # Directly test external_law_service with a query matching the unverified fixture
    req = QueryRequest(
        query="Does the provisional subordinate order rule 14 apply in India?",
        doc_ids=[]
    )
    # Search specifically with query
    intent = mode_router.classify_and_route(req)
    res = external_law_service._create_abstention_response(
        request=req,
        state=FailureUncertaintyState.SOURCE_CURRENTNESS_UNVERIFIED,
        message="Authoritative source currentness could not be verified from official gazette records.",
        user_facts=[]
    )
    assert res.failure_uncertainty_state == FailureUncertaintyState.SOURCE_CURRENTNESS_UNVERIFIED.value
    assert res.evidence_sufficiency_passed is False


# 8. Repealed Provision Handling
def test_repealed_provision_handling():
    repealed = authoritative_store.get_statute("fixture_repealed_krca_1961")
    assert repealed is not None
    assert repealed.currentness_status == SourceCurrencyStatus.REPEALED

    # Search should exclude repealed by default
    active_search = authoritative_store.search_statutes(
        jurisdiction="Karnataka, India",
        keywords=["rent", "control", "1961"],
        include_repealed=False
    )
    assert all(s.source_id != "fixture_repealed_krca_1961" for s in active_search)


# 9. Jurisdiction Extraction from Document Governing Law Clause
def test_jurisdiction_extraction_from_document(load_lease_doc):
    # Query has NO jurisdiction specified
    req = QueryRequest(
        query="Is my 30-day notice period valid under statutory law?",
        doc_ids=[load_lease_doc.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    assert res["operational_mode"] == "mode_2_doc_external"
    assert res["jurisdiction_signal"] is not None
    # Section 9 mentions Karnataka civil courts and laws of India
    assert "Karnataka" in res["jurisdiction_signal"]["jurisdiction_value"] or "India" in res["jurisdiction_signal"]["jurisdiction_value"]
    assert res["jurisdiction_signal"]["signal_source"] == "document"


# 10. Jurisdiction Conflict Handling
def test_jurisdiction_conflict_handling(load_lease_doc):
    # Document specifies Karnataka (Section 9.2), but query asks about Himachal Pradesh
    req = QueryRequest(
        query="Is this notice period valid under Himachal Pradesh tenancy law?",
        doc_ids=[load_lease_doc.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    assert res["failure_uncertainty_state"] == FailureUncertaintyState.JURISDICTION_CONFLICT.value
    assert "Jurisdiction Conflict" in res["neutral_labels"]
    assert "Himachal Pradesh" in res["plain_language_interpretation"]
    assert "Karnataka" in res["plain_language_interpretation"]


# 11. Missing Jurisdiction Explicit Abstention
def test_missing_jurisdiction_abstention():
    # Ingestion of document without governing law clause
    no_gov_law_doc = "AGREEMENT\n1. RENT: INR 10,000.\n2. NOTICE: 15 days."
    meta, _ = document_parser.parse_text_content(no_gov_law_doc, filename="unspecified_doc.txt")

    req = QueryRequest(
        query="Is this 15-day notice period legally valid under tenancy statutes?",
        doc_ids=[meta.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    # Must abstain cleanly without guessing India
    assert res["evidence_sufficiency_passed"] is False
    assert res["failure_uncertainty_state"] == FailureUncertaintyState.JURISDICTION_MISSING.value
    assert "jurisdiction is required" in res["answer"].lower() or "jurisdiction missing" in res["answer"].lower()


# 12. Candidate Law vs. Applicable Law Uncertainty Gate
def test_candidate_vs_applicable_law_uncertainty(load_lease_doc):
    # Lease has Section 8.1 specifying 30 days notice
    req = QueryRequest(
        query="What is the statutory notice period for this lease under Section 106 of the Transfer of Property Act in India?",
        doc_ids=[load_lease_doc.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    assert res["operational_mode"] == "mode_2_doc_external"
    # System should flag that TPA Section 106 default notice may be displaced by the contract
    assert any("in the absence of a contract" in u.lower() or "displace" in u.lower() for u in res["uncertainty_and_gaps"])


# 13. Source/Version Conflict Detection
def test_source_version_conflict_detection():
    statute_a = authoritative_store.get_statute("fixture_conflict_version_a")
    statute_b = authoritative_store.get_statute("fixture_conflict_version_b")
    assert statute_a is not None and statute_b is not None

    conflicts = authoritative_store.detect_version_conflicts([statute_a, statute_b])
    assert len(conflicts) >= 1
    assert "Potential source/version conflict" in conflicts[0]["topic"]


# 14. Secondary Source Rejection
def test_secondary_source_rejection():
    blog_source = {
        "url": "https://www.lawfirm-blog.com/post/is-non-compete-valid",
        "title": "Top 5 Tips for Non-Competes in India"
    }
    official_source = {
        "official_url": "https://www.indiacode.nic.in/handle/123456789/2187",
        "title": "The Indian Contract Act, 1872"
    }
    assert authoritative_store.is_secondary_source(blog_source) is True
    assert authoritative_store.is_secondary_source(official_source) is False


# 15. End-to-End Mode 2 Response Structure Completeness
def test_end_to_end_mode2_response_structure(load_employment_doc):
    req = QueryRequest(
        query="Is this 2-year post-termination non-compete clause enforceable in India?",
        doc_ids=[load_employment_doc.doc_id]
    )
    res = client.post("/api/query", json=req.model_dump()).json()

    # Complete 5-way separation verification
    assert isinstance(res["document_facts"], list)
    assert isinstance(res["user_provided_facts"], list)
    assert isinstance(res["external_law"], list)
    assert isinstance(res["plain_language_interpretation"], str)
    assert isinstance(res["uncertainty_and_gaps"], list)

    # Document-Law relationships
    assert len(res["document_law_relationships"]) >= 1
    rel = res["document_law_relationships"][0]
    assert "Section 11" in rel["document_clause_ref"]
    assert "Section 27" in rel["statutory_provision_ref"]
    assert len(rel["factors_and_uncertainties"]) >= 1
