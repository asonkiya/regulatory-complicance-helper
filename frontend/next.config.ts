import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/:path*`,
      },
    ];
  },
  turbopack: {
    resolveAlias: {
      // react-pdf optionally imports canvas (node-only); stub it out for the browser
      canvas: { browser: "./empty-module.js" },
    },
  },
};

export default nextConfig;
