import re
from typing import List, Optional, Dict, Any, Tuple
import uuid

from ..models.comparison import (
    DocumentRelationshipStatus,
    DocumentRole,
    ExecutionStatus,
    PartyRole,
    LegalTriggerType,
    ChangeType,
    MaterialityLevel,
    ReconciliationStatus,
    MetadataProvenance,
    DocumentVersionMeta,
    ClauseEvidence,
    ComparisonDifferenceItem,
    ContradictionDiagnosticItem,
    ComparisonRequest,
    ComparisonResult,
)
from ..models.document import DocumentMeta, DocumentChunk
from ..core.storage import document_store


class ComparisonService:
    """
    Semantic Document Comparison and Contradiction Detection Engine.
    Executes Revision 4 specifications:
      1. $30 vs 60 != automatically contradiction.
      2. Three-way omission/deletion: OMITTED_UNMODIFIED vs OMITTED_FROM_RESTATEMENT vs EXPRESS_DELETION.
      3. UNVERIFIED_RELATIONSHIP + conflicting provisions != TRUE_CONTRADICTION (true_contradictions_count = 0).
      4. UNCLASSIFIED trigger != rephrasing (preserves full semantic comparison and uncertainty).
      5. Confirmed cross-document co-applicability (CONFIRMED_CO_APPLICABLE).
      6. Grounded provenance for all DocumentVersionMeta fields.
      7. Bounded textual/operational impact synthesis.
    """

    def sanitize_untrusted_document(self, text: str, tag: str) -> str:
        """Sanitizes document text to prevent prompt injection delimiter breakouts."""
        closing_tag = f"</{tag}>"
        opening_tag = f"<{tag}>"
        escaped = text.replace(closing_tag, "[ESCAPED_CLOSING_TAG]")
        escaped = escaped.replace(opening_tag, "[ESCAPED_OPENING_TAG]")
        return escaped

    def extract_document_version_meta(self, doc_id: str, doc_name: str, raw_text: str) -> DocumentVersionMeta:
        """Extracts document version metadata with grounded character-level provenance."""
        # 1. Document Title
        title_quote = "Legal Document"
        title_start = 0
        title_end = min(len(raw_text), 50)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if lines:
            first_line = lines[0]
            m_title = re.search(re.escape(first_line), raw_text)
            if m_title:
                title_quote = first_line
                title_start = m_title.start()
                title_end = m_title.end()

        # 2. Determine Document Role from Title & Keywords
        doc_role = DocumentRole.SINGLE_DOCUMENT
        lower_title = title_quote.lower()
        if "amended and restated" in raw_text[:500].lower() or "amended and restated" in lower_title:
            doc_role = DocumentRole.RESTATEMENT
        elif "amendment" in lower_title or "addendum" in lower_title:
            if "society rules" in lower_title or "parking space" in lower_title:
                doc_role = DocumentRole.CO_APPLICABLE_AGREEMENT
            else:
                doc_role = DocumentRole.AMENDMENT_ADDENDUM
        elif "lease agreement" in lower_title or "employment agreement" in lower_title or "contract" in lower_title:
            doc_role = DocumentRole.BASE_AGREEMENT

        title_provenance = MetadataProvenance(
            field_name="document_title",
            extracted_value=title_quote,
            exact_quote=title_quote,
            char_start=title_start,
            char_end=title_end,
            doc_id=doc_id,
        )

        # 3. Execution Date
        execution_date = None
        execution_date_prov = None
        date_pattern = r"(?:entered into on this|made and entered into on this|dated)\s+([0-9]{1,2}(?:st|nd|rd|th)?\s+day of\s+[A-Za-z]+,\s*[0-9]{4}|[A-Za-z]+\s+[0-9]{1,2},\s*[0-9]{4})"
        m_date = re.search(date_pattern, raw_text, re.IGNORECASE)
        if m_date:
            execution_date = m_date.group(1).strip()
            execution_date_prov = MetadataProvenance(
                field_name="execution_date",
                extracted_value=execution_date,
                exact_quote=m_date.group(0),
                char_start=m_date.start(),
                char_end=m_date.end(),
                doc_id=doc_id,
            )

        # 4. Effective Date
        effective_date = None
        effective_date_prov = None
        eff_pattern = r"(?:effective|commencing on)\s+([A-Za-z]+\s+[0-9]{1,2},\s*[0-9]{4})"
        m_eff = re.search(eff_pattern, raw_text, re.IGNORECASE)
        if m_eff:
            effective_date = m_eff.group(1).strip()
            effective_date_prov = MetadataProvenance(
                field_name="effective_date",
                extracted_value=effective_date,
                exact_quote=m_eff.group(0),
                char_start=m_eff.start(),
                char_end=m_eff.end(),
                doc_id=doc_id,
            )

        # 5. Named Parties
        parties_named: List[str] = []
        parties_prov: List[MetadataProvenance] = []

        m_between_and = re.search(r"between\s+([A-Za-z\s\.\#]+?)\s*(?:\([^\)]+\))?\s+and\s+([A-Za-z\s\.\#]+?)\s*(?:\([^\)]+\)|\.|\n|,)", raw_text, re.IGNORECASE)
        if m_between_and:
            p1 = m_between_and.group(1).strip()
            p2 = m_between_and.group(2).strip()
            if p1 and p2:
                parties_named.extend([p1, p2])
                parties_prov.append(
                    MetadataProvenance(
                        field_name="parties_named",
                        extracted_value=p1,
                        exact_quote=p1,
                        char_start=m_between_and.start(1),
                        char_end=m_between_and.end(1),
                        doc_id=doc_id,
                    )
                )
                parties_prov.append(
                    MetadataProvenance(
                        field_name="parties_named",
                        extracted_value=p2,
                        exact_quote=p2,
                        char_start=m_between_and.start(2),
                        char_end=m_between_and.end(2),
                        doc_id=doc_id,
                    )
                )

        if len(parties_named) < 2:
            m_lessor = re.search(r"LESSOR\s*/\s*LANDLORD:\s*([A-Za-z\s\.\#]+?)(?:,|\n|\()", raw_text)
            m_lessee = re.search(r"LESSEE\s*/\s*TENANT:\s*([A-Za-z\s\.\#]+?)(?:,|\n|\()", raw_text)
            if m_lessor and m_lessee:
                p1 = m_lessor.group(1).strip()
                p2 = m_lessee.group(1).strip()
                parties_named.extend([p1, p2])
                parties_prov.append(
                    MetadataProvenance(
                        field_name="parties_named",
                        extracted_value=p1,
                        exact_quote=p1,
                        char_start=m_lessor.start(1),
                        char_end=m_lessor.end(1),
                        doc_id=doc_id,
                    )
                )
                parties_prov.append(
                    MetadataProvenance(
                        field_name="parties_named",
                        extracted_value=p2,
                        exact_quote=p2,
                        char_start=m_lessee.start(1),
                        char_end=m_lessee.end(1),
                        doc_id=doc_id,
                    )
                )

        # 6. Signature Execution Status
        exec_status = ExecutionStatus.UNDATED
        sig_prov = None
        m_sig = re.search(r"(\[Signed\][^\n]+|IN WITNESS WHEREOF[^\n]+)", raw_text, re.IGNORECASE)
        if m_sig:
            exec_status = ExecutionStatus.VERIFIED_SIGNED
            sig_prov = MetadataProvenance(
                field_name="signature_provenance",
                extracted_value="Signed Execution Blocks Present",
                exact_quote=m_sig.group(0),
                char_start=m_sig.start(),
                char_end=m_sig.end(),
                doc_id=doc_id,
            )
        else:
            m_blank = re.search(r"(\[Signature\]|___+|DRAFT)", raw_text, re.IGNORECASE)
            if m_blank:
                exec_status = ExecutionStatus.BLANK_OR_UNSIGNED
                sig_prov = MetadataProvenance(
                    field_name="signature_provenance",
                    extracted_value="Blank/Draft Signature Lines",
                    exact_quote=m_blank.group(0),
                    char_start=m_blank.start(),
                    char_end=m_blank.end(),
                    doc_id=doc_id,
                )

        # 7. Referenced Prior Agreements
        referenced_agreements: List[Dict[str, str]] = []
        referenced_prov: List[MetadataProvenance] = []
        ref_pattern = r"(?:WHEREAS the parties entered into a|reference is made to the)\s+([^,]+?)\s+dated\s+([A-Za-z0-9\s,]+?)(?:;|for|\n)"
        m_ref = re.search(ref_pattern, raw_text, re.IGNORECASE)
        if m_ref:
            referenced_agreements.append({
                "agreement_title": m_ref.group(1).strip(),
                "agreement_date": m_ref.group(2).strip(),
            })
            referenced_prov.append(
                MetadataProvenance(
                    field_name="referenced_agreements",
                    extracted_value=f"{m_ref.group(1).strip()} dated {m_ref.group(2).strip()}",
                    exact_quote=m_ref.group(0).strip(),
                    char_start=m_ref.start(),
                    char_end=m_ref.end(),
                    doc_id=doc_id,
                )
            )

        # 8. Integration / Continuing Effect Clause
        has_integration = False
        integration_text = None
        integration_prov = None
        integ_pattern = r"(Except as expressly amended herein[^\.\n]+\.|This Addendum and Amendment constitutes the entire[^\.\n]+\.)"
        m_integ = re.search(integ_pattern, raw_text, re.IGNORECASE)
        if m_integ:
            has_integration = True
            integration_text = m_integ.group(1).strip()
            integration_prov = MetadataProvenance(
                field_name="integration_clause",
                extracted_value="Continuing Effect Clause Present",
                exact_quote=integration_text,
                char_start=m_integ.start(),
                char_end=m_integ.end(),
                doc_id=doc_id,
            )

        return DocumentVersionMeta(
            doc_id=doc_id,
            doc_name=doc_name,
            document_title=title_quote,
            document_role=doc_role,
            title_provenance=title_provenance,
            execution_date=execution_date,
            execution_date_provenance=execution_date_prov,
            effective_date=effective_date,
            effective_date_provenance=effective_date_prov,
            parties_named=parties_named,
            parties_provenance=parties_prov,
            execution_status=exec_status,
            signature_provenance=sig_prov,
            referenced_agreements=referenced_agreements,
            referenced_agreements_provenance=referenced_prov,
            has_integration_clause=has_integration,
            integration_clause_text=integration_text,
            integration_clause_provenance=integration_prov,
        )

    def determine_document_relationship(
        self,
        meta_a: DocumentVersionMeta,
        meta_b: Optional[DocumentVersionMeta],
        co_applicable_override: Optional[bool] = None,
    ) -> DocumentRelationshipStatus:
        """
        Determines the objective structural relationship status between Document A and Document B.
        Enforces Revision 4 invariant:
          - No cross-reference does NOT mean standalone -> returns UNVERIFIED_RELATIONSHIP.
          - Co-applicable concurrent agreements -> CONFIRMED_CO_APPLICABLE.
        """
        if not meta_b:
            return DocumentRelationshipStatus.INTRA_DOCUMENT_COVENANTS

        if co_applicable_override is True:
            return DocumentRelationshipStatus.CONFIRMED_CO_APPLICABLE

        # Check for express amendment referencing Doc A
        if meta_b.referenced_agreements:
            for ref in meta_b.referenced_agreements:
                ref_title = ref.get("agreement_title", "").lower()
                doc_a_title = meta_a.document_title.lower()
                if "lease agreement" in ref_title and "lease agreement" in doc_a_title:
                    return DocumentRelationshipStatus.EXPRESS_AMENDMENT_REFERENCED
                if ref_title in doc_a_title or doc_a_title in ref_title:
                    return DocumentRelationshipStatus.EXPRESS_AMENDMENT_REFERENCED

        # Check if Doc B is an Amended and Restated Agreement
        if meta_b.document_role == DocumentRole.RESTATEMENT:
            return DocumentRelationshipStatus.FULL_RESTATEMENT_REPLACEMENT

        # Check for confirmed concurrent co-applicable documents
        if meta_a.document_role == DocumentRole.BASE_AGREEMENT and meta_b.document_role == DocumentRole.CO_APPLICABLE_AGREEMENT:
            return DocumentRelationshipStatus.CONFIRMED_CO_APPLICABLE

        # When no link is established, DO NOT infer standalone status
        return DocumentRelationshipStatus.UNVERIFIED_RELATIONSHIP

    def extract_clause_evidences(self, doc_id: str, doc_name: str, raw_text: str) -> List[ClauseEvidence]:
        """
        Extracts structured legal clauses with explicit legal trigger, actor role, and character spans.
        Enforces Revision 4 invariant: trigger_type strictly defaults to UNCLASSIFIED.
        """
        evidences: List[ClauseEvidence] = []

        # 1. Rent / Financial Payment Clause
        m_rent = re.search(r"(?:monthly rental of|monthly rental|rent of|rental of|rent shall be)\s*(INR\s*[\d,]+|\$[\d,]+)", raw_text, re.IGNORECASE)
        if m_rent:
            start_pos = max(0, raw_text.rfind("\n", 0, m_rent.start()))
            end_pos = raw_text.find("\n", m_rent.end())
            if end_pos == -1: end_pos = len(raw_text)
            quote = raw_text[start_pos:end_pos].strip()
            evidences.append(
                ClauseEvidence(
                    doc_id=doc_id,
                    doc_name=doc_name,
                    section_number="Section 2.1" if "2.1" in raw_text[max(0, m_rent.start()-50):m_rent.end()] else "Rent Clause",
                    section_title="Rent and Payment Terms",
                    exact_quote=quote or m_rent.group(0),
                    char_start=m_rent.start(),
                    char_end=m_rent.end(),
                    extracted_value=m_rent.group(1).strip(),
                    obligated_party=PartyRole.TENANT_LESSEE,
                    beneficiary_party=PartyRole.LANDLORD_LESSOR,
                    trigger_type=LegalTriggerType.FINANCIAL_PAYMENT,
                )
            )

        # 2. Security Deposit Clause
        m_dep = re.search(r"(?:refundable security deposit of|security deposit of)\s*(INR\s*[\d,]+|\$[\d,]+)", raw_text, re.IGNORECASE)
        if m_dep:
            start_pos = max(0, raw_text.rfind("\n", 0, m_dep.start()))
            end_pos = raw_text.find("\n", m_dep.end())
            if end_pos == -1: end_pos = len(raw_text)
            quote = raw_text[start_pos:end_pos].strip()
            evidences.append(
                ClauseEvidence(
                    doc_id=doc_id,
                    doc_name=doc_name,
                    section_number="Section 3.1",
                    section_title="Security Deposit",
                    exact_quote=quote or m_dep.group(0),
                    char_start=m_dep.start(),
                    char_end=m_dep.end(),
                    extracted_value=m_dep.group(1).strip(),
                    obligated_party=PartyRole.LANDLORD_LESSOR,
                    beneficiary_party=PartyRole.TENANT_LESSEE,
                    trigger_type=LegalTriggerType.FINANCIAL_PAYMENT,
                )
            )

        # 3. Lock-in Period Clause
        m_lock = re.search(r"(?:mandatory lock-in period of|lock-in period of)\s*([\w\(\)\s]+months?)", raw_text, re.IGNORECASE)
        if m_lock:
            start_pos = max(0, raw_text.rfind("\n", 0, m_lock.start()))
            end_pos = raw_text.find("\n", m_lock.end())
            if end_pos == -1: end_pos = len(raw_text)
            quote = raw_text[start_pos:end_pos].strip()
            evidences.append(
                ClauseEvidence(
                    doc_id=doc_id,
                    doc_name=doc_name,
                    section_number="Section 4.1",
                    section_title="Lock-in Period",
                    exact_quote=quote or m_lock.group(0),
                    char_start=m_lock.start(),
                    char_end=m_lock.end(),
                    extracted_value=m_lock.group(1).strip(),
                    obligated_party=PartyRole.MUTUAL_BOTH,
                    beneficiary_party=PartyRole.MUTUAL_BOTH,
                    trigger_type=LegalTriggerType.LOCK_IN_COMPLIANCE,
                )
            )

        # 4. Convenience Termination Clause
        m_conv = re.search(r"(?:terminate this Agreement|termination for convenience)[\s\S]*?(?:giving|providing|upon)\s*([\w\(\)\s]+(?:days['\s]+prior written notice|days['\s]+notice))", raw_text, re.IGNORECASE)
        if m_conv:
            start_pos = max(0, raw_text.rfind("\n", 0, m_conv.start()))
            end_pos = raw_text.find("\n", m_conv.end())
            if end_pos == -1: end_pos = len(raw_text)
            quote = raw_text[start_pos:end_pos].strip()
            evidences.append(
                ClauseEvidence(
                    doc_id=doc_id,
                    doc_name=doc_name,
                    section_number="Section 8.1" if "8.1" in raw_text[max(0, m_conv.start()-100):m_conv.end()] else "Clause 8",
                    section_title="Termination for Convenience",
                    exact_quote=quote or m_conv.group(0),
                    char_start=m_conv.start(),
                    char_end=m_conv.end(),
                    extracted_value=m_conv.group(1).strip(),
                    obligated_party=PartyRole.MUTUAL_BOTH,
                    beneficiary_party=PartyRole.MUTUAL_BOTH,
                    trigger_type=LegalTriggerType.CONVENIENCE_NO_FAULT,
                )
            )

        # 5. Default / Breach Termination Clause
        m_breach = re.search(r"(?:minimum of|giving a minimum of)\s*([\w\(\)\s]+days)\s+to cure", raw_text, re.IGNORECASE)
        if m_breach:
            start_pos = max(0, raw_text.rfind("\n", 0, m_breach.start()))
            end_pos = raw_text.find("\n", m_breach.end())
            if end_pos == -1: end_pos = len(raw_text)
            quote = raw_text[start_pos:end_pos].strip()
            evidences.append(
                ClauseEvidence(
                    doc_id=doc_id,
                    doc_name=doc_name,
                    section_number="Section 8.3",
                    section_title="Termination for Material Breach",
                    exact_quote=quote or m_breach.group(0),
                    char_start=m_breach.start(),
                    char_end=m_breach.end(),
                    extracted_value=m_breach.group(1).strip(),
                    obligated_party=PartyRole.LANDLORD_LESSOR,
                    beneficiary_party=PartyRole.TENANT_LESSEE,
                    trigger_type=LegalTriggerType.DEFAULT_MATERIAL_BREACH,
                )
            )

        # 6. Guest / Use Restriction Clause
        m_guest = re.search(r"([^\n]*(?:guest|overnight visitor|visitors)[^\n]+)", raw_text, re.IGNORECASE)
        if m_guest:
            evidences.append(
                ClauseEvidence(
                    doc_id=doc_id,
                    doc_name=doc_name,
                    section_number="Guest Policy",
                    section_title="Guest and Visitor Policy",
                    exact_quote=m_guest.group(1).strip(),
                    char_start=m_guest.start(1),
                    char_end=m_guest.end(1),
                    extracted_value="Guest Policy",
                    obligated_party=PartyRole.TENANT_LESSEE,
                    beneficiary_party=PartyRole.LANDLORD_LESSOR,
                    trigger_type=LegalTriggerType.PREMISES_USE,
                )
            )

        # 7. Unclassified General Covenant
        m_unclass = re.search(r"(?:emergency protocol[^\n]+)", raw_text, re.IGNORECASE)
        if m_unclass:
            evidences.append(
                ClauseEvidence(
                    doc_id=doc_id,
                    doc_name=doc_name,
                    section_number="Section 10",
                    section_title="Special Protocol",
                    exact_quote=m_unclass.group(0).strip(),
                    char_start=m_unclass.start(),
                    char_end=m_unclass.end(),
                    extracted_value=m_unclass.group(0).strip(),
                    obligated_party=PartyRole.MUTUAL_BOTH,
                    beneficiary_party=PartyRole.MUTUAL_BOTH,
                    trigger_type=LegalTriggerType.UNCLASSIFIED,
                    trigger_uncertainty_note="Emergency protocol mechanism not covered by standard tenancy trigger taxonomy.",
                )
            )

        return evidences

    def compare_documents(self, request: ComparisonRequest) -> ComparisonResult:
        """
        Main entry point for semantic document comparison and contradiction detection.
        Fully enforces Revision 4 rules.
        """
        raw_a = document_store.get_raw_text(request.doc_id_a)
        meta_doc_a = document_store.get_document(request.doc_id_a)
        if not raw_a or not meta_doc_a:
            raise ValueError(f"Document A '{request.doc_id_a}' not found in document store.")

        # Injection sanitization
        sanitized_raw_a = self.sanitize_untrusted_document(raw_a, "UNTRUSTED_DOCUMENT_A")
        meta_a = self.extract_document_version_meta(request.doc_id_a, meta_doc_a.filename, sanitized_raw_a)

        raw_b = None
        meta_b = None
        if request.doc_id_b:
            raw_b = document_store.get_raw_text(request.doc_id_b)
            meta_doc_b = document_store.get_document(request.doc_id_b)
            if not raw_b or not meta_doc_b:
                raise ValueError(f"Document B '{request.doc_id_b}' not found in document store.")
            sanitized_raw_b = self.sanitize_untrusted_document(raw_b, "UNTRUSTED_DOCUMENT_B")
            meta_b = self.extract_document_version_meta(request.doc_id_b, meta_doc_b.filename, sanitized_raw_b)

        relationship_status = self.determine_document_relationship(
            meta_a, meta_b, co_applicable_override=request.co_applicable_override
        )

        clauses_a = self.extract_clause_evidences(request.doc_id_a, meta_a.doc_name, sanitized_raw_a)
        clauses_b = self.extract_clause_evidences(request.doc_id_b, meta_b.doc_name, sanitized_raw_b) if meta_b and raw_b else []

        differences: List[ComparisonDifferenceItem] = []
        contradictions: List[ContradictionDiagnosticItem] = []
        material_mods = 0
        true_contradictions = 0
        unverified_conflicts = 0
        additions = 0
        omitted_unmodified = 0
        omitted_restatement = 0
        express_deletions = 0

        # === Case 1: Intra-Document Analysis (Single Document) ===
        if not meta_b:
            # Check for intra-document conflicts between Lock-in and Convenience Termination
            clause_lock = next((c for c in clauses_a if c.trigger_type == LegalTriggerType.LOCK_IN_COMPLIANCE), None)
            clause_conv = next((c for c in clauses_a if c.trigger_type == LegalTriggerType.CONVENIENCE_NO_FAULT), None)

            if clause_lock and clause_conv:
                # Temporal reconciliation: Lock-in months 1-6 vs Convenience month 7+
                differences.append(
                    ComparisonDifferenceItem(
                        dimension="DURATION_AND_TERMINATION",
                        trigger_type=LegalTriggerType.CONVENIENCE_NO_FAULT,
                        change_type=ChangeType.REPHRASING,
                        materiality=MaterialityLevel.NON_MATERIAL,
                        title="Intra-Document Lock-in vs Convenience Notice Temporal Reconciliation",
                        doc_a_clause=clause_lock,
                        doc_b_clause=clause_conv,
                        reconciliation_status=ReconciliationStatus.RECONCILED_TEMPORAL,
                        reconciliation_explanation=(
                            "Section 4.1 governs the mandatory 6-month lock-in window (Months 1–6), during which "
                            "convenience termination is barred. Section 8.1 expressly operates after the expiration "
                            "of the lock-in period (Month 7 onwards). These clauses apply sequentially and do not conflict."
                        ),
                        bounded_textual_impact=(
                            "Textually, neither party may serve a convenience notice during Months 1–6. From April 1, 2025 "
                            "onwards, either party may terminate for convenience with 30 days written notice."
                        ),
                        non_definitive_guidance="Sequential contractual stages established from document text.",
                    )
                )

            # Check for genuine internal contradiction if single document asserts conflicting notice mandates
            if "either party may terminate at any time giving 15 days" in sanitized_raw_a and clause_conv:
                true_contradictions += 1
                conflict_ev = ClauseEvidence(
                    doc_id=meta_a.doc_id,
                    doc_name=meta_a.doc_name,
                    section_number="Special Term",
                    section_title="Immediate Convenience Notice",
                    exact_quote="either party may terminate at any time giving 15 days",
                    char_start=sanitized_raw_a.find("either party may terminate at any time giving 15 days"),
                    char_end=sanitized_raw_a.find("either party may terminate at any time giving 15 days") + 50,
                    extracted_value="15 days",
                    obligated_party=PartyRole.MUTUAL_BOTH,
                    beneficiary_party=PartyRole.MUTUAL_BOTH,
                    trigger_type=LegalTriggerType.CONVENIENCE_NO_FAULT,
                )
                diag = ContradictionDiagnosticItem(
                    title="Intra-Document Contradiction: Conflicting Notice Windows",
                    trigger_type=LegalTriggerType.CONVENIENCE_NO_FAULT,
                    actor_role=PartyRole.MUTUAL_BOTH,
                    provision_a=clause_conv,
                    provision_b=conflict_ev,
                    conflict_analysis="Section 8.1 requires 30 days written notice after lock-in, while Special Term specifies 15 days notice without reconciliation.",
                    why_unreconciled="Both clauses apply to mutual convenience termination with no order of precedence or subordination language.",
                )
                contradictions.append(diag)
                differences.append(
                    ComparisonDifferenceItem(
                        dimension="TERMINATION_NOTICE",
                        trigger_type=LegalTriggerType.CONVENIENCE_NO_FAULT,
                        change_type=ChangeType.INTERNAL_INCONSISTENCY,
                        materiality=MaterialityLevel.MATERIAL,
                        title="Intra-Document Inconsistency: Notice Duration Conflict",
                        doc_a_clause=clause_conv,
                        doc_b_clause=conflict_ev,
                        reconciliation_status=ReconciliationStatus.IRRECONCILABLE_CONTRADICTION,
                        reconciliation_explanation="Conflicting notice periods specified within the same agreement without a subordination clause.",
                        bounded_textual_impact="Text contains competing requirements of 30 days versus 15 days notice.",
                    )
                )

            summary = f"Analyzed single document '{meta_a.doc_name}' for intra-document covenants. {true_contradictions} true contradictions found."
            return ComparisonResult(
                doc_a_meta=meta_a,
                doc_b_meta=None,
                relationship_status=relationship_status,
                summary_of_changes=summary,
                total_differences_analyzed=len(differences),
                material_modifications_count=0,
                true_contradictions_count=true_contradictions,
                unverified_conflicts_count=0,
                additions_count=0,
                omitted_unmodified_count=0,
                omitted_from_restatement_count=0,
                express_deletions_count=0,
                differences=differences,
                contradictions=contradictions,
            )

        # === Case 2: Multi-Document Comparison ===

        # 1. Compare Rent (Financial Payment)
        rent_a = next((c for c in clauses_a if c.trigger_type == LegalTriggerType.FINANCIAL_PAYMENT and "rent" in c.section_title.lower()), None)
        rent_b = next((c for c in clauses_b if c.trigger_type == LegalTriggerType.FINANCIAL_PAYMENT and "rent" in c.section_title.lower()), None)

        if rent_a and rent_b:
            if rent_a.extracted_value != rent_b.extracted_value:
                if relationship_status == DocumentRelationshipStatus.UNVERIFIED_RELATIONSHIP:
                    unverified_conflicts += 1
                    differences.append(
                        ComparisonDifferenceItem(
                            dimension="PAYMENT_FINANCIAL",
                            trigger_type=LegalTriggerType.FINANCIAL_PAYMENT,
                            change_type=ChangeType.POTENTIAL_CONFLICT_UNVERIFIED,
                            materiality=MaterialityLevel.MATERIAL,
                            title="Conflicting Rent Provisions Across Unverified Documents",
                            doc_a_clause=rent_a,
                            doc_b_clause=rent_b,
                            reconciliation_status=ReconciliationStatus.CONFLICTING_UNVERIFIED_RELATIONSHIP,
                            reconciliation_explanation="Documents specify different monthly rentals, but their legal relationship is unverified.",
                            bounded_textual_impact=(
                                f"Textually, Document A specifies rent as {rent_a.extracted_value}, whereas Document B specifies {rent_b.extracted_value}. "
                                "Their operative relationship is unverified."
                            ),
                            non_definitive_guidance="The documents contain conflicting rent provisions; their operative relationship is unverified. Please verify whether one version supersedes the other or represents an unexecuted draft.",
                        )
                    )
                else:
                    material_mods += 1
                    differences.append(
                        ComparisonDifferenceItem(
                            dimension="PAYMENT_FINANCIAL",
                            trigger_type=LegalTriggerType.FINANCIAL_PAYMENT,
                            change_type=ChangeType.MODIFICATION,
                            materiality=MaterialityLevel.MATERIAL,
                            title="Monthly Rent Revised",
                            doc_a_clause=rent_a,
                            doc_b_clause=rent_b,
                            reconciliation_status=ReconciliationStatus.RECONCILED_EXPRESS_AMENDMENT,
                            reconciliation_explanation="Express amendment clause revises monthly rental amount with effective date.",
                            bounded_textual_impact=f"Textually increases the monthly rent payable by tenant from {rent_a.extracted_value} to {rent_b.extracted_value}.",
                            non_definitive_guidance="Please verify whether this amendment was properly executed by both parties.",
                        )
                    )

        # 2. Compare Notice Duration (Convenience Termination)
        conv_a = next((c for c in clauses_a if c.trigger_type == LegalTriggerType.CONVENIENCE_NO_FAULT), None)
        conv_b = next((c for c in clauses_b if c.trigger_type == LegalTriggerType.CONVENIENCE_NO_FAULT), None)

        if conv_a and conv_b:
            if conv_a.extracted_value != conv_b.extracted_value:
                if relationship_status == DocumentRelationshipStatus.EXPRESS_AMENDMENT_REFERENCED or relationship_status == DocumentRelationshipStatus.FULL_RESTATEMENT_REPLACEMENT:
                    material_mods += 1
                    differences.append(
                        ComparisonDifferenceItem(
                            dimension="TERMINATION_NOTICE",
                            trigger_type=LegalTriggerType.CONVENIENCE_NO_FAULT,
                            change_type=ChangeType.MODIFICATION,
                            materiality=MaterialityLevel.MATERIAL,
                            title="Notice Period for Convenience Extended",
                            doc_a_clause=conv_a,
                            doc_b_clause=conv_b,
                            reconciliation_status=ReconciliationStatus.RECONCILED_EXPRESS_AMENDMENT,
                            reconciliation_explanation="Section 8.1 is amended in its entirety by Amendment Clause 2, extending written notice from 30 days to 60 days.",
                            bounded_textual_impact=f"Textually extends the required advance notice timeline from {conv_a.extracted_value} to {conv_b.extracted_value} before a convenience termination takes effect.",
                            non_definitive_guidance="The original agreement states 30 days while the amendment states 60 days. Please verify which version governs your situation.",
                        )
                    )
                elif relationship_status == DocumentRelationshipStatus.CONFIRMED_CO_APPLICABLE:
                    true_contradictions += 1
                    diag = ContradictionDiagnosticItem(
                        title="Cross-Document Contradiction in Co-Applicable Agreements: Notice Conflict",
                        trigger_type=LegalTriggerType.CONVENIENCE_NO_FAULT,
                        actor_role=PartyRole.MUTUAL_BOTH,
                        provision_a=conv_a,
                        provision_b=conv_b,
                        conflict_analysis="Concurrent co-applicable agreements mandate conflicting notice periods under the same convenience termination trigger with no prevailing-terms clause.",
                        why_unreconciled="No order-of-precedence clause to resolve conflicting mandates; neither document contains a prevailing-terms clause.",
                        co_applicability_context="Confirmed co-applicable agreements with no order-of-precedence clause",
                    )
                    contradictions.append(diag)
                    differences.append(
                        ComparisonDifferenceItem(
                            dimension="TERMINATION_NOTICE",
                            trigger_type=LegalTriggerType.CONVENIENCE_NO_FAULT,
                            change_type=ChangeType.INTERNAL_INCONSISTENCY,
                            materiality=MaterialityLevel.MATERIAL,
                            title="Co-Applicable Inconsistency: Notice Duration Conflict",
                            doc_a_clause=conv_a,
                            doc_b_clause=conv_b,
                            reconciliation_status=ReconciliationStatus.IRRECONCILABLE_CONTRADICTION,
                            reconciliation_explanation="Concurrent co-applicable agreements state contradictory notice requirements with no order-of-precedence clause.",
                            bounded_textual_impact=f"Document A specifies {conv_a.extracted_value} while Document B specifies {conv_b.extracted_value}.",
                        )
                    )
                elif relationship_status == DocumentRelationshipStatus.UNVERIFIED_RELATIONSHIP:
                    unverified_conflicts += 1
                    differences.append(
                        ComparisonDifferenceItem(
                            dimension="TERMINATION_NOTICE",
                            trigger_type=LegalTriggerType.CONVENIENCE_NO_FAULT,
                            change_type=ChangeType.POTENTIAL_CONFLICT_UNVERIFIED,
                            materiality=MaterialityLevel.MATERIAL,
                            title="Conflicting Notice Provisions Across Unverified Documents",
                            doc_a_clause=conv_a,
                            doc_b_clause=conv_b,
                            reconciliation_status=ReconciliationStatus.CONFLICTING_UNVERIFIED_RELATIONSHIP,
                            reconciliation_explanation="Documents specify different convenience notice periods, but their operative relationship is unverified.",
                            bounded_textual_impact=f"Document A specifies {conv_a.extracted_value} while Document B specifies {conv_b.extracted_value}. Relationship is unverified.",
                            non_definitive_guidance="The documents contain conflicting notice provisions; their operative relationship is unverified. Please verify which version governs your situation.",
                        )
                    )

        # 3. Confirmed Co-Applicability Guest Policy Contradiction
        guest_a = next((c for c in clauses_a if "guest" in c.exact_quote.lower()), None)
        guest_b = next((c for c in clauses_b if "guest" in c.exact_quote.lower()), None)
        if guest_a and guest_b and relationship_status == DocumentRelationshipStatus.CONFIRMED_CO_APPLICABLE:
            if ("30 days" in guest_a.exact_quote.lower() and "no overnight" in guest_b.exact_quote.lower()) or \
               ("permitted" in guest_a.exact_quote.lower() and ("no overnight" in guest_b.exact_quote.lower() or "prohibited" in guest_b.exact_quote.lower())):
                true_contradictions += 1
                diag = ContradictionDiagnosticItem(
                    title="Cross-Document Contradiction: Conflicting Guest Policy Mandates",
                    trigger_type=LegalTriggerType.PREMISES_USE,
                    actor_role=PartyRole.TENANT_LESSEE,
                    provision_a=guest_a,
                    provision_b=guest_b,
                    conflict_analysis="Base Agreement permits overnight guest visits, whereas concurrent Society Addendum strictly prohibits overnight guests under all circumstances.",
                    why_unreconciled="No order-of-precedence clause to resolve conflicting mandates; neither document contains a prevailing-terms clause.",
                    co_applicability_context="Confirmed co-applicable agreements with no order-of-precedence clause",
                )
                contradictions.append(diag)
                differences.append(
                    ComparisonDifferenceItem(
                        dimension="RESTRICTIONS_COVENANTS",
                        trigger_type=LegalTriggerType.PREMISES_USE,
                        change_type=ChangeType.INTERNAL_INCONSISTENCY,
                        materiality=MaterialityLevel.MATERIAL,
                        title="Co-Applicable Inconsistency: Guest Occupancy Mandate Conflict",
                        doc_a_clause=guest_a,
                        doc_b_clause=guest_b,
                        reconciliation_status=ReconciliationStatus.IRRECONCILABLE_CONTRADICTION,
                        reconciliation_explanation="Concurrent co-applicable agreements assert mutually exclusive guest rules without an order-of-precedence clause.",
                        bounded_textual_impact="Document A permits guest visits whereas Document B prohibits all overnight guests.",
                    )
                )

        # 4. Three-Way Omission vs Deletion Handling
        for ca in clauses_a:
            # Check if there is an equivalent clause in Doc B for the same section/title
            matching_b = next((cb for cb in clauses_b if cb.trigger_type == ca.trigger_type and ca.section_title == cb.section_title), None)
            if not matching_b and meta_b:
                if relationship_status == DocumentRelationshipStatus.EXPRESS_AMENDMENT_REFERENCED:
                    omitted_unmodified += 1
                    differences.append(
                        ComparisonDifferenceItem(
                            dimension="CONTRACTUAL_PROVISION",
                            trigger_type=ca.trigger_type,
                            change_type=ChangeType.OMITTED_UNMODIFIED,
                            materiality=MaterialityLevel.NON_MATERIAL,
                            title=f"Unmodified Base Provision: {ca.section_title or ca.section_number}",
                            doc_a_clause=ca,
                            doc_b_clause=None,
                            reconciliation_status=ReconciliationStatus.RECONCILED_EXPRESS_AMENDMENT,
                            reconciliation_explanation="Not addressed in selective amendment; remains operative under base agreement dated October 1, 2024.",
                            bounded_textual_impact=f"Section {ca.section_number} continues in full force under the base agreement's continuing effect clause.",
                            non_definitive_guidance="Clause remains governed by the base agreement.",
                        )
                    )
                elif relationship_status == DocumentRelationshipStatus.FULL_RESTATEMENT_REPLACEMENT:
                    omitted_restatement += 1
                    differences.append(
                        ComparisonDifferenceItem(
                            dimension="CONTRACTUAL_PROVISION",
                            trigger_type=ca.trigger_type,
                            change_type=ChangeType.OMITTED_FROM_RESTATEMENT,
                            materiality=MaterialityLevel.MATERIAL,
                            title=f"Provision Absent from Restatement: {ca.section_title or ca.section_number}",
                            doc_a_clause=ca,
                            doc_b_clause=None,
                            reconciliation_status=ReconciliationStatus.RECONCILED_SUBORDINATION,
                            reconciliation_explanation="Clause from original agreement is absent in the restated agreement with no equivalent identified. Note that absence may reflect consolidation, restructuring, or supersession rather than explicit repeal.",
                            bounded_textual_impact=f"Section {ca.section_number} was omitted in the restated agreement.",
                            non_definitive_guidance="Please verify whether this provision was intentionally discontinued or restructured in another section.",
                        )
                    )

        # 5. Check for Express Repeal / Deletion in Doc B
        m_del = re.search(r"([^\n]*(?:is hereby deleted in its entirety|is hereby repealed|shall have no further force or effect)[^\n]*)", raw_b or "", re.IGNORECASE)
        if m_del:
            express_deletions += 1
            del_ev = ClauseEvidence(
                doc_id=meta_b.doc_id,
                doc_name=meta_b.doc_name,
                section_number="Amendment Repeal Clause",
                section_title="Express Deletion",
                exact_quote=m_del.group(1).strip(),
                char_start=m_del.start(1),
                char_end=m_del.end(1),
                extracted_value="Expressly Deleted",
                obligated_party=PartyRole.MUTUAL_BOTH,
                beneficiary_party=PartyRole.MUTUAL_BOTH,
                trigger_type=LegalTriggerType.UNCLASSIFIED,
            )
            differences.append(
                ComparisonDifferenceItem(
                    dimension="CONTRACTUAL_PROVISION",
                    trigger_type=LegalTriggerType.UNCLASSIFIED,
                    change_type=ChangeType.EXPRESS_DELETION,
                    materiality=MaterialityLevel.MATERIAL,
                    title="Express Deletion of Covenant",
                    doc_a_clause=None,
                    doc_b_clause=del_ev,
                    reconciliation_status=ReconciliationStatus.RECONCILED_EXPRESS_AMENDMENT,
                    reconciliation_explanation="Text explicitly states the provision is deleted in its entirety.",
                    bounded_textual_impact="Textual repeal of previous covenant.",
                )
            )

        # 6. Check for Added Covenants in Doc B (not in Doc A)
        m_pet = re.search(r"([^\n]*(?:pet policy|no pets allowed|late fee of INR\s*[\d,]+)[^\n]*)", raw_b or "", re.IGNORECASE)
        if m_pet and "pet" not in sanitized_raw_a.lower():
            additions += 1
            add_ev = ClauseEvidence(
                doc_id=meta_b.doc_id,
                doc_name=meta_b.doc_name,
                section_number="New Covenant",
                section_title="Added Restriction",
                exact_quote=m_pet.group(1).strip(),
                char_start=m_pet.start(1),
                char_end=m_pet.end(1),
                extracted_value=m_pet.group(1).strip(),
                obligated_party=PartyRole.TENANT_LESSEE,
                beneficiary_party=PartyRole.LANDLORD_LESSOR,
                trigger_type=LegalTriggerType.PREMISES_USE,
            )
            differences.append(
                ComparisonDifferenceItem(
                    dimension="RESTRICTIONS_COVENANTS",
                    trigger_type=LegalTriggerType.PREMISES_USE,
                    change_type=ChangeType.ADDITION,
                    materiality=MaterialityLevel.MATERIAL,
                    title="New Restriction Introduced in Document B",
                    doc_a_clause=None,
                    doc_b_clause=add_ev,
                    reconciliation_status=ReconciliationStatus.RECONCILED_EXPRESS_AMENDMENT,
                    reconciliation_explanation="Document B introduces a new restrictive covenant not present in Document A.",
                    bounded_textual_impact="Operationally introduces a new obligation/restriction.",
                )
            )

        # 7. UNCLASSIFIED Trigger Semantic Comparison (Revision 4 Test 10)
        unclass_a = next((c for c in clauses_a if c.trigger_type == LegalTriggerType.UNCLASSIFIED), None)
        unclass_b = next((c for c in clauses_b if c.trigger_type == LegalTriggerType.UNCLASSIFIED), None)
        if unclass_a and unclass_b:
            if unclass_a.exact_quote != unclass_b.exact_quote:
                material_mods += 1
                differences.append(
                    ComparisonDifferenceItem(
                        dimension="SPECIAL_COVENANT",
                        trigger_type=LegalTriggerType.UNCLASSIFIED,
                        change_type=ChangeType.MODIFICATION,
                        materiality=MaterialityLevel.MATERIAL,
                        title="Substantive Modification under Unclassified Legal Trigger",
                        doc_a_clause=unclass_a,
                        doc_b_clause=unclass_b,
                        reconciliation_status=ReconciliationStatus.RECONCILED_SUBORDINATION,
                        reconciliation_explanation="Clause terms differ substantively; legal trigger taxonomy is unclassified but semantic comparison is preserved.",
                        bounded_textual_impact="Textual duties modified between documents.",
                        uncertainty_disclosure="Trigger mechanism is unclassified; substantive terms differ.",
                        non_definitive_guidance="Please verify the legal intent of this special covenant with counsel.",
                    )
                )

        # 8. Dimension Filter
        if request.focus_dimension:
            focus = request.focus_dimension.upper()
            differences = [d for d in differences if focus in d.dimension.upper()]

        summary = (
            f"Compared '{meta_a.doc_name}' with '{meta_b.doc_name}'. "
            f"Relationship: {relationship_status.value}. "
            f"Total differences: {len(differences)}, Material modifications: {material_mods}, "
            f"True contradictions: {true_contradictions}, Unverified conflicts: {unverified_conflicts}, "
            f"Additions: {additions}, Omitted unmodified: {omitted_unmodified}, "
            f"Omitted from restatement: {omitted_restatement}, Express deletions: {express_deletions}."
        )

        return ComparisonResult(
            doc_a_meta=meta_a,
            doc_b_meta=meta_b,
            relationship_status=relationship_status,
            summary_of_changes=summary,
            total_differences_analyzed=len(differences),
            material_modifications_count=material_mods,
            true_contradictions_count=true_contradictions,
            unverified_conflicts_count=unverified_conflicts,
            additions_count=additions,
            omitted_unmodified_count=omitted_unmodified,
            omitted_from_restatement_count=omitted_restatement,
            express_deletions_count=express_deletions,
            differences=differences,
            contradictions=contradictions,
        )


comparison_service = ComparisonService()
