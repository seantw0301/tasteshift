import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Production is served as static files under a sub-path; dev keeps the defaults.
  // Static export cannot be combined with cacheComponents / partialPrefetching.
  ...(process.env.STATIC_EXPORT
    ? { output: "export" as const, trailingSlash: true }
    : { cacheComponents: true, partialPrefetching: true }),
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || undefined,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
