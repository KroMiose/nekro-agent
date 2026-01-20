# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM node:20-slim AS frontend-builder

# 设置 npm 镜像
RUN npm config set registry https://registry.npmmirror.com

# 设置工作目录
WORKDIR /app/frontend

# 安装 pnpm
RUN npm install -g pnpm && pnpm config set registry https://registry.npmmirror.com

# 首先复制依赖文件，利用缓存
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 然后复制源代码并构建
COPY frontend/tsconfig*.json ./
COPY frontend/vite.config.ts ./
COPY frontend/postcss.config.js ./
COPY frontend/tailwind.config.js ./
COPY frontend/tsconfig.app.json ./
COPY frontend/tsconfig.json ./
COPY frontend/tsconfig.node.json ./
COPY frontend/index.html ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN pnpm build

# 使用更小的基础镜像来存储构建产物
FROM busybox:1.36 AS frontend-dist
COPY --from=frontend-builder /app/frontend/dist /frontend-dist

FROM python:3.11-slim-bullseye

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo 'Asia/Shanghai' > /etc/timezone

RUN apt update

# 分批安装依赖以避免 QEMU 段错误
RUN apt install -y ca-certificates curl
RUN apt install -y gnupg git
RUN apt install -y gcc libpq-dev libmagic-dev
RUN apt install -y docker.io
RUN apt install -y git

# 清理缓存
RUN apt clean && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV STATIC_DIR=/app/static

# 安装 UV（使用官方推荐方式）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# 首先复制依赖文件和 README（pyproject.toml 需要），利用缓存
COPY pyproject.toml uv.lock README.md ./

# 复制入口脚本（force-include 需要）
COPY run_bot.py ./

# 使用 UV 安装依赖（包括 nb-cli）
RUN uv sync --frozen --no-dev

# 复制应用代码
COPY nekro_agent ./nekro_agent
COPY plugins ./plugins
COPY .env.prod ./

# 从前端构建产物复制静态文件
COPY --from=frontend-dist /frontend-dist ${STATIC_DIR}

# 暴露端口
EXPOSE 8021

# 健康检查
HEALTHCHECK --interval=10s --timeout=3s CMD curl -f http://127.0.0.1:8021/api/health || exit 1

# 启动应用
CMD ["uv", "run", "bot", "--env=prod"]
