# 使用 Python 官方镜像作为基础镜像
FROM python:3.10.13-slim-bullseye

#设置时区
RUN /bin/cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone

# 安装 Poetry
RUN pip install poetry

# 设置工作目录
WORKDIR /app

# 复制项目文件到容器中
COPY . /app

RUN poetry config virtualenvs.create false

# 安装项目依赖项
RUN poetry install

# 健康检查
HEALTHCHECK --interval=5s --timeout=3s CMD curl -f http://127.0.0.1:9960/ping || exit 1

# 启动应用
CMD ["poetry", "run", "bot"]
