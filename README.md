# Legal Information Navigator

A GenAI-powered solution engineered to make complex legal information accessible, navigable, and actionable for everyday users based on their specific situation—grounded strictly in evidence, without replacing professional legal counsel.

---

## Key Capabilities

1. **Situation-Aware Guidance**: The user explains what is happening in natural language (e.g. *"My landlord wants me to leave in 15 days"*), and the system retrieves the specific provisions that matter to *their* situation.
2. **Three Operational Modes**:
   - **Mode 1: Document-Only Q&A**: Web retrieval is OFF by default. If questions require statutory or external law, the system dynamically reclassifies to Mode 2.
   - **Mode 2: Document + External Law**: Uploaded contract provisions mapped against governing statutes with conditional authoritative retrieval.
   - **Mode 3: General / No-Document Legal Information**: Explains legal concepts in plain language without requiring a document, retrieving and citing official statutes when jurisdiction-dependent.
3. **Strict 4-Tier Knowledge Hierarchy**:
   - Level 1: User-Provided Documents (Primary source for contract terms)
   - Level 2: User-Provided Facts (Treated as subjective assertions)
   - Level 3: Authoritative External Legal Sources (Official statutes, gazettes, codes)
   - Level 4: General Model Knowledge (Clearly distinguished; no hallucinations)
4. **Missing Information Engine**: Pre-reasoning gatekeeper identifies missing factual prerequisites rather than guessing.
5. **Prompt-Injection Defense**: Treats uploaded documents strictly as untrusted data in isolated containers.
6. **Actionable Outputs for Preparation**: Generates structured consultation briefs for legal advocates, timelines, and checklists.

---

## Quickstart Guide

### 1. Backend (FastAPI + Python 3.13)
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
Backend API will be accessible at: `http://localhost:8000`  
Swagger API Documentation: `http://localhost:8000/docs`

### 2. Frontend (Next.js 14 + Tailwind CSS)
```bash
cd frontend
npm.cmd install
npm.cmd run dev
```
Frontend Web UI will be accessible at: `http://localhost:3000`

### 3. Run Automated Unit Tests
```bash
python -m pytest backend/tests -v
```
