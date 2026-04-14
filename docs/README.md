# Accessibility Copilot — Documentation

Ingests university course materials (PPTX, PDF, MP4), detects Section 508 / WCAG 2.0 AA violations, generates AI-powered fixes via Claude, and presents a professor-facing review queue with downloadable remediated outputs.

## Docs index

| Doc | What it covers |
|---|---|
| [architecture.md](architecture.md) | System overview, pipeline stages, storage layout, Celery queues |
| [normalizers.md](normalizers.md) | NormalizedDocument data model; PPTX, PDF, video normalizers |
| [checkers.md](checkers.md) | All issue types, severities, WCAG mappings, checker logic |
| [remediators.md](remediators.md) | Alt text, captions, document title generation via Claude |
| [models.md](models.md) | Database schema — Asset, Issue, Artifact, AuditEvent |
| [api.md](api.md) | REST API endpoint reference |
| [tagged_pdf_generator.md](tagged_pdf_generator.md) | How the output PDF is built; alt text xref matching; known limits |
| [score_calculator.md](score_calculator.md) | Scoring formula and issue weights |
| [claude_service.md](claude_service.md) | Claude API wrapper — prompts, retries, response parsing |
| [development.md](development.md) | Local setup, running tests, migrations, project structure |

## Five-minute orientation

1. A file is uploaded → `POST /api/v1/assets/upload` → `AccessibilityAsset` created
2. A Celery chain runs: **normalize → check → remediate → output**
3. **Normalize** converts the file to `NormalizedDocument` (JSON on disk)
4. **Check** runs pure checker functions against the document; issues written to Postgres
5. **Remediate** calls Claude for `auto_fixable` issues; artifacts written to Postgres
6. **Output** calculates score + generates tagged PDF
7. Frontend polls `GET /jobs/{task_id}/status` for progress, then shows issues via `GET /assets/{id}/issues`
8. Professor reviews, approves/rejects fixes, downloads output

## Issue type quick reference

| Type | Severity | Auto-fixed | Source |
|---|---|---|---|
| MISSING_ALT_TEXT | CRITICAL | ✅ Claude vision | PPTX, PDF |
| MISSING_CAPTIONS | CRITICAL | ✅ faster-whisper + Claude | MP4 |
| UNTAGGED_PDF | CRITICAL | ✅ tagged PDF generator | PDF |
| MISSING_SLIDE_TITLE | SERIOUS | ❌ | PPTX |
| LOW_CONTRAST | SERIOUS | ❌ | PPTX |
| MISSING_HEADING_STRUCTURE | SERIOUS | ❌ | PDF |
| MISSING_LINK_TEXT | SERIOUS | ❌ | PDF |
| MISSING_TABLE_HEADERS | SERIOUS | ❌ | PDF |
| INADEQUATE_ALT_TEXT | SERIOUS | ✅ Claude vision | PPTX, PDF |
| MISSING_DOCUMENT_TITLE | MODERATE | ✅ Claude text | PDF |
| MISSING_LANGUAGE | MODERATE | ✅ tagged PDF generator | PDF |
| LOW_OCR_CONFIDENCE | SERIOUS | ❌ | PDF (scanned) |
| CONTRAST_UNVERIFIABLE | MINOR | ❌ | PPTX |
