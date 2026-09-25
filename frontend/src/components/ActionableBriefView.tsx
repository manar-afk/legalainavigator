'use client';

import React, { useState } from 'react';
import {
  FileText,
  Copy,
  Download,
  Check,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  User,
  CheckCircle2,
  Calendar,
  Layers,
  Search,
  ClipboardList,
  AlertCircle,
  FileCheck,
} from 'lucide-react';
import {
  ActionableOutputsContainer,
  ActionableLabel,
  ChecklistPriority,
  ChecklistCategory,
  ActionableSourceType,
} from '@/lib/types';

interface ActionableBriefViewProps {
  data: ActionableOutputsContainer;
}

export default function ActionableBriefView({ data }: ActionableBriefViewProps) {
  const [copied, setCopied] = useState(false);
  const { consultation_brief, covenants_matrix, preparation_checklist, markdown_brief_text } = data;

  const handleCopyMarkdown = () => {
    navigator.clipboard.writeText(markdown_brief_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([markdown_brief_text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `consultation_brief_${consultation_brief.brief_id.slice(0, 8)}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const getLabelBadge = (label: ActionableLabel) => {
    switch (label) {
      case 'important':
        return 'bg-amber-100 text-amber-900 border-amber-300';
      case 'review':
        return 'bg-blue-100 text-blue-900 border-blue-300';
      case 'potential_inconsistency':
        return 'bg-rose-100 text-rose-900 border-rose-300';
      case 'unclear':
        return 'bg-purple-100 text-purple-900 border-purple-300';
      case 'missing_information':
        return 'bg-orange-100 text-orange-900 border-orange-300';
      case 'requires_professional_review':
        return 'bg-red-100 text-red-900 border-red-300';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-300';
    }
  };

  const getSourceTypeBadge = (sourceType: ActionableSourceType) => {
    switch (sourceType) {
      case 'document_provision':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'user_assertion':
        return 'bg-sky-50 text-sky-700 border-sky-200';
      case 'external_law':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'gatekeeper_derived':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'comparison_derived':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'synthesized_preparation':
        return 'bg-slate-100 text-slate-600 border-slate-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const getCategoryBadge = (cat: ChecklistCategory) => {
    switch (cat) {
      case 'document_gathering':
        return 'Document Gathering';
      case 'factual_verification':
        return 'Factual Verification';
      case 'questions_to_clarify':
        return 'Question for Counsel';
      case 'immediate_procedural_step':
        return 'Procedural Step';
      default:
        return cat;
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* 1. Header & Actions */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-blue-50 text-blue-700 rounded-lg">
              <FileCheck className="w-6 h-6" />
            </span>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Professional Legal Consultation Brief</h2>
              <p className="text-xs text-slate-500">
                Generated: {new Date(consultation_brief.generated_at).toLocaleString()} • Operational Mode: <code className="bg-slate-100 px-1 py-0.5 rounded text-xs">{consultation_brief.operational_mode}</code>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <button
            onClick={handleCopyMarkdown}
            className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition"
            title="Copy brief as formatted Markdown"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
            {copied ? 'Copied Markdown' : 'Copy Brief'}
          </button>
          <button
            onClick={handleDownloadMarkdown}
            className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm transition"
            title="Download .md file"
          >
            <Download className="w-4 h-4" />
            Download .md
          </button>
        </div>
      </div>

      {/* 2. Supervisory Notice Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-3 text-amber-900">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed">
          <span className="font-semibold block mb-0.5">Informational Supervisory Notice</span>
          {consultation_brief.disclaimer}
        </div>
      </div>

      {/* 3. Client Situation & Role Profile */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800 font-semibold">
            <User className="w-4 h-4 text-slate-500" />
            <h3>1. Client Situation & Role Context</h3>
          </div>
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium border ${
            consultation_brief.role_profile.role_resolution_status === 'unresolved_conflict'
              ? 'bg-rose-100 text-rose-800 border-rose-300'
              : 'bg-slate-100 text-slate-700 border-slate-300'
          }`}>
            Status: {consultation_brief.role_profile.role_resolution_status}
          </span>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-1">
              Client Situation Summary
            </span>
            <p className="text-sm text-slate-800 bg-slate-50 border border-slate-200 rounded-lg p-3 italic">
              &ldquo;{consultation_brief.client_situation_summary}&rdquo;
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block">Declared Role</span>
              <span className="font-semibold text-sm text-slate-800">
                {consultation_brief.role_profile.declared_role || 'Unspecified'}
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block">Inferred Role</span>
              <span className="font-semibold text-sm text-slate-800">
                {consultation_brief.role_profile.inferred_role || 'Unresolved / Role-Neutral'}
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block">Inference Confidence</span>
              <span className="font-semibold text-sm text-slate-800">
                {(consultation_brief.role_profile.role_confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {consultation_brief.role_profile.role_uncertainty_note && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <span>{consultation_brief.role_profile.role_uncertainty_note}</span>
            </div>
          )}
        </div>
      </div>

      {/* 4. Governing Documents */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2 text-slate-800 font-semibold">
          <FileText className="w-4 h-4 text-slate-500" />
          <h3>2. Governing Documents & Execution Metadata</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/50 text-xs font-semibold text-slate-500 border-b border-slate-200">
              <tr>
                <th className="py-3 px-6">Document Name</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Execution Status</th>
                <th className="py-3 px-4">Execution Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {consultation_brief.governing_documents.map((doc, idx) => (
                <tr key={idx} className="hover:bg-slate-50/50 transition">
                  <td className="py-3 px-6 font-medium text-slate-900">
                    {doc.doc_name}
                    <span className="block text-xs text-slate-400 font-mono">{doc.doc_id.slice(0, 12)}...</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-xs px-2.5 py-1 rounded bg-slate-100 text-slate-700 font-mono">
                      {doc.document_role}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`text-xs px-2.5 py-1 rounded font-medium ${
                      doc.execution_status === 'verified_signed'
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-amber-50 text-amber-700'
                    }`}>
                      {doc.execution_status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600 text-xs">
                    {doc.execution_date || 'Undated'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Document-Described Covenants Matrix */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800 font-semibold">
            <Layers className="w-4 h-4 text-slate-500" />
            <h3>3. Document-Described Covenants Matrix</h3>
          </div>
          <span className="text-xs text-slate-500">
            {covenants_matrix.length} bilateral covenant(s) mapped
          </span>
        </div>
        <div className="p-4 bg-slate-50/70 border-b border-slate-200 text-xs text-slate-600 italic">
          *Note: The following entries describe what the uploaded contract textually states. They do not constitute an independent legal determination of enforceability.*
        </div>
        <div className="divide-y divide-slate-100">
          {covenants_matrix.map((cov) => (
            <div key={cov.covenant_id} className="p-6 space-y-3 hover:bg-slate-50/50 transition">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold text-slate-900 text-sm">{cov.title}</h4>
                  <span className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-medium">
                    {cov.covenant_type}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500">Obligated:</span>
                  <span className="font-medium text-slate-800 bg-slate-100 px-2 py-0.5 rounded">
                    {cov.obligated_party}
                  </span>
                  <span className="text-slate-500">→ Beneficiary:</span>
                  <span className="font-medium text-slate-800 bg-slate-100 px-2 py-0.5 rounded">
                    {cov.beneficiary_party}
                  </span>
                </div>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs space-y-1">
                <div className="flex justify-between items-center text-slate-500 text-[11px]">
                  <span>
                    Exact Quote • {cov.clause_evidence.section_number || cov.clause_evidence.section_title || 'Section'}
                  </span>
                  <span className="font-mono">
                    [{cov.provenance.char_start} - {cov.provenance.char_end}]
                  </span>
                </div>
                <blockquote className="text-slate-800 italic font-serif">
                  &ldquo;{cov.clause_evidence.exact_quote}&rdquo;
                </blockquote>
              </div>

              {cov.associated_deadline && (
                <div className="text-xs text-slate-600 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-medium">Associated Deadline / Period:</span> {cov.associated_deadline}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 6. Targeted Questions for Legal Counsel */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800 font-semibold">
            <HelpCircle className="w-4 h-4 text-slate-500" />
            <h3>4. Curated Questions for Legal Counsel</h3>
          </div>
          <span className="text-xs text-slate-500">
            {consultation_brief.targeted_questions_for_counsel.length} curated question(s)
          </span>
        </div>
        <div className="divide-y divide-slate-100">
          {consultation_brief.targeted_questions_for_counsel.map((q, idx) => (
            <div key={q.question_id} className="p-6 space-y-2 hover:bg-slate-50/50 transition">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  <span className="font-bold text-blue-600 text-sm mt-0.5">Q{idx + 1}.</span>
                  <p className="font-medium text-slate-900 text-sm leading-snug">{q.question_text}</p>
                </div>
                <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium border uppercase tracking-wider shrink-0 ${getLabelBadge(q.neutral_label)}`}>
                  {q.neutral_label}
                </span>
              </div>
              <p className="text-xs text-slate-600 pl-7">{q.context_rationale}</p>
              
              {q.supporting_evidence_refs.length > 0 && (
                <div className="pl-7 pt-1 flex flex-wrap gap-2">
                  {q.supporting_evidence_refs.map((ev, evIdx) => (
                    <span
                      key={evIdx}
                      className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded border ${getSourceTypeBadge(ev.source_type)}`}
                      title={ev.exact_quote || ev.source_ref}
                    >
                      <span className="font-semibold">{ev.source_type}:</span> {ev.source_ref}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 7. Missing Factual Preconditions (Gatekeeper) */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800 font-semibold">
            <Search className="w-4 h-4 text-slate-500" />
            <h3>5. Missing Factual Preconditions to Clarify</h3>
          </div>
          <span className="text-xs text-slate-500">
            {consultation_brief.missing_facts_to_clarify.length} unstated item(s)
          </span>
        </div>
        <div className="p-6">
          {consultation_brief.missing_facts_to_clarify.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No material blocking factual preconditions were flagged as unstated.</p>
          ) : (
            <ul className="space-y-2.5 text-xs text-slate-700">
              {consultation_brief.missing_facts_to_clarify.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2.5 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* 8. Identified Inconsistencies & Review Flags */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800 font-semibold">
            <ShieldAlert className="w-4 h-4 text-slate-500" />
            <h3>6. Identified Inconsistencies & Review Flags</h3>
          </div>
          <span className="text-xs text-slate-500">
            {consultation_brief.identified_inconsistencies_and_review_flags.length} flag(s)
          </span>
        </div>
        <div className="p-6 space-y-3">
          {consultation_brief.identified_inconsistencies_and_review_flags.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No internal contradictions or unverified conflicts identified.</p>
          ) : (
            consultation_brief.identified_inconsistencies_and_review_flags.map((flag) => (
              <div
                key={flag.flag_id}
                className="p-3.5 rounded-lg border bg-slate-50/70 border-slate-200 space-y-1.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-xs text-slate-900">{flag.title}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-semibold border uppercase ${getLabelBadge(flag.label)}`}>
                    {flag.label}
                  </span>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed">{flag.neutral_explanation}</p>
                <div className="text-[11px] text-slate-500 flex items-center gap-1">
                  <span>Source:</span>
                  <code className="text-[10px] bg-slate-100 px-1 py-0.5 rounded text-slate-600">
                    {flag.supporting_evidence.source_ref}
                  </code>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 9. Actionable Preparation Checklist (Deterministic Priority) */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800 font-semibold">
            <ClipboardList className="w-4 h-4 text-slate-500" />
            <h3>7. Actionable Preparation Checklist</h3>
          </div>
          <span className="text-xs text-slate-500">
            {preparation_checklist.filter((i) => i.priority === 'blocking').length} Blocking • {preparation_checklist.length} Total
          </span>
        </div>
        <div className="divide-y divide-slate-100">
          {preparation_checklist.map((item) => (
            <div key={item.item_id} className="p-5 flex items-start gap-4 hover:bg-slate-50/50 transition">
              <div className="pt-0.5 shrink-0">
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded text-blue-600 border-slate-300 focus:ring-blue-500"
                  readOnly
                />
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  {item.priority === 'blocking' ? (
                    <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded font-bold bg-rose-100 text-rose-800 border border-rose-300">
                      <AlertTriangle className="w-3 h-3" />
                      BLOCKING
                    </span>
                  ) : (
                    <span className="inline-flex items-center text-[11px] px-2 py-0.5 rounded font-medium bg-slate-100 text-slate-700">
                      STANDARD
                    </span>
                  )}
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                    {getCategoryBadge(item.category)}
                  </span>
                  <span className="text-xs font-semibold text-slate-900">{item.task_description}</span>
                </div>
                <p className="text-xs text-slate-600">{item.rationale}</p>
                <div className="pt-1 flex items-center gap-2 text-[11px] text-slate-400">
                  <span>Provenance:</span>
                  <span className={`px-1.5 py-0.5 rounded border text-[10px] ${getSourceTypeBadge(item.provenance.source_type)}`}>
                    {item.provenance.source_type}
                  </span>
                  {item.provenance.source_ref && (
                    <span className="truncate max-w-xs font-mono text-[10px]">
                      {item.provenance.source_ref}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
