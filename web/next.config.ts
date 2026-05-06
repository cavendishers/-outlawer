import type { NextConfig } from "next";

const apiProxyTarget = process.env.API_PROXY_TARGET || "http://api:8000";
const distDir = process.env.NEXT_DIST_DIR || ".next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  distDir,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiProxyTarget}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
