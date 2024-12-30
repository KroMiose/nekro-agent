#!/bin/bash

# 一键部署 nekro-agent 插件脚本

# region 更新软件源
echo "正在更新软件源..."
if ! sudo apt-get update; then
    echo "Error: 更新软件源失败，请检查您的网络连接。"
    exit 1
fi

# 检查 Docker 安装情况
if ! command -v docker &>/dev/null; then
    read -p "Docker 未安装，是否安装？[Y/n] " answer
    if [[ $answer == "Y" || $answer == "y" || $answer == "" ]]; then
        echo "正在安装 Docker..."
        if ! sudo apt-get install docker.io -y; then
            echo "Error: Docker 安装失败，请检查您的网络连接或软件源配置。"
            exit 1
        fi
    else
        echo "Error: Docker 未安装。请先安装 Docker 后再运行该脚本。"
        echo "安装命令: sudo apt-get install docker.io"
        exit 1
    fi
fi

# 检查 Docker Compose 安装情况
if ! command -v docker-compose &>/dev/null; then
    read -p "Docker Compose 未安装，是否安装？[Y/n] " answer
    if [[ $answer == "Y" || $answer == "y" || $answer == "" ]]; then
        echo "正在安装 Docker Compose..."
        if ! sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose; then
            echo "Error: Docker Compose 下载失败，请检查您的网络连接。"
            exit 1
        fi
        if ! sudo chmod +x /usr/local/bin/docker-compose; then
            echo "Error: 无法设置 Docker Compose 可执行权限，请检查您的权限配置。"
            exit 1
        fi
    else
        echo "Error: Docker Compose 未安装。请先安装 Docker Compose 后再运行该脚本。"
        echo "安装命令: sudo curl -L https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose"
        exit 1
    fi
fi

# endregion

# 设置应用目录 优先使用环境变量
if [ -z "$NEKRO_DATA_DIR" ]; then
    NEKRO_DATA_DIR=${NEKRO_DATA_DIR:-"${HOME}/srv/nekro_agent"}
fi

echo "NEKRO_DATA_DIR: $NEKRO_DATA_DIR"

export NEKRO_DATA_DIR=$NEKRO_DATA_DIR

# 创建应用目录
mkdir -p $NEKRO_DATA_DIR || {
    echo "Error: 无法创建应用目录 $NEKRO_DATA_DIR，请检查您的权限配置。"
    exit 1
}

# 进入应用目录
cd $NEKRO_DATA_DIR || {
    echo "Error: 无法进入应用目录 $NEKRO_DATA_DIR。"
    exit 1
}

# 如果当前目录没有 .env 文件，从仓库获取.env.example 并修改 .env 文件
if [ ! -f .env ]; then
    echo "未找到.env文件，正在从仓库获取.env.example..."
    if ! wget https://raw.githubusercontent.com/KroMiose/nekro-agent/main/docker/.env.example -O .env.temp; then
        echo "Error: 无法获取.env.example文件，请检查网络连接或手动创建.env文件。"
        exit 1
    fi

    # 替换或添加 NEKRO_DATA_DIR
    if grep -q "^NEKRO_DATA_DIR=" .env.temp; then
        # 如果存在，就替换
        sed -i "s|^NEKRO_DATA_DIR=.*|NEKRO_DATA_DIR=${NEKRO_DATA_DIR}|" .env.temp
    else
        # 如果不存在，就添加
        echo "NEKRO_DATA_DIR=${NEKRO_DATA_DIR}" >>.env.temp
    fi

    # 将修改后的文件移动为 .env
    mv .env.temp .env
    echo "已获取并修改 .env 模板。"
fi

# 从.env文件加载环境变量
if [ -f .env ]; then
    # 确保 INSTANCE_NAME 有值
    INSTANCE_NAME=$(grep INSTANCE_NAME .env | cut -d '=' -f2)
    if [ -z "$INSTANCE_NAME" ]; then
        echo "Error: INSTANCE_NAME 未在 .env 文件中设置"
        exit 1
    fi
    export INSTANCE_NAME=$INSTANCE_NAME

    # 确保 NEKRO_EXPOSE_PORT 有值
    NEKRO_EXPOSE_PORT=$(grep NEKRO_EXPOSE_PORT .env | cut -d '=' -f2)
    if [ -z "$NEKRO_EXPOSE_PORT" ]; then
        echo "Error: NEKRO_EXPOSE_PORT 未在 .env 文件中设置"
        exit 1
    fi
    export NEKRO_EXPOSE_PORT=$NEKRO_EXPOSE_PORT
fi

read -p "请检查并按需修改.env文件中的配置，未修改则按照默认配置安装，确认是否继续安装？[Y/n] " answer
if [[ $answer == "n" || $answer == "N" ]]; then
    echo "安装已取消"
    exit 0
fi

# 拉取 docker-compose.yml 文件
echo "正在拉取 docker-compose.yml 文件..."
if ! wget https://raw.githubusercontent.com/KroMiose/nekro-agent/main/docker/docker-compose-x-napcat.yml -O docker-compose.yml; then
    echo "Error: 无法拉取 docker-compose.yml 文件，请检查您的网络连接。"
    exit 1
fi

# 从.env文件加载环境变量
if [ -f .env ]; then
    # 确保 INSTANCE_NAME 有值
    INSTANCE_NAME=$(grep INSTANCE_NAME .env | cut -d '=' -f2)
    if [ -z "$INSTANCE_NAME" ]; then
        echo "Error: INSTANCE_NAME 未在 .env 文件中设置"
        exit 1
    fi

    # 使用 --env-file 参数而不是 export
    echo "使用实例名称: ${INSTANCE_NAME}"
    echo "启动主服务中..."
    if ! sudo docker-compose --env-file .env up -d; then
        echo "Error: 无法启动主服务，请检查 Docker Compose 配置。"
        exit 1
    fi
else
    echo "Error: .env 文件不存在"
    exit 1
fi

# 拉取沙盒镜像
echo "拉取沙盒镜像..."
if ! sudo docker pull kromiose/nekro-agent-sandbox; then
    echo "Error: 无法拉取沙盒镜像，请检查您的网络连接。"
    exit 1
fi

# 放行防火墙端口
echo "放行防火墙 ${NEKRO_EXPOSE_PORT:-8021} 端口..."
if ! sudo ufw allow ${NEKRO_EXPOSE_PORT:-8021}/tcp; then
    echo "Error: 无法放行防火墙 ${NEKRO_EXPOSE_PORT:-8021} 端口，如服务访问受限，请检查防火墙设置。"
fi

echo "部署完成！你可以通过 \`sudo docker logs -f ${INSTANCE_NAME}_agent\` 来查看 Nekro Agent 服务日志。"

# 提示用户修改配置文件
CONFIG_FILE="${NEKRO_DATA_DIR}/configs/nekro-agent.yaml"
echo "NekroAgent 应用本体安装完成！"

echo "请使用 \"sudo docker logs ${INSTANCE_NAME}_napcat\" 查看机器人 QQ 账号二维码"
echo "请根据需要编辑配置文件: $CONFIG_FILE"
echo "编辑后可通过以下命令重启 nekro-agent 容器:"
echo "  \"sudo docker restart ${INSTANCE_NAME}_agent\""
