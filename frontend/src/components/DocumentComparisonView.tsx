'use client';

import React from 'react';
import {
  GitCompare,
  AlertTriangle,
  FileText,
  CheckCircle,
  HelpCircle,
  Info,
  Calendar,
  Users,
  ShieldAlert,
  ArrowRight,
  Clock,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import {
  ComparisonResult,
  ComparisonDifferenceItem,
  ContradictionDiagnosticItem,
  DocumentRelationshipStatus,
  ChangeType,
  MaterialityLevel,
  ReconciliationStatus,
} from '@/lib/types';

interface DocumentComparisonViewProps {
  comparison: ComparisonResult;
}

export default function DocumentComparisonView({ comparison }: DocumentComparisonViewProps) {
  const getRelationshipBadge = (status: DocumentRelationshipStatus) => {
    switch (status) {
      case 'express_amendment_referenced':
        return {
          label: 'Express Amendment Referenced',
          bg: 'bg-emerald-100 text-emerald-800 border-emerald-300',
        };
      case 'full_restatement_replacement':
        return {
          label: 'Full Restatement Replacement',
          bg: 'bg-indigo-100 text-indigo-800 border-indigo-300',
        };
      case 'confirmed_co_applicable':
        return {
          label: 'Confirmed Co-Applicable Concurrent Agreements',
          bg: 'bg-amber-100 text-amber-800 border-amber-300',
        };
      case 'unverified_relationship':
        return {
          label: 'Unverified Document Relationship',
          bg: 'bg-rose-100 text-rose-800 border-rose-300',
        };
      case 'intra_document_covenants':
        return {
          label: 'Intra-Document Covenants Analysis',
          bg: 'bg-slate-100 text-slate-800 border-slate-300',
        };
      default:
        return {
          label: status,
          bg: 'bg-slate-100 text-slate-700 border-slate-200',
        };
    }
  };

  const getChangeTypeBadge = (ct: ChangeType) => {
    switch (ct) {
      case 'modification':
        return { label: 'Modification', bg: 'bg-amber-100 text-amber-800' };
      case 'addition':
        return { label: 'New Addition', bg: 'bg-blue-100 text-blue-800' };
      case 'omitted_unmodified':
        return { label: 'Unmodified Base Provision', bg: 'bg-slate-100 text-slate-700' };
      case 'omitted_from_restatement':
        return { label: 'Absent from Restatement', bg: 'bg-purple-100 text-purple-800' };
      case 'express_deletion':
        return { label: 'Express Deletion', bg: 'bg-rose-100 text-rose-800' };
      case 'potential_conflict_unverified':
        return { label: 'Unverified Conflict', bg: 'bg-orange-100 text-orange-800' };
      case 'internal_inconsistency':
        return { label: 'True Inconsistency', bg: 'bg-red-100 text-red-800 font-bold' };
      case 'rephrasing':
        return { label: 'Rephrasing / Clarification', bg: 'bg-gray-100 text-gray-700' };
      default:
        return { label: ct, bg: 'bg-gray-100 text-gray-700' };
    }
  };

  const getReconciliationBadge = (rec: ReconciliationStatus) => {
    switch (rec) {
      case 'reconciled_express_amendment':
        return { label: 'Reconciled: Express Amendment', color: 'text-emerald-700 bg-emerald-50' };
      case 'reconciled_temporal':
        return { label: 'Reconciled: Sequential Timeframe', color: 'text-blue-700 bg-blue-50' };
      case 'reconciled_subordination':
        return { label: 'Reconciled: Subordination Clause', color: 'text-indigo-700 bg-indigo-50' };
      case 'reconciled_actor_asymmetry':
        return { label: 'Reconciled: Asymmetric Party Rights', color: 'text-cyan-700 bg-cyan-50' };
      case 'conflicting_unverified_relationship':
        return { label: 'Unreconciled: Unverified Relationship', color: 'text-orange-700 bg-orange-50' };
      case 'irreconcilable_contradiction':
        return { label: 'Irreconcilable Contradiction', color: 'text-rose-700 bg-rose-50 font-bold' };
      default:
        return { label: rec, color: 'text-slate-700 bg-slate-50' };
    }
  };

  const relBadge = getRelationshipBadge(comparison.relationship_status);

  return (
    <div className="space-y-6">
      {/* Header Diagnostic Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
          <div className="flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-indigo-600" />
            <h3 className="font-bold text-slate-900 text-base">
              Semantic Document Comparison & Contradiction Engine
            </h3>
          </div>
          <span className={`text-xs px-3 py-1 rounded-full font-semibold border ${relBadge.bg}`}>
            {relBadge.label}
          </span>
        </div>

        {/* Document Version Metadata */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200 text-xs">
          <div>
            <div className="font-bold text-slate-800 flex items-center gap-1.5 mb-1">
              <FileText className="w-3.5 h-3.5 text-indigo-600" />
              Document A: {comparison.doc_a_meta.document_title}
            </div>
            <div className="text-slate-600 space-y-0.5">
              <div>Filename: <span className="font-mono">{comparison.doc_a_meta.doc_name}</span></div>
              {comparison.doc_a_meta.execution_date && (
                <div>Executed: <span className="font-medium text-slate-800">{comparison.doc_a_meta.execution_date}</span></div>
              )}
              {comparison.doc_a_meta.effective_date && (
                <div>Effective: <span className="font-medium text-slate-800">{comparison.doc_a_meta.effective_date}</span></div>
              )}
            </div>
          </div>

          {comparison.doc_b_meta && (
            <div>
              <div className="font-bold text-slate-800 flex items-center gap-1.5 mb-1">
                <FileText className="w-3.5 h-3.5 text-emerald-600" />
                Document B: {comparison.doc_b_meta.document_title}
              </div>
              <div className="text-slate-600 space-y-0.5">
                <div>Filename: <span className="font-mono">{comparison.doc_b_meta.doc_name}</span></div>
                {comparison.doc_b_meta.execution_date && (
                  <div>Executed: <span className="font-medium text-slate-800">{comparison.doc_b_meta.execution_date}</span></div>
                )}
                {comparison.doc_b_meta.effective_date && (
                  <div>Effective: <span className="font-medium text-slate-800">{comparison.doc_b_meta.effective_date}</span></div>
                )}
                {comparison.doc_b_meta.has_integration_clause && (
                  <div className="text-emerald-700 font-medium">Continuing Effect / Integration Clause Verified</div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Metric Counter Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 text-center text-xs">
          <div className="p-2 bg-slate-50 border border-slate-200 rounded-lg">
            <div className="text-slate-500 font-medium">Differences</div>
            <div className="text-base font-bold text-slate-900">{comparison.total_differences_analyzed}</div>
          </div>
          <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="text-amber-700 font-medium">Modifications</div>
            <div className="text-base font-bold text-amber-900">{comparison.material_modifications_count}</div>
          </div>
          <div className={`p-2 border rounded-lg ${
            comparison.true_contradictions_count > 0 ? 'bg-red-50 border-red-300' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className={`font-medium ${comparison.true_contradictions_count > 0 ? 'text-red-700 font-bold' : 'text-slate-500'}`}>
              True Contradictions
            </div>
            <div className={`text-base font-bold ${comparison.true_contradictions_count > 0 ? 'text-red-900' : 'text-slate-900'}`}>
              {comparison.true_contradictions_count}
            </div>
          </div>
          <div className={`p-2 border rounded-lg ${
            comparison.unverified_conflicts_count > 0 ? 'bg-orange-50 border-orange-300' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className={`font-medium ${comparison.unverified_conflicts_count > 0 ? 'text-orange-700' : 'text-slate-500'}`}>
              Unverified Conflicts
            </div>
            <div className={`text-base font-bold ${comparison.unverified_conflicts_count > 0 ? 'text-orange-900' : 'text-slate-900'}`}>
              {comparison.unverified_conflicts_count}
            </div>
          </div>
          <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="text-blue-700 font-medium">Additions</div>
            <div className="text-base font-bold text-blue-900">{comparison.additions_count}</div>
          </div>
          <div className="p-2 bg-slate-50 border border-slate-200 rounded-lg">
            <div className="text-slate-500 font-medium">Unmodified</div>
            <div className="text-base font-bold text-slate-800">{comparison.omitted_unmodified_count}</div>
          </div>
          <div className="p-2 bg-purple-50 border border-purple-200 rounded-lg">
            <div className="text-purple-700 font-medium">Absent Restated</div>
            <div className="text-base font-bold text-purple-900">{comparison.omitted_from_restatement_count}</div>
          </div>
        </div>

        {/* Non-Conclusory Guidance Banner */}
        <div className="bg-amber-50/70 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold">Non-Conclusory Advisory:</span>{' '}
            {comparison.non_definitive_advisory}
          </div>
        </div>
      </div>

      {/* True Contradictions Diagnostic Cards (if any) */}
      {comparison.contradictions && comparison.contradictions.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-bold text-red-900 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-red-600" />
            True Established Contradictions ({comparison.contradictions.length})
          </h4>
          <div className="space-y-3">
            {comparison.contradictions.map((contra, idx) => (
              <div key={idx} className="bg-red-50/80 border border-red-200 rounded-xl p-4 space-y-3 text-xs">
                <div className="flex justify-between items-start">
                  <div className="font-bold text-red-900 text-sm">{contra.title}</div>
                  <span className="bg-red-200 text-red-800 px-2 py-0.5 rounded text-[11px] font-semibold">
                    Irreconcilable Conflict
                  </span>
                </div>
                <p className="text-red-900 leading-relaxed">{contra.conflict_analysis}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-white p-3 rounded-lg border border-red-200">
                  <div>
                    <span className="font-semibold text-slate-700">Provision A ({contra.provision_a.doc_name}):</span>
                    <blockquote className="mt-1 italic text-slate-800 bg-slate-50 p-2 rounded border border-slate-200">
                      "{contra.provision_a.exact_quote}"
                    </blockquote>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-700">Provision B ({contra.provision_b.doc_name}):</span>
                    <blockquote className="mt-1 italic text-slate-800 bg-slate-50 p-2 rounded border border-slate-200">
                      "{contra.provision_b.exact_quote}"
                    </blockquote>
                  </div>
                </div>
                <div className="text-slate-700 bg-red-100/50 p-2.5 rounded border border-red-200">
                  <strong>Why Unreconciled:</strong> {contra.why_unreconciled}
                </div>
                <div className="text-slate-600 italic">
                  Guidance: {contra.non_definitive_guidance}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Material Differences & Reconciled Clauses */}
      <div className="space-y-3">
        <h4 className="text-sm font-bold text-slate-800 flex items-center gap-2">
          <GitCompare className="w-4 h-4 text-indigo-600" />
          Semantic Clause Comparisons & Reconciled Differences ({comparison.differences.length})
        </h4>

        <div className="space-y-4">
          {comparison.differences.map((diff, idx) => {
            const ctBadge = getChangeTypeBadge(diff.change_type);
            const recBadge = getReconciliationBadge(diff.reconciliation_status);

            return (
              <div
                key={diff.difference_id || idx}
                className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3 text-xs hover:border-slate-300 transition"
              >
                {/* Item Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded font-semibold text-[11px] ${ctBadge.bg}`}>
                      {ctBadge.label}
                    </span>
                    <span className="font-bold text-slate-900 text-sm">{diff.title}</span>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded font-medium text-[11px] border border-current ${recBadge.color}`}>
                    {recBadge.label}
                  </span>
                </div>

                {/* Side-by-side or dual provision view */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                  {diff.doc_a_clause ? (
                    <div>
                      <div className="font-semibold text-slate-700 flex items-center justify-between mb-1">
                        <span>{diff.doc_a_clause.doc_name} ({diff.doc_a_clause.section_number})</span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          chars {diff.doc_a_clause.char_start}–{diff.doc_a_clause.char_end}
                        </span>
                      </div>
                      <blockquote className="italic text-slate-800 bg-white p-2 rounded border border-slate-200">
                        "{diff.doc_a_clause.exact_quote}"
                      </blockquote>
                      {diff.doc_a_clause.extracted_value && (
                        <div className="mt-1 text-slate-600">
                          Extracted Value: <span className="font-semibold text-slate-800">{diff.doc_a_clause.extracted_value}</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-slate-400 italic flex items-center justify-center p-3">
                      Not present in Document A (New addition)
                    </div>
                  )}

                  {diff.doc_b_clause ? (
                    <div>
                      <div className="font-semibold text-slate-700 flex items-center justify-between mb-1">
                        <span>{diff.doc_b_clause.doc_name} ({diff.doc_b_clause.section_number})</span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          chars {diff.doc_b_clause.char_start}–{diff.doc_b_clause.char_end}
                        </span>
                      </div>
                      <blockquote className="italic text-slate-800 bg-white p-2 rounded border border-slate-200">
                        "{diff.doc_b_clause.exact_quote}"
                      </blockquote>
                      {diff.doc_b_clause.extracted_value && (
                        <div className="mt-1 text-slate-600">
                          Extracted Value: <span className="font-semibold text-slate-800">{diff.doc_b_clause.extracted_value}</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-slate-400 italic flex items-center justify-center p-3">
                      Unaddressed in Document B (Remains operative under base agreement)
                    </div>
                  )}
                </div>

                {/* Plain English Operational Impact */}
                <div className="bg-indigo-50/50 p-2.5 rounded-lg border border-indigo-100 text-slate-800 leading-relaxed">
                  <span className="font-semibold text-indigo-900">Textual & Operational Implication:</span>{' '}
                  {diff.bounded_textual_impact}
                </div>

                {/* Uncertainty Disclosure if Unclassified Trigger */}
                {diff.uncertainty_disclosure && (
                  <div className="bg-amber-50 p-2 rounded border border-amber-200 text-amber-900 italic">
                    Uncertainty Note: {diff.uncertainty_disclosure}
                  </div>
                )}

                {/* Non-conclusory guidance */}
                <div className="text-slate-500 italic text-[11px]">
                  Verification: {diff.non_definitive_guidance}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
