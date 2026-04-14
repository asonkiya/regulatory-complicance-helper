import Link from "next/link";
import type { Asset } from "../../lib/types";
import { ScoreRing } from "./ScoreRing";
import { StatusBadge } from "./StatusBadge";

const TYPE_ICON: Record<string, string> = {
  PPTX: "📊",
  PDF: "📄",
  MP4: "🎬",
};

interface AssetCardProps {
  asset: Asset;
  score?: number;
}

export function AssetCard({ asset, score }: AssetCardProps) {
  const icon = TYPE_ICON[asset.source_type] ?? "📎";
  const isProcessing = !["COMPLETE", "FAILED"].includes(asset.processing_status);

  return (
    <Link
      href={`/assets/${asset.asset_id}`}
      className="block bg-white rounded-lg border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      aria-label={`${asset.original_filename}, ${asset.source_type}, status: ${asset.processing_status}${score !== undefined ? `, score: ${score}` : ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-2xl flex-shrink-0" aria-hidden="true">
            {icon}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {asset.original_filename}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {asset.source_type} ·{" "}
              {new Date(asset.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {score !== undefined ? (
          <ScoreRing score={score} size={48} />
        ) : (
          <div className="flex-shrink-0">
            <StatusBadge status={asset.processing_status} />
          </div>
        )}
      </div>

      {isProcessing && (
        <div
          className="mt-3 h-1 bg-gray-100 rounded-full overflow-hidden"
          aria-hidden="true"
        >
          <div className="h-1 bg-blue-400 rounded-full animate-pulse w-3/4" />
        </div>
      )}
    </Link>
  );
}
