# Legal Information Navigator

> **"Understand, compare, and navigate legal documents and information — grounded in evidence and authoritative legal sources."**

A GenAI-powered solution engineered to make complex legal information accessible, navigable, and actionable for everyday users based on their specific situation—grounded strictly in verified evidence, without replacing professional legal counsel.

---

## 🎯 Problem Statement Alignment

### The Core Challenge
Legal information can often be complex, difficult to understand, and challenging to navigate without professional assistance. **Legal Information Navigator** makes legal information and basic legal assistance accessible, transparent, and actionable by empowering users to **understand**, **compare**, and **navigate** legal documents and information grounded in evidence.

### Complete Coverage of Potential Use Cases

| # | Potential Use Case | Implemented System Capability | Primary Endpoint / UI Action |
|---|---|---|---|
| **1** | **Simplifying complex legal documents** | Plain-language synthesis transforms dense contract clauses into easy-to-understand summaries with verified textual provenance. | `POST /api/v1/navigate` (`what_this_means_in_plain_language`) / *Simplify Document* preset |
| **2** | **Comparing contracts, agreements, or policies** | Semantic diff engine detecting material amendments, express deletions, additions, and co-applicability contradictions across agreements. | `POST /api/compare` / *Compare Agreements* preset |
| **3** | **Highlighting important clauses, obligations, risks, or inconsistencies** | Dedicated **Covenants & Risks Matrix** extracting party-specific affirmative covenants, negative restrictions, deadlines, and review flags. | `POST /api/v1/navigate` (`covenants_matrix`) / *Audit Clauses & Risks* preset |
| **4** | **Answering questions based on provided legal documents** | Evidence-gated QA answering strictly from verified chunk spans [start_char:end_char] with explicit abstention when information is absent. | `POST /api/query` & `POST /api/v1/navigate` (`sources`) |
| **5** | **Helping users understand their options and potential next steps** | Substantive situational translation presenting actionable pathways, legal prerequisites, and consequences of choices. | `POST /api/v1/navigate` (`why_it_matters`) / *Options & Next Steps* preset |
| **6** | **Generating summaries, checklists, or other actionable outputs** | Synthesizes chronological checklists, procedural requirements, document gathering tasks, and markdown summaries. | `POST /api/v1/navigate` (`actionable_checklist`) / *Action Checklist* preset |
| **7** | **Helping users prepare information or questions for a legal professional** | Generates an attorney-ready **Consultation Brief** (.md export) including case overview, clause index, factual gaps, and curated questions for counsel. | `POST /api/v1/navigate` (`consultation_brief_markdown`) / *Prepare for Attorney* preset |

---

## ⚡ Efficiency & Resource Utilization

The codebase is optimized for optimal **time and memory utilization**:

1. **Algorithmic $O(N)$ Retrieval**:
   - Precomputes term IDFs and corpus average length once outside the scoring loop, eliminating $O(N^2)$ inside-loop recalculations.
   - Tokenizes and caches chunk tokens at module ingestion time using precompiled regular expressions.
2. **Memory-Bounded Document Store (`InMemoryDocumentStore`)**:
   - Uses `collections.OrderedDict` with LRU eviction capped at `MAX_DOCUMENTS_IN_MEMORY` (default 50) to prevent unbounded memory growth.
   - Eliminates redundant in-memory storage of uncompressed binary files, maintaining only authentic text representations and SHA-256 hashes.
3. **Multi-Tier Query & Navigation Response Cache (`FastLRUResponseCache`)**:
   - Thread-safe LRU response caching for identical document sets and queries, delivering sub-millisecond retrieval (average benchmark latency: **4.1 ms**, median **2.6 ms**).
   - Automatic cache invalidation upon document uploads, deletions, or updates.
4. **Precompiled Regex Architecture**:
   - All prompt-injection, delimiter breakout, currency, duration, and notice patterns are precompiled at module load time to eliminate regex compilation overhead.
5. **Frontend Workspace Caching**:
   - Prevents duplicate uploads and redundant API network roundtrips when files or sample agreements are already loaded in the workspace.

---

## 🔒 Security Architecture & Vulnerability Mitigation

The application adheres to OWASP secure development practices:

1. **Path Traversal Defense (CWE-22)**:
   - All uploaded filenames and sample document requests are sanitized with `os.path.basename` and strict directory boundary validation (`os.path.commonpath`), completely preventing directory traversal attacks.
2. **Resource Consumption & DoS Prevention (CWE-400)**:
   - Strict upload limits enforced at the stream layer: `MAX_UPLOAD_SIZE_BYTES` (15 MB) and `MAX_TEXT_CONTENT_CHARS` (1,000,000 characters).
   - Input character limits on user queries (5,000 chars) and situation narratives (20,000 chars) with null-byte (`\x00`) elimination.
3. **Safe CORS Policy (CWE-942)**:
   - Explicit origin filtering; wildcards (`*`) are disallowed when `allow_credentials=True`.
4. **Comprehensive HTTP Security Headers**:
   - Enforces `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Strict-Transport-Security`, and strict `Referrer-Policy` across both FastAPI backend and Next.js frontend.
5. **Adversarial Prompt-Injection Defense**:
   - Scans incoming document text for injection and delimiter breakouts (`<UNTRUSTED_DOCUMENT_DATA>`), neutralizes escape tags, and strictly marks user-supplied data as passive evidence.
6. **Definitive Legal Statement Softening**:
   - Automated guardrail filter transforms conclusory assertions into neutral informational explanations, upholding ethical legal boundaries.

---

## ♿ Accessibility (WCAG 2.1 AA Compliance)

- **Form Controls & Labels**: All inputs, textareas, and select elements feature permanent visible `<label>` tags with matching `htmlFor` / `id` bindings.
- **ARIA Semantics**: Comprehensive ARIA landmark roles (`role="dialog"`, `role="region"`, `role="group"`, `aria-modal="true"`, `aria-expanded`, `aria-controls`, `aria-label`).
- **Contrast Ratios**: Verified text contrast exceeding 4.5:1 for standard text and 3:1 for large text across all color themes.
- **Keyboard Navigation**: Explicit focus rings (`focus-visible:ring-2 focus-visible:ring-indigo-500`) and skip navigation link (`#main-content`).

---

## 📊 Verification & Evaluation Benchmark

### 1. Pytest Test Suite
```text
======================= 168 passed, 1 warning in 3.01s ========================
```
- **168 / 168 tests passing (100%)** across all functional phases, security checks, and neutrality invariants.

### 2. 14-Archetype Benchmark Evaluation (`test_suite.py`)
```text
================================================================================
RESULTS: 14/14 PASSED (100.0%)
HALLUCINATION RATE: 0.0%
AVERAGE LATENCY: 4.1 ms (Median: 2.6 ms, p95: 8.1 ms)
================================================================================
```
- **14 / 14 scenarios passing (100%)** with **0.0% hallucination rate** across Simple Factual, Multi-Clause, Situation-Specific, Document Comparison, External Law, and Adversarial Injection benchmarks.

### 3. Production Build
```text
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Generating static pages (4/4) ...
 ✓ Generating static pages (4/4)
```

---

## 🚀 Quickstart Guide

### 1. Backend (FastAPI + Python 3.13)
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
- Backend API: `http://localhost:8000`
- Swagger API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/health`

### 2. Frontend (Next.js 14 + Tailwind CSS)
```bash
cd frontend
npm install
npm run dev # or npm run build && npm run start
```
- Web Application: `http://localhost:3000`

### 3. Run Automated Pytest Regression Suite
```bash
python -m pytest backend/tests -v
```

### 4. Run 14-Scenario Benchmark Evaluation Suite
```bash
python backend/app/evaluation/test_suite.py
```
