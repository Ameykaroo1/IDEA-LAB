/** @type {import('next').NextConfig} */
const rawBackend = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
const backendUrl = rawBackend.replace(/\/api\/?$/, '').replace(/\/+$/, '');

const nextConfig = {
  reactStrictMode: false,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
