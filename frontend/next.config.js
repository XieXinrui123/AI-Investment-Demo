/** @type {import('next').NextConfig} */
const apiInternalUrl = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000'

const nextConfig = {
  reactStrictMode: true,
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: `${apiInternalUrl}/api/:path*`,
        },
      ],
    }
  },
}

module.exports = nextConfig
