#!/bin/bash

# 默认使用 GitHub
USE_GITCODE=false

# 解析命令行参数
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -g|--gitcode)
            USE_GITCODE=true
            shift # 移除 --gitcode
            ;;
        *)
            # 未知选项
            echo "未知选项: $1"
            exit 1
            ;;
    esac
done

# Define base URLs
GITHUB_BASE_URL="https://raw.githubusercontent.com/KroMiose/nekro-agent/main/docker"
GITCODE_BASE_URL="https://raw.gitcode.com/gh_mirrors/ne/nekro-agent/raw/main/docker"

if [ "$USE_GITCODE" = true ]; then
    BASE_URL=$GITCODE_BASE_URL
    echo "使用 GitCode 加速源"
else
    BASE_URL=$GITHUB_BASE_URL
    echo "使用 GitHub 源 (可添加 -g 或 --gitcode 参数使用 GitCode 加速)"
fi

# 生成随机字符串的函数
generate_random_string() {
    local length=$1
    cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w $length | head -n 1
}

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
            echo "您也可以尝试使用 pip 安装：sudo pip install docker-compose -i https://pypi.tuna.tsinghua.edu.cn/simple"
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

# 设置开放目录权限
sudo chmod -R 777 $NEKRO_DATA_DIR

# 进入应用目录
cd $NEKRO_DATA_DIR || {
    echo "Error: 无法进入应用目录 $NEKRO_DATA_DIR。"
    exit 1
}

# 如果当前目录没有 .env 文件，从仓库获取.env.example 并修改 .env 文件
if [ ! -f .env ]; then
    echo "未找到.env文件，正在从仓库获取.env.example..."
    if ! wget ${BASE_URL}/.env.example -O .env.temp; then
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

    # 生成随机的 ONEBOT_ACCESS_TOKEN 和 NEKRO_ADMIN_PASSWORD（如果它们为空）
    ONEBOT_ACCESS_TOKEN=$(grep ONEBOT_ACCESS_TOKEN .env.temp | cut -d '=' -f2)
    if [ -z "$ONEBOT_ACCESS_TOKEN" ]; then
        ONEBOT_ACCESS_TOKEN=$(generate_random_string 32)
        sed -i "s|^ONEBOT_ACCESS_TOKEN=.*|ONEBOT_ACCESS_TOKEN=${ONEBOT_ACCESS_TOKEN}|" .env.temp
    fi

    NEKRO_ADMIN_PASSWORD=$(grep NEKRO_ADMIN_PASSWORD .env.temp | cut -d '=' -f2)
    if [ -z "$NEKRO_ADMIN_PASSWORD" ]; then
        NEKRO_ADMIN_PASSWORD=$(generate_random_string 16)
        sed -i "s|^NEKRO_ADMIN_PASSWORD=.*|NEKRO_ADMIN_PASSWORD=${NEKRO_ADMIN_PASSWORD}|" .env.temp
    fi

    QDRANT_API_KEY=$(grep QDRANT_API_KEY .env.temp | cut -d '=' -f2)
    if [ -z "$QDRANT_API_KEY" ]; then
        QDRANT_API_KEY=$(generate_random_string 32)
        sed -i "s|^QDRANT_API_KEY=.*|QDRANT_API_KEY=${QDRANT_API_KEY}|" .env.temp
    fi

    # 将修改后的文件移动为 .env
    mv .env.temp .env
    echo "已获取并修改 .env 模板。"
else
    # 如果已存在 .env 文件，检查并更新密钥
    ONEBOT_ACCESS_TOKEN=$(grep ONEBOT_ACCESS_TOKEN .env | cut -d '=' -f2)
    if [ -z "$ONEBOT_ACCESS_TOKEN" ]; then
        ONEBOT_ACCESS_TOKEN=$(generate_random_string 32)
        sed -i "s|^ONEBOT_ACCESS_TOKEN=.*|ONEBOT_ACCESS_TOKEN=${ONEBOT_ACCESS_TOKEN}|" .env
    fi

    NEKRO_ADMIN_PASSWORD=$(grep NEKRO_ADMIN_PASSWORD .env | cut -d '=' -f2)
    if [ -z "$NEKRO_ADMIN_PASSWORD" ]; then
        NEKRO_ADMIN_PASSWORD=$(generate_random_string 16)
        sed -i "s|^NEKRO_ADMIN_PASSWORD=.*|NEKRO_ADMIN_PASSWORD=${NEKRO_ADMIN_PASSWORD}|" .env
    fi

    QDRANT_API_KEY=$(grep QDRANT_API_KEY .env | cut -d '=' -f2)
    if [ -z "$QDRANT_API_KEY" ]; then
        QDRANT_API_KEY=$(generate_random_string 32)
        sed -i "s|^QDRANT_API_KEY=.*|QDRANT_API_KEY=${QDRANT_API_KEY}|" .env
    fi
fi

# 从.env文件加载环境变量
if [ -f .env ]; then
    # 设置 INSTANCE_NAME 默认值为空字符串
    INSTANCE_NAME=$(grep INSTANCE_NAME .env | cut -d '=' -f2)
    export INSTANCE_NAME=$INSTANCE_NAME

    # 确保 NEKRO_EXPOSE_PORT 有值
    NEKRO_EXPOSE_PORT=$(grep NEKRO_EXPOSE_PORT .env | cut -d '=' -f2)
    if [ -z "$NEKRO_EXPOSE_PORT" ]; then
        echo "Error: NEKRO_EXPOSE_PORT 未在 .env 文件中设置"
        exit 1
    fi
    export NEKRO_EXPOSE_PORT=$NEKRO_EXPOSE_PORT

    NAPCAT_EXPOSE_PORT=$(grep NAPCAT_EXPOSE_PORT .env | cut -d '=' -f2)
    if [ -z "$NAPCAT_EXPOSE_PORT" ]; then
        echo "Error: NAPCAT_EXPOSE_PORT 未在 .env 文件中设置"
        exit 1
    fi
    export NAPCAT_EXPOSE_PORT=$NAPCAT_EXPOSE_PORT
fi

read -p "请检查并按需修改.env文件中的配置，未修改则按照默认配置安装，确认是否继续安装？[Y/n] " answer
if [[ $answer == "n" || $answer == "N" ]]; then
    echo "安装已取消"
    exit 0
fi

# 拉取 docker-compose.yml 文件
echo "正在拉取 docker-compose.yml 文件..."
if ! wget ${BASE_URL}/docker-compose-x-napcat.yml -O docker-compose.yml; then
    echo "Error: 无法拉取 docker-compose.yml 文件，请检查您的网络连接。"
    exit 1
fi

# 拉取服务镜像
echo "拉取服务镜像..."
if ! sudo docker-compose --env-file .env pull; then
    echo "Error: 无法拉取服务镜像，请检查您的网络连接。"
    exit 1
fi

# 从.env文件加载环境变量
if [ -f .env ]; then
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
echo -e "\n正在配置防火墙..."
echo "放行 NekroAgent 主服务端口 ${NEKRO_EXPOSE_PORT:-8021}/tcp..."
if ! sudo ufw allow ${NEKRO_EXPOSE_PORT:-8021}/tcp; then
    echo "Warning: 无法放行防火墙端口 ${NEKRO_EXPOSE_PORT:-8021}，如服务访问受限，请检查防火墙设置。"
fi

echo "放行 NapCat 服务端口 ${NAPCAT_EXPOSE_PORT:-6099}/tcp..."
if ! sudo ufw allow ${NAPCAT_EXPOSE_PORT:-6099}/tcp; then
    echo "Warning: 无法放行防火墙端口 ${NAPCAT_EXPOSE_PORT:-6099}，如服务访问受限，请检查防火墙设置。"
fi

echo -e "\n=== 部署完成！==="
echo "你可以通过以下命令查看服务日志："
if [ -z "$INSTANCE_NAME" ]; then
    echo "  NekroAgent: 'sudo docker logs -f nekro_agent'"
    echo "  NapCat: 'sudo docker logs -f napcat'"
else
    echo "  NekroAgent: \"sudo docker logs -f ${INSTANCE_NAME}nekro_agent\""
    echo "  NapCat: \"sudo docker logs -f ${INSTANCE_NAME}napcat\""
fi

# 显示重要的配置信息
echo -e "\n=== 重要配置信息 ==="
ONEBOT_ACCESS_TOKEN=$(grep ONEBOT_ACCESS_TOKEN .env | cut -d '=' -f2)
NEKRO_ADMIN_PASSWORD=$(grep NEKRO_ADMIN_PASSWORD .env | cut -d '=' -f2)
QDRANT_API_KEY=$(grep QDRANT_API_KEY .env | cut -d '=' -f2)
echo "OneBot 访问令牌: ${ONEBOT_ACCESS_TOKEN}"
echo "管理员账号: admin | 密码: ${NEKRO_ADMIN_PASSWORD}"

echo -e "\n=== 服务访问信息 ==="
echo "NekroAgent 主服务端口: ${NEKRO_EXPOSE_PORT:-8021}"
echo "NekroAgent Web 访问地址: http://127.0.0.1:${NEKRO_EXPOSE_PORT:-8021}"
echo "NapCat 服务端口: ${NAPCAT_EXPOSE_PORT:-6099}"

echo -e "\n=== 注意事项 ==="
echo "1. 如果您使用的是云服务器，请在云服务商控制台的安全组中放行以下端口："
echo "   - ${NEKRO_EXPOSE_PORT:-8021}/tcp (NekroAgent 主服务)"
echo "   - ${NAPCAT_EXPOSE_PORT:-6099}/tcp (NapCat 服务)"
echo "2. 如果需要从外部访问，请将上述地址中的 127.0.0.1 替换为您的服务器公网IP"
if [ -z "$INSTANCE_NAME" ]; then
    echo "3. 请使用 'sudo docker logs napcat' 查看机器人 QQ 账号二维码进行登录"
else
    echo "3. 请使用 \"sudo docker logs ${INSTANCE_NAME}napcat\" 查看机器人 QQ 账号二维码进行登录"
fi

echo -e "\n安装完成！祝您使用愉快！"
