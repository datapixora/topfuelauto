/** @type {import('next').NextConfig} */
const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE ||
  'http://localhost:8000/api/v1';

const nextConfig = {
  env: {
    NEXT_PUBLIC_API_BASE: apiBase,
    NEXT_PUBLIC_API_BASE_URL: apiBase,
  },
};

module.exports = nextConfig;
