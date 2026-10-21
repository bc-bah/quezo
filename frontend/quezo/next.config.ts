import type { NextConfig } from "next";

const config: NextConfig = {
  logging: false,
  poweredByHeader: false,
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "Cache-Control", value: "private, no-store" },
        { key: "Referrer-Policy", value: "strict-origin" },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
      ],
    }, {
      source: "/auth/:path*",
      headers: [{ key: "Referrer-Policy", value: "no-referrer" }],
    }];
  },
};
export default config;
