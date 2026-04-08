/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // NEXT_PUBLIC_API_URL and NEXT_PUBLIC_EXTENSION_ID must be passed
  // as build args (--build-arg) or set in the environment at build time.
  // Do NOT hardcode localhost here — it leaks into production builds.
};

module.exports = nextConfig;
