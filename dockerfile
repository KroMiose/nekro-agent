FROM python:3.10.13-slim-bullseye

#设置时区
RUN /bin/cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone

# 系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    docker.io

# 安装 Poetry 和 nb-cli
RUN pip install poetry nb-cli

WORKDIR /app
COPY . /app

# 安装项目依赖项
RUN poetry config virtualenvs.create false
RUN poetry install

# 暴露端口
EXPOSE 8021

# 健康检查
HEALTHCHECK --interval=10s --timeout=3s CMD curl -f http://127.0.0.1:8021/api/ping || exit 1

# 启动应用
CMD ["nb", "run"]
