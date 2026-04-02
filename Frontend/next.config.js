/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/calendar/:path*',
        destination: `${process.env.BACKEND_URL || 'https://ia-backend-prod-ftyhfnvyla-ew.a.run.app'}/api/calendar/:path*`,
      },
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL || 'https://ia-backend-prod-ftyhfnvyla-ew.a.run.app'}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
