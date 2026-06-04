import type { NextConfig } from "next";

const backendOrigin =
  process.env.API_REWRITE_ORIGIN ||
  (process.env.VERCEL ? "https://api.bizplot.co.kr" : "http://localhost:8000");

const nextConfig: NextConfig = {
  // 로컬에서는 FastAPI(:8000), Vercel에서는 공개 API 도메인으로 프록시한다.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
