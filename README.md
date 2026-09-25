# Legal Information Navigator

A GenAI-powered solution engineered to make complex legal information accessible, navigable, and actionable for everyday users based on their specific situation—grounded strictly in evidence, without replacing professional legal counsel.

---

## Key Capabilities

1. **Situation-Aware Guidance**: The user explains what is happening in natural language (e.g. *"My landlord wants me to leave in 15 days"*), and the system retrieves the specific provisions that matter to *their* situation.
2. **Unified Navigation Orchestrator (`POST /api/v1/navigate`)**:
   - Seamless single-entrypoint that coordinates document grounding, cross-document comparison, external statutory framework retrieval, and actionable preparation synthesis without exposing internal phase machinery to the user.
   - Internal execution modes (Document-Only, Document + External Law, General Q&A) operate under the hood, with telemetry isolated in an expandable diagnostics drawer.
3. **Evidence-Bound Dynamic Extraction**:
   - 4-stage verification pipeline: Candidate $\to$ exact source-span verification $\to$ semantic query association $\to$ provenance $\to$ grounded claim.
   - Differentiates semantic roles (salary vs. joining bonus, rent vs. deposit, termination notice vs. default cure).
4. **Strict 4-Tier Knowledge Hierarchy**:
   - Level 1: User-Provided Documents (Primary source for contract terms)
   - Level 2: User-Provided Facts (Treated as subjective assertions)
   - Level 3: Authoritative External Legal Sources (Official statutes, gazettes, codes)
   - Level 4: General Model Knowledge (Clearly distinguished; zero fabricated claims)
5. **Actionable Outputs & Professional Briefs**:
   - Generates attorney consultation briefs, document-described covenants matrices, and bounded investigative checklists.

---

## Quickstart Guide

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

### 3. Run Automated Pytest Regression Suite (168 Tests)
```bash
python -m pytest backend/tests -v
```

### 4. Run Benchmark Evaluation Suite (14 Scenarios, 138 Assertions)
```bash
cd backend
python -c "from app.evaluation.runner import EvaluationRunner; runner = EvaluationRunner(); print(runner.run_all().to_markdown())"
```
