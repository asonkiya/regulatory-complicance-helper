"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

interface Highlight {
  bbox: [number, number, number, number]; // [x0, y0, x1, y1] in PDF points, top-left origin
  color?: string;
}

interface PdfViewerProps {
  fileUrl: string;
  /** 0-indexed page to display */
  targetPage?: number;
  highlights?: Highlight[];
}

export function PdfViewer({
  fileUrl,
  targetPage,
  highlights = [],
}: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1); // 1-indexed for display
  const [pageDims, setPageDims] = useState<{
    pdfWidth: number;
    pdfHeight: number;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState<number>(600);

  // Observe container width for responsive scaling
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Navigate to target page when it changes
  useEffect(() => {
    if (targetPage !== undefined && targetPage >= 0 && targetPage < numPages) {
      setCurrentPage(targetPage + 1);
    }
  }, [targetPage, numPages]);

  const onDocumentLoadSuccess = useCallback(
    ({ numPages: n }: { numPages: number }) => {
      setNumPages(n);
      if (targetPage !== undefined && targetPage >= 0 && targetPage < n) {
        setCurrentPage(targetPage + 1);
      }
    },
    [targetPage]
  );

  const onPageLoadSuccess = useCallback(
    (page: { originalWidth: number; originalHeight: number }) => {
      setPageDims({
        pdfWidth: page.originalWidth,
        pdfHeight: page.originalHeight,
      });
    },
    []
  );

  // Desired render width — leave padding for the container
  const pageWidth = Math.min(containerWidth - 32, 800);
  const scale = pageDims ? pageWidth / pageDims.pdfWidth : 1;
  const renderedHeight = pageDims ? pageDims.pdfHeight * scale : 0;

  return (
    <div ref={containerRef} className="flex flex-col h-full bg-gray-100">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200 flex-shrink-0">
        <button
          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          disabled={currentPage <= 1}
          className="px-2 py-1 text-sm rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Previous page"
        >
          Prev
        </button>
        <span className="text-sm text-gray-600">
          Page {currentPage} of {numPages || "..."}
        </span>
        <button
          onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
          disabled={currentPage >= numPages}
          className="px-2 py-1 text-sm rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Next page"
        >
          Next
        </button>
      </div>

      {/* PDF Page with highlight overlays */}
      <div className="flex-1 overflow-auto flex justify-center p-4">
        <div
          className="relative"
          style={{ width: pageWidth, height: renderedHeight || "auto" }}
        >
          <Document
            file={fileUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            loading={
              <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
                Loading PDF...
              </div>
            }
            error={
              <div className="flex items-center justify-center h-64 text-red-400 text-sm">
                Failed to load PDF
              </div>
            }
          >
            <Page
              pageNumber={currentPage}
              width={pageWidth}
              onLoadSuccess={onPageLoadSuccess}
              renderAnnotationLayer={false}
              renderTextLayer={false}
            />
          </Document>

          {/* Highlight overlays — positioned over the rendered page */}
          {pageDims &&
            highlights.map((h, i) => {
              const [x0, y0, x1, y1] = h.bbox;
              const left = x0 * scale;
              const top = y0 * scale;
              const width = (x1 - x0) * scale;
              const height = (y1 - y0) * scale;
              const color = h.color ?? "rgba(239, 68, 68, 0.8)";

              return (
                <div
                  key={i}
                  className="absolute pointer-events-none border-2 rounded-sm transition-all duration-200"
                  style={{
                    left,
                    top,
                    width,
                    height,
                    borderColor: color,
                    backgroundColor: color.replace(
                      /[\d.]+\)$/,
                      "0.12)"
                    ),
                  }}
                  aria-hidden="true"
                />
              );
            })}
        </div>
      </div>
    </div>
  );
}
