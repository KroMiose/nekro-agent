#!/bin/ash

# 默认不使用 napcat
WITH_NAPCAT=""

# 解析命令行参数
while [ "$#" -gt 0 ]; do
    case "$1" in
    --with-napcat)
        WITH_NAPCAT=true
        shift
        ;;
    *)
        # 未知选项
        echo "未知选项: $1"
        exit 1
        ;;
    esac
done

# Define base URLs
BASE_URLS="https://raw.githubusercontent.com/KroMiose/nekro-agent/main/docker https://ep.nekro.ai/e/KroMiose/nekro-agent/main/docker"

# 下载文件
get_remote_file() {
    local filename=$1
    local output=$2
    for base_url in $BASE_URLS; do
        url=${base_url}/${filename}
        if ! wget -q -O "$output" "$url" 2>/dev/null; then
            echo "下载失败，尝试其他源..."
            continue
        fi
        return 0
    done
    return 1
}

# 生成随机字符串的函数（兼容软路由环境）
generate_random_string() {
    local length=$1
    # 多种方法尝试生成随机字符串
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 $((length * 2)) | tr -dc 'a-zA-Z0-9' | head -c "$length"
    elif [ -c /dev/urandom ]; then
        dd if=/dev/urandom bs=1 count=$((length * 2)) 2>/dev/null | tr -dc 'a-zA-Z0-9' | head -c "$length"
    else
        # 最后备选方案：使用日期和随机数
        date +%s%N | md5sum | head -c "$length"
    fi
}

# 安装 Docker Compose
install_docker_compose() {
    echo "正在安装 Docker Compose..."
    
    # 首先尝试通过 opkg 安装
    if command -v opkg >/dev/null 2>&1; then
        echo "通过 opkg 安装 Docker Compose..."
        opkg update
        if opkg install docker-compose; then
            echo "✓ Docker Compose 安装成功"
            DOCKER_COMPOSE_CMD="docker-compose"
            return 0
        else
            echo "opkg 安装失败，尝试其他方法..."
        fi
    fi
    
    # 如果 opkg 安装失败，尝试下载二进制文件
    echo "通过二进制文件安装 Docker Compose..."
    
    # 检测系统架构
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64)
            arch="x86_64"
            ;;
        aarch64)
            arch="aarch64"
            ;;
        armv7l)
            arch="armv7"
            ;;
        *)
            echo "不支持的架构: $arch"
            return 1
            ;;
    esac
    
    # 获取最新版本
    local version
    version=$(wget -qO- https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    
    if [ -z "$version" ]; then
        version="v2.24.0"  # 备用版本
    fi
    
    # 下载 Docker Compose
    local download_url="https://github.com/docker/compose/releases/download/${version}/docker-compose-linux-${arch}"
    
    echo "下载 Docker Compose ${version} for ${arch}..."
    if wget -q -O /usr/local/bin/docker-compose "$download_url"; then
        chmod +x /usr/local/bin/docker-compose
        DOCKER_COMPOSE_CMD="docker-compose"
        echo "✓ Docker Compose 安装成功"
        return 0
    else
        echo "✗ Docker Compose 下载失败"
        return 1
    fi
}

# 检查 Docker 环境
check_docker_environment() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "错误: Docker 未安装"
        echo "iStoreOS 应该自带 Docker，请检查系统是否正常"
        exit 1
    fi
    
    # 检查 docker compose 功能
    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
        echo "✓ 使用 Docker Compose Plugin"
    elif command -v docker-compose >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker-compose"
        echo "✓ 使用 Docker Compose Standalone"
    else
        echo "Docker Compose 未安装，正在尝试安装..."
        if install_docker_compose; then
            echo "✓ Docker Compose 安装完成"
        else
            echo "错误: Docker Compose 安装失败"
            echo "请手动安装 Docker Compose 后重试"
            exit 1
        fi
    fi
}

# 检查 Docker 存储空间
check_docker_space() {
    echo "检查 Docker 存储空间..."
    
    # 获取当前 Docker 根目录
    local docker_root
    docker_root=$(docker info 2>/dev/null | grep "Docker Root Dir" | cut -d ':' -f2 | tr -d ' ' || echo "/overlay/upper/opt/docker")
    
    # 检查可用空间（以KB为单位）
    local available_kb
    if [ -d "$docker_root" ]; then
        available_kb=$(df "$docker_root" 2>/dev/null | awk 'NR==2 {print $4}' | grep -E '^[0-9]+$' || echo "0")
    else
        available_kb="0"
    fi
    
    # 转换为 MB 和 GB
    local available_mb=$((available_kb / 1024))
    local available_gb=$((available_mb / 1024))
    
    echo "当前 Docker 目录: $docker_root"
    echo "可用空间: ${available_gb}GB (${available_mb}MB)"
    
    # 如果小于 3GB，发出警告并退出
    if [ "$available_mb" -lt 3072 ]; then  # 3GB in MB
        echo ""
        echo "⚠️  警告: Docker 根目录可用空间不足 (小于 3GB)"
        echo "NekroAgent 需要较多存储空间，建议先迁移 Docker 目录到更大的存储空间"
        echo "安装已取消，请先迁移 Docker 目录后再运行安装脚本"
        exit 1
    fi
}

# 初始化变量
DOCKER_COMPOSE_CMD=""

# 检查 Docker 环境
echo "检查 Docker 环境..."
check_docker_environment

# 检查 Docker 存储空间
check_docker_space

# 设置应用目录 优先使用环境变量
if [ -z "$NEKRO_DATA_DIR" ]; then
    NEKRO_DATA_DIR=${NEKRO_DATA_DIR:-"${HOME}/srv/nekro_agent"}
fi

echo "NEKRO_DATA_DIR: $NEKRO_DATA_DIR"

export NEKRO_DATA_DIR=$NEKRO_DATA_DIR

# 创建应用目录
mkdir -p "$NEKRO_DATA_DIR" || {
    echo "Error: 无法创建应用目录 $NEKRO_DATA_DIR，请检查您的权限配置。"
    exit 1
}

# 设置目录权限
chmod -R 777 "$NEKRO_DATA_DIR"

# 进入应用目录
cd "$NEKRO_DATA_DIR" || {
    echo "Error: 无法进入应用目录 $NEKRO_DATA_DIR。"
    exit 1
}

# 如果当前目录没有 .env 文件，从仓库获取.env.example 并修改 .env 文件
if [ ! -f .env ]; then
    echo "未找到.env文件，正在从仓库获取.env.example..."
    if ! get_remote_file .env.example .env.example; then
        echo "Error: 无法获取.env.example文件，请检查网络连接或手动创建.env文件。"
        exit 1
    fi
    if ! cp .env.example .env; then
        echo "Error: 无法将文件 .env.example 复制为 .env"
        exit 1
    fi
fi

# 替换或添加 NEKRO_DATA_DIR
if grep -q "^NEKRO_DATA_DIR=" .env; then
    # 如果存在，就替换
    sed -i "s|^NEKRO_DATA_DIR=.*|NEKRO_DATA_DIR=${NEKRO_DATA_DIR}|" .env
else
    # 如果不存在，就添加
    echo "NEKRO_DATA_DIR=${NEKRO_DATA_DIR}" >>.env
fi

# 生成随机的 ONEBOT_ACCESS_TOKEN 和 NEKRO_ADMIN_PASSWORD（如果它们为空）
ONEBOT_ACCESS_TOKEN=$(grep -m1 '^ONEBOT_ACCESS_TOKEN' .env | cut -d '=' -f2)
if [ -z "$ONEBOT_ACCESS_TOKEN" ]; then
    echo "生成 ONEBOT_ACCESS_TOKEN..."
    ONEBOT_ACCESS_TOKEN=$(generate_random_string 32)
    if [ -z "$ONEBOT_ACCESS_TOKEN" ]; then
        echo "Error: 无法生成随机字符串 ONEBOT_ACCESS_TOKEN"
        exit 1
    fi
    sed -i "s|^ONEBOT_ACCESS_TOKEN=.*|ONEBOT_ACCESS_TOKEN=${ONEBOT_ACCESS_TOKEN}|" .env
fi

NEKRO_ADMIN_PASSWORD=$(grep -m1 '^NEKRO_ADMIN_PASSWORD=' .env | cut -d '=' -f2)
if [ -z "$NEKRO_ADMIN_PASSWORD" ]; then
    echo "生成 NEKRO_ADMIN_PASSWORD..."
    NEKRO_ADMIN_PASSWORD=$(generate_random_string 16)
    if [ -z "$NEKRO_ADMIN_PASSWORD" ]; then
        echo "Error: 无法生成随机字符串 NEKRO_ADMIN_PASSWORD"
        exit 1
    fi
    sed -i "s|^NEKRO_ADMIN_PASSWORD=.*|NEKRO_ADMIN_PASSWORD=${NEKRO_ADMIN_PASSWORD}|" .env
fi

QDRANT_API_KEY=$(grep -m1 '^QDRANT_API_KEY=' .env | cut -d '=' -f2)
if [ -z "$QDRANT_API_KEY" ]; then
    echo "生成 QDRANT_API_KEY..."
    QDRANT_API_KEY=$(generate_random_string 32)
    if [ -z "$QDRANT_API_KEY" ]; then
        echo "Error: 无法生成随机字符串 QDRANT_API_KEY"
        exit 1
    fi
    sed -i "s|^QDRANT_API_KEY=.*|QDRANT_API_KEY=${QDRANT_API_KEY}|" .env
fi

# 从.env文件加载环境变量
INSTANCE_NAME=$(grep -m1 '^INSTANCE_NAME=' .env | cut -d '=' -f2)
export INSTANCE_NAME=${INSTANCE_NAME:-""}

# 确保 NEKRO_EXPOSE_PORT 有值
NEKRO_EXPOSE_PORT=$(grep -m1 '^NEKRO_EXPOSE_PORT=' .env | cut -d '=' -f2)
if [ -z "$NEKRO_EXPOSE_PORT" ]; then
    echo "Error: NEKRO_EXPOSE_PORT 未在 .env 文件中设置"
    exit 1
fi
export NEKRO_EXPOSE_PORT=$NEKRO_EXPOSE_PORT

if [ "$WITH_NAPCAT" ]; then
    NAPCAT_EXPOSE_PORT=$(grep -m1 '^NAPCAT_EXPOSE_PORT=' .env | cut -d '=' -f2)
    if [ -z "$NAPCAT_EXPOSE_PORT" ]; then
        echo "Error: NAPCAT_EXPOSE_PORT 未在 .env 文件中设置"
        exit 1
    fi
    export NAPCAT_EXPOSE_PORT=$NAPCAT_EXPOSE_PORT
fi

read -r -p "请检查并按需修改.env文件中的配置，未修改则按照默认配置安装，确认是否继续安装？[Y/n] " yn
echo ""
[ -z "$yn" ] && yn=y
if ! echo "$yn" | grep -q "^[Yy]"; then
    echo -e "安装已取消..."
    exit 0
fi

# 拉取 docker-compose.yml 文件
if [ -z "$WITH_NAPCAT" ]; then
    read -r -p "是否同时使用 napcat 服务？[Y/n] " yn
    echo ""
    [ -z "$yn" ] && yn=y
    if echo "$yn" | grep -q "^[Yy]"; then
        WITH_NAPCAT=true
    else
        echo "不使用 napcat 服务"
    fi
fi

if [ "$WITH_NAPCAT" ]; then
    echo "将同时运行 napcat 服务"
    compose_file=docker-compose-x-napcat.yml
else
    compose_file=docker-compose.yml
fi

echo "正在获取 docker-compose.yml 文件..."
if ! get_remote_file "$compose_file" docker-compose.yml; then
    echo "Error: 无法拉取 docker-compose.yml 文件，请检查您的网络连接。"
    exit 1
fi

# 拉取服务镜像
echo "拉取服务镜像..."
if ! $DOCKER_COMPOSE_CMD --env-file .env pull; then
    echo "Error: 无法拉取服务镜像，请检查您的网络连接。"
    exit 1
fi

# 从.env文件加载环境变量
if [ -f .env ]; then
    echo "使用实例名称: ${INSTANCE_NAME}"
    echo "启动主服务中..."
    if ! $DOCKER_COMPOSE_CMD --env-file .env up -d; then
        echo "Error: 无法启动主服务，请检查 Docker Compose 配置。"
        exit 1
    fi
else
    echo "Error: .env 文件不存在"
    exit 1
fi

# 拉取沙盒镜像
echo "拉取沙盒镜像..."
if ! docker pull kromiose/nekro-agent-sandbox; then
    echo "Error: 无法拉取沙盒镜像，请检查您的网络连接。"
    exit 1
fi

# 配置防火墙（使用 OpenWrt 的 uci 命令）
echo "NekroAgent 主服务需放行端口 ${NEKRO_EXPOSE_PORT:-8021}/tcp..."
if [ "$WITH_NAPCAT" ]; then
    echo "NapCat 服务需放行端口 ${NAPCAT_EXPOSE_PORT:-6099}/tcp..."
fi

if command -v uci >/dev/null 2>&1; then
    echo -e "\n正在配置防火墙..."
    
    # 检查并添加 NekroAgent 端口
    if ! uci show firewall | grep -q "nekro_agent.*${NEKRO_EXPOSE_PORT:-8021}"; then
        uci add firewall rule
        uci set firewall.@rule[-1].name='NekroAgent'
        uci set firewall.@rule[-1].src='wan'
        uci set firewall.@rule[-1].proto='tcp'
        uci set firewall.@rule[-1].dest_port="${NEKRO_EXPOSE_PORT:-8021}"
        uci set firewall.@rule[-1].target='ACCEPT'
        echo "已添加 NekroAgent 防火墙规则"
    else
        echo "NekroAgent 防火墙规则已存在"
    fi

    # 检查并添加 NapCat 端口（如果使用）
    if [ "$WITH_NAPCAT" ]; then
        if ! uci show firewall | grep -q "napcat.*${NAPCAT_EXPOSE_PORT:-6099}"; then
            uci add firewall rule
            uci set firewall.@rule[-1].name='NapCat'
            uci set firewall.@rule[-1].src='wan'
            uci set firewall.@rule[-1].proto='tcp'
            uci set firewall.@rule[-1].dest_port="${NAPCAT_EXPOSE_PORT:-6099}"
            uci set firewall.@rule[-1].target='ACCEPT'
            echo "已添加 NapCat 防火墙规则"
        else
            echo "NapCat 防火墙规则已存在"
        fi
    fi
    
    uci commit firewall
    
    # 重启防火墙
    echo "重启防火墙服务..."
    if /etc/init.d/firewall restart >/dev/null 2>&1; then
        echo "防火墙规则已添加并重启"
    else
        echo "防火墙重启完成"
    fi
fi

# 获取局域网IP地址
get_lan_ip() {
    # 尝试多种方法获取局域网IP
    local ip
    ip=$(ip addr show | grep -E 'inet (192\.168|10\.|172\.1[6789]|172\.2[0-9]|172\.3[01])' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d'/' -f1)
    
    if [ -z "$ip" ]; then
        ip=$(ifconfig | grep -E 'inet (addr:)?(192\.168|10\.|172\.1[6789]|172\.2[0-9]|172\.3[01])' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d':' -f2)
    fi
    
    echo "$ip"
}

LAN_IP=$(get_lan_ip)

# 显示 Docker 存储信息
echo -e "\n=== Docker 存储信息 ==="
docker_root=$(docker info 2>/dev/null | grep "Docker Root Dir" | cut -d ':' -f2 | tr -d ' ' || echo "未知")
echo "Docker 根目录: $docker_root"

# 显示存储使用情况
echo "存储使用情况:"
df -h "$docker_root" 2>/dev/null || echo "无法获取存储信息"

echo -e "\n=== 部署完成！==="
echo "你可以通过以下命令查看服务日志："
echo "  NekroAgent: 'docker logs -f ${INSTANCE_NAME}nekro_agent'"
if [ "$WITH_NAPCAT" ]; then
    echo "  NapCat: 'docker logs -f ${INSTANCE_NAME}napcat'"
fi

# 显示重要的配置信息
echo -e "\n=== 重要配置信息 ==="
ONEBOT_ACCESS_TOKEN=$(grep -m1 '^ONEBOT_ACCESS_TOKEN=' .env | cut -d '=' -f2)
NEKRO_ADMIN_PASSWORD=$(grep -m1 '^NEKRO_ADMIN_PASSWORD=' .env | cut -d '=' -f2)
echo "OneBot 访问令牌: ${ONEBOT_ACCESS_TOKEN}"
echo "管理员账号: admin | 密码: ${NEKRO_ADMIN_PASSWORD}"

echo -e "\n=== 服务访问信息 ==="
echo "NekroAgent 主服务端口: ${NEKRO_EXPOSE_PORT:-8021}"
echo "NekroAgent Web 本地访问地址: http://127.0.0.1:${NEKRO_EXPOSE_PORT:-8021}"

# 显示局域网访问地址
if [ -n "$LAN_IP" ]; then
    echo "NekroAgent Web 局域网访问地址: http://${LAN_IP}:${NEKRO_EXPOSE_PORT:-8021}"
else
    echo "NekroAgent Web 局域网访问地址: 请使用路由器IP替换127.0.0.1"
fi

if [ "$WITH_NAPCAT" ]; then
    echo "NapCat 服务端口: ${NAPCAT_EXPOSE_PORT:-6099}"
    echo "NapCat 服务本地地址: http://127.0.0.1:${NAPCAT_EXPOSE_PORT:-6099}"
    if [ -n "$LAN_IP" ]; then
        echo "NapCat 服务局域网访问地址: http://${LAN_IP}:${NAPCAT_EXPOSE_PORT:-6099}"
    else
        echo "NapCat 服务局域网访问地址: 请使用路由器IP替换127.0.0.1"
    fi
else
    echo "OneBot WebSocket 连接地址: ws://127.0.0.1:${NEKRO_EXPOSE_PORT:-8021}/onebot/v11/ws"
    if [ -n "$LAN_IP" ]; then
        echo "OneBot WebSocket 局域网连接地址: ws://${LAN_IP}:${NEKRO_EXPOSE_PORT:-8021}/onebot/v11/ws"
    else
        echo "OneBot WebSocket 局域网连接地址: 请使用路由器IP替换127.0.0.1"
    fi
fi

echo -e "\n=== 注意事项 ==="
echo "1. 软路由防火墙规则已自动配置"
echo "2. 请使用 'docker logs ${INSTANCE_NAME}napcat' 查看机器人 QQ 账号二维码进行登录"
echo "3. 应用数据存储在: $NEKRO_DATA_DIR"

echo -e "\n安装完成！祝您使用愉快！"