'use client';

import React, { useState } from 'react';
import { EvidenceSnippet, AuthoritativeLegalSource, JudicialPrecedentSource } from '@/lib/types';
import { FileText, CheckCircle2, Bookmark, ExternalLink, Scale, Landmark, ShieldCheck } from 'lucide-react';

interface EvidenceViewerProps {
  sources: EvidenceSnippet[];
  externalLaw?: AuthoritativeLegalSource[];
  precedents?: JudicialPrecedentSource[];
}

export default function EvidenceViewer({ sources, externalLaw = [], precedents = [] }: EvidenceViewerProps) {
  const [activeSnippetId, setActiveSnippetId] = useState<string | null>(
    sources.length > 0 ? sources[0].snippet_id : null
  );

  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <Bookmark className="w-3.5 h-3.5 text-indigo-600" />
          Traceable Evidence Citations ({sources.length})
        </h4>
        <span className="text-[11px] text-slate-400 font-medium">Verified Source Quotes</span>
      </div>

      <div className="space-y-2.5">
        {sources.map((snippet) => {
          const isSelected = activeSnippetId === snippet.snippet_id;
          return (
            <div
              key={snippet.snippet_id}
              onClick={() => setActiveSnippetId(snippet.snippet_id)}
              className={`p-3.5 rounded-lg border transition cursor-pointer text-xs ${
                isSelected
                  ? 'bg-indigo-50/70 border-indigo-300 ring-1 ring-indigo-400'
                  : 'bg-slate-50 border-slate-200 hover:bg-slate-100/70'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="bg-indigo-600 text-white font-mono font-bold px-2 py-0.5 rounded text-[10px]">
                    {snippet.section_number || 'Section'}
                  </span>
                  {snippet.section_title && (
                    <span className="font-semibold text-slate-800">
                      {snippet.section_title}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 text-slate-400 text-[10px]">
                  <span>{snippet.filename || 'Document'}</span>
                  {snippet.page_number !== null && snippet.page_number !== undefined && (
                    <span>• Page {snippet.page_number}</span>
                  )}
                  {snippet.paragraph_index !== null && snippet.paragraph_index !== undefined && (
                    <span>• Para {snippet.paragraph_index + 1}</span>
                  )}
                  {snippet.start_char !== undefined && snippet.end_char !== undefined && (
                    <span className="font-mono bg-slate-200/60 px-1 py-0.5 rounded">
                      chars {snippet.start_char}-{snippet.end_char}
                    </span>
                  )}
                </div>
              </div>

              <blockquote className="italic text-slate-700 border-l-2 border-indigo-400 pl-2.5 py-0.5 my-1 font-serif text-[12.5px] leading-relaxed bg-white/60 rounded-r">
                &ldquo;{snippet.quote}&rdquo;
              </blockquote>

              <div className="flex items-center justify-between pt-1 text-[10px] text-slate-500">
                <span className="flex items-center gap-1 text-emerald-700 font-medium">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  Verified in authentic extracted text
                </span>
                {isSelected && (
                  <span className="text-indigo-600 font-medium flex items-center gap-0.5">
                    Focused Citation
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Authoritative Legislation Section */}
      {externalLaw && externalLaw.length > 0 && (
        <div className="pt-4 border-t border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-blue-600" />
              Authoritative Legislation & Statutes ({externalLaw.length})
            </h4>
            <span className="text-[10px] bg-blue-50 text-blue-700 font-semibold px-2 py-0.5 rounded border border-blue-200">
              Verified Primary Law
            </span>
          </div>

          <div className="space-y-2">
            {externalLaw.map((law) => (
              <div
                key={law.source_id}
                className="p-3 bg-blue-50/50 rounded-lg border border-blue-200 text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="bg-blue-700 text-white font-mono font-bold px-2 py-0.5 rounded text-[10px]">
                      {law.section_provision}
                    </span>
                    <span className="font-bold text-slate-800">{law.title}</span>
                  </div>
                  <a
                    href={law.official_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[11px] text-blue-700 hover:underline font-medium"
                  >
                    Official Portal <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <p className="text-[11px] text-slate-500">{law.issuing_authority}</p>

                <blockquote className="italic text-slate-700 border-l-2 border-blue-400 pl-2 py-0.5 font-serif text-[12px] bg-white/70 rounded-r">
                  &ldquo;{law.exact_retrieved_text}&rdquo;
                </blockquote>

                <div className="flex items-center justify-between pt-1 text-[10px] text-slate-500">
                  <span className="flex items-center gap-1 text-emerald-700 font-medium">
                    <ShieldCheck className="w-3 h-3 text-emerald-600" />
                    Status: {law.currentness_status} (Last amended: {law.last_amendment_date || 'N/A'})
                  </span>
                  <span className="font-mono text-slate-400">{law.source_locator_version_info}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Judicial Precedents Section */}
      {precedents && precedents.length > 0 && (
        <div className="pt-4 border-t border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Landmark className="w-3.5 h-3.5 text-purple-600" />
              Judicial Precedents & Rulings ({precedents.length})
            </h4>
            <span className="text-[10px] bg-purple-50 text-purple-700 font-semibold px-2 py-0.5 rounded border border-purple-200">
              Precedential Status: Verified Metadata
            </span>
          </div>

          <div className="space-y-2">
            {precedents.map((prec) => (
              <div
                key={prec.precedent_id}
                className="p-3 bg-purple-50/50 rounded-lg border border-purple-200 text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-bold text-slate-900 text-[12.5px]">{prec.case_name}</span>
                    <span className="ml-2 text-purple-700 font-mono text-[11px] font-semibold">
                      {prec.citation}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-500">{prec.decision_date}</span>
                </div>

                <div className="flex items-center gap-2 text-[10.5px] text-slate-600">
                  <span className="font-medium text-slate-700">{prec.court}</span>
                  <span>•</span>
                  <span>{prec.relevant_provision}</span>
                </div>

                <blockquote className="italic text-slate-700 border-l-2 border-purple-400 pl-2 py-0.5 font-serif text-[12px] bg-white/70 rounded-r">
                  &ldquo;{prec.verbatim_excerpt}&rdquo;
                </blockquote>

                <div className="pt-1 text-[10px] text-purple-800 font-medium">
                  {prec.binding_status}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
