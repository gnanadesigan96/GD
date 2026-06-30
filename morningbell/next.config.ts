import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  images: {
    domains: ['res.cloudinary.com', 'localhost'],
  },
};

export default nextConfig;
