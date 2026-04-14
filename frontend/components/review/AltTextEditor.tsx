"use client";

import { useState } from "react";
import type { Artifact, Issue } from "../../lib/types";

interface AltTextEditorProps {
  issue: Issue;
  artifact: Artifact | undefined;
  onApprove: (altText: string) => void;
  onReject: () => void;
}

export function AltTextEditor({
  issue,
  artifact,
  onApprove,
  onReject,
}: AltTextEditorProps) {
  const [text, setText] = useState(
    artifact?.content_snapshot ?? issue.fix_recommendation ?? ""
  );
  const [saving, setSaving] = useState(false);

  const handleApprove = async () => {
    setSaving(true);
    try {
      await onApprove(text);
    } finally {
      setSaving(false);
    }
  };

  const editorId = `alt-text-${issue.issue_id}`;
  const descId = `alt-text-desc-${issue.issue_id}`;

  return (
    <div className="p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-1">
        Alt Text Review
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        Review and edit the AI-generated alt text before approving.
      </p>

      {/* Confidence indicator */}
      {artifact && issue.confidence_score !== null && (
        <p className="text-xs text-gray-400 mb-4" id={descId}>
          AI confidence:{" "}
          <span className={issue.confidence_score >= 0.8 ? "text-green-600" : "text-yellow-600"}>
            {Math.round((issue.confidence_score ?? 0) * 100)}%
          </span>
        </p>
      )}

      <div className="mb-4">
        <label
          htmlFor={editorId}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Alt text
        </label>
        <textarea
          id={editorId}
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-describedby={descId}
          rows={4}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          placeholder="Describe the image for screen reader users..."
        />
        <p className="text-xs text-gray-400 mt-1">{text.length} characters</p>
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleApprove}
          disabled={saving || !text.trim()}
          className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-green-500"
          aria-label="Approve this alt text"
        >
          {saving ? "Saving..." : "Approve"}
        </button>
        <button
          onClick={onReject}
          className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400"
          aria-label="Reject this alt text suggestion"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
