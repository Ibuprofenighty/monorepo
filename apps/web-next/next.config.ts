import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export by default; switch to SSR per project-profile §7.
  output: "export",
  transpilePackages: ["@project/api-client"],
};

export default nextConfig;
