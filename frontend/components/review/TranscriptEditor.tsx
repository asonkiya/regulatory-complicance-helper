"use client";

import { useState } from "react";
import type { Artifact, Issue } from "../../lib/types";
import { getArtifactDownloadUrl } from "../../lib/api";

interface TranscriptEditorProps {
  issue: Issue;
  vttArtifact: Artifact | undefined;
  srtArtifact: Artifact | undefined;
  onApprove: () => void;
}

export function TranscriptEditor({
  issue,
  vttArtifact,
  srtArtifact,
  onApprove,
}: TranscriptEditorProps) {
  const [saving, setSaving] = useState(false);

  const handleApprove = async () => {
    setSaving(true);
    try {
      await onApprove();
    } finally {
      setSaving(false);
    }
  };

  const hasCaptions = vttArtifact?.generation_status === "COMPLETE";

  return (
    <div className="p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-1">
        Caption Review
      </h2>
      <p className="text-sm text-gray-500 mb-6">
        AI-generated captions from the audio track.
      </p>

      {!hasCaptions ? (
        <p className="text-sm text-yellow-700 bg-yellow-50 rounded-md p-3">
          Caption generation is still in progress. Check back shortly.
        </p>
      ) : (
        <>
          <p className="text-sm text-green-700 bg-green-50 rounded-md p-3 mb-6">
            Captions generated successfully.
          </p>

          <div className="flex gap-3 mb-6">
            {vttArtifact && (
              <a
                href={getArtifactDownloadUrl(vttArtifact.artifact_id)}
                download="captions.vtt"
                className="text-sm text-blue-600 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
                aria-label="Download VTT caption file"
              >
                Download VTT
              </a>
            )}
            {srtArtifact && (
              <a
                href={getArtifactDownloadUrl(srtArtifact.artifact_id)}
                download="captions.srt"
                className="text-sm text-blue-600 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
                aria-label="Download SRT caption file"
              >
                Download SRT
              </a>
            )}
          </div>

          <button
            onClick={handleApprove}
            disabled={saving}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-green-500"
            aria-label="Approve captions"
          >
            {saving ? "Saving..." : "Approve Captions"}
          </button>
        </>
      )}
    </div>
  );
}
