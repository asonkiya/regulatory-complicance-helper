"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { DropZone } from "../../components/upload/DropZone";
import { UploadProgress } from "../../components/upload/UploadProgress";
import { uploadAsset } from "../../lib/api";
import { useJobStatus } from "../../lib/hooks/useJobStatus";

export default function UploadPage() {
  const router = useRouter();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [assetId, setAssetId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { status, isComplete, isFailed } = useJobStatus(taskId);

  const handleFileDrop = async (file: File) => {
    setUploadError(null);
    try {
      const result = await uploadAsset(file);
      setAssetId(result.asset_id);
      setTaskId(result.task_id);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  useEffect(() => {
    if (isComplete && assetId) {
      router.push(`/assets/${assetId}`);
    }
  }, [isComplete, assetId, router]);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Accessibility Copilot
        </h1>
        <p className="text-gray-600 mb-8">
          Upload course materials to check and fix accessibility issues.
        </p>

        {!taskId ? (
          <>
            <DropZone onFileDrop={handleFileDrop} />
            {uploadError && (
              <p role="alert" className="mt-4 text-sm text-red-600">
                {uploadError}
              </p>
            )}
          </>
        ) : (
          <UploadProgress
            status={status}
            isFailed={isFailed}
            errorMessage={status?.error ?? null}
          />
        )}
      </div>
    </main>
  );
}
