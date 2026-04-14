"""
Checks for missing captions/subtitles on MP4 files.
"""
from app.processing.checkers import IssueResult
from app.processing.normalizers import NormalizedDocument


def check_captions(doc: NormalizedDocument) -> list[IssueResult]:
    if doc.source_type != "MP4":
        return []

    if doc.media is None:
        return []

    if doc.media.has_embedded_captions:
        return []

    # No embedded captions and no pre-existing VTT — flag as missing
    return [
        IssueResult(
            issue_type="MISSING_CAPTIONS",
            severity="CRITICAL",
            location_in_asset={"media": True},
            fix_recommendation="No captions found. Will generate captions from the audio transcript.",
            auto_fixable=True,
        )
    ]
