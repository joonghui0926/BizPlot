import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 브라우저가 어떤 호스트(터널/직접IP/localhost)로 접속하든 API가 닿도록
  // 같은 오리진 /api 요청을 백엔드(FastAPI :8000)로 서버사이드 프록시한다.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
