"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";

interface DropZoneProps {
  onFileDrop: (file: File) => void;
}

const ACCEPTED = {
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
  "application/pdf": [".pdf"],
  "video/mp4": [".mp4"],
};

export function DropZone({ onFileDrop }: DropZoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) onFileDrop(accepted[0]);
    },
    [onFileDrop]
  );

  const { getRootProps, getInputProps, isDragActive, fileRejections } =
    useDropzone({
      onDrop,
      accept: ACCEPTED,
      maxFiles: 1,
      maxSize: 500 * 1024 * 1024,
    });

  return (
    <div>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 bg-white hover:border-gray-400"
        }`}
        aria-label="File upload area. Drag and drop or click to select a PPTX, PDF, or MP4 file."
      >
        <input {...getInputProps()} aria-label="File input" />
        <p className="text-4xl mb-4" aria-hidden="true">
          {isDragActive ? "📂" : "📁"}
        </p>
        <p className="text-gray-700 font-medium mb-1">
          {isDragActive ? "Drop to upload" : "Drag & drop or click to upload"}
        </p>
        <p className="text-gray-400 text-sm">PPTX, PDF, MP4 · Max 500 MB</p>
      </div>
      {fileRejections.length > 0 && (
        <p role="alert" className="mt-2 text-sm text-red-600">
          {fileRejections[0].errors[0].message}
        </p>
      )}
    </div>
  );
}
