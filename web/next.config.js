/** @type {import('next').NextConfig} */

// Next.js 14 writes both `next dev` and `next build` output into `.next`, so
// running a production build while the dev server is up corrupts the dev
// server's chunks ("Cannot find module './819.js'"). Keeping dev on its own
// directory removes that whole class of failure.
const isDev = process.env.NODE_ENV !== 'production';

const nextConfig = {
  reactStrictMode: true,
  ...(isDev ? { distDir: '.next-dev' } : {}),
  // A build must never silently succeed against a half-written tree.
  typescript: { ignoreBuildErrors: false },
  eslint: { ignoreDuringBuilds: false },
};

module.exports = nextConfig;
