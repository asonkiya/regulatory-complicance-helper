"use client";

import Link from "next/link";
import { use, useState } from "react";
import useSWR from "swr";
import { listIssues, listArtifacts, updateIssue } from "../../../../lib/api";
import { IssuePanel } from "../../../../components/review/IssuePanel";
import { AltTextEditor } from "../../../../components/review/AltTextEditor";
import { TranscriptEditor } from "../../../../components/review/TranscriptEditor";
import type { Issue, Artifact } from "../../../../lib/types";

interface Params {
  assetId: string;
}

export default function ReviewPage({ params }: { params: Promise<Params> }) {
  const { assetId } = use(params);
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);

  const { data: issueData, mutate: mutateIssues } = useSWR(
    `issues-${assetId}`,
    () => listIssues(assetId)
  );
  const { data: artifacts } = useSWR<Artifact[]>(
    `artifacts-${assetId}`,
    () => listArtifacts(assetId)
  );

  const issues = issueData?.issues ?? [];

  const getArtifactForIssue = (issue: Issue): Artifact | undefined =>
    artifacts?.find((a) => a.issue_id === issue.issue_id);

  const handleApprove = async (issue: Issue, altText?: string) => {
    await updateIssue(issue.issue_id, {
      review_status: "APPROVED",
      ...(altText ? { fix_recommendation: altText } : {}),
    });
    await mutateIssues();
    setSelectedIssue(null);
  };

  const handleReject = async (issue: Issue) => {
    await updateIssue(issue.issue_id, { review_status: "REJECTED" });
    await mutateIssues();
    setSelectedIssue(null);
  };

  const renderRightPanel = () => {
    if (!selectedIssue) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400 text-sm">
          Select an issue to review
        </div>
      );
    }

    const artifact = getArtifactForIssue(selectedIssue);

    if (
      selectedIssue.issue_type === "MISSING_ALT_TEXT" ||
      selectedIssue.issue_type === "INADEQUATE_ALT_TEXT"
    ) {
      return (
        <AltTextEditor
          issue={selectedIssue}
          artifact={artifact}
          onApprove={(text) => handleApprove(selectedIssue, text)}
          onReject={() => handleReject(selectedIssue)}
        />
      );
    }

    if (selectedIssue.issue_type === "MISSING_CAPTIONS") {
      const vttArtifact = artifacts?.find(
        (a) =>
          a.issue_id === selectedIssue.issue_id &&
          a.artifact_type === "CAPTIONS_VTT"
      );
      return (
        <TranscriptEditor
          issue={selectedIssue}
          vttArtifact={vttArtifact}
          srtArtifact={artifacts?.find(
            (a) =>
              a.issue_id === selectedIssue.issue_id &&
              a.artifact_type === "CAPTIONS_SRT"
          )}
          onApprove={() => handleApprove(selectedIssue)}
        />
      );
    }

    // Generic issue: show recommendation text
    return (
      <div className="p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">
          {selectedIssue.issue_type.replace(/_/g, " ")}
        </h2>
        <p className="text-sm text-gray-700 mb-6">
          {selectedIssue.fix_recommendation ?? "No recommendation available."}
        </p>
        <div className="flex gap-3">
          <button
            onClick={() => handleApprove(selectedIssue)}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            Acknowledge
          </button>
          <button
            onClick={() => handleReject(selectedIssue)}
            className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400"
          >
            Skip
          </button>
        </div>
      </div>
    );
  };

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <Link
          href={`/assets/${assetId}`}
          className="text-gray-500 hover:text-gray-700 text-sm"
          aria-label="Back to asset detail"
        >
          ← Asset
        </Link>
        <h1 className="text-xl font-semibold text-gray-900">Review Issues</h1>
        <span className="text-sm text-gray-500">
          {issues.filter((i) => i.review_status === "PENDING").length} pending
        </span>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left panel: issue list */}
        <aside
          className="w-80 bg-white border-r border-gray-200 overflow-y-auto flex-shrink-0"
          aria-label="Issues list"
        >
          {issues.length === 0 ? (
            <p className="p-6 text-sm text-gray-500">No issues found.</p>
          ) : (
            <ul>
              {issues.map((issue) => (
                <li key={issue.issue_id}>
                  <IssuePanel
                    issue={issue}
                    isSelected={selectedIssue?.issue_id === issue.issue_id}
                    onClick={() => setSelectedIssue(issue)}
                  />
                </li>
              ))}
            </ul>
          )}
        </aside>

        {/* Right panel: contextual editor */}
        <section
          className="flex-1 overflow-y-auto"
          aria-label="Issue detail and editor"
          aria-live="polite"
        >
          {renderRightPanel()}
        </section>
      </div>
    </main>
  );
}
