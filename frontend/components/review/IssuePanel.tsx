import type { Issue, Severity } from "../../lib/types";

const SEVERITY_CONFIG: Record<Severity, { label: string; className: string }> =
  {
    CRITICAL: { label: "Critical", className: "bg-red-100 text-red-700" },
    SERIOUS: { label: "Serious", className: "bg-orange-100 text-orange-700" },
    MODERATE: { label: "Moderate", className: "bg-yellow-100 text-yellow-700" },
    MINOR: { label: "Minor", className: "bg-gray-100 text-gray-600" },
  };

const STATUS_ICON: Record<string, string> = {
  APPROVED: "✅",
  REJECTED: "❌",
  SKIPPED: "⏭️",
  PENDING: "○",
};

interface IssuePanelProps {
  issue: Issue;
  isSelected: boolean;
  onClick: () => void;
}

export function IssuePanel({ issue, isSelected, onClick }: IssuePanelProps) {
  const severity = SEVERITY_CONFIG[issue.severity] ?? {
    label: issue.severity,
    className: "bg-gray-100 text-gray-600",
  };
  const statusIcon = STATUS_ICON[issue.review_status] ?? "○";
  const issueLabel = issue.issue_type.replace(/_/g, " ").toLowerCase();

  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={isSelected}
      aria-label={`${issueLabel}, severity: ${severity.label}, status: ${issue.review_status}`}
      className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-gray-50 focus:outline-none focus:bg-blue-50 transition-colors ${
        isSelected ? "bg-blue-50 border-l-2 border-l-blue-500" : ""
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${severity.className}`}
        >
          {severity.label}
        </span>
        <span className="text-sm" aria-hidden="true">
          {statusIcon}
        </span>
      </div>
      <p className="text-sm text-gray-900 capitalize">{issueLabel}</p>
      {issue.location_in_asset && (
        <p className="text-xs text-gray-400 mt-0.5">
          {formatLocation(issue.location_in_asset)}
        </p>
      )}
    </button>
  );
}

function formatLocation(loc: Record<string, unknown>): string {
  if ("slide" in loc) return `Slide ${(loc.slide as number) + 1}`;
  if ("page" in loc) return `Page ${(loc.page as number) + 1}`;
  if ("media" in loc) return "Video";
  if ("document" in loc) return "Document";
  return "";
}
