'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  HelpCircle,
  Scale,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  RefreshCw,
  Info,
  CheckSquare,
  UserCheck,
  Clock,
  GitCompare,
  FileCheck,
  ClipboardList,
  Upload,
  FilePlus,
  Trash2,
  Paperclip,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  Download,
  Copy,
  Terminal,
  Activity,
  Compass,
} from 'lucide-react';
import {
  HealthStatus,
  DocumentMeta,
  UserRole,
  UnifiedNavigationResponse,
} from '@/lib/types';
import {
  fetchHealth,
  fetchLoadedDocuments,
  uploadDocumentFile,
  uploadTextDocument,
  deleteDocument,
  loadSampleDocument,
  navigateLegalContext,
} from '@/lib/api';
import EvidenceViewer from '@/components/EvidenceViewer';
import DocumentComparisonView from '@/components/DocumentComparisonView';

export default function HomePage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  // Document Management State
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showPasteModal, setShowPasteModal] = useState(false);
  const [pastedTitle, setPastedTitle] = useState('custom_agreement.txt');
  const [pastedContent, setPastedContent] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Unified Navigator Inputs
  const [declaredRole, setDeclaredRole] = useState<string>('auto');
  const [situationText, setSituationText] = useState('');
  const [questionText, setQuestionText] = useState('');
  const [jurisdictionText, setJurisdictionText] = useState('');

  // Unified Response State
  const [navResponse, setNavResponse] = useState<UnifiedNavigationResponse | null>(null);
  const [isNavigating, setIsNavigating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Diagnostics Drawer
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [copiedBrief, setCopiedBrief] = useState(false);

  // Initial Load
  const refreshDocuments = async () => {
    try {
      const docs = await fetchLoadedDocuments();
      setDocuments(docs);
      if (docs.length > 0 && selectedDocs.length === 0) {
        setSelectedDocs([docs[0].doc_id]);
      }
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
  };

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setHealth(h);
        setLoadingHealth(false);
      })
      .catch((err) => {
        console.error('Health check failed:', err);
        setLoadingHealth(false);
      });

    refreshDocuments();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    setIsUploading(true);
    setErrorMsg(null);
    try {
      for (let i = 0; i < e.target.files.length; i++) {
        const doc = await uploadDocumentFile(e.target.files[i]);
        setSelectedDocs((prev) => Array.from(new Set([...prev, doc.doc_id])));
      }
      await refreshDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || 'File upload failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handlePasteSubmit = async () => {
    if (!pastedContent.trim()) return;
    setIsUploading(true);
    setErrorMsg(null);
    try {
      const doc = await uploadTextDocument(pastedContent.trim(), pastedTitle || 'pasted_agreement.txt');
      await refreshDocuments();
      setSelectedDocs((prev) => Array.from(new Set([...prev, doc.doc_id])));
      setShowPasteModal(false);
      setPastedContent('');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to ingest pasted agreement');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDoc = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteDocument(docId);
      setSelectedDocs((prev) => prev.filter((id) => id !== docId));
      await refreshDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to remove document');
    }
  };

  const handleLoadSample = async (sampleName: string) => {
    setIsUploading(true);
    setErrorMsg(null);
    try {
      const doc = await loadSampleDocument(sampleName);
      await refreshDocuments();
      setSelectedDocs((prev) => Array.from(new Set([...prev, doc.doc_id])));
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load sample document');
    } finally {
      setIsUploading(false);
    }
  };

  const toggleDocSelection = (docId: string) => {
    setSelectedDocs((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const handleNavigate = async () => {
    if (!questionText.trim() && !situationText.trim()) {
      setErrorMsg('Please enter your question or describe your situation.');
      return;
    }

    setIsNavigating(true);
    setErrorMsg(null);

    try {
      const res = await navigateLegalContext({
        query: questionText.trim(),
        situation_description: situationText.trim() || undefined,
        declared_role: declaredRole !== 'auto' ? declaredRole : undefined,
        doc_ids: selectedDocs,
        jurisdiction: jurisdictionText.trim() || undefined,
      });
      setNavResponse(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to process legal inquiry.');
    } finally {
      setIsNavigating(false);
    }
  };

  const handleCopyBrief = () => {
    if (navResponse?.consultation_brief_markdown) {
      navigator.clipboard.writeText(navResponse.consultation_brief_markdown);
      setCopiedBrief(true);
      setTimeout(() => setCopiedBrief(false), 2000);
    }
  };

  const handleDownloadBrief = () => {
    if (!navResponse?.consultation_brief_markdown) return;
    const blob = new Blob([navResponse.consultation_brief_markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Legal_Consultation_Brief_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8">
      {/* Workspace Card */}
      <section className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 px-6 py-5 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-400" />
              Tell Us What You're Dealing With
            </h2>
            <p className="text-xs text-slate-300 mt-0.5">
              Attach contracts, describe the situation, and ask your question. The navigator coordinates textual analysis, comparisons, and statutory rules automatically.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleLoadSample('residential_lease_agreement.txt')}
              disabled={isUploading}
              className="text-xs bg-white/10 hover:bg-white/20 text-white px-3 py-1.5 rounded-lg border border-white/20 transition flex items-center gap-1.5"
            >
              <FileCheck className="w-3.5 h-3.5" />
              Load Lease Document
            </button>
          </div>
        </div>

          <div className="p-6 space-y-6">
            {/* Document Ingestion & Attachment Bar */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Paperclip className="w-3.5 h-3.5 text-indigo-600" />
                  Attached Documents ({selectedDocs.length} selected of {documents.length})
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    multiple
                    accept=".txt,.pdf,.docx"
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg border border-slate-300 font-medium transition flex items-center gap-1.5"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Upload File(s)
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowPasteModal(true)}
                    disabled={isUploading}
                    className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg border border-slate-300 font-medium transition flex items-center gap-1.5"
                  >
                    <FilePlus className="w-3.5 h-3.5" />
                    Paste Text
                  </button>
                </div>
              </div>

              {/* Document List Chips */}
              {documents.length > 0 ? (
                <div className="flex flex-wrap gap-2 pt-1">
                  {documents.map((doc) => {
                    const isSelected = selectedDocs.includes(doc.doc_id);
                    return (
                      <div
                        key={doc.doc_id}
                        onClick={() => toggleDocSelection(doc.doc_id)}
                        className={`cursor-pointer group flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium border transition-all ${
                          isSelected
                            ? 'bg-indigo-50 border-indigo-300 text-indigo-900 shadow-sm'
                            : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                        }`}
                      >
                        <div className={`w-2 h-2 rounded-full ${isSelected ? 'bg-indigo-600' : 'bg-slate-400'}`} />
                        <span className="truncate max-w-[200px]" title={doc.filename}>{doc.filename}</span>
                        <span className="text-[10px] text-slate-400">({doc.total_characters} chars)</span>
                        <button
                          type="button"
                          onClick={(e) => handleDeleteDoc(doc.doc_id, e)}
                          className="opacity-60 hover:opacity-100 hover:text-red-600 transition"
                          title="Remove document"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="border border-dashed border-slate-300 rounded-xl p-4 text-center bg-slate-50/50">
                  <p className="text-xs text-slate-500">
                    No documents attached yet. You can upload contracts (PDF, DOCX, TXT) or ask general questions without a document.
                  </p>
                </div>
              )}
            </div>

            {/* Role & Jurisdiction Inputs */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-indigo-600" />
                  Your Perspective
                </label>
                <select
                  value={declaredRole}
                  onChange={(e) => setDeclaredRole(e.target.value)}
                  className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="auto">Auto-Detect from Context</option>
                  <option value="tenant">Tenant / Lessee</option>
                  <option value="landlord">Landlord / Lessor</option>
                  <option value="employee">Employee</option>
                  <option value="employer">Employer</option>
                  <option value="contractor">Independent Contractor / Consultant</option>
                  <option value="client">Client / Customer</option>
                  <option value="general">Neutral / General</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Scale className="w-3.5 h-3.5 text-indigo-600" />
                  Governing Jurisdiction (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Karnataka, India / California, USA / England & Wales"
                  value={jurisdictionText}
                  onChange={(e) => setJurisdictionText(e.target.value)}
                  className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Situation Background Input (Optional) */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-indigo-600" />
                Situation Background & What Happened (Optional)
              </label>
              <textarea
                rows={2}
                placeholder="Example: I rented a flat in Bangalore on a 1-year lease. Yesterday my landlord verbally told me to leave in 15 days because he wants to sell. I have paid rent on time every month."
                value={situationText}
                onChange={(e) => setSituationText(e.target.value)}
                className="w-full text-xs bg-white border border-slate-300 rounded-lg p-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-y"
              />
            </div>

            {/* Direct Question Input */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5 text-indigo-600" />
                What specific question would you like answered?
              </label>
              <textarea
                rows={2}
                placeholder="Example: Can he force me to leave in 15 days, and what are the notice requirements?"
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                className="w-full text-xs bg-white border border-slate-300 rounded-lg p-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-y"
              />
            </div>

            {/* Error Message */}
            {errorMsg && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Submit CTA */}
            <div className="flex items-center justify-end pt-2">
              <button
                type="button"
                onClick={handleNavigate}
                disabled={isNavigating}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold text-xs px-6 py-2.5 rounded-xl shadow-md shadow-indigo-100 transition flex items-center gap-2"
              >
                {isNavigating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Analyzing Legal Context...</span>
                  </>
                ) : (
                  <>
                    <span>Navigate Legal Context</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </section>

        {/* Unified Response Container */}
        {navResponse && (
          <section className="space-y-6">
            {/* Perspective & Direct Summary Card */}
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
              <div className="bg-slate-900 text-white px-6 py-4 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <Compass className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-sm font-bold tracking-tight text-white">
                    Legal Information & Practical Translation
                  </h3>
                </div>
                {navResponse.inferred_role && (
                  <span className="text-[11px] font-semibold uppercase px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
                    Perspective: {navResponse.inferred_role}
                  </span>
                )}
              </div>

              <div className="p-6 space-y-6">
                {/* Plain-Language Perspective Summary */}
                <div className="p-4 bg-indigo-50/60 border border-indigo-100 rounded-xl">
                  <h4 className="text-xs font-bold text-indigo-900 uppercase tracking-wider mb-1">
                    Summary & Plain-Language Perspective
                  </h4>
                  <p className="text-sm text-slate-800 leading-relaxed font-medium">
                    {navResponse.summary_and_perspective}
                  </p>
                </div>

                {/* Substantive Contract Meaning */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
                    Substantive Legal & Contractual Meaning
                  </h4>
                  <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                    {navResponse.what_this_means_in_plain_language || navResponse.answer}
                  </p>
                </div>

                {/* Why It Matters */}
                {navResponse.why_it_matters && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-indigo-600" />
                      Why It Matters to Your Situation
                    </h4>
                    <p className="text-xs text-slate-700 leading-relaxed bg-amber-50/50 p-3.5 rounded-xl border border-amber-200/80">
                      {navResponse.why_it_matters}
                    </p>
                  </div>
                )}

                {/* What the Document Says */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-indigo-600" />
                    What the Document Says (Contractual Text)
                  </h4>
                  <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs text-slate-800 leading-relaxed font-mono whitespace-pre-wrap">
                    {navResponse.what_the_document_says}
                  </div>
                </div>

                {/* Evidence Citations */}
                {navResponse.sources && navResponse.sources.length > 0 && (
                  <div className="pt-2">
                    <EvidenceViewer sources={navResponse.sources} />
                  </div>
                )}
              </div>
            </div>

            {/* Comparative Analysis (If 2+ documents) */}
            {navResponse.comparative_analysis && (
              <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
                <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
                  <h3 className="text-sm font-bold tracking-tight flex items-center gap-2">
                    <GitCompare className="w-4 h-4 text-emerald-400" />
                    Cross-Document Comparative Analysis
                  </h3>
                  <span className="text-[11px] font-semibold text-emerald-300">
                    {navResponse.comparative_analysis.total_differences_analyzed} Differences Analyzed
                  </span>
                </div>
                <div className="p-6">
                  <DocumentComparisonView comparison={navResponse.comparative_analysis} />
                </div>
              </div>
            )}

            {/* Governing Legal Framework (If applicable) */}
            {navResponse.governing_legal_framework && navResponse.governing_legal_framework.length > 0 && (
              <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
                <div className="bg-slate-900 text-white px-6 py-4 flex items-center gap-2">
                  <Scale className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-bold tracking-tight">
                    Governing Statutory & Legal Framework
                  </h3>
                </div>
                <div className="p-6 space-y-4">
                  {navResponse.jurisdiction_note && (
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-800 flex items-center gap-2">
                      <Info className="w-4 h-4 text-blue-600 shrink-0" />
                      <span>{navResponse.jurisdiction_note}</span>
                    </div>
                  )}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {navResponse.governing_legal_framework.map((rule, idx) => (
                      <div key={idx} className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-900">{rule.statute}</span>
                          <span className="text-[10px] font-mono bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded border border-indigo-200">
                            {rule.section}
                          </span>
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed">{rule.summary}</p>
                        {rule.applicability && (
                          <p className="text-[11px] text-slate-500 italic border-t border-slate-200 pt-1.5 mt-1.5">
                            Applicability: {rule.applicability}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* What is Unclear or Missing (Gaps & Inconsistencies) */}
            {(navResponse.what_is_unclear_or_missing || (navResponse.uncertainties && navResponse.uncertainties.length > 0)) && (
              <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
                <div className="bg-amber-600 text-white px-6 py-4 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  <h3 className="text-sm font-bold tracking-tight">
                    Factual Gaps & Items Requiring Clarification
                  </h3>
                </div>
                <div className="p-6 space-y-4">
                  {navResponse.what_is_unclear_or_missing && (
                    <p className="text-xs text-slate-800 leading-relaxed font-medium bg-amber-50/70 p-3.5 rounded-xl border border-amber-200">
                      {navResponse.what_is_unclear_or_missing}
                    </p>
                  )}
                  {navResponse.uncertainties && navResponse.uncertainties.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                        Specific Identified Ambiguities
                      </h4>
                      <ul className="space-y-1.5">
                        {navResponse.uncertainties.map((item, idx) => (
                          <li key={idx} className="text-xs text-slate-700 flex items-start gap-2">
                            <span className="text-amber-500 font-bold shrink-0">•</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Actionable Preparation Checklist */}
            {navResponse.actionable_checklist && navResponse.actionable_checklist.length > 0 && (
              <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
                <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
                  <h3 className="text-sm font-bold tracking-tight flex items-center gap-2">
                    <CheckSquare className="w-4 h-4 text-indigo-400" />
                    Actionable Preparation Checklist
                  </h3>
                  <span className="text-[11px] font-semibold text-slate-300">
                    Bounded Next Steps
                  </span>
                </div>
                <div className="p-6">
                  <ul className="space-y-2.5">
                    {navResponse.actionable_checklist.map((step, idx) => (
                      <li key={idx} className="flex items-start gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                        <span className="leading-relaxed">{step}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Consultation Brief Export */}
            {navResponse.consultation_brief_markdown && (
              <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
                <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
                  <h3 className="text-sm font-bold tracking-tight flex items-center gap-2">
                    <ClipboardList className="w-4 h-4 text-indigo-400" />
                    Professional Consultation Brief
                  </h3>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleCopyBrief}
                      className="text-xs bg-white/10 hover:bg-white/20 text-white px-3 py-1.5 rounded-lg border border-white/20 transition flex items-center gap-1.5"
                    >
                      {copiedBrief ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedBrief ? 'Copied' : 'Copy Brief'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleDownloadBrief}
                      className="text-xs bg-white/10 hover:bg-white/20 text-white px-3 py-1.5 rounded-lg border border-white/20 transition flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download .md</span>
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-800 font-mono whitespace-pre-wrap max-h-80 overflow-y-auto leading-relaxed">
                    {navResponse.consultation_brief_markdown}
                  </div>
                </div>
              </div>
            )}

            {/* Collapsible Evidence & System Diagnostics Drawer */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <button
                type="button"
                onClick={() => setShowDiagnostics(!showDiagnostics)}
                className="w-full px-6 py-3.5 bg-slate-100/70 hover:bg-slate-100 flex items-center justify-between text-xs font-semibold text-slate-700 transition"
              >
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-slate-500" />
                  <span>Evidence & System Diagnostics</span>
                </div>
                {showDiagnostics ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showDiagnostics && (
                <div className="p-6 border-t border-slate-200 bg-slate-50/50 space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="p-3 bg-white rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">Effective Mode</span>
                      <span className="text-xs font-mono font-semibold text-indigo-700">{navResponse.diagnostics.effective_mode}</span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">Query Category</span>
                      <span className="text-xs font-mono font-semibold text-slate-700">{navResponse.diagnostics.category}</span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">Latency</span>
                      <span className="text-xs font-mono font-semibold text-slate-700">{navResponse.diagnostics.latency_ms} ms</span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">Sufficiency Passed</span>
                      <span className={`text-xs font-mono font-semibold ${navResponse.diagnostics.evidence_sufficiency_passed ? 'text-emerald-700' : 'text-amber-700'}`}>
                        {String(navResponse.diagnostics.evidence_sufficiency_passed)}
                      </span>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-500 leading-relaxed pt-2">
                    <p>Telemetry and execution tracing coordinate document grounding, cross-document comparison diffs, external statutory databases, and situation role inference.</p>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

      {/* Paste Modal */}
      {showPasteModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FilePlus className="w-4 h-4 text-indigo-600" />
                Paste Agreement Text
              </h3>
              <button
                type="button"
                onClick={() => setShowPasteModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Document Title
                </label>
                <input
                  type="text"
                  value={pastedTitle}
                  onChange={(e) => setPastedTitle(e.target.value)}
                  className="w-full text-xs bg-white border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g. consulting_agreement.txt"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Agreement Text Content
                </label>
                <textarea
                  rows={8}
                  value={pastedContent}
                  onChange={(e) => setPastedContent(e.target.value)}
                  className="w-full text-xs bg-white border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                  placeholder="Paste contract clauses or agreement text here..."
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowPasteModal(false)}
                className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg font-medium transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePasteSubmit}
                disabled={isUploading || !pastedContent.trim()}
                className="text-xs bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg font-medium transition flex items-center gap-1.5"
              >
                {isUploading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Ingest & Attach
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
