import path from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["http://localhost:3000", "http://127.0.0.1:3000"],
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
