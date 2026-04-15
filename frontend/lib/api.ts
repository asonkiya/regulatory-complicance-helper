import type {
  Artifact,
  AssetListResponse,
  AssetUploadResponse,
  Asset,
  Issue,
  IssueListResponse,
  JobStatus,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Assets ──────────────────────────────────────────────────────────────────

export async function uploadAsset(
  file: File,
  courseId?: string
): Promise<AssetUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  if (courseId) form.append("course_id", courseId);

  const res = await fetch(`${API_BASE}/api/v1/assets/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Upload failed ${res.status}: ${body}`);
  }
  return res.json() as Promise<AssetUploadResponse>;
}

export async function listAssets(params?: {
  page?: number;
  page_size?: number;
  source_type?: string;
  processing_status?: string;
}): Promise<AssetListResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.source_type) qs.set("source_type", params.source_type);
  if (params?.processing_status)
    qs.set("processing_status", params.processing_status);
  return request<AssetListResponse>(`/assets?${qs}`);
}

export async function getAsset(assetId: string): Promise<Asset> {
  return request<Asset>(`/assets/${assetId}`);
}

export function getAssetFileUrl(assetId: string): string {
  return `${API_BASE}/api/v1/assets/${assetId}/file`;
}

// ── Issues ──────────────────────────────────────────────────────────────────

export async function listIssues(
  assetId: string,
  params?: { severity?: string; review_status?: string }
): Promise<IssueListResponse> {
  const qs = new URLSearchParams();
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.review_status) qs.set("review_status", params.review_status);
  return request<IssueListResponse>(`/assets/${assetId}/issues?${qs}`);
}

export async function updateIssue(
  issueId: string,
  body: { review_status?: string; fix_recommendation?: string }
): Promise<Issue> {
  return request<Issue>(`/issues/${issueId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ── Artifacts ────────────────────────────────────────────────────────────────

export async function listArtifacts(assetId: string): Promise<Artifact[]> {
  return request<Artifact[]>(`/assets/${assetId}/artifacts`);
}

export function getArtifactDownloadUrl(artifactId: string): string {
  return `${API_BASE}/api/v1/artifacts/${artifactId}/download`;
}

export async function bulkApproveArtifacts(
  assetId: string,
  approvedBy = "professor"
): Promise<Artifact[]> {
  return request<Artifact[]>(`/assets/${assetId}/artifacts/approve`, {
    method: "POST",
    body: JSON.stringify({ approved_by: approvedBy }),
  });
}

// ── Jobs ─────────────────────────────────────────────────────────────────────

export async function getJobStatus(taskId: string): Promise<JobStatus> {
  return request<JobStatus>(`/jobs/${taskId}/status`);
}
