# API Reference

Base path: `/api/v1`  
Interactive docs: `http://localhost:8000/docs` (Swagger UI)

All endpoints return JSON. File uploads use `multipart/form-data`. Errors follow FastAPI's default `{"detail": "..."}` format.

---

## Upload

### `POST /assets/upload`

Accepts a file, validates its type, saves it to disk, creates an `AccessibilityAsset` record, and dispatches the processing pipeline.

**Request:** `multipart/form-data`

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file | ✅ | PDF, PPTX, or MP4 |
| `course_id` | string | ❌ | Optional course identifier |

**Accepted MIME types:**
- `application/pdf` → PDF
- `application/vnd.openxmlformats-officedocument.presentationml.presentation` → PPTX
- `video/mp4` → MP4

**Response: 202 Accepted**
```json
{
  "asset_id": "uuid",
  "original_filename": "lecture1.pdf",
  "source_type": "PDF",
  "processing_status": "PENDING",
  "task_id": "celery-task-uuid"
}
```

Use `task_id` to poll processing progress via `GET /jobs/{task_id}/status`.

---

## Jobs

### `GET /jobs/{task_id}/status`

Polls the Celery task for pipeline progress. Reads the current stage from Redis — gives more granular progress than Celery's binary PENDING/SUCCESS states.

**Response:**
```json
{
  "task_id": "...",
  "asset_id": "uuid or null",
  "state": "STARTED",
  "current_stage": "CHECKING",
  "progress_percent": 45,
  "error": null
}
```

**State values:** `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`, `RETRY`  
**Stage values:** `NORMALIZING` (20%), `CHECKING` (45%), `REMEDIATING` (65%), `OUTPUTTING` (85%), `COMPLETE` (100%)

---

## Assets

### `GET /assets`

List assets with pagination and optional filtering.

**Query parameters:**

| Param | Default | Notes |
|---|---|---|
| `page` | 1 | 1-based page number |
| `page_size` | 20 | 1–100 |
| `source_type` | — | Filter: `PDF`, `PPTX`, `MP4` |
| `processing_status` | — | Filter: `PENDING`, `COMPLETE`, `FAILED`, etc. |

**Response:**
```json
{
  "assets": [AssetResponse, ...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### `GET /assets/{asset_id}`

Get a single asset by UUID.

**Response:** `AssetResponse`
```json
{
  "asset_id": "uuid",
  "course_id": "CS101",
  "original_filename": "lecture.pdf",
  "source_type": "PDF",
  "processing_status": "COMPLETE",
  "file_version": 1,
  "created_at": "2026-04-13T10:00:00Z",
  "updated_at": "2026-04-13T10:02:30Z"
}
```

---

## Issues

### `GET /assets/{asset_id}/issues`

List all detected issues for an asset.

**Query parameters:**

| Param | Notes |
|---|---|
| `severity` | Filter: `CRITICAL`, `SERIOUS`, `MODERATE`, `MINOR` |
| `review_status` | Filter: `PENDING`, `APPROVED`, `REJECTED`, `SKIPPED` |

Results are sorted: CRITICAL → SERIOUS → MODERATE → MINOR.

**Response:**
```json
{
  "issues": [IssueResponse, ...],
  "total": 12
}
```

**IssueResponse:**
```json
{
  "issue_id": "uuid",
  "asset_id": "uuid",
  "issue_type": "MISSING_ALT_TEXT",
  "severity": "CRITICAL",
  "location_in_asset": {"slide": 2, "element_id": "slide2_img0"},
  "fix_recommendation": "A bar chart showing Q3 revenue growth...",
  "auto_fixable": true,
  "confidence_score": 0.92,
  "review_status": "PENDING",
  "created_at": "2026-04-13T10:01:00Z"
}
```

### `PATCH /issues/{issue_id}`

Update the review status or fix recommendation for an issue.

**Request body:**
```json
{
  "review_status": "APPROVED",
  "fix_recommendation": "Optional custom text override"
}
```

Both fields are optional. `review_status` must be one of `PENDING`, `APPROVED`, `REJECTED`, `SKIPPED`.

**Response:** Updated `IssueResponse`

---

## Artifacts

### `GET /assets/{asset_id}/artifacts`

List all generated artifacts for an asset.

**Response:** `list[ArtifactResponse]`
```json
[
  {
    "artifact_id": "uuid",
    "asset_id": "uuid",
    "issue_id": "uuid or null",
    "artifact_type": "ALT_TEXT",
    "generation_status": "COMPLETE",
    "storage_location": null,
    "content_snapshot": "A bar chart showing quarterly revenue...",
    "approved_by": null,
    "approved_at": null,
    "created_at": "2026-04-13T10:02:00Z"
  }
]
```

### `GET /artifacts/{artifact_id}/download`

Serves the artifact file. Creates a `DOWNLOAD_ARTIFACT` audit event.

**Response:** File stream (`FileResponse`)  
**Error:** 404 if artifact not found or `storage_location` file missing

### `POST /assets/{asset_id}/artifacts/approve`

Bulk-approves all `COMPLETE` unapproved artifacts for an asset. Use this after the professor has reviewed the review queue.

**Request body:**
```json
{"approved_by": "professor"}
```

**Response:** `list[ArtifactResponse]` — the approved artifacts with `approved_at` set.

After approving artifacts, call `POST /assets/{asset_id}/generate-outputs` (if implemented) or trigger `generate_outputs` task to rebuild the tagged PDF with approved content.

---

## Health

### `GET /health`

```json
{"status": "ok"}
```
