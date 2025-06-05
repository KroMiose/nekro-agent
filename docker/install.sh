#!/bin/bash

# 默认不使用 napcat
WITH_NAPCAT=""

# 解析命令行参数
while [[ "$#" -gt 0 ]]; do
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
BASE_URLS=(
    "https://raw.githubusercontent.com/KroMiose/nekro-agent/main/docker"
    "https://raw.gitcode.com/gh_mirrors/ne/nekro-agent/raw/main/docker"
)

# Docker 镜像
DOCKER_IMAGE_MIRRORS=(
    "https://docker.m.daocloud.io"
    "https://docker.1ms.run"
    "https://ccr.ccs.tencentyun.com"
)

# 下载文件
get_remote_file() {
    local filename=$1
    local output=$2
    for base_url in "${BASE_URLS[@]}"; do
        url=${base_url}/${filename}
        if ! curl -sL -f -o "$output" "$url"; then
            echo "下载失败，尝试其他源..."
            continue
        fi
        return
    done
    return 1
}

# 生成随机字符串的函数
generate_random_string() {
    local length=$1
    tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w "$length" | head -n 1
}

# 选择 Docker 安装镜像
select_docker_install_mirror() {
    echo "请选择使用的 Docker 安装源："
    echo "    1) Docker 官方"
    echo "    2) 阿里"
    echo "    3) Azure 中国云"

    read -r -p "请输入选项数字 (默认为 1): " num
    echo ""
    [ -z "$num" ] && num=1
    case "$num" in
        1)
            ;;
        2)
            DOCKER_PKG_MIRROR="Aliyun"
            ;;
        3)
            DOCKER_PKG_MIRROR="AzureChinaCloud"
            ;;
        *)
            >&2 echo "未知选项，退出..."
            exit 1
            ;;
    esac
}

# 通过脚本安装 docker
install_docker_via_official_script() {
    mirror="${1:-Aliyun}"
    max_retries=3
    attempt_num=0

    if command -v apt-get &>/dev/null; then
        echo "Warn: 为避免冲突，将卸载可能已从系统安装的 docker.io docker-doc docker-compose podman-docker containerd runc"
        for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove $pkg; done
    fi
    echo "尝试获取 Docker 安装脚本..."
    while [ "$attempt_num" -le "$max_retries" ]; do
        if content=$(curl -fsSL https://get.docker.com); then
            echo "Docker 安装脚本下载完成."
            # 使用 sed 命令修改 sleep 以取消等待
            if printf '%s\n' "$content" | sed 's#sleep#test#g' | sh -s -- --mirror "$mirror"; then
                DOCKER_COMPOSE_CMD="docker compose"
                return 0
            else
                echo "Docker 安装失败..." >&2
                return 1
            fi
        else
            if [ "$attempt_num" -eq "$max_retries" ]; then
                echo "Docker 安装脚本下载失败..." >&2
                return 1
            fi
            echo "Docker 安装脚本下载失败，正在重试($((attempt_num + 1))/$max_retries)"
            sleep 1
        fi
        attempt_num=$((attempt_num + 1))
    done
    return 1
}

# Docker 备用安装方式
install_docker_fallback() {
    if ! command -v apt-get &>/dev/null; then
        echo "包管理器非 apt，暂不支持..."
        return 1
    fi
    echo "正在更新软件源..."
    if ! sudo apt-get update; then
        echo "Error: 更新软件源失败，请检查您的网络连接。"
        return 1
    fi
    echo "正在安装 Docker..."
    if ! sudo apt-get install -y docker.io docker-compose; then
        echo "Error: Docker 安装失败，请检查您的网络连接或软件源配置。" >&2
        return 1
    fi
    DOCKER_COMPOSE_CMD=docker-compose
}

# 添加 Docker 镜像源
add_docker_mirrors_prepend() {
    if [[ $# -eq 0 ]]; then
        return 1
    fi

    if ! command -v jq &> /dev/null; then
        echo "Error: jq 未安装" >&2
        return 1
    fi

    local daemon_file="/etc/docker/daemon.json"
    local current_json_input="{}"
    local mirrors_array_string="[]"
    if (($# > 0)); then
        mirrors_array_string=$(printf '%s\n' "$@" | jq -R . | jq -s .)
    fi

    if sudo test -f "$daemon_file" && sudo test -s "$daemon_file"; then
        if sudo jq -e 'type == "object"' "$daemon_file" >/dev/null 2>&1; then
            current_json_input=$(cat "$daemon_file")
        else
            echo "Error: $daemon_file 文件内容有误。" >&2
            echo "请修复该文件或将其删除后重试。" >&2
            return 1
        fi
        sudo cp "$daemon_file" "$daemon_file.bak"
    else
        sudo mkdir -p "/etc/docker/"
    fi

    local updated_json
    updated_json=$(echo "$current_json_input" | jq \
        --argjson new_mirrors_jq "$mirrors_array_string" \
        'if .["registry-mirrors"] != null and (.["registry-mirrors"] | type) != "array" then
                error("Error: daemon.json 中的 registry-mirrors 已存在但不是一个数组！请检查文件内容。")
        else
            .["registry-mirrors"] = ($new_mirrors_jq) + (.["registry-mirrors"] // [])
        end | .["registry-mirrors"] = ((.["registry-mirrors"] // []) | unique)'
    )

    # shellcheck disable=SC2181
    if [[ $? -ne 0 ]] || [[ -z "$updated_json" ]]; then
        echo "Error: jq 处理 JSON 失败。" >&2
        return 1
    fi

    if echo "$updated_json" | sudo tee "$daemon_file" > /dev/null; then
        return 0
    fi
    echo "Error: 写入 $daemon_file 文件失败。" >&2
    return 1
}

DOCKER_COMPOSE_CMD=""
if command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE_CMD=docker-compose
elif docker compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
fi

# 安装 Docker
if ! command -v docker &>/dev/null && [[ -z $DOCKER_COMPOSE_CMD ]]; then
    echo "NerkoAgent 依赖于 Docker Compose，当前环境缺失"
    echo "优先使用 Docker 官方脚本进行安装"
    if ! command -v apt-get &>/dev/null; then
        echo "Warn: 您可能需要手动卸载已安装的 docker"
    fi

    read -r -p "是否安装？[Y/n] " yn
    echo ""
    [ -z "$yn" ] && yn=y
    if ! [[ "$yn" =~ ^[Yy]$ ]]; then
        echo "已取消..." >&2
        exit 1
    fi
    echo "正在通过 Docker 官方安装脚本进行安装"
    select_docker_install_mirror
    if ! install_docker_via_official_script "$DOCKER_PKG_MIRROR"; then
        echo "Docker 安装失败..." >&2
        echo "正在尝试备用安装方式..."
        if ! install_docker_fallback; then
            echo "安装失败，退出..." >&2
            exit 1
        fi
    fi
fi

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

# 设置开放目录权限
sudo chmod -R 777 "$NEKRO_DATA_DIR"

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
    ONEBOT_ACCESS_TOKEN=$(generate_random_string 32)
    sed -i "s|^ONEBOT_ACCESS_TOKEN=.*|ONEBOT_ACCESS_TOKEN=${ONEBOT_ACCESS_TOKEN}|" .env
fi

NEKRO_ADMIN_PASSWORD=$(grep -m1 '^NEKRO_ADMIN_PASSWORD=' .env | cut -d '=' -f2)
if [ -z "$NEKRO_ADMIN_PASSWORD" ]; then
    NEKRO_ADMIN_PASSWORD=$(generate_random_string 16)
    sed -i "s|^NEKRO_ADMIN_PASSWORD=.*|NEKRO_ADMIN_PASSWORD=${NEKRO_ADMIN_PASSWORD}|" .env
fi

QDRANT_API_KEY=$(grep -m1 '^QDRANT_API_KEY=' .env | cut -d '=' -f2)
if [ -z "$QDRANT_API_KEY" ]; then
    QDRANT_API_KEY=$(generate_random_string 32)
    sed -i "s|^QDRANT_API_KEY=.*|QDRANT_API_KEY=${QDRANT_API_KEY}|" .env
fi

# 从.env文件加载环境变量
# 设置 INSTANCE_NAME 默认值为空字符串
INSTANCE_NAME=$(grep -m1 '^INSTANCE_NAME=' .env | cut -d '=' -f2)
export INSTANCE_NAME=$INSTANCE_NAME

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
if ! [[ "$yn" =~ ^[Yy]$ ]]; then
    echo -e "安装已取消..."
    exit 0
fi

# 添加 Docker 镜像到 daemon.json
echo -n "是否添加 Docker 镜像源（若无 jq 将安装）？[Y/n] "
read -r yn
echo ""
[ -z "$yn" ] && yn=y
if [[ "$yn" =~ ^[Yy]$ ]]; then
    if ! command -v jq &>/dev.null; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        else
            echo "包管理器非 apt，暂不支持..."
        fi
    fi
    if add_docker_mirrors_prepend "${DOCKER_IMAGE_MIRRORS[@]}"; then
        sudo systemctl daemon-reload
        sudo systemctl restart docker
    else
        echo "Error: 添加失败" >&2
    fi
fi

# 拉取 docker-compose.yml 文件
if [ -z "$WITH_NAPCAT" ]; then
    read -r -p "是否同时使用 napcat 服务？[Y/n] " yn
    echo ""
    [ -z "$yn" ] && yn=y
    if [[ "$yn" =~ ^[Yy]$ ]]; then
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
if ! sudo bash -c "$DOCKER_COMPOSE_CMD --env-file .env pull"; then
    echo "Error: 无法拉取服务镜像，请检查您的网络连接。"
    exit 1
fi

# 从.env文件加载环境变量
if [ -f .env ]; then
    # 使用 --env-file 参数而不是 export
    echo "使用实例名称: ${INSTANCE_NAME}"
    echo "启动主服务中..."
    if ! sudo bash -c "$DOCKER_COMPOSE_CMD --env-file .env up -d"; then
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
echo "NekroAgent 主服务需放行端口 ${NEKRO_EXPOSE_PORT:-8021}/tcp..."
if [ "$WITH_NAPCAT" ]; then
    echo "NapCat 服务需放行端口 ${NAPCAT_EXPOSE_PORT:-6099}/tcp..."
fi
if command -v ufw &>/dev/null; then
    echo -e "\n正在配置防火墙..."
    if ! sudo ufw allow "${NEKRO_EXPOSE_PORT:-8021}/tcp"; then
        echo "Warning: 无法放行防火墙端口 ${NEKRO_EXPOSE_PORT:-8021}，如服务访问受限，请检查防火墙设置。"
    fi

    if [ "$WITH_NAPCAT" ]; then
        if ! sudo ufw allow "${NAPCAT_EXPOSE_PORT:-6099}/tcp"; then
            echo "Warning: 无法放行防火墙端口 ${NAPCAT_EXPOSE_PORT:-6099}，如服务访问受限，请检查防火墙设置。"
        fi
    fi
fi

echo -e "\n=== 部署完成！==="
echo "你可以通过以下命令查看服务日志："
echo "  NekroAgent: 'sudo docker logs -f ${INSTANCE_NAME}nekro_agent'"
echo "  NapCat: 'sudo docker logs -f ${INSTANCE_NAME}napcat'"

# 显示重要的配置信息
echo -e "\n=== 重要配置信息 ==="
ONEBOT_ACCESS_TOKEN=$(grep -m1 '^ONEBOT_ACCESS_TOKEN=' .env | cut -d '=' -f2)
NEKRO_ADMIN_PASSWORD=$(grep -m1 '^NEKRO_ADMIN_PASSWORD=' .env | cut -d '=' -f2)
QDRANT_API_KEY=$(grep -m1 '^QDRANT_API_KEY=' .env | cut -d '=' -f2)
echo "OneBot 访问令牌: ${ONEBOT_ACCESS_TOKEN}"
echo "管理员账号: admin | 密码: ${NEKRO_ADMIN_PASSWORD}"

echo -e "\n=== 服务访问信息 ==="
echo "NekroAgent 主服务端口: ${NEKRO_EXPOSE_PORT:-8021}"
echo "NekroAgent Web 访问地址: http://127.0.0.1:${NEKRO_EXPOSE_PORT:-8021}"
if [ "$WITH_NAPCAT" ]; then
    echo "NapCat 服务端口: ${NAPCAT_EXPOSE_PORT:-6099}"
else
    echo "OneBot WebSocket 连接地址: ws://127.0.0.1:${NEKRO_EXPOSE_PORT:-8021}/onebot/v11/ws"
fi

echo -e "\n=== 注意事项 ==="
echo "1. 如果您使用的是云服务器，请在云服务商控制台的安全组中放行以下端口："
echo "   - ${NEKRO_EXPOSE_PORT:-8021}/tcp (NekroAgent 主服务)"
if [ "$WITH_NAPCAT" ]; then
    echo "   - ${NAPCAT_EXPOSE_PORT:-6099}/tcp (NapCat 服务)"
fi
echo "2. 如果需要从外部访问，请将上述地址中的 127.0.0.1 替换为您的服务器公网IP"
echo "3. 请使用 'sudo docker logs ${INSTANCE_NAME}napcat' 查看机器人 QQ 账号二维码进行登录"

echo -e "\n安装完成！祝您使用愉快！"
