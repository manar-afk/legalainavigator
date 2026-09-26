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

  // Diagnostics Drawer & Brief Collapsible
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [showBrief, setShowBrief] = useState(false);
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
        const file = e.target.files[i];
        // Efficiency: prevent duplicate upload if same file is already in workspace
        const existing = documents.find((d) => d.filename === file.name);
        if (existing) {
          setSelectedDocs((prev) => Array.from(new Set([...prev, existing.doc_id])));
          continue;
        }
        const doc = await uploadDocumentFile(file);
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
    // Efficiency: check if sample is already loaded in workspace before making duplicate API call
    const existing = documents.find((d) => d.filename === sampleName);
    if (existing) {
      setSelectedDocs((prev) => Array.from(new Set([...prev, existing.doc_id])));
      return;
    }
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
      {/* ============================================================ */}
      {/* P0 — HERO / PROBLEM STATEMENT ALIGNMENT BANNER */}
      {/* ============================================================ */}
      <section className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 sm:p-8 space-y-6" aria-label="Product Capability Overview">
        <div className="max-w-4xl space-y-2.5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200/70 text-indigo-700 text-xs font-semibold">
            <Scale className="w-3.5 h-3.5" aria-hidden="true" />
            <span>AI Legal Decision Support & Navigation</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight leading-snug">
            Understand, compare, and navigate legal documents and information — grounded in evidence and authoritative legal sources.
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed font-normal">
            Legal Information Navigator bridges the gap between dense contractual language, governing statutory frameworks, and real-world legal consultation.
          </p>
        </div>

        {/* Three Concise Capability Indicators */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 space-y-1.5 hover:border-indigo-300 transition-colors">
            <div className="flex items-center gap-2 text-indigo-700 font-bold text-xs uppercase tracking-wider">
              <BookOpen className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>UNDERSTAND</span>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed font-medium">
              Plain-language explanations of relevant legal provisions.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 space-y-1.5 hover:border-emerald-300 transition-colors">
            <div className="flex items-center gap-2 text-emerald-700 font-bold text-xs uppercase tracking-wider">
              <GitCompare className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>COMPARE</span>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed font-medium">
              Identify meaningful differences between document versions.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 space-y-1.5 hover:border-sky-300 transition-colors">
            <div className="flex items-center gap-2 text-sky-700 font-bold text-xs uppercase tracking-wider">
              <Compass className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>NAVIGATE</span>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed font-medium">
              Identify missing information and prepare questions for professional legal review.
            </p>
          </div>
        </div>
      </section>

      {/* Workspace Card */}
      <section className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden" aria-label="Legal Inquiry Workspace">
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 px-6 py-5 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-400" aria-hidden="true" />
              Tell Us What You're Dealing With
            </h2>
            <p className="text-xs text-slate-300 mt-0.5 font-normal">
              Attach contracts, describe the situation, and ask your question. The navigator coordinates textual analysis, comparisons, and statutory rules automatically.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Sample document options">
            <span className="text-xs text-slate-300 font-medium mr-1 hidden sm:inline">Try a Sample:</span>
            <button
              type="button"
              onClick={() => handleLoadSample('employment_contract.txt')}
              disabled={isUploading}
              aria-label="Load sample Employment Agreement"
              className="text-xs bg-white/10 hover:bg-white/20 text-white px-2.5 py-1.5 rounded-lg border border-white/20 transition flex items-center gap-1 shadow-sm focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:outline-none"
              title="Load sample Employment Agreement"
            >
              <FileCheck className="w-3.5 h-3.5 text-indigo-300" aria-hidden="true" />
              <span>Employment</span>
            </button>
            <button
              type="button"
              onClick={() => handleLoadSample('master_services_agreement.txt')}
              disabled={isUploading}
              aria-label="Load sample Master Services Agreement or Mutual NDA"
              className="text-xs bg-white/10 hover:bg-white/20 text-white px-2.5 py-1.5 rounded-lg border border-white/20 transition flex items-center gap-1 shadow-sm focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:outline-none"
              title="Load sample Master Services Agreement / NDA"
            >
              <FileCheck className="w-3.5 h-3.5 text-emerald-300" aria-hidden="true" />
              <span>Services / NDA</span>
            </button>
            <button
              type="button"
              onClick={() => handleLoadSample('residential_lease_agreement.txt')}
              disabled={isUploading}
              aria-label="Load sample Residential Lease Agreement"
              className="text-xs bg-white/10 hover:bg-white/20 text-white px-2.5 py-1.5 rounded-lg border border-white/20 transition flex items-center gap-1 shadow-sm focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:outline-none"
              title="Load sample Residential Lease Agreement"
            >
              <FileCheck className="w-3.5 h-3.5 text-amber-300" aria-hidden="true" />
              <span>Lease</span>
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Document Ingestion & Attachment Bar */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label htmlFor="file-upload-input" className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5 cursor-pointer">
                <Paperclip className="w-3.5 h-3.5 text-indigo-600" aria-hidden="true" />
                Attached Documents ({selectedDocs.length} selected of {documents.length})
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="file-upload-input"
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  multiple
                  accept=".txt,.pdf,.docx"
                  aria-label="Upload agreement files (PDF, DOCX, TXT)"
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  aria-label="Upload document files from your device"
                  className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg border border-slate-300 font-medium transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
                >
                  <Upload className="w-3.5 h-3.5" aria-hidden="true" />
                  Upload File(s)
                </button>
                <button
                  type="button"
                  onClick={() => setShowPasteModal(true)}
                  disabled={isUploading}
                  aria-label="Open dialog to paste agreement text directly"
                  className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg border border-slate-300 font-medium transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
                >
                  <FilePlus className="w-3.5 h-3.5" aria-hidden="true" />
                  Paste Text
                </button>
              </div>
            </div>

            {/* Document List Chips */}
            {documents.length > 0 ? (
              <div className="flex flex-wrap gap-2 pt-1" role="list" aria-label="Attached document list">
                {documents.map((doc) => {
                  const isSelected = selectedDocs.includes(doc.doc_id);
                  return (
                    <div
                      key={doc.doc_id}
                      role="listitem"
                      onClick={() => toggleDocSelection(doc.doc_id)}
                      className={`cursor-pointer group flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium border transition-all ${
                        isSelected
                          ? 'bg-indigo-50 border-indigo-300 text-indigo-900 shadow-sm'
                          : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      <div className={`w-2 h-2 rounded-full ${isSelected ? 'bg-indigo-600' : 'bg-slate-400'}`} aria-hidden="true" />
                      <span className="truncate max-w-[200px]" title={doc.filename}>{doc.filename}</span>
                      <span className="text-[11px] text-slate-500 font-medium">({doc.total_characters} chars)</span>
                      <button
                        type="button"
                        onClick={(e) => handleDeleteDoc(doc.doc_id, e)}
                        className="opacity-70 hover:opacity-100 hover:text-red-600 transition p-0.5 rounded focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
                        title="Remove document"
                        aria-label={`Remove document ${doc.filename}`}
                      >
                        <X className="w-3.5 h-3.5" aria-hidden="true" />
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="border border-dashed border-slate-300 rounded-xl p-4 text-center bg-slate-50/50">
                <p className="text-xs text-slate-600">
                  No documents attached yet. You can upload contracts (PDF, DOCX, TXT) or ask general questions without a document.
                </p>
              </div>
            )}
          </div>

          {/* Role & Jurisdiction Inputs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
            <div>
              <label htmlFor="role-select" className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-indigo-600" aria-hidden="true" />
                Your Perspective
              </label>
              <select
                id="role-select"
                value={declaredRole}
                onChange={(e) => setDeclaredRole(e.target.value)}
                aria-label="Select your role or perspective"
                className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none focus:border-indigo-500"
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
              <label htmlFor="jurisdiction-input" className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5 text-indigo-600" aria-hidden="true" />
                Governing Jurisdiction (Optional)
              </label>
              <input
                id="jurisdiction-input"
                type="text"
                placeholder="e.g. Karnataka, India / California, USA / England & Wales"
                value={jurisdictionText}
                onChange={(e) => setJurisdictionText(e.target.value)}
                aria-label="Governing Jurisdiction (Optional)"
                className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Situation Background Input (Optional) */}
          <div className="space-y-1.5">
            <label htmlFor="situation-input" className="block text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-indigo-600" aria-hidden="true" />
              Situation Background & What Happened (Optional)
            </label>
            <textarea
              id="situation-input"
              rows={2}
              placeholder="Example: I rented a flat in Bangalore on a 1-year lease. Yesterday my landlord verbally told me to leave in 15 days because he wants to sell. I have paid rent on time every month."
              value={situationText}
              onChange={(e) => setSituationText(e.target.value)}
              aria-label="Situation Background & What Happened (Optional)"
              className="w-full text-xs bg-white border border-slate-300 rounded-lg p-3 text-slate-800 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none focus:border-indigo-500 resize-y"
            />
          </div>

          {/* Direct Question Input */}
          <div className="space-y-1.5">
            <label htmlFor="question-input" className="block text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-indigo-600" aria-hidden="true" />
              What specific question would you like answered?
            </label>
            <textarea
              id="question-input"
              rows={2}
              placeholder="Example: Can he force me to leave in 15 days, and what are the notice requirements?"
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              aria-label="What specific question would you like answered?"
              className="w-full text-xs bg-white border border-slate-300 rounded-lg p-3 text-slate-800 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none focus:border-indigo-500 resize-y"
            />
          </div>

          {/* Error Message */}
          {errorMsg && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center gap-2" role="alert">
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" aria-hidden="true" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Submit CTA */}
          <div className="flex items-center justify-end pt-2">
            <button
              type="button"
              onClick={handleNavigate}
              disabled={isNavigating}
              aria-label="Navigate legal context and analyze agreements"
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold text-xs px-6 py-2.5 rounded-xl shadow-md shadow-indigo-100 transition flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
            >
              {isNavigating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>Analyzing Legal Context...</span>
                </>
              ) : (
                <>
                  <span>Navigate Legal Context</span>
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </>
              )}
            </button>
          </div>
        </div>
      </section>

        {/* Unified Response Container */}
        {navResponse && (
          <section className="space-y-6">
            {/* ============================================================ */}
            {/* 1. WHAT WE FOUND */}
            {/* ============================================================ */}
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
              <div className="bg-slate-900 text-white px-6 py-4 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <Compass className="w-5 h-5 text-indigo-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">1. What We Found</span>
                </div>
                {navResponse.inferred_role && (
                  <span className="text-[11px] font-semibold uppercase px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
                    Perspective: {navResponse.inferred_role}
                  </span>
                )}
              </div>

              <div className="p-6 space-y-4">
                <div className="p-4 bg-indigo-50/70 border border-indigo-100 rounded-xl">
                  <h4 className="text-xs font-bold text-indigo-900 uppercase tracking-wider mb-1.5">
                    Direct Plain-Language Finding
                  </h4>
                  <p className="text-sm text-slate-800 leading-relaxed font-medium">
                    {navResponse.summary_and_perspective}
                  </p>
                </div>
                {navResponse.answer && navResponse.answer !== navResponse.summary_and_perspective && (
                  <div className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                    <span className="font-semibold text-slate-900 block mb-1">Key Takeaway:</span>
                    {navResponse.answer}
                  </div>
                )}
              </div>
            </div>

            {/* ============================================================ */}
            {/* 2. EVIDENCE / LEGAL BASIS */}
            {/* ============================================================ */}
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
              <div className="bg-slate-900 text-white px-6 py-4 flex items-center gap-2.5">
                <BookOpen className="w-5 h-5 text-emerald-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">2. Evidence & Legal Basis</span>
              </div>

              <div className="p-6 space-y-6">
                {/* Contractual / Factual Text */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-indigo-600" />
                    Agreement Text & Information Basis
                  </h4>
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-800 leading-relaxed font-mono whitespace-pre-wrap">
                    {navResponse.what_the_document_says}
                  </div>
                </div>

                {/* Evidence Citations */}
                {navResponse.sources && navResponse.sources.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-slate-100">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <FileCheck className="w-3.5 h-3.5 text-emerald-600" />
                      Retrieved Clause Offsets & Citations
                    </h4>
                    <EvidenceViewer sources={navResponse.sources} />
                  </div>
                )}

                {/* Governing Legal Framework (External Statutory Law) */}
                {navResponse.governing_legal_framework && navResponse.governing_legal_framework.length > 0 && (
                  <div className="space-y-3 pt-2 border-t border-slate-100">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Scale className="w-3.5 h-3.5 text-amber-600" />
                      Authoritative Statutory Framework
                    </h4>
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
                )}

                {/* Cross-Document Comparison (If 2+ docs) */}
                {navResponse.comparative_analysis && (
                  <div className="space-y-3 pt-2 border-t border-slate-100">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                        <GitCompare className="w-3.5 h-3.5 text-indigo-600" />
                        Cross-Document Comparison Analysis
                      </h4>
                      <span className="text-[11px] font-semibold text-emerald-600">
                        {navResponse.comparative_analysis.total_differences_analyzed} Differences Analyzed
                      </span>
                    </div>
                    <DocumentComparisonView comparison={navResponse.comparative_analysis} />
                  </div>
                )}
              </div>
            </div>

            {/* ============================================================ */}
            {/* 3. WHAT THIS MEANS FOR YOUR SITUATION */}
            {/* ============================================================ */}
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
              <div className="bg-slate-900 text-white px-6 py-4 flex items-center gap-2.5">
                <Scale className="w-5 h-5 text-sky-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-sky-400">3. What This Means For Your Situation</span>
              </div>

              <div className="p-6 space-y-4">
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Practical Substantive Translation
                  </h4>
                  <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200">
                    {navResponse.what_this_means_in_plain_language || navResponse.answer}
                  </p>
                </div>

                {navResponse.why_it_matters && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-indigo-600" />
                      Why It Matters to Your Position
                    </h4>
                    <p className="text-xs text-slate-700 leading-relaxed bg-amber-50/50 p-4 rounded-xl border border-amber-200/80">
                      {navResponse.why_it_matters}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* ============================================================ */}
            {/* 4. WHAT IS UNCLEAR OR NEEDS VERIFICATION */}
            {/* ============================================================ */}
            {(navResponse.what_is_unclear_or_missing || (navResponse.uncertainties && navResponse.uncertainties.length > 0)) && (
              <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
                <div className="bg-amber-600 text-white px-6 py-4 flex items-center gap-2.5">
                  <AlertTriangle className="w-5 h-5 text-amber-200" />
                  <span className="text-xs font-bold uppercase tracking-wider text-amber-200">4. What Is Unclear or Needs Verification</span>
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
                        Specific Factual Gaps to Clarify
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

            {/* ============================================================ */}
            {/* 5. PREPARE FOR THE NEXT STEP */}
            {/* ============================================================ */}
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
              <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <CheckSquare className="w-5 h-5 text-indigo-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">5. Prepare For The Next Step</span>
                </div>
                <span className="text-[11px] font-semibold text-slate-300">
                  Actionable Checklist
                </span>
              </div>

              <div className="p-6 space-y-6">
                {/* Actionable Preparation Checklist */}
                {navResponse.actionable_checklist && navResponse.actionable_checklist.length > 0 && (
                  <div className="space-y-2.5">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Preparation Tasks for Legal Consultation
                    </h4>
                    <ul className="space-y-2.5">
                      {navResponse.actionable_checklist.map((step, idx) => (
                        <li key={idx} className="flex items-start gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                          <span className="leading-relaxed">{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Collapsible Consultation Brief */}
                {navResponse.consultation_brief_markdown && (
                  <div className="pt-2 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={() => setShowBrief(!showBrief)}
                      aria-expanded={showBrief}
                      aria-controls="brief-content-panel"
                      aria-label={showBrief ? "Collapse Professional Consultation Brief" : "Expand Professional Consultation Brief"}
                      className="w-full px-4 py-3 bg-indigo-50/80 hover:bg-indigo-100 text-indigo-950 font-semibold rounded-xl border border-indigo-200/80 text-xs flex items-center justify-between transition shadow-sm focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
                    >
                      <div className="flex items-center gap-2">
                        <ClipboardList className="w-4 h-4 text-indigo-600" aria-hidden="true" />
                        <span>View Professional Consultation Brief</span>
                      </div>
                      {showBrief ? <ChevronUp className="w-4 h-4 text-indigo-600" aria-hidden="true" /> : <ChevronDown className="w-4 h-4 text-indigo-600" aria-hidden="true" />}
                    </button>

                    {showBrief && (
                      <div id="brief-content-panel" role="region" aria-label="Professional Consultation Brief" className="mt-3 bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-medium text-slate-600">
                            Structured factual summary and clause index for your attorney
                          </span>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={handleCopyBrief}
                              aria-label="Copy consultation brief to clipboard"
                              className="text-xs bg-white hover:bg-slate-100 text-slate-700 px-3 py-1.5 rounded-lg border border-slate-300 transition flex items-center gap-1.5 shadow-sm focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
                            >
                              {copiedBrief ? <Check className="w-3.5 h-3.5 text-emerald-600" aria-hidden="true" /> : <Copy className="w-3.5 h-3.5" aria-hidden="true" />}
                              <span>{copiedBrief ? 'Copied' : 'Copy Brief'}</span>
                            </button>
                            <button
                              type="button"
                              onClick={handleDownloadBrief}
                              aria-label="Download consultation brief as Markdown file"
                              className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 shadow-sm font-medium focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
                            >
                              <Download className="w-3.5 h-3.5" aria-hidden="true" />
                              <span>Download .md</span>
                            </button>
                          </div>
                        </div>
                        <div className="bg-white p-4 rounded-lg border border-slate-200 text-xs text-slate-800 font-mono whitespace-pre-wrap max-h-80 overflow-y-auto leading-relaxed">
                          {navResponse.consultation_brief_markdown}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Collapsible Evidence & System Diagnostics Drawer */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <button
                type="button"
                onClick={() => setShowDiagnostics(!showDiagnostics)}
                aria-expanded={showDiagnostics}
                aria-controls="diagnostics-panel"
                aria-label={showDiagnostics ? "Collapse Evidence & System Diagnostics" : "Expand Evidence & System Diagnostics"}
                className="w-full px-6 py-3.5 bg-slate-100/70 hover:bg-slate-100 flex items-center justify-between text-xs font-semibold text-slate-700 transition focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
              >
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-slate-500" aria-hidden="true" />
                  <span>Evidence & System Diagnostics</span>
                </div>
                {showDiagnostics ? <ChevronUp className="w-4 h-4" aria-hidden="true" /> : <ChevronDown className="w-4 h-4" aria-hidden="true" />}
              </button>

              {showDiagnostics && (
                <div id="diagnostics-panel" role="region" aria-label="Evidence and System Diagnostics" className="p-6 border-t border-slate-200 bg-slate-50/50 space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="p-3 bg-white rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold uppercase text-slate-600 block mb-1">Effective Mode</span>
                      <span className="text-xs font-mono font-semibold text-indigo-700">{navResponse.diagnostics.effective_mode}</span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold uppercase text-slate-600 block mb-1">Query Category</span>
                      <span className="text-xs font-mono font-semibold text-slate-700">{navResponse.diagnostics.category}</span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold uppercase text-slate-600 block mb-1">Latency</span>
                      <span className="text-xs font-mono font-semibold text-slate-700">{navResponse.diagnostics.latency_ms} ms</span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold uppercase text-slate-600 block mb-1">Sufficiency Passed</span>
                      <span className={`text-xs font-mono font-semibold ${navResponse.diagnostics.evidence_sufficiency_passed ? 'text-emerald-700' : 'text-amber-700'}`}>
                        {String(navResponse.diagnostics.evidence_sufficiency_passed)}
                      </span>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-600 leading-relaxed pt-2">
                    <p>Telemetry and execution tracing coordinate document grounding, cross-document comparison diffs, external statutory databases, and situation role inference.</p>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

      {/* Paste Modal */}
      {showPasteModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="paste-modal-title">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 id="paste-modal-title" className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FilePlus className="w-4 h-4 text-indigo-600" aria-hidden="true" />
                Paste Agreement Text
              </h3>
              <button
                type="button"
                onClick={() => setShowPasteModal(false)}
                aria-label="Close paste document modal"
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label htmlFor="pasted-doc-title" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Document Title
                </label>
                <input
                  id="pasted-doc-title"
                  type="text"
                  value={pastedTitle}
                  onChange={(e) => setPastedTitle(e.target.value)}
                  className="w-full text-xs bg-white border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g. consulting_agreement.txt"
                />
              </div>

              <div>
                <label htmlFor="pasted-doc-content" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Agreement Text Content
                </label>
                <textarea
                  id="pasted-doc-content"
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
                className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg font-medium transition focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePasteSubmit}
                disabled={isUploading || !pastedContent.trim()}
                className="text-xs bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg font-medium transition flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
              >
                {isUploading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Check className="w-3.5 h-3.5" aria-hidden="true" />}
                Ingest & Attach
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
