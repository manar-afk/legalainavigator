"""
External Law Grounding Engine (Mode 2: Document + External Law).
Implements the strict 8-step pipeline:
  Mode 1 Doc Analysis -> External Law Detection -> Jurisdiction Resolution ->
  Authoritative Retrieval -> Currency Verification -> Relevance/Applicability Gate ->
  Document <-> Law Connection -> 5-Way Information Separation.
"""

from typing import List, Optional, Dict, Any
import re
import uuid

from ..models.query import QueryRequest, IntentClassification, OperationalMode, QueryCategory
from ..models.response import GroundedAnswer, EvidenceSnippet, MissingInfoItem, InconsistencyItem
from ..models.external_law import (
    AuthoritativeLegalSource,
    JudicialPrecedentSource,
    FailureUncertaintyState,
    SourceCurrencyStatus,
    JurisdictionSignal,
    DocumentLawRelationship,
)
from ..services.retrieval import domain_retriever
from ..services.authoritative_legal_store import authoritative_store
from ..services.jurisdiction_service import jurisdiction_service
from ..services.guardrails import guardrail_service
from ..core.storage import document_store


class ExternalLawService:
    """
    Mode 2 Service connecting private contract covenants with verified public legal frameworks.
    Strictly forbids open web search; uses verified authoritative legal snapshots.
    """

    @classmethod
    def answer_external_law_query(
        cls,
        request: QueryRequest,
        intent: IntentClassification
    ) -> GroundedAnswer:
        query_text = request.query.strip()
        query_lower = query_text.lower()
        user_facts = [request.situation.raw_description] if request.situation and request.situation.raw_description else []
        target_doc_ids = request.doc_ids or document_store.list_all_doc_ids()

        # Step 1: Mode 1 Document Retrieval (Locate relevant contract clauses)
        scored_chunks = domain_retriever.retrieve_chunks(
            query=query_text,
            doc_ids=target_doc_ids,
            top_k=3,
            min_threshold=0.5
        )

        # Check for Insufficient Document Context
        if not scored_chunks and not target_doc_ids:
            return cls._create_abstention_response(
                request=request,
                state=FailureUncertaintyState.INSUFFICIENT_DOCUMENT_CONTEXT,
                message="No uploaded document context available to evaluate against external law.",
                user_facts=user_facts
            )

        # Step 2: Jurisdiction Resolution & Conflict Detection
        j_signal, j_state, j_advisory = jurisdiction_service.resolve_jurisdiction(
            query=query_text,
            doc_ids=target_doc_ids,
            explicit_jurisdiction=request.jurisdiction
        )

        # If Jurisdiction Missing -> Explicit Abstention
        if j_state == FailureUncertaintyState.JURISDICTION_MISSING or not j_signal:
            return cls._create_abstention_response(
                request=request,
                state=FailureUncertaintyState.JURISDICTION_MISSING,
                message=j_advisory or "Jurisdiction missing; cannot evaluate external law without state or country context.",
                user_facts=user_facts
            )

        # If Jurisdiction Conflict -> Flag and handle
        has_jurisdiction_conflict = (j_state == FailureUncertaintyState.JURISDICTION_CONFLICT)

        jurisdiction_val = j_signal.jurisdiction_value

        # Step 3: Extract Topic Keywords for Authoritative Legal Retrieval
        topic_keywords = domain_retriever.tokenize(query_text, filter_stopwords=True)
        if "non-compete" in query_lower or "non compete" in query_lower or "competition" in query_lower or "restraint" in query_lower:
            topic_keywords.extend(["restraint", "trade", "section 27", "contract act", "non-compete", "void"])
        if "notice" in query_lower or "terminate" in query_lower or "leave" in query_lower or "evict" in query_lower:
            topic_keywords.extend(["notice", "lease", "section 106", "section 111", "eviction", "rent act", "tenancy"])
        if "deposit" in query_lower or "security" in query_lower:
            topic_keywords.extend(["deposit", "security", "refund", "rent act", "ceiling"])

        # Step 4: Authoritative Legal-Source Retrieval (NOT open web search)
        candidate_statutes = authoritative_store.search_statutes(
            jurisdiction=jurisdiction_val,
            keywords=topic_keywords,
            include_repealed=True  # Include to inspect currency status explicitly
        )

        # Check for Source Unavailable -> Explicit Abstention
        if not candidate_statutes:
            return cls._create_abstention_response(
                request=request,
                state=FailureUncertaintyState.AUTHORITATIVE_SOURCE_NOT_FOUND,
                message=(
                    f"The current authoritative statutory provision for '{query_text}' in {jurisdiction_val} "
                    "could not be verified in the authoritative legal repository, so no legal conclusion is presented."
                ),
                user_facts=user_facts,
                j_signal=j_signal
            )

        # Step 5: Evidence-Based Source Validity & Currency Verification
        active_statutes: List[AuthoritativeLegalSource] = []
        repealed_statutes: List[AuthoritativeLegalSource] = []
        unverified_currency_statutes: List[AuthoritativeLegalSource] = []

        for s in candidate_statutes:
            if s.currentness_status == SourceCurrencyStatus.REPEALED:
                repealed_statutes.append(s)
            elif s.currentness_status == SourceCurrencyStatus.SOURCE_CURRENTNESS_UNVERIFIED:
                unverified_currency_statutes.append(s)
            else:
                active_statutes.append(s)

        # Check for Currency Failure State
        if unverified_currency_statutes and not active_statutes:
            return cls._create_abstention_response(
                request=request,
                state=FailureUncertaintyState.SOURCE_CURRENTNESS_UNVERIFIED,
                message=(
                    f"Authoritative source currentness could not be verified from official gazette records "
                    f"for '{unverified_currency_statutes[0].title}'. No active legal conclusion can be presented."
                ),
                user_facts=user_facts,
                j_signal=j_signal
            )

        # If only repealed statute exists, abstain from applying it as active law
        if repealed_statutes and not active_statutes:
            return cls._create_abstention_response(
                request=request,
                state=FailureUncertaintyState.AUTHORITATIVE_SOURCE_NOT_FOUND,
                message=(
                    f"The retrieved provision ({repealed_statutes[0].title}) has been repealed in its entirety "
                    f"({repealed_statutes[0].source_locator_version_info}). It cannot be applied as active law."
                ),
                user_facts=user_facts,
                j_signal=j_signal
            )

        # Retrieve verified judicial precedents
        candidate_precedents = authoritative_store.search_precedents(
            jurisdiction=jurisdiction_val,
            keywords=topic_keywords
        )

        # Step 6: Detect Potential Source / Version Conflicts
        version_conflicts = authoritative_store.detect_version_conflicts(active_statutes)

        # Step 7: Candidate Law vs Applicable Law Relevance Gate
        top_statute = active_statutes[0]
        top_chunk = scored_chunks[0][0] if scored_chunks else None
        if len(scored_chunks) > 1 and "non-compete" in query_lower:
            for chk, sc in scored_chunks:
                if "non-compete" in chk.text.lower() or "non-competition" in chk.text.lower() or chk.section_number == "11":
                    top_chunk = chk
                    break

        applicability_uncertain = False
        applicability_reason = ""

        # Example: TPA Section 106 states "in the absence of a contract... to the contrary"
        if "106" in top_statute.section_provision:
            if top_chunk and ("day" in top_chunk.text.lower() or "notice" in top_chunk.text.lower()):
                applicability_uncertain = True
                applicability_reason = (
                    "Section 106 of the Transfer of Property Act, 1882 expressly applies 'in the absence of a "
                    "contract or local law or usage to the contrary'. Because your agreement contains an express written "
                    "notice clause, the contract clause may displace the statutory default notice rule."
                )

        # Step 8: Connect Document Provision <-> External Law (Neutral 4-Stage Synthesis)
        if top_chunk:
            sec_num = top_chunk.section_number or "Clause"
            if sec_num.isdigit() or (len(sec_num) <= 4 and sec_num[0].isdigit()):
                sec_label = f"Section {sec_num}"
            elif not sec_num.lower().startswith("section"):
                sec_label = f"Section {sec_num}"
            else:
                sec_label = sec_num
            doc_clause_ref = f"{sec_label} ({top_chunk.filename})"
        else:
            doc_clause_ref = "Document Provision"
        doc_clause_text = top_chunk.text.strip() if top_chunk else "Contract clause text not isolated."

        # Extract verified document evidence snippets (Strict Invariant: document_facts != external_law)
        verified_snippets: List[EvidenceSnippet] = []
        document_facts: List[str] = []
        chunks_to_include = [top_chunk] if top_chunk else []
        for chk, _ in scored_chunks:
            if chk not in chunks_to_include:
                chunks_to_include.append(chk)

        for chk in chunks_to_include:
            sentences = [s.strip() for s in re.split(r"(?<=[.\n])\s+", chk.text) if len(s.strip()) > 20]
            q_toks = set(domain_retriever.tokenize(query_text, filter_stopwords=True))
            best_sentence = sentences[0] if sentences else chk.text[:150]
            best_cnt = 0
            for s in sentences:
                cnt = sum(1 for tok in q_toks if tok in s.lower())
                if cnt > best_cnt:
                    best_cnt = cnt
                    best_sentence = s
            first_sentence = best_sentence
            raw_doc = document_store.get_raw_text(chk.doc_id) or ""
            c_start = raw_doc.find(first_sentence) if first_sentence in raw_doc else chk.span.start_char
            c_end = c_start + len(first_sentence) if c_start != -1 else chk.span.end_char

            verified_snippets.append(EvidenceSnippet(
                snippet_id=str(uuid.uuid4())[:8],
                doc_id=chk.doc_id,
                filename=chk.filename,
                section_number=chk.section_number,
                section_title=chk.section_title,
                page_number=chk.page_number,
                paragraph_index=chk.paragraph_index,
                quote=first_sentence,
                start_char=c_start,
                end_char=c_end,
                source_type="document"
            ))
            sec_num = chk.section_number or "Clause"
            sec_label = f"Section {sec_num}" if not sec_num.lower().startswith("section") else sec_num
            document_facts.append(f"{sec_label} ({chk.filename}): {first_sentence}")

        # Construct 4-stage relationship
        precedent_text = ""
        top_precedent = candidate_precedents[0] if candidate_precedents else None
        if top_precedent:
            precedent_text = (
                f"In {top_precedent.case_name} ({top_precedent.citation}), the {top_precedent.court} "
                f"reviewed {top_precedent.relevant_provision}, observing that: '{top_precedent.verbatim_excerpt.strip()}'. "
                f"Status: {top_precedent.binding_status}."
            )

        # Factors determining enforceability (non-definitive)
        factors = []
        if "27" in top_statute.section_provision or "non-compete" in query_lower:
            factors = [
                "Whether the restrictive covenant operates strictly post-termination or during the term of active service.",
                "Whether confidential trade secrets, customer goodwill, or proprietary source code are involved.",
                "How an Indian civil court assesses the balance between statutory freedom of trade under Section 27 and non-disclosure obligations."
            ]
        elif "106" in top_statute.section_provision or "notice" in query_lower:
            factors = [
                "Whether the agreement was duly registered and contains an express termination clause displacing default statutory rules.",
                "Whether the tenancy is governed by State-specific rent control legislation (e.g. Karnataka Rent Act, 1999).",
                "Whether appropriate written notice delivery was executed and acknowledged."
            ]
        else:
            factors = [
                "Specific terms of the written contract vs mandatory statutory provisions.",
                "Judicial discretion of the court having territorial and subject-matter jurisdiction."
            ]

        # 4-stage neutral explanation
        stage_1 = f"1. Document Provision: {doc_clause_ref} provides that '{doc_clause_text[:200]}...'."
        stage_2 = (
            f"2. Statutory Provision: {top_statute.section_provision} of {top_statute.title} "
            f"({top_statute.issuing_authority}; {top_statute.source_locator_version_info}; Status: {top_statute.currentness_status.value}) specifies: "
            f"'{top_statute.exact_retrieved_text.strip()}'."
        )
        stage_3 = f"3. Judicial Discussion: {precedent_text}" if precedent_text else "3. Judicial Discussion: No conflicting landmark precedent indexed."
        stage_4 = f"4. Factors & Uncertainty: Enforceability in practice is not automatic and depends on: {'; '.join(factors)}."

        combined_interpretation = f"{stage_1}\n\n{stage_2}\n\n{stage_3}\n\n{stage_4}"
        if has_jurisdiction_conflict and j_advisory:
            combined_interpretation = f"Note: {j_advisory}\n\n{combined_interpretation}"

        softened_answer = guardrail_service.soften_definitive_statements(
            f"The agreement specifies {doc_clause_ref}. The retrieved statutory provision ({top_statute.section_provision} of {top_statute.title}) "
            f"governs {top_statute.provision_title or 'this subject'}. Whether the agreement clause is enforceable in this particular circumstance "
            f"may depend on: {factors[0]}."
        )

        uncertainties = []
        if applicability_uncertain:
            uncertainties.append(applicability_reason)
        if has_jurisdiction_conflict:
            uncertainties.append(j_advisory)
        if version_conflicts:
            uncertainties.append(version_conflicts[0]["details"])
        uncertainties.extend([
            f"Statutory provisions retrieved from official authority ({top_statute.issuing_authority}).",
            "The system presents the applicable provisions neutrally and does not declare legal outcomes or invalidity."
        ])

        neutral_labels = ["Mode 2 (Doc + External Law)", "Authoritative Statute", "Evidence-Based Currency"]
        if applicability_uncertain:
            neutral_labels.append("Legal Applicability Uncertain")
        if has_jurisdiction_conflict:
            neutral_labels.append("Jurisdiction Conflict")
        if version_conflicts:
            neutral_labels.append("Conflicting Authorities")

        # Serialized External Law & Precedents
        external_law_dicts = [s.model_dump() for s in active_statutes]
        precedent_dicts = [p.model_dump() for p in candidate_precedents]

        # Serialized Document Law Relationship
        rel_model = DocumentLawRelationship(
            document_clause_ref=doc_clause_ref,
            document_clause_text=doc_clause_text[:300],
            statutory_provision_ref=f"{top_statute.section_provision} ({top_statute.title})",
            statutory_provision_text=top_statute.exact_retrieved_text,
            judicial_discussion=precedent_text if precedent_text else None,
            factors_and_uncertainties=factors,
            relationship_explanation=combined_interpretation
        )

        return GroundedAnswer(
            document_facts=document_facts,
            user_provided_facts=user_facts,
            external_law=external_law_dicts,
            judicial_precedents=precedent_dicts,
            failure_uncertainty_state=(
                FailureUncertaintyState.JURISDICTION_CONFLICT.value if has_jurisdiction_conflict else
                (FailureUncertaintyState.LEGAL_APPLICABILITY_UNCERTAIN.value if applicability_uncertain else
                 (FailureUncertaintyState.CONFLICTING_AUTHORITIES.value if version_conflicts else None))
            ),
            jurisdiction_signal=j_signal.model_dump() if j_signal else None,
            document_law_relationships=[rel_model.model_dump()],
            plain_language_interpretation=combined_interpretation,
            uncertainty_and_gaps=uncertainties,
            answer=softened_answer,
            what_the_document_says=doc_clause_text[:250],
            what_this_means_in_plain_language=combined_interpretation,
            why_it_matters_to_your_situation=(
                f"Connecting your agreement terms with {top_statute.title} in {jurisdiction_val} provides the legal framework "
                f"that an advocate or court would evaluate."
            ),
            what_is_unclear_or_missing=(
                applicability_reason if applicability_uncertain else "Complete factual dispute context and formal court filings."
            ),
            what_to_check_next=[
                f"Review {top_statute.section_provision} on official portal: {top_statute.official_url}",
                "Consult a licensed legal professional to evaluate enforceability in light of your specific facts."
            ],
            sources=verified_snippets,
            missing_info_details=[],
            inconsistencies=[],
            neutral_labels=neutral_labels,
            operational_mode=OperationalMode.MODE_2_DOC_EXTERNAL,
            query_category=QueryCategory.E_EXTERNAL_LEGAL_INFO,
            evidence_sufficiency_passed=True,
            professional_review_recommended=True
        )

    @classmethod
    def _create_abstention_response(
        cls,
        request: QueryRequest,
        state: FailureUncertaintyState,
        message: str,
        user_facts: List[str],
        j_signal: Optional[JurisdictionSignal] = None
    ) -> GroundedAnswer:
        """
        Generates explicit abstention without manufacturing unverified legal conclusions.
        """
        return GroundedAnswer(
            document_facts=[],
            user_provided_facts=user_facts,
            external_law=[],
            judicial_precedents=[],
            failure_uncertainty_state=state.value,
            jurisdiction_signal=j_signal.model_dump() if j_signal else None,
            document_law_relationships=[],
            plain_language_interpretation=message,
            uncertainty_and_gaps=[
                f"Mode 2 execution halted under state: '{state.value}'.",
                message
            ],
            answer=f"Unable to provide external legal evaluation: {message}",
            what_the_document_says="External legal evaluation halted.",
            what_this_means_in_plain_language=message,
            why_it_matters_to_your_situation="Accurate legal information cannot be provided without verified authoritative sources.",
            what_is_unclear_or_missing=message,
            what_to_check_next=[
                "Specify the governing jurisdiction (e.g. Karnataka, India).",
                "Ensure uploaded documents include the applicable governing law clause."
            ],
            sources=[],
            missing_info_details=[
                MissingInfoItem(
                    field_name=state.value,
                    description=message,
                    why_it_matters="Cannot provide statutory guidance without verified authoritative evidence."
                )
            ],
            inconsistencies=[],
            neutral_labels=["Mode 2 (Doc + External Law)", f"State: {state.value}", "Abstention"],
            operational_mode=OperationalMode.MODE_2_DOC_EXTERNAL,
            query_category=QueryCategory.F_INSUFFICIENT_INFO,
            evidence_sufficiency_passed=False,
            professional_review_recommended=True
        )


external_law_service = ExternalLawService()
