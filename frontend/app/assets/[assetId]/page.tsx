"use client";

import Link from "next/link";
import { use } from "react";
import useSWR from "swr";
import { getAsset, listArtifacts, getArtifactDownloadUrl } from "../../../lib/api";
import type { Artifact } from "../../../lib/types";
import { ScoreRing } from "../../../components/dashboard/ScoreRing";
import { StatusBadge } from "../../../components/dashboard/StatusBadge";

interface Params {
  assetId: string;
}

export default function AssetDetailPage({ params }: { params: Promise<Params> }) {
  const { assetId } = use(params);

  const { data: asset } = useSWR(
    `asset-${assetId}`,
    () => getAsset(assetId),
    { refreshInterval: 3000 }
  );
  const { data: artifacts } = useSWR<Artifact[]>(
    `artifacts-${assetId}`,
    () => listArtifacts(assetId)
  );

  const report = artifacts?.find((a) => a.artifact_type === "ACCESSIBILITY_REPORT");
  const score = report?.content_snapshot ? parseInt(report.content_snapshot, 10) : null;

  const downloadableArtifacts = artifacts?.filter(
    (a) =>
      a.generation_status === "COMPLETE" &&
      a.artifact_type !== "ACCESSIBILITY_REPORT" &&
      a.storage_location
  );

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <Link
          href="/dashboard"
          className="text-gray-500 hover:text-gray-700 text-sm"
          aria-label="Back to dashboard"
        >
          ← Dashboard
        </Link>
        <h1 className="text-xl font-semibold text-gray-900 truncate">
          {asset?.original_filename ?? "Loading..."}
        </h1>
        {asset && <StatusBadge status={asset.processing_status} />}
      </header>

      <div className="px-6 py-8 max-w-4xl">
        {/* Score + summary */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6 flex items-center gap-8">
          {score !== null ? (
            <ScoreRing score={score} size={80} />
          ) : (
            <div
              className="w-20 h-20 rounded-full bg-gray-100 animate-pulse"
              aria-label="Calculating score"
            />
          )}
          <div>
            <p className="text-2xl font-bold text-gray-900">
              {score !== null ? `${score}/100` : "—"}
            </p>
            <p className="text-gray-500 text-sm">Accessibility score</p>
            <Link
              href={`/assets/${assetId}/review`}
              className="mt-2 inline-block text-blue-600 hover:underline text-sm font-medium"
            >
              Review issues →
            </Link>
          </div>
        </div>

        {/* Downloads */}
        {downloadableArtifacts && downloadableArtifacts.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">
              Accessible Outputs
            </h2>
            <ul className="space-y-2">
              {downloadableArtifacts.map((artifact) => (
                <li key={artifact.artifact_id}>
                  <a
                    href={getArtifactDownloadUrl(artifact.artifact_id)}
                    download
                    className="text-blue-600 hover:underline text-sm"
                    aria-label={`Download ${artifact.artifact_type.replace(/_/g, " ").toLowerCase()}`}
                  >
                    {artifact.artifact_type.replace(/_/g, " ").toLowerCase()}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </main>
  );
}
