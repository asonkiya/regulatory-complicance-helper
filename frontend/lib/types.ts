// Mirrors Pydantic schemas from the FastAPI backend

export type SourceType = "PPTX" | "PDF" | "MP4";
export type ProcessingStatus =
  | "PENDING"
  | "NORMALIZING"
  | "CHECKING"
  | "REMEDIATING"
  | "OUTPUTTING"
  | "COMPLETE"
  | "FAILED";
export type Severity = "CRITICAL" | "SERIOUS" | "MODERATE" | "MINOR";
export type ReviewStatus = "PENDING" | "APPROVED" | "REJECTED" | "SKIPPED";
export type ArtifactType =
  | "ALT_TEXT"
  | "TRANSCRIPT"
  | "CAPTIONS_VTT"
  | "CAPTIONS_SRT"
  | "TAGGED_PDF"
  | "ACCESSIBILITY_REPORT";

export interface Asset {
  asset_id: string;
  course_id: string | null;
  original_filename: string;
  source_type: SourceType;
  processing_status: ProcessingStatus;
  file_version: number;
  created_at: string;
  updated_at: string;
}

export interface AssetUploadResponse {
  asset_id: string;
  original_filename: string;
  source_type: SourceType;
  processing_status: ProcessingStatus;
  task_id: string;
}

export interface AssetListResponse {
  assets: Asset[];
  total: number;
  page: number;
  page_size: number;
}

export interface Issue {
  issue_id: string;
  asset_id: string;
  issue_type: string;
  severity: Severity;
  location_in_asset: Record<string, unknown> | null;
  fix_recommendation: string | null;
  auto_fixable: boolean;
  confidence_score: number | null;
  review_status: ReviewStatus;
  created_at: string;
}

export interface IssueListResponse {
  issues: Issue[];
  total: number;
}

export interface Artifact {
  artifact_id: string;
  asset_id: string;
  issue_id: string | null;
  artifact_type: ArtifactType;
  generation_status: "PENDING" | "COMPLETE" | "FAILED";
  storage_location: string | null;
  content_snapshot: string | null;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface JobStatus {
  task_id: string;
  asset_id: string | null;
  state: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY";
  current_stage: string | null;
  progress_percent: number | null;
  error: string | null;
}

export interface AccessibilityReport {
  asset_id: string;
  score: number;
  total_issues: number;
  issues_by_severity: Record<Severity, number>;
  auto_fixed_count: number;
  pending_review_count: number;
  wcag_criteria_map: Record<string, string[]>;
}
