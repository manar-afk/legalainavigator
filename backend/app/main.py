from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
import os
from pydantic import BaseModel

from .core.config import settings
from .core.storage import document_store
from .core.gemini_client import gemini_client
from .models.query import QueryRequest, IntentClassification, OperationalMode, QueryCategory
from .models.document import DocumentMeta, DocumentChunk
from .models.response import GroundedAnswer
from .models.situation import UserSituation, UserRole
from .models.navigate import NavigateRequest, UnifiedNavigationResponse
from .services.mode_router import mode_router
from .services.document_parser import document_parser
from .services.general_qa import general_qa_service
from .services.grounding_engine import grounding_engine
from .services.external_law_service import external_law_service
from .models.comparison import ComparisonRequest, ComparisonResult, ContradictionDiagnosticItem
from .services.comparison_service import comparison_service
from .models.actionable import ActionableOutputsContainer, ActionableGenerateRequest
from .services.actionable_service import actionable_service
from .evaluation.runner import EvaluationRunner
from .evaluation.metrics import BenchmarkScorecard

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="GenAI-powered Legal Information Navigator making legal documents accessible and navigable."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextUploadRequest(BaseModel):
    filename: str = "document.txt"
    content: str


@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs"
    }


@app.get("/health")
@app.get(f"{settings.API_PREFIX}/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "live_gemini_active": gemini_client.is_live,
        "configured_fast_model": settings.DEFAULT_FAST_MODEL,
        "configured_reasoning_model": settings.DEFAULT_REASONING_MODEL,
        "configured_embedding_model": settings.DEFAULT_EMBEDDING_MODEL,
        "total_documents_loaded": len(document_store.list_documents()),
    }


@app.get(f"{settings.API_PREFIX}/documents", response_model=List[DocumentMeta])
def list_documents():
    return document_store.list_documents()


@app.get(f"{settings.API_PREFIX}/documents/{{doc_id}}", response_model=DocumentMeta)
def get_document(doc_id: str):
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.get(f"{settings.API_PREFIX}/documents/{{doc_id}}/chunks", response_model=List[DocumentChunk])
def get_document_chunks(doc_id: str):
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_store.get_chunks(doc_id)


@app.post(f"{settings.API_PREFIX}/documents/upload", response_model=DocumentMeta)
async def upload_document_file(file: UploadFile = File(...)):
    filename = file.filename or "uploaded_file"
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if filename.lower().endswith(".pdf"):
        meta, _ = document_parser.parse_pdf_bytes(file_bytes, filename=filename)
    elif filename.lower().endswith(".docx"):
        meta, _ = document_parser.parse_docx_bytes(file_bytes, filename=filename)
    else:
        text_content = file_bytes.decode("utf-8", errors="replace")
        meta, _ = document_parser.parse_text_content(text_content, filename=filename)

    return meta


@app.post(f"{settings.API_PREFIX}/documents/text", response_model=DocumentMeta)
def upload_text_document(req: TextUploadRequest):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Document content cannot be empty.")
    meta, _ = document_parser.parse_text_content(req.content, filename=req.filename)
    return meta


@app.post(f"{settings.API_PREFIX}/documents/load-sample", response_model=DocumentMeta)
def load_sample_document(sample_name: str = "residential_lease_agreement.txt"):
    sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample_documents", sample_name))
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail=f"Sample document '{sample_name}' not found at {sample_path}")

    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    meta, _ = document_parser.parse_text_content(content, filename=sample_name)
    return meta


@app.delete(f"{settings.API_PREFIX}/documents/{{doc_id}}")
def delete_document(doc_id: str):
    success = document_store.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True, "doc_id": doc_id}


@app.post(f"{settings.API_PREFIX}/mode/classify", response_model=IntentClassification)
def classify_query_mode(request: QueryRequest):
    try:
        return mode_router.classify_and_route(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/query", response_model=GroundedAnswer)
def execute_query(request: QueryRequest):
    """
    Executes user query according to routed operational mode.
    - Mode 1: Document-Only grounded Q&A with verified evidence citations.
    - Mode 3: General / No-Document legal information.
    - Mode 2: Reclassified Document + External Law (prepared for Phase 5 external retrieval).
    """
    try:
        intent = mode_router.classify_and_route(request)

        # Mode 1: Document-Only Q&A
        if intent.effective_mode == OperationalMode.MODE_1_DOC_ONLY:
            return grounding_engine.answer_document_query(request, intent)

        # Mode 3: General / No-Document Q&A
        if intent.effective_mode == OperationalMode.MODE_3_GENERAL_NO_DOC:
            return general_qa_service.answer_general_query(request, intent)

        # Mode 2: Document + External Law execution
        return external_law_service.answer_external_law_query(request, intent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/navigate", response_model=UnifiedNavigationResponse)
@app.post(f"{settings.API_PREFIX}/v1/navigate", response_model=UnifiedNavigationResponse)
@app.post("/api/v1/navigate", response_model=UnifiedNavigationResponse)
def navigate_legal_context(request: NavigateRequest) -> UnifiedNavigationResponse:
    """
    Unified Legal Information Navigator entrypoint.
    Thinly coordinates mode classification, document grounding, multi-doc comparison,
    external law retrieval, and actionable preparation synthesis without exposing
    internal modes or phase-specific machinery to the user.
    """
    import time
    start_time = time.time()
    try:
        active_doc_ids = list(request.doc_ids)

        # 1. Ingest pasted text if provided and not yet registered
        if request.pasted_content and request.pasted_content.strip():
            meta, _ = document_parser.parse_text_content(
                request.pasted_content.strip(),
                filename="pasted_agreement.txt"
            )
            if meta.doc_id not in active_doc_ids:
                active_doc_ids.append(meta.doc_id)

        # 2. Build situation context if provided
        situation = None
        role_enum = None
        if request.situation_description or request.declared_role or request.jurisdiction:
            role_enum = UserRole.GENERAL
            if request.declared_role:
                try:
                    role_enum = UserRole(request.declared_role.lower())
                except ValueError:
                    role_enum = UserRole.GENERAL
            situation = UserSituation(
                raw_description=request.situation_description or request.query or "",
                declared_role=role_enum,
                jurisdiction=request.jurisdiction
            )

        effective_query = (request.query or "").strip()
        if not effective_query and request.situation_description:
            effective_query = request.situation_description.strip()
        if not effective_query:
            effective_query = "Summarize key contractual terms, obligations, and notice requirements."

        query_req = QueryRequest(
            query=effective_query,
            doc_ids=active_doc_ids,
            situation=situation,
            jurisdiction=request.jurisdiction
        )

        # 3. Classify and route
        intent = mode_router.classify_and_route(query_req)
        if request.requested_mode is not None:
            intent.effective_mode = request.requested_mode

        # 4. Engine dispatch
        grounded_ans: Optional[GroundedAnswer] = None
        comp_res: Optional[ComparisonResult] = None
        actionable_out: Optional[ActionableOutputsContainer] = None

        # Multi-document scenario: run comparison if 2+ documents
        if len(active_doc_ids) >= 2:
            try:
                comp_req = ComparisonRequest(doc_id_a=active_doc_ids[0], doc_id_b=active_doc_ids[1])
                comp_res = comparison_service.compare_documents(comp_req)
            except Exception:
                comp_res = None

        if intent.effective_mode == OperationalMode.MODE_1_DOC_ONLY and len(active_doc_ids) > 0:
            grounded_ans = grounding_engine.answer_document_query(query_req, intent)
        elif intent.effective_mode == OperationalMode.MODE_2_DOC_EXTERNAL and len(active_doc_ids) > 0:
            grounded_ans = external_law_service.answer_external_law_query(query_req, intent)
        else:
            # Mode 3 (No doc or general legal topic)
            grounded_ans = general_qa_service.answer_general_query(query_req, intent)

        # Generate Actionable Preparation Outputs
        try:
            comparison_secondary_id = active_doc_ids[1] if len(active_doc_ids) >= 2 else None
            actionable_out = actionable_service.generate_actionable_outputs(
                doc_ids=active_doc_ids,
                situation_description=request.situation_description or request.query,
                declared_role=role_enum,
                comparison_doc_id=comparison_secondary_id,
                query_text=effective_query,
                operational_mode=intent.effective_mode.value,
                precomputed_comparison=comp_res
            )
        except Exception:
            actionable_out = None

        # 5. Harmonize into UnifiedNavigationResponse
        inferred_role_str = None
        if grounded_ans and grounded_ans.situation_analysis:
            inferred_role_str = grounded_ans.situation_analysis.get("inferred_role")
        if not inferred_role_str and request.declared_role:
            inferred_role_str = request.declared_role

        summary = (grounded_ans.what_this_means_in_plain_language or grounded_ans.answer) if grounded_ans else ""
        if inferred_role_str and inferred_role_str != "unknown":
            perspective_tag = f"From your perspective as {inferred_role_str.capitalize()}: "
            if not summary.lower().startswith("from your perspective"):
                summary = perspective_tag + summary

        # Extract checklist
        checklist = list(grounded_ans.what_to_check_next) if (grounded_ans and grounded_ans.what_to_check_next) else []
        if actionable_out and actionable_out.preparation_checklist:
            checklist = [item.task_description for item in actionable_out.preparation_checklist]

        # Extract covenants matrix
        cov_matrix = actionable_out.covenants_matrix if actionable_out else None

        # Extract brief markdown
        brief_md = actionable_out.markdown_brief_text if actionable_out else None

        # Extract legal framework
        framework_data = None
        if grounded_ans and grounded_ans.external_law:
            framework_data = []
            for el in grounded_ans.external_law:
                if isinstance(el, dict):
                    framework_data.append({
                        "statute": el.get("title") or el.get("statute") or el.get("statute_name") or el.get("source_name", "Statute"),
                        "section": el.get("section_provision") or el.get("section") or el.get("section_reference", "General"),
                        "summary": el.get("provision_title") or el.get("summary") or el.get("rule_summary", ""),
                        "applicability": el.get("exact_retrieved_text") or el.get("applicability") or el.get("applicability_context", "")
                    })
                elif hasattr(el, "rule_summary"):
                    framework_data.append({
                        "statute": getattr(el, "title", "") or getattr(el, "statute_name", "") or getattr(el, "source_name", "Statute"),
                        "section": getattr(el, "section_provision", "") or getattr(el, "section_reference", "General"),
                        "summary": getattr(el, "provision_title", "") or getattr(el, "rule_summary", ""),
                        "applicability": getattr(el, "exact_retrieved_text", "") or getattr(el, "applicability_context", "")
                    })

        # Format sources
        sources_list = list(grounded_ans.sources) if (grounded_ans and grounded_ans.sources) else []

        # Jurisdiction note
        jur_note = None
        if intent.is_jurisdiction_missing or (not intent.target_jurisdiction and len(active_doc_ids) == 0):
            jur_note = "Jurisdiction was not specified. Statutory and regulatory rules vary substantially by jurisdiction."
        elif intent.target_jurisdiction:
            jur_note = f"Governing jurisdiction: {intent.target_jurisdiction}."

        # Diagnostics payload
        elapsed_ms = (time.time() - start_time) * 1000
        diag = {
            "effective_mode": intent.effective_mode.value,
            "category": intent.category.value,
            "confidence": intent.confidence,
            "evidence_sufficiency_passed": grounded_ans.evidence_sufficiency_passed if grounded_ans else True,
            "latency_ms": round(elapsed_ms, 2),
            "doc_count": len(active_doc_ids),
            "has_comparison": comp_res is not None,
            "has_external_law": bool(grounded_ans and grounded_ans.external_law),
        }

        doc_says = None
        if len(active_doc_ids) == 0:
            doc_says = "No document was provided. This response is based on the information supplied and, where applicable, authoritative legal context."
        elif grounded_ans and grounded_ans.what_the_document_says:
            doc_says = grounded_ans.what_the_document_says
        else:
            doc_says = "No document was provided for textual analysis."

        return UnifiedNavigationResponse(
            summary_and_perspective=summary,
            answer=grounded_ans.answer if grounded_ans else "",
            inferred_role=inferred_role_str,
            what_the_document_says=doc_says,
            what_this_means_in_plain_language=grounded_ans.what_this_means_in_plain_language if grounded_ans else "",
            why_it_matters=grounded_ans.why_it_matters_to_your_situation if grounded_ans else None,
            sources=sources_list,
            comparative_analysis=comp_res,
            governing_legal_framework=framework_data,
            jurisdiction_note=jur_note,
            what_is_unclear_or_missing=grounded_ans.what_is_unclear_or_missing if grounded_ans else None,
            uncertainties=grounded_ans.uncertainty_and_gaps if grounded_ans else [],
            actionable_checklist=checklist,
            covenants_matrix=cov_matrix,
            consultation_brief_markdown=brief_md,
            diagnostics=diag
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/compare", response_model=ComparisonResult)
def compare_documents(request: ComparisonRequest):
    """
    Compares two documents or versions semantically, detecting material modifications,
    additions, omissions, express deletions, and true contradictions under Revision 4 rules.
    """
    try:
        return comparison_service.compare_documents(request)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_PREFIX}/documents/{{doc_id}}/contradictions", response_model=List[ContradictionDiagnosticItem])
def get_document_contradictions(doc_id: str):
    """
    Evaluates a single document for intra-document contradictions and internal inconsistencies.
    """
    try:
        req = ComparisonRequest(doc_id_a=doc_id, doc_id_b=None)
        res = comparison_service.compare_documents(req)
        return res.contradictions
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/actionable/generate", response_model=ActionableOutputsContainer)
def generate_actionable_outputs(req: ActionableGenerateRequest):
    """
    Synthesizes Consultation Brief, Document-Described Covenants Matrix,
    and Bounded Preparation Checklist across grounding, external law, and situation engines.
    """
    try:
        return actionable_service.generate_actionable_outputs(
            doc_ids=req.doc_ids,
            situation_description=req.situation_description,
            declared_role=req.declared_role,
            comparison_doc_id=req.comparison_doc_id,
            query_text=req.query_text,
            operational_mode=req.operational_mode,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/evaluation/run", response_model=BenchmarkScorecard)
@app.get(f"{settings.API_PREFIX}/evaluation/run", response_model=BenchmarkScorecard)
def run_evaluation_suite(x_evaluation_key: Optional[str] = Header(None, alias="X-Evaluation-Key")):
    """
    Executes the automated benchmark evaluation suite and returns
    detailed metrics, accuracy scores, and the markdown scorecard.
    Protected in production: disabled unless ENABLE_EVALUATION_ENDPOINT=true and
    if EVALUATION_KEY is configured, valid X-Evaluation-Key header must be supplied.
    """
    if not settings.ENABLE_EVALUATION_ENDPOINT:
        raise HTTPException(status_code=403, detail="Evaluation endpoint is disabled.")
    if settings.EVALUATION_KEY and x_evaluation_key != settings.EVALUATION_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Evaluation-Key.")
    try:
        runner = EvaluationRunner()
        return runner.run_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



