# ============================================
# FinanceAICrews Frontend - Multi-stage Build
# ============================================
# 使用 Next.js standalone 输出优化镜像体积
# 最终镜像约 100-150MB (vs 传统 1GB+)
# ============================================

# Stage 1: 依赖安装 (包含 devDependencies 用于构建)
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# 复制依赖文件
COPY package.json package-lock.json* ./
# 安装所有依赖 (包含 devDependencies，构建需要)
RUN npm install

# Stage 2: 构建
FROM node:20-alpine AS builder
WORKDIR /app

# 复制所有依赖
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 设置环境变量 (构建时)
# NEXT_PUBLIC_API_URL 留空，生产环境由 Nginx 代理
ENV NEXT_PUBLIC_API_URL=""
ENV NEXT_TELEMETRY_DISABLED=1

# 构建 (standalone 模式)
RUN npm run build

# Stage 3: 生产运行
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# 创建非 root 用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制 standalone 输出
# 注意: turbopack.root 配置导致 standalone 输出在子目录下
# Docker 构建时工作目录是 /app，所以输出在 .next/standalone/app/
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone/app ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# standalone 模式下直接运行 server.js
CMD ["node", "server.js"]
