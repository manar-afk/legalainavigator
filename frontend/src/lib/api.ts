import { HealthStatus, DocumentMeta, IntentClassification, UserSituation, GroundedAnswer } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) {
    throw new Error(`Failed to fetch system health: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchLoadedDocuments(): Promise<DocumentMeta[]> {
  const res = await fetch(`${API_BASE_URL}/documents`);
  if (!res.ok) {
    throw new Error(`Failed to fetch documents: ${res.statusText}`);
  }
  return res.json();
}

export async function loadSampleDocument(sampleName: string = "residential_lease_agreement.txt"): Promise<DocumentMeta> {
  const res = await fetch(`${API_BASE_URL}/documents/load-sample?sample_name=${encodeURIComponent(sampleName)}`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to load sample document: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadDocumentFile(file: File): Promise<DocumentMeta> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Failed to upload document: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadTextDocument(content: string, filename: string = "document.txt"): Promise<DocumentMeta> {
  const res = await fetch(`${API_BASE_URL}/documents/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, filename }),
  });
  if (!res.ok) {
    throw new Error(`Failed to upload text document: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteDocument(docId: string): Promise<boolean> {
  const res = await fetch(`${API_BASE_URL}/documents/${docId}`, {
    method: 'DELETE',
  });
  return res.ok;
}

export async function classifyQuery(
  query: string,
  docIds: string[] = [],
  situation?: UserSituation,
  jurisdiction?: string
): Promise<IntentClassification> {
  const res = await fetch(`${API_BASE_URL}/mode/classify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      doc_ids: docIds,
      situation,
      jurisdiction,
    }),
  });

  if (!res.ok) {
    throw new Error(`Mode classification failed: ${res.statusText}`);
  }
  return res.json();
}

export async function executeQuery(
  query: string,
  docIds: string[] = [],
  situation?: UserSituation,
  jurisdiction?: string
): Promise<GroundedAnswer> {
  const res = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      doc_ids: docIds,
      situation,
      jurisdiction,
    }),
  });

  if (!res.ok) {
    throw new Error(`Query execution failed: ${res.statusText}`);
  }
  return res.json();
}

export async function compareDocuments(
  docIdA: string,
  docIdB?: string,
  focusDimension?: string,
  coApplicableOverride?: boolean
): Promise<import('./types').ComparisonResult> {
  const res = await fetch(`${API_BASE_URL}/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      doc_id_a: docIdA,
      doc_id_b: docIdB,
      focus_dimension: focusDimension,
      co_applicable_override: coApplicableOverride,
    }),
  });

  if (!res.ok) {
    throw new Error(`Document comparison failed: ${res.statusText}`);
  }
  return res.json();
}

export async function generateActionableOutputs(
  req: import('./types').ActionableGenerateRequest
): Promise<import('./types').ActionableOutputsContainer> {
  const res = await fetch(`${API_BASE_URL}/actionable/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    throw new Error(`Actionable outputs generation failed: ${res.statusText}`);
  }
  return res.json();
}

export async function navigateLegalContext(
  req: import('./types').NavigateRequest
): Promise<import('./types').UnifiedNavigationResponse> {
  const res = await fetch(`${API_BASE_URL}/navigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    throw new Error(`Navigation failed: ${res.statusText}`);
  }
  return res.json();
}


