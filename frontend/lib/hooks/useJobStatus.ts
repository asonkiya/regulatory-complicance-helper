"use client";

import { useEffect, useRef, useState } from "react";
import { getJobStatus } from "../api";
import type { JobStatus } from "../types";

const TERMINAL_STATES = new Set(["SUCCESS", "FAILURE"]);
const POLL_INTERVAL_MS = 3000;

export function useJobStatus(taskId: string | null) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        const data = await getJobStatus(taskId);
        setStatus(data);
        if (TERMINAL_STATES.has(data.state)) {
          clearInterval(intervalRef.current!);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    };

    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    // Pause polling when tab is hidden
    const handleVisibility = () => {
      if (document.hidden) {
        clearInterval(intervalRef.current!);
      } else {
        poll();
        intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      clearInterval(intervalRef.current!);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [taskId]);

  const isComplete = status?.state === "SUCCESS";
  const isFailed = status?.state === "FAILURE";
  const isProcessing = !isComplete && !isFailed && taskId !== null;

  return { status, error, isComplete, isFailed, isProcessing };
}
