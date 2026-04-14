import type { JobStatus } from "../../lib/types";

interface UploadProgressProps {
  status: JobStatus | null;
  isFailed: boolean;
  errorMessage: string | null;
}

const STAGE_LABELS: Record<string, string> = {
  NORMALIZING: "Parsing file...",
  CHECKING: "Running accessibility checks...",
  REMEDIATING: "Generating AI fixes...",
  OUTPUTTING: "Creating accessible outputs...",
  COMPLETE: "Complete!",
};

export function UploadProgress({ status, isFailed, errorMessage }: UploadProgressProps) {
  const stage = status?.current_stage ?? "NORMALIZING";
  const progress = status?.progress_percent ?? 10;
  const label = STAGE_LABELS[stage] ?? "Processing...";

  if (isFailed) {
    return (
      <div
        role="alert"
        className="bg-white rounded-xl border border-red-200 p-8 text-center"
      >
        <p className="text-2xl mb-3" aria-hidden="true">❌</p>
        <p className="font-semibold text-red-700 mb-1">Processing failed</p>
        <p className="text-sm text-gray-500">{errorMessage ?? "Unknown error"}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
      <p className="text-2xl mb-4" aria-hidden="true">⚙️</p>
      <p className="font-medium text-gray-800 mb-1" aria-live="polite">
        {label}
      </p>
      <p className="text-sm text-gray-400 mb-6">
        This may take a few minutes for large files.
      </p>
      <div
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Processing progress"
        className="w-full bg-gray-100 rounded-full h-2"
      >
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 mt-2">{progress}%</p>
    </div>
  );
}
