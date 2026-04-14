# Tagged PDF Generator

**File:** `backend/app/processing/output_generators/tagged_pdf_generator.py`

Produces `output_tagged.pdf` — a copy of the original PDF with accessibility metadata injected. Called by `output_task` in the final pipeline stage, but only runs if at least one artifact has been approved.

## What it injects

| What | How | Condition |
|---|---|---|
| `/MarkInfo/Marked = True` | pikepdf dict on PDF root | Always |
| `/Lang = "en-US"` | pikepdf string on PDF root | Always |
| XMP `dc:title` | pikepdf metadata context manager | If not already set |
| `/Alt` on image XObjects | pikepdf string on XObject | Per approved alt text |

This is MVP-scoped. It does **not** rebuild the structure tree or inject heading tags — those require full structure tree traversal which is out of scope.

## How alt text injection works

The normalizer extracts each embedded image's PDF **xref number** and stores it in `NormalizedElement.extra["xref"]`. The generator uses this to match approved alt text to the correct image XObject:

```
approved ALT_TEXT artifacts
    → {element_id: alt_text}            (from DB)
    → load normalized.json
    → match element_id to element.extra["xref"]
    → {xref: alt_text}                  (int key)
    → iterate pdf.pages → XObjects
    → xobj_ref.objgen[0] == xref?
    → inject xobj["/Alt"] = alt_text
```

This correctly handles PDFs with multiple images — the old MVP approach only worked when exactly one alt text existed.

## Document title

Priority order for the title injected into XMP `dc:title`:
1. Approved `DOCUMENT_TITLE` artifact (Claude-generated)
2. Original filename (fallback)

The generator checks whether a title is already set before overwriting, so manually-titled PDFs are not silently renamed.

## Output path

`{STORAGE_BASE_PATH}/{asset_id}/output_tagged.pdf`

A `GeneratedArtifact` row with `artifact_type="TAGGED_PDF"` points to this file. Professors download it via `GET /artifacts/{artifact_id}/download`.

## Limitations (known, intentional)

- **No structure tree creation** for untagged PDFs. `/MarkInfo/Marked = True` is set, but without an actual `/StructTreeRoot` this does not make the PDF truly tagged. A proper implementation would require building H1/H2 paragraph elements, which pikepdf supports in principle but is high-risk for existing content.
- **Language is hardcoded to `en-US`**. Multi-language document support is not implemented.
- **No reading order correction.** Content stream order is unchanged.
- **Only image XObjects are processed** — inline images (rare) are not handled.
