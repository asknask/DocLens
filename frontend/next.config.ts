import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable CORS proxy for local development only
  async rewrites() {
    // Only use rewrites in development - in production, frontend calls API directly
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*',
        },
      ];
    }
    return [];
  },

  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
};

export default nextConfig;
