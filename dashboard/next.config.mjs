/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    // Required so server-only fetches with API_BEARER_TOKEN are revalidated
    // on a sane cadence in production. Pages opt into this via revalidate.
    typedRoutes: false,
  },
};

export default nextConfig;
