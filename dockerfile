FROM node:20-slim AS frontend-builder

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

FROM python:3.10.13-slim-bullseye

# 设置时区和镜像源
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo 'Asia/Shanghai' > /etc/timezone

# 系统依赖
ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
        ca-certificates \
        gnupg \
        git \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置 pip 镜像
RUN pip config set global.index-url https://mirrors.ustc.edu.cn/pypi/web/simple

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV STATIC_DIR=/app/static

# 安装 Poetry 和 nb-cli
RUN pip install poetry==1.8.0 nb-cli

# 首先复制依赖文件，利用缓存
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# 复制应用代码
COPY nekro_agent ./nekro_agent
COPY extensions ./extensions
COPY .env.prod ./

# 从前端构建产物复制静态文件
COPY --from=frontend-dist /frontend-dist ${STATIC_DIR}

# 暴露端口
EXPOSE 8021

# 健康检查
HEALTHCHECK --interval=10s --timeout=3s CMD curl -f http://127.0.0.1:8021/api/health || exit 1

# 启动应用
CMD ["nb", "run"]
