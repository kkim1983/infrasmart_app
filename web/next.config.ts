import type { NextConfig } from "next";

// CAPACITOR_BUILD=true 일 때만 정적 익스포트 (npx cap sync 용)
// 브라우저 직접 테스트 시에는 dev 서버 + rewrite 프록시 사용
const isCapacitorBuild = process.env.CAPACITOR_BUILD === 'true';

// 백엔드 서버 주소
// 로컬: http://localhost:8000
// 프로덕션 EC2: https://api.yourdomain.com
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const nextConfig: NextConfig = {
  ...(isCapacitorBuild && { output: 'export' }),
  images: { unoptimized: true },

  // 브라우저 dev 테스트 시 CORS 없이 백엔드 프록시 (Capacitor 빌드 시 불필요)
  ...(!isCapacitorBuild && {
    turbopack: { root: __dirname },
    // 로컬 기기(모바일/태블릿)에서 접근 허용
    allowedDevOrigins: ['127.0.0.1', '192.168.0.0/16', '10.0.0.0/8'],
    rewrites: async () => [
      {
        source: '/api/v1/:path*',
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
      {
        source: '/files/:path*',
        destination: `${BACKEND_URL}/files/:path*`,
      },
    ],
  }),
};

export default nextConfig;
