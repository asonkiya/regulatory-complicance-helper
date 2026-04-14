# Database Models

All models live in `backend/app/models/` and inherit from `Base` (SQLAlchemy `DeclarativeBase`). PostgreSQL is the only supported database.

## AccessibilityAsset

**File:** `models/asset.py`  
The root entity. Created on file upload, updated throughout the pipeline.

| Column | Type | Notes |
|---|---|---|
| `asset_id` | UUID (PK) | Auto-generated |
| `course_id` | str | Optional course identifier |
| `original_filename` | str | Uploaded filename |
| `source_type` | str | `PPTX` \| `PDF` \| `MP4` |
| `source_location` | str | Absolute path to original file |
| `file_version` | int | Starts at 1 |
| `normalized_content_ref` | str | Path to `normalized.json` |
| `processing_status` | str | See status flow below |
| `created_at` | datetime (UTC) | |
| `updated_at` | datetime (UTC) | Auto-updated |

**Processing status flow:**
```
PENDING → NORMALIZING → CHECKING → REMEDIATING → OUTPUTTING → COMPLETE
                                                              → FAILED (from any stage)
```

**Relationships:** `issues[]`, `artifacts[]`, `audit_events[]` (all cascade delete)

---

## AccessibilityIssue

**File:** `models/issue.py`  
One row per detected violation. Created in bulk by `check_task`.

| Column | Type | Notes |
|---|---|---|
| `issue_id` | UUID (PK) | |
| `asset_id` | UUID (FK) | Cascade delete |
| `issue_type` | str | See [checkers.md](checkers.md) for full list |
| `severity` | str | `CRITICAL` \| `SERIOUS` \| `MODERATE` \| `MINOR` |
| `location_in_asset` | JSONB | Schema varies by issue type |
| `fix_recommendation` | str | Human-readable suggestion; updated by remediators |
| `auto_fixable` | bool | If True, remediate_task acts on it |
| `confidence_score` | float | 0.0–1.0; None = certain |
| `review_status` | str | `PENDING` \| `APPROVED` \| `REJECTED` \| `SKIPPED` |
| `created_at` | datetime (UTC) | |

**Review status semantics:**
- `APPROVED` — professor has accepted the fix; counts as resolved in score
- `SKIPPED` — professor chose to ignore; counts as resolved in score
- `REJECTED` — professor rejected the AI fix; deduction stays
- `PENDING` — awaiting review; deduction stays

**Relationships:** `asset`, `artifacts[]`

---

## GeneratedArtifact

**File:** `models/artifact.py`  
AI-generated outputs linked to assets and optionally to the issue they remediate.

| Column | Type | Notes |
|---|---|---|
| `artifact_id` | UUID (PK) | |
| `asset_id` | UUID (FK) | Cascade delete |
| `issue_id` | UUID (FK, nullable) | Set null on issue delete |
| `artifact_type` | str | See types below |
| `generation_status` | str | `PENDING` \| `COMPLETE` \| `FAILED` |
| `storage_location` | str | Absolute path (for file artifacts) |
| `content_snapshot` | str | Inline text (for small artifacts like alt text) |
| `approved_by` | str | Username of approver |
| `approved_at` | datetime | Set when professor approves |
| `created_at` | datetime (UTC) | |

**Artifact types:**

| Type | Content | Storage |
|---|---|---|
| `ALT_TEXT` | Generated alt text string | `content_snapshot` |
| `DOCUMENT_TITLE` | Generated PDF title string | `content_snapshot` |
| `CAPTIONS_VTT` | WebVTT caption file | `storage_location` |
| `CAPTIONS_SRT` | SubRip caption file | `storage_location` |
| `TAGGED_PDF` | Accessibility-tagged PDF | `storage_location` |
| `ACCESSIBILITY_REPORT` | JSON score report | `storage_location` |

**Approval:** `approved_at` being set is the signal used by `tagged_pdf_generator` to include an artifact's content in the output PDF. The bulk-approve endpoint (`POST /assets/{id}/artifacts/approve`) sets `approved_at` on all `COMPLETE` unapproved artifacts at once.

---

## AuditEvent

**File:** `models/audit.py`  
Append-only log of user actions.

| Column | Type | Notes |
|---|---|---|
| `event_id` | UUID (PK) | |
| `actor` | str | Username or system identifier |
| `action` | str | e.g. `DOWNLOAD_ARTIFACT`, `APPROVE_ARTIFACT` |
| `asset_id` | UUID (FK, nullable) | Set null on asset delete |
| `artifact_id` | UUID (nullable) | For artifact-level actions |
| `timestamp` | datetime (UTC) | |
| `before_state` | JSONB | Snapshot before change |
| `after_state` | JSONB | Snapshot after change |

Currently written by the `download_artifact` endpoint. Can be extended for any action that needs an audit trail.
