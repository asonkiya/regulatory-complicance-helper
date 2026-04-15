# PDF Accessibility Issues

All currently implemented accessibility checks for PDF documents, their severity, and remediation status.

## Auto-Fixable Issues

These issues have AI-powered remediators that generate fixes automatically.

### MISSING_ALT_TEXT
- **Severity:** CRITICAL
- **WCAG:** 1.1.1 Non-text Content (Level A)
- **Score Deduction:** 20 points
- **Detects:** Images on PDF pages with no alt text
- **Remediation:** Claude vision generates a descriptive alt text using the image and surrounding page context

### INADEQUATE_ALT_TEXT
- **Severity:** SERIOUS
- **WCAG:** 1.1.1 Non-text Content (Level A)
- **Score Deduction:** 5 points
- **Detects:** Images with generic or insufficient alt text (e.g. "image", "fig.png", filenames, text under 3 characters)
- **Remediation:** Claude vision replaces the generic text with a meaningful description

### UNTAGGED_PDF
- **Severity:** CRITICAL
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **Score Deduction:** 15 points
- **Detects:** PDFs lacking accessibility structure tags (no `/MarkInfo /Marked` in the catalog)
- **Remediation:** Tagged PDF generator injects `/MarkInfo`, `/Lang`, image `/Alt` attributes, and XMP title

### MISSING_LANGUAGE
- **Severity:** MODERATE
- **WCAG:** 3.1.1 Language of Page (Level A)
- **Score Deduction:** 5 points
- **Detects:** PDF document missing the `/Lang` property in the catalog
- **Remediation:** Tagging process adds `/Lang "en-US"` to the PDF catalog

### MISSING_DOCUMENT_TITLE
- **Severity:** MODERATE
- **WCAG:** 2.4.2 Page Titled (Level A)
- **Score Deduction:** 6 points
- **Detects:** Tagged PDFs without a descriptive document title (only flagged on tagged PDFs; untagged PDFs are covered by UNTAGGED_PDF)
- **Remediation:** Claude generates a title from the filename and first-page text, injected into XMP metadata

## Manual-Review Issues

These issues are flagged with a recommendation but require the professor to fix them.

### MISSING_LINK_TEXT
- **Severity:** SERIOUS
- **WCAG:** 2.4.4 Link Purpose (Level A)
- **Score Deduction:** 8 points
- **Detects:** Hyperlinks with ambiguous or missing text — "click here", "read more", "link", raw URLs, or empty link text
- **Recommendation:** Replace link text with a description of the destination

### MISSING_TABLE_HEADERS
- **Severity:** SERIOUS
- **WCAG:** 1.3.1 Info and Relationships (Level A)
- **Score Deduction:** 8 points
- **Detects:** Tables with 2+ rows that lack a designated header row (heuristic detection, confidence 0.75)
- **Recommendation:** Mark the first row as a header row with proper table header tags

### MISSING_HEADING_STRUCTURE
- **Severity:** SERIOUS
- **WCAG:** 1.3.1 Info and Relationships / 2.4.6 Headings and Labels (Level A/AA)
- **Score Deduction:** 8 points
- **Detects:** Untagged PDFs with text that appears to be headings (font size >= 1.5x body average) but lacks semantic heading tags
- **Recommendation:** Add semantic heading tags (H1, H2, etc.) to structure the document

### LOW_OCR_CONFIDENCE
- **Severity:** SERIOUS
- **WCAG:** 1.1.1 Non-text Content (Level A)
- **Score Deduction:** 3 points
- **Detects:** Scanned PDF pages where OCR confidence falls below 70%
- **Recommendation:** Review the scanned content for accuracy; the source scan may be low quality
