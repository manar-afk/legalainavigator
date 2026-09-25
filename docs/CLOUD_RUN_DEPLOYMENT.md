# Google Cloud Run Production Deployment & Security Hardening Guide

This guide provides comprehensive instructions to deploy the Legal Information Navigator backend to Google Cloud Run in accordance with the Phase 10 Revision 2 production architecture and enterprise security standards.

---

## 1. Prerequisites

1. **Google Cloud SDK (`gcloud`)** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
2. **Enabled Google Cloud Services**:
   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
   ```
3. **Secret Manager Setup (Recommended over plain environment variables)**:
   Store your Gemini API key in Google Cloud Secret Manager:
   ```bash
   echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
   ```
   Grant the Cloud Run service identity access to read the secret:
   ```bash
   PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
   gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
       --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```

---

## 2. Container Security Hardening (Revision 2 Specification)

The Legal Information Navigator container implements the following security safeguards:

1. **Non-Root Execution User**:
   - Container executes strictly under `USER appuser` (UID 10001, GID 10001).
   - Root privilege escalation is prevented inside the container namespace.
2. **Pinned Dependencies**:
   - Python dependencies are strictly pinned in `backend/requirements.txt` to eliminate supply chain drift.
3. **Optimized Build Context (`.dockerignore`)**:
   - VCS directories (`.git`), credentials (`.env*`), test caches (`.pytest_cache`), and frontend sources are excluded from the container build context.
4. **Sanitized Logging Architecture**:
   - Log streams contain operational telemetry, latency, and status codes.
   - PII, full uploaded contract text, and sensitive user situation narratives are never logged to `stdout`/`stderr`.
5. **Dynamic Port Binding**:
   - Uvicorn dynamically binds to `0.0.0.0:${PORT:-8000}`, seamlessly adopting the Cloud Run assigned `$PORT` (default 8080).
6. **Evaluation Endpoint Security**:
   - The `/api/evaluation/run` endpoint is protected by `ENVIRONMENT=production`. In production, it is disabled unless explicitly enabled via `ENABLE_EVALUATION_ENDPOINT=true` and an authorized `X-Evaluation-Key` header is provided.

---

## 3. Production Deployment Commands

### Option A: Build and Deploy via Cloud Build & Secret Manager (Recommended)

```bash
# 1. Submit hardened container build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/legal-navigator-backend:latest .

# 2. Deploy to Cloud Run with Secret Manager and non-root execution
gcloud run deploy legal-navigator-backend \
    --image gcr.io/YOUR_PROJECT_ID/legal-navigator-backend:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-secrets="GEMINI_API_KEY=projects/YOUR_PROJECT_ID/secrets/GEMINI_API_KEY:latest" \
    --set-env-vars="ENVIRONMENT=production,ENABLE_EVALUATION_ENDPOINT=true,EVALUATION_KEY=YOUR_SECURE_EVAL_KEY,USE_VERTEX_AI=false" \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 60s
```

### Option B: Automated Scripts

- **Linux / macOS**:
  ```bash
  chmod +x scripts/deploy_cloud_run.sh
  ./scripts/deploy_cloud_run.sh
  ```
- **Windows PowerShell**:
  ```powershell
  .\scripts\deploy_cloud_run.ps1 -ProjectId "YOUR_PROJECT_ID" -Region "us-central1"
  ```

---

## 4. Post-Deployment Verification

Once deployed, Google Cloud Run returns a service URL (e.g. `https://legal-navigator-backend-xyz.a.run.app`).

1. **Health Check Probe**:
   ```bash
   curl -s https://YOUR_SERVICE_URL/health
   # Expected response: {"status":"healthy","version":"1.0.0", ...}
   ```

2. **Execute 14-Archetype Benchmark Evaluation**:
   ```bash
   curl -s -H "X-Evaluation-Key: YOUR_SECURE_EVAL_KEY" https://YOUR_SERVICE_URL/api/evaluation/run
   # Expected response: BenchmarkScorecard with 14/14 cases passed, 0.0% hallucination rate
   ```

3. **Verify Evaluation Security Gate (Without Key)**:
   ```bash
   curl -s -i https://YOUR_SERVICE_URL/api/evaluation/run
   # Expected response: HTTP 401 Unauthorized (when key required) or 403 Forbidden (when disabled)
   ```

4. **Interactive API Documentation**:
   Navigate to `https://YOUR_SERVICE_URL/docs` in your browser.
