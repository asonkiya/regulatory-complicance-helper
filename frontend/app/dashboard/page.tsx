"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { AssetCard } from "../../components/dashboard/AssetCard";
import { listAssets } from "../../lib/api";
import type { Asset, AssetListResponse } from "../../lib/types";

const fetcher = () => listAssets({ page: 1, page_size: 50 });

export default function DashboardPage() {
  const { data, error, isLoading } = useSWR<AssetListResponse>(
    "assets",
    fetcher,
    { refreshInterval: 5000 }
  );

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">
          Accessibility Copilot
        </h1>
        <Link
          href="/upload"
          className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Upload File
        </Link>
      </header>

      <div className="px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-medium text-gray-900">
            Course Materials
            {data && (
              <span className="ml-2 text-sm text-gray-500 font-normal">
                ({data.total} file{data.total !== 1 ? "s" : ""})
              </span>
            )}
          </h2>
        </div>

        {isLoading && (
          <p className="text-gray-500" aria-live="polite">
            Loading...
          </p>
        )}

        {error && (
          <p role="alert" className="text-red-600">
            Failed to load assets. Is the backend running?
          </p>
        )}

        {data && data.assets.length === 0 && (
          <div className="text-center py-16 text-gray-500">
            <p className="text-lg mb-4">No files uploaded yet.</p>
            <Link
              href="/upload"
              className="text-blue-600 hover:underline font-medium"
            >
              Upload your first file
            </Link>
          </div>
        )}

        {data && data.assets.length > 0 && (
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            aria-label="Course materials list"
          >
            {data.assets.map((asset: Asset) => (
              <AssetCard key={asset.asset_id} asset={asset} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
