/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Silence workspace root inference warning (multiple lockfiles in monorepo style)
  outputFileTracingRoot: require('path').join(__dirname, '..'),
  env: {
    // For browser requests - force IPv4 localhost to avoid ::1 issues
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:5555',
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:5555/api',
    NEXT_PUBLIC_APP_NAME: 'ofitec.ai',
    NEXT_PUBLIC_VERSION: '1.0.0',
    NEXT_PUBLIC_BUILD_STAMP:
      process.env.NEXT_PUBLIC_BUILD_STAMP || `Build: ${new Date().toISOString()}`,
  },
  async rewrites() {
    // Use backend URL from environment, fallback to Docker internal network
    const backendUrl = process.env.BACKEND_URL || 'http://backend:5555';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
  async redirects() {
    return [
      { source: '/', destination: '/ceo/overview', permanent: false },
      { source: '/finanzas/cobros', destination: '/finanzas/facturas-venta', permanent: false },
      { source: '/finanzas/pagos', destination: '/finanzas/facturas-compra', permanent: false },
    ];
  },
  images: {
    domains: ['localhost', '127.0.0.1'],
  },
};

module.exports = nextConfig;
