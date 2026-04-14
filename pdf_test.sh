#!/usr/bin/env bash
# pdf_test.sh — Manual end-to-end test for the PDF accessibility pipeline.
#
# Usage:
#   ./pdf_test.sh                          # uses sample PDFs bundled below (created on the fly)
#   ./pdf_test.sh path/to/your.pdf         # test your own PDF
#
# What it does:
#   1. Runs unit tests for all new PDF checkers
#   2. Creates a minimal test PDF (or uses yours)
#   3. Uploads it via the API and polls until processing finishes
#   4. Prints the issues found and the accessibility score
#   5. Checks that the expected issue types are present

set -euo pipefail

API="${API_URL:-http://localhost:8000}"
PASS=0
FAIL=0
SKIP=0

# ── Colours ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}  PASS${RESET}  $*"; ((PASS++)); }
fail() { echo -e "${RED}  FAIL${RESET}  $*"; ((FAIL++)); }
skip() { echo -e "${YELLOW}  SKIP${RESET}  $*"; ((SKIP++)); }
info() { echo -e "        $*"; }

# ── 1. Unit tests ──────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " Step 1: Unit tests"
echo "══════════════════════════════════════════════"

if ! command -v pytest &>/dev/null; then
    skip "pytest not found — skipping unit tests (run: pip install -e '.[dev]' in backend/)"
else
    cd backend
    if pytest tests/test_pdf_checkers.py -v --tb=short 2>&1; then
        ok "All unit tests passed"
    else
        fail "Unit tests failed — fix before proceeding"
    fi
    cd ..
fi

# ── 2. Create test PDF (if no input provided) ──────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " Step 2: Prepare test PDF"
echo "══════════════════════════════════════════════"

INPUT_PDF="${1:-}"
TMPDIR_PDF=$(mktemp -d)
trap 'rm -rf "$TMPDIR_PDF"' EXIT

if [[ -n "$INPUT_PDF" ]]; then
    if [[ ! -f "$INPUT_PDF" ]]; then
        echo "Error: file not found: $INPUT_PDF"
        exit 1
    fi
    TEST_PDF="$INPUT_PDF"
    info "Using your PDF: $TEST_PDF"
else
    # Create a minimal PDF using Python (reportlab or fpdf2 if available, otherwise fpdf)
    TEST_PDF="$TMPDIR_PDF/test_accessibility.pdf"
    python3 - <<'PYEOF' "$TEST_PDF"
import sys
output_path = sys.argv[1]

# Try fpdf2 first, then reportlab, then write a raw minimal PDF as last resort
try:
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=24)
    pdf.cell(0, 10, "Introduction to Accessibility", ln=True)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "This document demonstrates accessibility issues.", ln=True)
    pdf.cell(0, 10, "For more information, click here.", ln=True)
    pdf.output(output_path)
    print(f"  Created test PDF with fpdf2: {output_path}")
except ImportError:
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        c = canvas.Canvas(output_path, pagesize=letter)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(72, 700, "Introduction to Accessibility")
        c.setFont("Helvetica", 12)
        c.drawString(72, 670, "This document demonstrates accessibility issues.")
        c.drawString(72, 650, "For more information, click here.")
        c.save()
        print(f"  Created test PDF with reportlab: {output_path}")
    except ImportError:
        # Minimal valid raw PDF — no images, no links, just text
        raw = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 120>>stream
BT /F1 24 Tf 72 700 Td (Introduction to Accessibility) Tj ET
BT /F1 12 Tf 72 650 Td (For more information, click here.) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000438 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
520
%%EOF"""
        with open(output_path, "wb") as f:
            f.write(raw)
        print(f"  Created minimal raw PDF: {output_path}")
PYEOF
    info "Test PDF ready: $TEST_PDF"
fi

# ── 3. Check API is reachable ─────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " Step 3: Check API connectivity"
echo "══════════════════════════════════════════════"

if ! curl -sf "$API/health" >/dev/null 2>&1 && \
   ! curl -sf "$API/docs" >/dev/null 2>&1; then
    skip "API not reachable at $API — skipping upload tests"
    skip "  Start the backend first: docker compose up  (or uvicorn app.main:app --reload)"
    echo ""
    echo "══════════════════════════════════════════════"
    echo " Summary"
    echo "══════════════════════════════════════════════"
    echo "  PASS: $PASS  FAIL: $FAIL  SKIP: $SKIP"
    [[ $FAIL -eq 0 ]] && exit 0 || exit 1
fi

ok "API reachable at $API"

# ── 4. Upload PDF ─────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " Step 4: Upload PDF"
echo "══════════════════════════════════════════════"

UPLOAD_RESP=$(curl -sf -X POST "$API/api/v1/assets/upload" \
    -F "file=@$TEST_PDF;type=application/pdf" \
    -F "course_name=PDF Accessibility Test" 2>&1) || {
    fail "Upload request failed"
    echo "$UPLOAD_RESP"
    exit 1
}

info "Upload response: $UPLOAD_RESP"

ASSET_ID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('asset_id',''))" 2>/dev/null || true)
TASK_ID=$(echo "$UPLOAD_RESP"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('task_id',''))"  2>/dev/null || true)

if [[ -z "$ASSET_ID" ]]; then
    fail "No asset_id in upload response"
    exit 1
fi

ok "Uploaded — asset_id: $ASSET_ID  task_id: ${TASK_ID:-n/a}"

# ── 5. Poll for completion ─────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " Step 5: Wait for pipeline to finish"
echo "══════════════════════════════════════════════"

POLL_URL="$API/api/v1/jobs/${TASK_ID}/status"
MAX_WAIT=180  # seconds
ELAPSED=0
STAGE=""

while true; do
    STATUS_RESP=$(curl -sf "$POLL_URL" 2>/dev/null || echo '{}')
    STATE=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('state',''))" 2>/dev/null || true)
    STAGE=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stage',''))" 2>/dev/null || true)

    echo -ne "\r  State: ${STATE:-?}  Stage: ${STAGE:-?}  (${ELAPSED}s)   "

    if [[ "$STATE" == "SUCCESS" ]]; then
        echo ""
        ok "Pipeline completed in ${ELAPSED}s"
        break
    elif [[ "$STATE" == "FAILURE" ]]; then
        echo ""
        fail "Pipeline failed — check Celery logs"
        break
    fi

    if [[ $ELAPSED -ge $MAX_WAIT ]]; then
        echo ""
        fail "Timed out after ${MAX_WAIT}s waiting for completion (last stage: $STAGE)"
        break
    fi

    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

# ── 6. Fetch issues and check results ─────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " Step 6: Validate detected issues"
echo "══════════════════════════════════════════════"

ISSUES_RESP=$(curl -sf "$API/api/v1/assets/$ASSET_ID/issues" 2>/dev/null || echo '[]')
ISSUE_TYPES=$(echo "$ISSUES_RESP" | python3 -c "
import sys, json
issues = json.load(sys.stdin)
if isinstance(issues, dict):
    issues = issues.get('issues', issues.get('items', []))
types = [i.get('issue_type','') for i in issues]
print('\n'.join(types))
" 2>/dev/null || true)

info "Issue types found:"
echo "$ISSUE_TYPES" | sed 's/^/    /'

# Check expected issues are present (will depend on PDF content)
check_issue_present() {
    local issue_type="$1"
    local optional="${2:-required}"
    if echo "$ISSUE_TYPES" | grep -qx "$issue_type"; then
        ok "$issue_type detected"
    elif [[ "$optional" == "optional" ]]; then
        skip "$issue_type not found (optional — depends on PDF content)"
    else
        fail "$issue_type not detected (expected for test PDF)"
    fi
}

# These depend on the PDF content — the generated test PDF is untagged
check_issue_present "UNTAGGED_PDF"
check_issue_present "MISSING_HEADING_STRUCTURE" optional
check_issue_present "MISSING_LINK_TEXT"         optional
check_issue_present "MISSING_TABLE_HEADERS"     optional
check_issue_present "MISSING_DOCUMENT_TITLE"    optional  # only fires for tagged PDFs

# ── 7. Fetch accessibility score ───────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " Step 7: Accessibility score"
echo "══════════════════════════════════════════════"

SCORE_RESP=$(curl -sf "$API/api/v1/assets/$ASSET_ID/score" 2>/dev/null || echo '{}')
SCORE=$(echo "$SCORE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('score','?'))" 2>/dev/null || echo "?")
TOTAL=$(echo "$SCORE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_issues','?'))" 2>/dev/null || echo "?")

info "Score: $SCORE / 100  |  Total issues: $TOTAL"

if [[ "$SCORE" != "?" ]]; then
    if python3 -c "exit(0 if $SCORE < 100 else 1)" 2>/dev/null; then
        ok "Score < 100 (issues were detected — pipeline is working)"
    else
        skip "Score is 100 — no issues found; PDF may already be fully accessible"
    fi
fi

# ── 8. Trigger tagged PDF generation (optional smoke test) ─────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " Step 8: Tagged PDF generation smoke test"
echo "══════════════════════════════════════════════"

GEN_RESP=$(curl -sf -X POST "$API/api/v1/assets/$ASSET_ID/generate-outputs" 2>/dev/null || echo '{}')
GEN_STATUS=$(echo "$GEN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status', d.get('message','?')))" 2>/dev/null || echo "?")
info "Generate outputs response: $GEN_STATUS"

# Poll for output
sleep 5
OUTPUTS_RESP=$(curl -sf "$API/api/v1/assets/$ASSET_ID/outputs" 2>/dev/null || echo '{}')
HAS_TAGGED=$(echo "$OUTPUTS_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
outputs = d if isinstance(d, list) else d.get('outputs', [])
has = any('tagged' in str(o).lower() for o in outputs)
print('yes' if has else 'no')
" 2>/dev/null || echo "no")

if [[ "$HAS_TAGGED" == "yes" ]]; then
    ok "Tagged PDF artifact present in outputs"
else
    skip "Tagged PDF not yet in outputs (may still be processing, or no approved alt texts yet)"
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " Summary"
echo "══════════════════════════════════════════════"
echo "  PASS: $PASS   FAIL: $FAIL   SKIP: $SKIP"
echo ""
echo "  Asset ID: $ASSET_ID"
echo "  Review queue: $API/api/v1/assets/$ASSET_ID/issues"
echo ""

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
