import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone', // Docker 최적화
};

export default nextConfig;
