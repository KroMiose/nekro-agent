FROM node:20-slim AS frontend-builder

# 设置工作目录
WORKDIR /app/frontend

# 首先复制依赖文件，利用缓存
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# 然后复制源代码并构建
COPY frontend/tsconfig*.json ./
COPY frontend/vite.config.ts ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN npm run build

# 使用更小的基础镜像来存储构建产物
FROM busybox:1.36 AS frontend-dist
COPY --from=frontend-builder /app/frontend/dist /frontend-dist

FROM python:3.10.13-slim-bullseye

# 设置时区
RUN /bin/cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone

# 系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

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
COPY configs ./configs

# 从前端构建产物复制静态文件
COPY --from=frontend-dist /frontend-dist ${STATIC_DIR}

# 暴露端口
EXPOSE 8021

# 健康检查
HEALTHCHECK --interval=10s --timeout=3s CMD curl -f http://127.0.0.1:8021/api/ping || exit 1

# 启动应用
CMD ["nb", "run"]
