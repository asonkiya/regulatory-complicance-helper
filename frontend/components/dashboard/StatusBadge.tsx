import type { ProcessingStatus } from "../../lib/types";

const STATUS_CONFIG: Record<
  ProcessingStatus,
  { label: string; className: string }
> = {
  PENDING: { label: "Pending", className: "bg-gray-100 text-gray-600" },
  NORMALIZING: { label: "Parsing", className: "bg-blue-100 text-blue-700" },
  CHECKING: { label: "Checking", className: "bg-blue-100 text-blue-700" },
  REMEDIATING: { label: "AI Fix", className: "bg-purple-100 text-purple-700" },
  OUTPUTTING: { label: "Generating", className: "bg-indigo-100 text-indigo-700" },
  COMPLETE: { label: "Complete", className: "bg-green-100 text-green-700" },
  FAILED: { label: "Failed", className: "bg-red-100 text-red-700" },
};

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    className: "bg-gray-100 text-gray-600",
  };

  return (
    <span
      role="status"
      aria-label={`Status: ${config.label}`}
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
