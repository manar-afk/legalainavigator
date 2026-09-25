'use client';

import React from 'react';
import {
  MissingInfoReport,
  EvidenceSufficiencyLevel,
  EvidentiaryState
} from '@/lib/types';
import {
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  GitBranch,
  ShieldAlert,
  Search,
  FileCheck2,
  FileQuestion,
  Split,
  ChevronRight
} from 'lucide-react';

interface MissingInfoPanelProps {
  report?: MissingInfoReport;
}

export default function MissingInfoPanel({ report }: MissingInfoPanelProps) {
  if (!report) {
    return null;
  }

  const getSufficiencyBadge = (level: EvidenceSufficiencyLevel) => {
    switch (level) {
      case 'sufficient':
        return {
          bg: 'bg-emerald-50 border-emerald-300 text-emerald-800',
          icon: <CheckCircle2 className="w-4 h-4 text-emerald-600" />,
          label: 'Sufficient Evidence'
        };
      case 'partially_sufficient':
        return {
          bg: 'bg-amber-50 border-amber-300 text-amber-800',
          icon: <HelpCircle className="w-4 h-4 text-amber-600" />,
          label: 'Partially Sufficient (Non-blocking gaps)'
        };
      case 'insufficient':
        return {
          bg: 'bg-rose-50 border-rose-300 text-rose-800',
          icon: <AlertCircle className="w-4 h-4 text-rose-600" />,
          label: 'Insufficient Evidence (Blocking gaps unstated)'
        };
      case 'indeterminate':
        return {
          bg: 'bg-purple-50 border-purple-300 text-purple-800',
          icon: <ShieldAlert className="w-4 h-4 text-purple-600" />,
          label: 'Indeterminate (Contradiction on blocking predicate)'
        };
      default:
        return {
          bg: 'bg-slate-50 border-slate-300 text-slate-700',
          icon: <HelpCircle className="w-4 h-4 text-slate-500" />,
          label: 'Unknown Sufficiency'
        };
    }
  };

  const getEvidentiaryStateBadge = (state: EvidentiaryState) => {
    switch (state) {
      case 'contract_silence':
        return {
          bg: 'bg-slate-100 text-slate-800 border-slate-300',
          label: 'Contract Silence (Topic unaddressed in contract)'
        };
      case 'missing_factual_evidence':
        return {
          bg: 'bg-orange-50 text-orange-800 border-orange-300',
          label: 'Missing Factual Evidence (Clause present, facts unstated)'
        };
      case 'ambiguous_evidence':
        return {
          bg: 'bg-purple-50 text-purple-800 border-purple-300',
          label: 'Ambiguous Evidence (Conflicting assertions or provisions)'
        };
      case 'evidence_established':
        return {
          bg: 'bg-teal-50 text-teal-800 border-teal-300',
          label: 'Evidence Established'
        };
      default:
        return {
          bg: 'bg-slate-100 text-slate-700 border-slate-300',
          label: state
        };
    }
  };

  const suff = getSufficiencyBadge(report.sufficiency_level);
  const evid = getEvidentiaryStateBadge(report.evidentiary_state);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-5 text-xs text-slate-700">
      {/* Header with Title and Sufficiency Badge */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <FileQuestion className="w-5 h-5 text-indigo-600" />
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Missing Information & Prerequisite Analysis
            </h3>
            <p className="text-[11px] text-slate-500">
              Pre-reasoning gatekeeper evaluating required evidence, blocking gates, and conditional pathways
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className={`px-2.5 py-1 rounded-full border text-xs font-semibold flex items-center gap-1.5 ${suff.bg}`}>
            {suff.icon}
            <span>{suff.label}</span>
          </div>

          <div className={`px-2.5 py-1 rounded-full border text-[11px] font-medium ${evid.bg}`}>
            <span>{evid.label}</span>
          </div>
        </div>
      </div>

      {/* Heuristic & Applicability Status Summary */}
      <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-slate-800">
            {report.heuristic_name || 'Prerequisite Detection Heuristic'}
          </span>
          <span className="text-[11px] text-slate-500 font-mono">
            {report.heuristic_status === 'framework_not_required'
              ? 'Framework: Not Required (Direct Lookup)'
              : 'Framework: Prerequisite Heuristic Applied'}
          </span>
        </div>
        <p className="text-slate-600 leading-relaxed">
          {report.overall_gap_summary}
        </p>

        <div className="pt-1 flex items-center gap-2 text-[11px]">
          <span className="font-semibold text-slate-700">Contractual Applicability Determined:</span>
          {report.is_applicability_determined ? (
            <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Yes (Unique Pathway Verified)
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold flex items-center gap-1">
              <Split className="w-3 h-3" /> No (Conditional on Missing Facts)
            </span>
          )}
        </div>
      </div>

      {/* Predicates Breakdown */}
      {((report.missing_predicates && report.missing_predicates.length > 0) ||
        (report.ambiguous_predicates && report.ambiguous_predicates.length > 0) ||
        (report.established_predicates && report.established_predicates.length > 0)) && (
        <div className="space-y-2.5">
          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <Search className="w-3.5 h-3.5 text-indigo-600" />
            Prerequisite Factual & Contractual Predicates
          </h4>

          <div className="space-y-2">
            {/* Missing Predicates */}
            {report.missing_predicates && report.missing_predicates.map((p) => (
              <div
                key={p.predicate_id}
                className="p-3 rounded-lg border border-amber-200 bg-amber-50/50 space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">{p.label}</span>
                    <span className="bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded text-[10px] font-mono">
                      {p.category}
                    </span>
                    {p.is_blocking ? (
                      <span className="bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded text-[10px] font-bold">
                        Blocking Gate
                      </span>
                    ) : (
                      <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px]">
                        Non-Blocking
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] font-semibold text-amber-700 uppercase bg-amber-100 px-2 py-0.5 rounded">
                    Status: Missing
                  </span>
                </div>

                <p className="text-slate-700 font-medium italic text-[11px]">
                  &quot;{p.semantic_unstated_phrasing || p.description}&quot;
                </p>

                <div className="text-[11px] text-slate-600">
                  <span className="font-semibold text-slate-700">Why it matters: </span>
                  {p.why_it_matters}
                </div>

                {p.suggested_investigation && (
                  <div className="text-[11px] text-indigo-700 flex items-center gap-1">
                    <ChevronRight className="w-3 h-3 text-indigo-500" />
                    <span className="font-medium">Investigation: </span>
                    {p.suggested_investigation}
                  </div>
                )}
              </div>
            ))}

            {/* Ambiguous Predicates */}
            {report.ambiguous_predicates && report.ambiguous_predicates.map((p) => (
              <div
                key={p.predicate_id}
                className="p-3 rounded-lg border border-purple-200 bg-purple-50/50 space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">{p.label}</span>
                    <span className="bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded text-[10px] font-mono">
                      {p.category}
                    </span>
                    {p.is_blocking && (
                      <span className="bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded text-[10px] font-bold">
                        Blocking Predicate
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] font-semibold text-purple-700 uppercase bg-purple-100 px-2 py-0.5 rounded">
                    Status: Ambiguous / Contradictory
                  </span>
                </div>

                <p className="text-slate-700 font-medium text-[11px]">
                  {p.description || p.semantic_unstated_phrasing}
                </p>
                <div className="text-[11px] text-slate-600">
                  <span className="font-semibold text-slate-700">Why it matters: </span>
                  {p.why_it_matters}
                </div>
              </div>
            ))}

            {/* Established Predicates */}
            {report.established_predicates && report.established_predicates.map((p) => (
              <div
                key={p.predicate_id}
                className="p-2.5 rounded-lg border border-slate-200 bg-slate-50 space-y-1"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="font-semibold text-slate-900">{p.label}</span>
                    <span className="bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded text-[10px] font-mono">
                      {p.category}
                    </span>
                  </div>
                  <span className="text-[10px] font-semibold text-emerald-700 uppercase bg-emerald-100 px-2 py-0.5 rounded">
                    Status: Established
                  </span>
                </div>

                {p.provenance && (
                  <div className="text-[10px] text-slate-500 flex items-center gap-1.5 pt-0.5 font-mono">
                    <span className="text-indigo-600 font-semibold">{p.provenance.source_ref}</span>
                    {p.provenance.extracted_value && (
                      <span className="bg-slate-200 px-1 rounded text-slate-800">
                        {p.provenance.extracted_value}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Conditional Applicability Pathways */}
      {report.conditional_pathways && report.conditional_pathways.length > 0 && (
        <div className="space-y-2.5 pt-1 border-t border-slate-100">
          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <GitBranch className="w-3.5 h-3.5 text-indigo-600" />
            Conditional Applicability Pathways ({report.conditional_pathways.length})
          </h4>
          <p className="text-[11px] text-slate-500">
            Objective contractual pathways depending on unstated or pending factual conditions (No outcome prediction)
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {report.conditional_pathways.map((pw, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100/70 transition space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 text-xs">{pw.pathway_name}</span>
                  <span className="bg-indigo-100 text-indigo-800 font-mono text-[10px] px-2 py-0.5 rounded font-semibold">
                    {pw.applicable_provision}
                  </span>
                </div>

                <div className="text-[11px] text-slate-700">
                  <span className="font-semibold text-slate-900">Condition: </span>
                  {pw.factual_condition}
                </div>

                <div className="text-[11px] text-slate-600">
                  <span className="font-semibold text-slate-900">Contract Stipulation: </span>
                  {pw.contractual_stipulation}
                </div>

                {pw.evidence_required_to_confirm && pw.evidence_required_to_confirm.length > 0 && (
                  <div className="pt-1 text-[10px] text-slate-500 space-y-0.5">
                    <span className="font-semibold text-slate-700">Evidence Required to Confirm:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-600">
                      {pw.evidence_required_to_confirm.map((ev, eIdx) => (
                        <li key={eIdx}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contradictions Alert if any */}
      {report.contradictions && report.contradictions.length > 0 && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 space-y-1">
          <div className="flex items-center gap-1.5 text-rose-800 font-bold text-xs">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <span>Unresolved Contradictions Detected</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[11px] text-rose-700">
            {report.contradictions.map((c, cIdx) => (
              <li key={cIdx}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Bounded Investigative Recommendations */}
      {report.investigative_recommendations && report.investigative_recommendations.length > 0 && (
        <div className="space-y-1.5 pt-1 border-t border-slate-100">
          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <FileCheck2 className="w-3.5 h-3.5 text-indigo-600" />
            Bounded Investigation Guidance
          </h4>
          <ul className="space-y-1 text-[11px] text-slate-600">
            {report.investigative_recommendations.map((rec, rIdx) => (
              <li key={rIdx} className="flex items-start gap-1.5">
                <ChevronRight className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0 mt-0.5" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
