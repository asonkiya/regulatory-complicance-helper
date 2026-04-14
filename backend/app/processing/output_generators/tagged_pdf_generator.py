"""
Generates an accessibility-tagged PDF using pikepdf.
Injects /MarkInfo, /Lang, image /Alt attributes (matched by xref), and XMP title.
"""
import json
import logging
from pathlib import Path

import pikepdf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.artifact import GeneratedArtifact
from app.models.asset import AccessibilityAsset
from app.services.storage_service import get_asset_dir

logger = logging.getLogger(__name__)


def generate_tagged_pdf(db: Session, asset: AccessibilityAsset) -> Path | None:
    """
    Creates a tagged PDF from the original and approved alt text artifacts.
    Returns the output path or None if tagging fails.
    """
    if asset.source_type != "PDF":
        return None

    asset_dir = get_asset_dir(str(asset.asset_id))
    output_path = asset_dir / "output_tagged.pdf"

    # Collect approved alt text keyed by element_id
    alt_text_map = _collect_approved_alt_text(db, asset)

    # Build {xref: alt_text} by matching element_ids from the normalized doc
    xref_to_alt = _build_xref_alt_map(asset, alt_text_map)

    # Collect approved document title (if any)
    approved_title = _collect_approved_title(db, asset)

    try:
        with pikepdf.open(asset.source_location) as pdf:
            # 1. Mark document as tagged
            if "/MarkInfo" not in pdf.Root:
                pdf.Root["/MarkInfo"] = pdf.make_indirect(
                    pikepdf.Dictionary(**{"/Marked": True})
                )
            else:
                pdf.Root["/MarkInfo"]["/Marked"] = True

            # 2. Add document language
            if "/Lang" not in pdf.Root:
                pdf.Root["/Lang"] = pikepdf.String("en-US")

            # 3. Add document title to XMP metadata (prefer approved title, fallback to filename)
            _inject_xmp_title(pdf, approved_title or asset.original_filename)

            # 4. Inject /Alt strings on image XObjects, matched by xref
            _inject_image_alt_text(pdf, xref_to_alt)

            pdf.save(str(output_path))

        logger.info("Tagged PDF generated for asset %s", asset.asset_id)
        return output_path

    except Exception:
        logger.exception("Failed to generate tagged PDF for asset %s", asset.asset_id)
        return None


def _collect_approved_alt_text(db: Session, asset: AccessibilityAsset) -> dict[str, str]:
    """Return {element_id: alt_text} for all approved ALT_TEXT artifacts."""
    from app.models.issue import AccessibilityIssue

    alt_map: dict[str, str] = {}
    artifacts = db.scalars(
        select(GeneratedArtifact).where(
            GeneratedArtifact.asset_id == asset.asset_id,
            GeneratedArtifact.artifact_type == "ALT_TEXT",
            GeneratedArtifact.approved_at.is_not(None),
        )
    ).all()

    for artifact in artifacts:
        if artifact.issue_id and artifact.content_snapshot:
            issue = db.get(AccessibilityIssue, artifact.issue_id)
            if issue and issue.location_in_asset:
                element_id = issue.location_in_asset.get("element_id", "")
                if element_id:
                    alt_map[element_id] = artifact.content_snapshot

    return alt_map


def _build_xref_alt_map(asset: AccessibilityAsset, alt_text_map: dict[str, str]) -> dict[int, str]:
    """
    Build {xref: alt_text} by loading the normalized JSON and matching element_ids.
    Falls back to empty dict if the normalized file is unavailable.
    """
    if not alt_text_map or not asset.normalized_content_ref:
        return {}

    try:
        from app.processing.normalizers import NormalizedDocument
        with open(asset.normalized_content_ref) as f:
            doc = NormalizedDocument.from_dict(json.load(f))

        xref_to_alt: dict[int, str] = {}
        for page in doc.pages:
            for element in page.elements:
                if element.element_id in alt_text_map:
                    xref = element.extra.get("xref")
                    if xref is not None:
                        xref_to_alt[int(xref)] = alt_text_map[element.element_id]
        return xref_to_alt
    except Exception:
        logger.warning("Could not load normalized doc for asset %s; skipping xref alt map", asset.asset_id)
        return {}


def _collect_approved_title(db: Session, asset: AccessibilityAsset) -> str | None:
    """Return the approved DOCUMENT_TITLE artifact content, or None."""
    artifact = db.scalars(
        select(GeneratedArtifact).where(
            GeneratedArtifact.asset_id == asset.asset_id,
            GeneratedArtifact.artifact_type == "DOCUMENT_TITLE",
            GeneratedArtifact.approved_at.is_not(None),
        )
    ).first()
    return artifact.content_snapshot if artifact and artifact.content_snapshot else None


def _inject_xmp_title(pdf: pikepdf.Pdf, title: str) -> None:
    """Add document title to XMP metadata only if not already set."""
    try:
        with pdf.open_metadata() as meta:
            if not meta.get("dc:title"):
                meta["dc:title"] = title
    except Exception:
        logger.warning("Could not set XMP title; trying DocInfo")
        try:
            if not pdf.docinfo.get("/Title"):
                pdf.docinfo["/Title"] = title
        except Exception:
            pass


def _inject_image_alt_text(pdf: pikepdf.Pdf, xref_to_alt: dict[int, str]) -> None:
    """
    Injects /Alt attribute on image XObjects, matched by xref number.
    Iterates all pages and applies alt text only to images whose xref is in the map.
    """
    if not xref_to_alt:
        return

    for page in pdf.pages:
        resources = page.get("/Resources", {})
        xobjects = resources.get("/XObject", {})
        for _name, xobj_ref in xobjects.items():
            xobj = xobj_ref
            if xobj.get("/Subtype") == "/Image":
                try:
                    xref = xobj_ref.objgen[0]
                    if xref in xref_to_alt:
                        xobj["/Alt"] = pikepdf.String(xref_to_alt[xref])
                except Exception:
                    pass
