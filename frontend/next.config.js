/** @type {import('next').NextConfig} */
const path = require('path');
const withNextIntl = require('next-intl/plugin')('./i18n/request.ts');

const nextConfig = {
  reactStrictMode: true,
  
  // 启用 standalone 输出模式，生成极小的独立运行文件夹
  // Docker 镜像体积可减小 70% 以上
  output: "standalone",
  
  // To silence the workspace root warning
  // https://nextjs.org/docs/app/api-reference/config/next-config-js/turbopack#root-directory
  turbopack: {
    root: path.resolve(__dirname, '../'),
  },
  
  experimental: {
  },
  
  // 开发环境下的 API 代理（生产环境由 Nginx 处理）
  async rewrites() {
    // 仅在开发环境启用 rewrite
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*',
        },
        // SSE 流式响应代理（让 Copilot 的流式响应也能走代理）
        {
          source: '/api/v1/copilot/chat/stream',
          destination: 'http://localhost:8000/api/v1/copilot/chat/stream',
        },
      ];
    }
    return [];
  },
};

module.exports = withNextIntl(nextConfig);
