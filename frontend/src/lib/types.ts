export type OperationalMode =
  | 'mode_1_doc_only'
  | 'mode_2_doc_external'
  | 'mode_3_general_no_doc';

export type QueryCategory =
  | 'document_factual'
  | 'document_interpretation'
  | 'document_comparison'
  | 'situation_specific'
  | 'external_legal_info'
  | 'insufficient_info'
  | 'professional_judgment';

export type UserRole =
  | 'tenant'
  | 'landlord'
  | 'employee'
  | 'employer'
  | 'customer'
  | 'service_provider'
  | 'borrower'
  | 'lender'
  | 'buyer'
  | 'seller'
  | 'general';

export type RoleResolutionStatus =
  | 'declared_by_user'
  | 'inferred_high_confidence'
  | 'inferred_low_confidence'
  | 'role_neutral'
  | 'unresolved_conflict';

export type FactStatus =
  | 'user_asserted'
  | 'not_stated'
  | 'document_supported'
  | 'document_contradicted'
  | 'unresolved';

export type DiscrepancyType =
  | 'potential_conflict'
  | 'direct_contradiction'
  | 'scope_difference'
  | 'condition_precedent_unmet';

export interface TimelineAnchor {
  raw_value: string;
  normalized_value: string;
  event_type: string;
  source: string;
  confidence: number;
}

export interface FinancialEntity {
  raw_value: string;
  numeric_amount?: number;
  currency: string;
  item_type: string;
  source: string;
  confidence: number;
}

export interface SituationFactItem {
  fact_id: string;
  assertion_text: string;
  fact_status: FactStatus;
  turn_index: number;
  is_superseded: boolean;
  superseded_by?: string;
  superseded_reason?: string;
}

export interface SituationAnalysis {
  declared_role?: UserRole;
  inferred_role: UserRole;
  role_confidence: number;
  role_evidence?: string;
  role_resolution_status: RoleResolutionStatus;
  counterparty_role?: UserRole;
  stated_facts: SituationFactItem[];
  timeline_anchors: TimelineAnchor[];
  financial_elements: FinancialEntity[];
  core_legal_topic: string;
  discrepancy_signals: Array<{
    type: string;
    user_assertion: string;
    document_clause_ref: string;
    contract_stipulation: string;
    neutral_explanation: string;
  }>;
}

export interface UserSituation {
  raw_description: string;
  declared_role?: UserRole;
  jurisdiction?: string;
  turn_index?: number;
  previous_assertions?: string[];
}

export interface DocumentMeta {
  doc_id: string;
  filename: string;
  file_type: string;
  total_pages: number;
  total_characters: number;
  total_chunks: number;
  uploaded_at?: string;
}

export interface EvidenceSnippet {
  snippet_id: string;
  doc_id?: string;
  filename?: string;
  section_number?: string;
  section_title?: string;
  page_number?: number;
  paragraph_index?: number;
  quote: string;
  start_char?: number;
  end_char?: number;
  source_type: string;
  effective_date?: string;
}

export interface MissingInfoItem {
  field_name: string;
  description: string;
  why_it_matters: string;
  framework_context?: string;
}

export interface InconsistencyItem {
  topic: string;
  description: string;
  clause_a_ref: string;
  clause_a_text: string;
  clause_b_ref: string;
  clause_b_text: string;
  neutral_advisory: string;
}

export interface AuthoritativeLegalSource {
  source_id: string;
  jurisdiction: string;
  source_type: string;
  title: string;
  issuing_authority: string;
  section_provision: string;
  provision_title?: string;
  official_url: string;
  retrieval_date: string;
  enactment_date?: string;
  effective_date?: string;
  last_amendment_date?: string;
  currentness_status: string;
  verification_status: string;
  exact_retrieved_text: string;
  source_locator_version_info: string;
  provenance_notes: string;
  is_authoritative: boolean;
}

export interface JudicialPrecedentSource {
  precedent_id: string;
  case_name: string;
  court: string;
  court_level: string;
  decision_date: string;
  citation: string;
  bench_strength?: string;
  binding_status: string;
  precedential_scope: string;
  status_verification: string;
  relevant_provision: string;
  relevant_paragraph_section: string;
  verbatim_excerpt: string;
  discussion_summary: string;
  official_registry_url?: string;
  provenance_notes: string;
}

export interface JurisdictionSignal {
  signal_source: string;
  jurisdiction_value: string;
  evidence_text?: string;
  confidence: number;
}

export interface DocumentLawRelationship {
  document_clause_ref: string;
  document_clause_text: string;
  statutory_provision_ref: string;
  statutory_provision_text: string;
  judicial_discussion?: string;
  factors_and_uncertainties: string[];
  relationship_explanation: string;
}

export interface GroundedAnswer {
  document_facts: string[];
  user_provided_facts: string[];
  external_law: AuthoritativeLegalSource[];
  judicial_precedents?: JudicialPrecedentSource[];
  failure_uncertainty_state?: string;
  jurisdiction_signal?: JurisdictionSignal;
  document_law_relationships?: DocumentLawRelationship[];
  plain_language_interpretation: string;
  uncertainty_and_gaps: string[];

  answer: string;
  what_the_document_says?: string;
  what_this_means_in_plain_language: string;
  why_it_matters_to_your_situation?: string;
  what_is_unclear_or_missing?: string;
  what_to_check_next: string[];

  sources: EvidenceSnippet[];
  missing_info_details: MissingInfoItem[];
  inconsistencies: InconsistencyItem[];
  neutral_labels: string[];
  operational_mode: OperationalMode;
  query_category: QueryCategory;
  evidence_sufficiency_passed: boolean;
  professional_review_recommended: boolean;
  situation_analysis?: SituationAnalysis;
  missing_info_report?: MissingInfoReport;
}

export type EvidenceSufficiencyLevel =
  | 'sufficient'
  | 'partially_sufficient'
  | 'insufficient'
  | 'indeterminate';

export type EvidentiaryState =
  | 'contract_silence'
  | 'missing_factual_evidence'
  | 'ambiguous_evidence'
  | 'evidence_established';

export type HeuristicStatus =
  | 'applied'
  | 'framework_not_required';

export type PredicateCategory =
  | 'document_date'
  | 'factual_event'
  | 'notice_receipt'
  | 'contractual_provision'
  | 'party_consent'
  | 'external_statute';

export type PredicateStatus =
  | 'established'
  | 'missing'
  | 'ambiguous'
  | 'not_applicable';

export type PredicateSourceStatus =
  | 'document_proven'
  | 'user_asserted'
  | 'unstated'
  | 'contradictory_signals';

export interface PredicateProvenance {
  source_type: string;
  source_ref?: string;
  exact_quote?: string;
  start_char?: number;
  end_char?: number;
  extracted_value?: string;
  source_description?: string;
}

export interface MissingPredicateItem {
  predicate_id: string;
  label: string;
  category: PredicateCategory;
  is_blocking: boolean;
  status: PredicateStatus;
  source_status: PredicateSourceStatus;
  mode_applicability: OperationalMode[];
  why_it_matters: string;
  impact_on_pathway?: Record<string, string>;
  suggested_investigation: string;
  provenance?: PredicateProvenance;
  semantic_unstated_phrasing?: string;
  description?: string;
  predicate_name?: string;
}

export interface ConditionalApplicabilityPathway {
  pathway_name: string;
  factual_condition: string;
  applicable_provision: string;
  contractual_stipulation: string;
  evidence_required_to_confirm: string[];
}

export interface MissingInfoReport {
  heuristic_status: HeuristicStatus;
  heuristic_name?: string;
  evidentiary_state: EvidentiaryState;
  sufficiency_level: EvidenceSufficiencyLevel;
  established_predicates: MissingPredicateItem[];
  missing_predicates: MissingPredicateItem[];
  ambiguous_predicates: MissingPredicateItem[];
  conditional_pathways: ConditionalApplicabilityPathway[];
  overall_gap_summary: string;
  is_applicability_determined: boolean;
  contradictions?: string[];
  investigative_recommendations?: string[];
  query_text?: string;
}

export interface IntentClassification {
  category: QueryCategory;
  effective_mode: OperationalMode;
  is_reclassified: boolean;
  reclassification_reason?: string;
  requires_external_law: boolean;
  is_conceptual_only: boolean;
  is_jurisdiction_missing: boolean;
  target_jurisdiction?: string;
  retrieval_prepared: boolean;
  retrieval_target_query?: string;
  confidence: number;
  explanation?: string;
}

export interface LawyerPrepBrief {
  client_situation: string;
  stated_user_facts: string[];
  relevant_documents: string[];
  relevant_clauses_extracted: string[];
  potential_inconsistencies: string[];
  missing_facts_to_investigate: string[];
  recommended_questions_for_lawyer: string[];
  disclaimer: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  live_gemini_active: boolean;
  configured_fast_model: string;
  configured_reasoning_model: string;
  configured_embedding_model: string;
  total_documents_loaded: number;
}

// === Phase 8: Comparison & Contradiction Types ===

export type DocumentRelationshipStatus =
  | 'express_amendment_referenced'
  | 'full_restatement_replacement'
  | 'confirmed_co_applicable'
  | 'unverified_relationship'
  | 'intra_document_covenants'
  | 'confirmed_standalone';

export type DocumentRole =
  | 'base_agreement'
  | 'amendment_addendum'
  | 'restatement'
  | 'side_letter'
  | 'co_applicable_agreement'
  | 'unlinked_document'
  | 'single_document';

export type ExecutionStatus =
  | 'verified_signed'
  | 'blank_or_unsigned'
  | 'dated_unverified_signature'
  | 'undated';

export type PartyRole =
  | 'tenant_lessee'
  | 'landlord_lessor'
  | 'employee'
  | 'employer'
  | 'mutual_both'
  | 'unspecified';

export type LegalTriggerType =
  | 'unclassified'
  | 'convenience_no_fault'
  | 'default_material_breach'
  | 'expiration_term'
  | 'lock_in_compliance'
  | 'financial_payment'
  | 'premises_use'
  | 'repair_maintenance'
  | 'dispute_forum';

export type ChangeType =
  | 'modification'
  | 'addition'
  | 'omitted_unmodified'
  | 'omitted_from_restatement'
  | 'express_deletion'
  | 'rephrasing'
  | 'potential_conflict_unverified'
  | 'internal_inconsistency';

export type MaterialityLevel =
  | 'material'
  | 'non_material'
  | 'indeterminate';

export type ReconciliationStatus =
  | 'reconciled_temporal'
  | 'reconciled_subordination'
  | 'reconciled_actor_asymmetry'
  | 'reconciled_express_amendment'
  | 'conflicting_unverified_relationship'
  | 'irreconcilable_contradiction';

export interface MetadataProvenance {
  field_name: string;
  extracted_value: string;
  exact_quote: string;
  char_start: number;
  char_end: number;
  doc_id: string;
}

export interface DocumentVersionMeta {
  doc_id: string;
  doc_name: string;
  document_title: string;
  document_role: DocumentRole;
  title_provenance?: MetadataProvenance;
  execution_date?: string;
  execution_date_provenance?: MetadataProvenance;
  effective_date?: string;
  effective_date_provenance?: MetadataProvenance;
  parties_named: string[];
  parties_provenance: MetadataProvenance[];
  execution_status: ExecutionStatus;
  signature_provenance?: MetadataProvenance;
  referenced_agreements: Array<Record<string, string>>;
  referenced_agreements_provenance: MetadataProvenance[];
  has_integration_clause: boolean;
  integration_clause_text?: string;
  integration_clause_provenance?: MetadataProvenance;
}

export interface ClauseEvidence {
  doc_id: string;
  doc_name: string;
  section_number?: string;
  section_title?: string;
  exact_quote: string;
  char_start: number;
  char_end: number;
  extracted_value?: string;
  obligated_party: PartyRole;
  beneficiary_party: PartyRole;
  trigger_type: LegalTriggerType;
  trigger_uncertainty_note?: string;
}

export interface ComparisonDifferenceItem {
  difference_id: string;
  dimension: string;
  trigger_type: LegalTriggerType;
  change_type: ChangeType;
  materiality: MaterialityLevel;
  title: string;
  doc_a_clause?: ClauseEvidence;
  doc_b_clause?: ClauseEvidence;
  reconciliation_status: ReconciliationStatus;
  reconciliation_explanation: string;
  bounded_textual_impact: string;
  uncertainty_disclosure?: string;
  non_definitive_guidance: string;
}

export interface ContradictionDiagnosticItem {
  contradiction_id: string;
  title: string;
  trigger_type: LegalTriggerType;
  actor_role: PartyRole;
  provision_a: ClauseEvidence;
  provision_b: ClauseEvidence;
  conflict_analysis: string;
  why_unreconciled: string;
  co_applicability_context?: string;
  non_definitive_guidance: string;
}

export interface ComparisonRequest {
  doc_id_a: string;
  doc_id_b?: string;
  focus_dimension?: string;
  user_situation?: string;
  operational_mode?: string;
  co_applicable_override?: boolean;
}

export interface ComparisonResult {
  comparison_id: string;
  doc_a_meta: DocumentVersionMeta;
  doc_b_meta?: DocumentVersionMeta;
  relationship_status: DocumentRelationshipStatus;
  summary_of_changes: string;
  total_differences_analyzed: number;
  material_modifications_count: number;
  true_contradictions_count: number;
  unverified_conflicts_count: number;
  additions_count: number;
  omitted_unmodified_count: number;
  omitted_from_restatement_count: number;
  express_deletions_count: number;
  differences: ComparisonDifferenceItem[];
  contradictions: ContradictionDiagnosticItem[];
  non_definitive_advisory: string;
}

// ============================================================================
// PHASE 9: ACTIONABLE OUTPUTS & PROFESSIONAL BRIEF MODELS
// ============================================================================

export type ActionableSourceType =
  | 'document_provision'
  | 'user_assertion'
  | 'external_law'
  | 'gatekeeper_derived'
  | 'comparison_derived'
  | 'synthesized_preparation';

export interface ActionableItemProvenance {
  source_type: ActionableSourceType;
  source_ref: string;
  document_id?: string;
  document_name?: string;
  exact_quote?: string;
  char_start?: number;
  char_end?: number;
}

export type ActionableLabel =
  | 'important'
  | 'review'
  | 'potential_inconsistency'
  | 'unclear'
  | 'missing_information'
  | 'requires_professional_review';

export type CovenantClassification =
  | 'financial_payment'
  | 'notice_timeline'
  | 'mandatory_compliance'
  | 'use_restriction'
  | 'maintenance_repair'
  | 'dispute_resolution'
  | 'general_obligation';

export interface DocumentDescribedCovenantItem {
  covenant_id: string;
  title: string;
  obligated_party: PartyRole;
  beneficiary_party: PartyRole;
  covenant_type: CovenantClassification;
  trigger_type: LegalTriggerType;
  associated_deadline?: string;
  clause_evidence: ClauseEvidence;
  provenance: ActionableItemProvenance;
  origin_reference_id: string;
  governing_status_note: string;
}

export type ChecklistCategory =
  | 'document_gathering'
  | 'factual_verification'
  | 'questions_to_clarify'
  | 'immediate_procedural_step';

export type ChecklistPriority =
  | 'blocking'
  | 'standard';

export interface ActionableChecklistItem {
  item_id: string;
  category: ChecklistCategory;
  task_description: string;
  rationale: string;
  priority: ChecklistPriority;
  provenance: ActionableItemProvenance;
  origin_reference_id: string;
}

export interface LawyerQuestionItem {
  question_id: string;
  question_text: string;
  context_rationale: string;
  origin_phase: string;
  origin_reference_id: string;
  supporting_evidence_refs: ActionableItemProvenance[];
  neutral_label: ActionableLabel;
}

export interface ReviewFlagItem {
  flag_id: string;
  label: ActionableLabel;
  title: string;
  neutral_explanation: string;
  origin_reference_id: string;
  supporting_evidence: ActionableItemProvenance;
}

export interface RoleResolutionProfile {
  declared_role?: UserRole;
  inferred_role?: UserRole;
  role_confidence: number;
  role_evidence: string[];
  role_resolution_status: RoleResolutionStatus;
  role_uncertainty_note?: string;
}

export interface ProfessionalConsultationBrief {
  brief_id: string;
  generated_at: string;
  client_situation_summary: string;
  role_profile: RoleResolutionProfile;
  governing_documents: DocumentVersionMeta[];
  key_contractual_provisions: ClauseEvidence[];
  targeted_questions_for_counsel: LawyerQuestionItem[];
  missing_facts_to_clarify: string[];
  identified_inconsistencies_and_review_flags: ReviewFlagItem[];
  plain_language_overview: string;
  operational_mode: string;
  external_statutory_context?: AuthoritativeLegalSource[];
  disclaimer: string;
}

export interface ActionableOutputsContainer {
  consultation_brief: ProfessionalConsultationBrief;
  covenants_matrix: DocumentDescribedCovenantItem[];
  preparation_checklist: ActionableChecklistItem[];
  markdown_brief_text: string;
}

export interface ActionableGenerateRequest {
  doc_ids: string[];
  situation_description?: string;
  declared_role?: UserRole;
  comparison_doc_id?: string;
  query_text?: string;
  operational_mode?: string;
}

export interface NavigateRequest {
  query?: string;
  situation_description?: string;
  declared_role?: string;
  doc_ids?: string[];
  jurisdiction?: string;
  pasted_content?: string;
  requested_mode?: OperationalMode;
}

export interface UnifiedNavigationResponse {
  summary_and_perspective: string;
  answer: string;
  inferred_role?: string;
  what_the_document_says: string;
  what_this_means_in_plain_language: string;
  why_it_matters?: string;
  sources: EvidenceSnippet[];
  comparative_analysis?: ComparisonResult;
  governing_legal_framework?: Array<{
    statute: string;
    section: string;
    summary: string;
    applicability: string;
  }>;
  jurisdiction_note?: string;
  what_is_unclear_or_missing?: string;
  uncertainties: string[];
  actionable_checklist: string[];
  covenants_matrix?: DocumentDescribedCovenantItem[];
  consultation_brief_markdown?: string;
  diagnostics: {
    effective_mode: string;
    category: string;
    confidence?: number;
    evidence_sufficiency_passed?: boolean;
    latency_ms: number;
    doc_count: number;
    has_comparison: boolean;
    has_external_law: boolean;
  };
}


