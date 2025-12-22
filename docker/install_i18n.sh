#!/bin/bash

# ============================================
# Language Selection / 语言选择
# ============================================

# Detect system language
detect_language() {
    case "${LANG:-}" in
        zh_CN*|zh_TW*|zh_HK*|zh_SG*)
            echo "zh"
            ;;
        *)
            echo "en"
            ;;
    esac
}

# Select language at startup
select_language() {
    echo "================================================"
    echo "Please select language / 请选择语言:"
    echo "  1) English"
    echo "  2) 简体中文"
    echo "================================================"
    read -r -p "Enter option (default: auto-detect) / 输入选项 (默认: 自动检测): " lang_choice
    echo ""
    
    case "$lang_choice" in
        1)
            LANG_SELECTED="en"
            ;;
        2)
            LANG_SELECTED="zh"
            ;;
        "")
            LANG_SELECTED=$(detect_language)
            ;;
        *)
            echo "Invalid option, using auto-detect / 无效选项，使用自动检测"
            LANG_SELECTED=$(detect_language)
            ;;
    esac
}

# Initialize language
select_language

# ============================================
# Text Translation Functions / 文本翻译函数
# ============================================

t() {
    local key="$1"
    case "$LANG_SELECTED" in
        zh)
            case "$key" in
                "unknown_option") echo "未知选项" ;;
                "download_failed_retry") echo "下载失败，尝试其他源..." ;;
                "select_docker_mirror") echo "请选择使用的 Docker 安装源：" ;;
                "docker_official") echo "Docker 官方" ;;
                "aliyun") echo "阿里" ;;
                "azure_china") echo "Azure 中国云" ;;
                "enter_option_default") echo "请输入选项数字 (默认为 1): " ;;
                "unknown_option_exit") echo "未知选项，退出..." ;;
                "warn_uninstall_docker") echo "Warn: 为避免冲突，将卸载可能已从系统安装的 docker.io docker-doc docker-compose podman-docker containerd runc" ;;
                "try_get_docker_script") echo "尝试获取 Docker 安装脚本..." ;;
                "docker_script_downloaded") echo "Docker 安装脚本下载完成." ;;
                "docker_install_failed") echo "Docker 安装失败..." ;;
                "docker_script_download_failed") echo "Docker 安装脚本下载失败..." ;;
                "docker_script_download_retry") echo "Docker 安装脚本下载失败，正在重试" ;;
                "pkg_manager_not_apt") echo "包管理器非 apt，暂不支持..." ;;
                "updating_sources") echo "正在更新软件源..." ;;
                "error_update_sources") echo "Error: 更新软件源失败，请检查您的网络连接。" ;;
                "installing_docker") echo "正在安装 Docker..." ;;
                "error_docker_install") echo "Error: Docker 安装失败，请检查您的网络连接或软件源配置。" ;;
                "error_jq_not_installed") echo "Error: jq 未安装" ;;
                "error_daemon_json_invalid") echo "Error: /etc/docker/daemon.json 文件内容有误。" ;;
                "fix_or_delete_file") echo "请修复该文件或将其删除后重试。" ;;
                "error_jq_process_failed") echo "Error: jq 处理 JSON 失败。" ;;
                "error_write_daemon_json") echo "Error: 写入 /etc/docker/daemon.json 文件失败。" ;;
                "nekro_depends_docker") echo "NerkoAgent 依赖于 Docker Compose，当前环境缺失" ;;
                "prefer_official_script") echo "优先使用 Docker 官方脚本进行安装" ;;
                "warn_manual_uninstall") echo "Warn: 您可能需要手动卸载已安装的 docker" ;;
                "confirm_install") echo "是否安装？[Y/n] " ;;
                "cancelled") echo "已取消..." ;;
                "installing_via_official") echo "正在通过 Docker 官方安装脚本进行安装" ;;
                "trying_fallback") echo "正在尝试备用安装方式..." ;;
                "install_failed_exit") echo "安装失败，退出..." ;;
                "nekro_data_dir") echo "NEKRO_DATA_DIR: " ;;
                "error_create_dir") echo "Error: 无法创建应用目录 $NEKRO_DATA_DIR，请检查您的权限配置。" ;;
                "error_enter_dir") echo "Error: 无法进入应用目录 $NEKRO_DATA_DIR。" ;;
                "env_not_found") echo "未找到.env文件，正在从仓库获取.env.example..." ;;
                "error_get_env_example") echo "Error: 无法获取.env.example文件，请检查网络连接或手动创建.env文件。" ;;
                "error_copy_env") echo "Error: 无法将文件 .env.example 复制为 .env" ;;
                "error_nekro_port_not_set") echo "Error: NEKRO_EXPOSE_PORT 未在 .env 文件中设置" ;;
                "error_napcat_port_not_set") echo "Error: NAPCAT_EXPOSE_PORT 未在 .env 文件中设置" ;;
                "confirm_env_config") echo "请检查并按需修改.env文件中的配置，未修改则按照默认配置安装，确认是否继续安装？[Y/n] " ;;
                "install_cancelled") echo "安装已取消..." ;;
                "add_docker_mirrors") echo "是否添加 Docker 镜像源（若无 jq 将安装）？[Y/n] " ;;
                "error_add_failed") echo "Error: 添加失败" ;;
                "use_napcat") echo "是否同时使用 napcat 服务？[Y/n] " ;;
                "not_use_napcat") echo "不使用 napcat 服务" ;;
                "will_run_napcat") echo "将同时运行 napcat 服务" ;;
                "getting_compose_file") echo "正在获取 docker-compose.yml 文件..." ;;
                "error_get_compose") echo "Error: 无法拉取 docker-compose.yml 文件，请检查您的网络连接。" ;;
                "pulling_images") echo "拉取服务镜像..." ;;
                "error_pull_images") echo "Error: 无法拉取服务镜像，请检查您的网络连接。" ;;
                "using_instance_name") echo "使用实例名称: " ;;
                "starting_service") echo "启动主服务中..." ;;
                "error_start_service") echo "Error: 无法启动主服务，请检查 Docker Compose 配置。" ;;
                "error_env_not_exist") echo "Error: .env 文件不存在" ;;
                "pulling_sandbox") echo "拉取沙盒镜像..." ;;
                "error_pull_sandbox") echo "Error: 无法拉取沙盒镜像，请检查您的网络连接。" ;;
                "need_allow_port") echo "NekroAgent 主服务需放行端口" ;;
                "napcat_need_allow_port") echo "NapCat 服务需放行端口" ;;
                "configuring_firewall") echo "正在配置防火墙..." ;;
                "warn_firewall_failed") echo "Warning: 无法放行防火墙端口" ;;
                "warn_firewall_check") echo "，如服务访问受限，请检查防火墙设置。" ;;
                "deployment_complete") echo "=== 部署完成！===" ;;
                "view_logs") echo "你可以通过以下命令查看服务日志：" ;;
                "important_config") echo "=== 重要配置信息 ===" ;;
                "onebot_token") echo "OneBot 访问令牌: " ;;
                "admin_account") echo "管理员账号: admin | 密码: " ;;
                "service_access") echo "=== 服务访问信息 ===" ;;
                "nekro_port") echo "NekroAgent 主服务端口: " ;;
                "nekro_web_url") echo "NekroAgent Web 访问地址: " ;;
                "napcat_port") echo "NapCat 服务端口: " ;;
                "onebot_ws_url") echo "OneBot WebSocket 连接地址: " ;;
                "notes") echo "=== 注意事项 ===" ;;
                "note_1") echo "1. 如果您使用的是云服务器，请在云服务商控制台的安全组中放行以下端口：" ;;
                "note_nekro_port") echo "   - ${NEKRO_EXPOSE_PORT:-8021}/tcp (NekroAgent 主服务)" ;;
                "note_napcat_port") echo "   - ${NAPCAT_EXPOSE_PORT:-6099}/tcp (NapCat 服务)" ;;
                "note_2") echo "2. 如果需要从外部访问，请将上述地址中的 127.0.0.1 替换为您的服务器公网IP" ;;
                "note_3") echo "3. 请使用 'sudo docker logs ${INSTANCE_NAME}napcat' 查看机器人 QQ 账号二维码进行登录" ;;
                "install_complete") echo "安装完成！祝您使用愉快！" ;;
                *) echo "$key" ;;
            esac
            ;;
        en)
            case "$key" in
                "unknown_option") echo "Unknown option" ;;
                "download_failed_retry") echo "Download failed, trying other sources..." ;;
                "select_docker_mirror") echo "Please select Docker installation source:" ;;
                "docker_official") echo "Docker Official" ;;
                "aliyun") echo "Aliyun" ;;
                "azure_china") echo "Azure China Cloud" ;;
                "enter_option_default") echo "Enter option number (default: 1): " ;;
                "unknown_option_exit") echo "Unknown option, exiting..." ;;
                "warn_uninstall_docker") echo "Warn: To avoid conflicts, will uninstall possibly installed docker.io docker-doc docker-compose podman-docker containerd runc" ;;
                "try_get_docker_script") echo "Trying to get Docker installation script..." ;;
                "docker_script_downloaded") echo "Docker installation script downloaded." ;;
                "docker_install_failed") echo "Docker installation failed..." ;;
                "docker_script_download_failed") echo "Docker installation script download failed..." ;;
                "docker_script_download_retry") echo "Docker installation script download failed, retrying" ;;
                "pkg_manager_not_apt") echo "Package manager is not apt, not supported yet..." ;;
                "updating_sources") echo "Updating package sources..." ;;
                "error_update_sources") echo "Error: Failed to update package sources, please check your network connection." ;;
                "installing_docker") echo "Installing Docker..." ;;
                "error_docker_install") echo "Error: Docker installation failed, please check your network connection or package source configuration." ;;
                "error_jq_not_installed") echo "Error: jq is not installed" ;;
                "error_daemon_json_invalid") echo "Error: /etc/docker/daemon.json file content is invalid." ;;
                "fix_or_delete_file") echo "Please fix the file or delete it and try again." ;;
                "error_jq_process_failed") echo "Error: jq JSON processing failed." ;;
                "error_write_daemon_json") echo "Error: Failed to write /etc/docker/daemon.json file." ;;
                "nekro_depends_docker") echo "NerkoAgent depends on Docker Compose, which is missing in the current environment" ;;
                "prefer_official_script") echo "Prefer to install using Docker official script" ;;
                "warn_manual_uninstall") echo "Warn: You may need to manually uninstall the installed docker" ;;
                "confirm_install") echo "Install? [Y/n] " ;;
                "cancelled") echo "Cancelled..." ;;
                "installing_via_official") echo "Installing via Docker official script" ;;
                "trying_fallback") echo "Trying fallback installation method..." ;;
                "install_failed_exit") echo "Installation failed, exiting..." ;;
                "nekro_data_dir") echo "NEKRO_DATA_DIR: " ;;
                "error_create_dir") echo "Error: Cannot create application directory $NEKRO_DATA_DIR, please check your permissions." ;;
                "error_enter_dir") echo "Error: Cannot enter application directory $NEKRO_DATA_DIR." ;;
                "env_not_found") echo ".env file not found, getting .env.example from repository..." ;;
                "error_get_env_example") echo "Error: Cannot get .env.example file, please check network connection or manually create .env file." ;;
                "error_copy_env") echo "Error: Cannot copy file .env.example to .env" ;;
                "error_nekro_port_not_set") echo "Error: NEKRO_EXPOSE_PORT is not set in .env file" ;;
                "error_napcat_port_not_set") echo "Error: NAPCAT_EXPOSE_PORT is not set in .env file" ;;
                "confirm_env_config") echo "Please check and modify the configuration in .env file as needed. If not modified, install with default configuration. Continue installation? [Y/n] " ;;
                "install_cancelled") echo "Installation cancelled..." ;;
                "add_docker_mirrors") echo "Add Docker registry mirrors (will install jq if not present)? [Y/n] " ;;
                "error_add_failed") echo "Error: Add failed" ;;
                "use_napcat") echo "Use napcat service together? [Y/n] " ;;
                "not_use_napcat") echo "Not using napcat service" ;;
                "will_run_napcat") echo "Will run napcat service together" ;;
                "getting_compose_file") echo "Getting docker-compose.yml file..." ;;
                "error_get_compose") echo "Error: Cannot pull docker-compose.yml file, please check your network connection." ;;
                "pulling_images") echo "Pulling service images..." ;;
                "error_pull_images") echo "Error: Cannot pull service images, please check your network connection." ;;
                "using_instance_name") echo "Using instance name: " ;;
                "starting_service") echo "Starting main service..." ;;
                "error_start_service") echo "Error: Cannot start main service, please check Docker Compose configuration." ;;
                "error_env_not_exist") echo "Error: .env file does not exist" ;;
                "pulling_sandbox") echo "Pulling sandbox image..." ;;
                "error_pull_sandbox") echo "Error: Cannot pull sandbox image, please check your network connection." ;;
                "need_allow_port") echo "NekroAgent main service needs to allow port" ;;
                "napcat_need_allow_port") echo "NapCat service needs to allow port" ;;
                "configuring_firewall") echo "Configuring firewall..." ;;
                "warn_firewall_failed") echo "Warning: Cannot allow firewall port" ;;
                "warn_firewall_check") echo ", if service access is restricted, please check firewall settings." ;;
                "deployment_complete") echo "=== Deployment Complete! ===" ;;
                "view_logs") echo "You can view service logs with the following commands:" ;;
                "important_config") echo "=== Important Configuration Information ===" ;;
                "onebot_token") echo "OneBot Access Token: " ;;
                "admin_account") echo "Admin Account: admin | Password: " ;;
                "service_access") echo "=== Service Access Information ===" ;;
                "nekro_port") echo "NekroAgent Main Service Port: " ;;
                "nekro_web_url") echo "NekroAgent Web Access URL: " ;;
                "napcat_port") echo "NapCat Service Port: " ;;
                "onebot_ws_url") echo "OneBot WebSocket Connection URL: " ;;
                "notes") echo "=== Notes ===" ;;
                "note_1") echo "1. If you are using a cloud server, please allow the following ports in the security group of your cloud provider's console:" ;;
                "note_nekro_port") echo "   - ${NEKRO_EXPOSE_PORT:-8021}/tcp (NekroAgent Main Service)" ;;
                "note_napcat_port") echo "   - ${NAPCAT_EXPOSE_PORT:-6099}/tcp (NapCat Service)" ;;
                "note_2") echo "2. If you need to access from outside, please replace 127.0.0.1 in the above addresses with your server's public IP" ;;
                "note_3") echo "3. Please use 'sudo docker logs ${INSTANCE_NAME}napcat' to view the QQ account QR code for bot login" ;;
                "install_complete") echo "Installation complete! Enjoy!" ;;
                *) echo "$key" ;;
            esac
            ;;
    esac
}

# ============================================
# Original Script Logic / 原始脚本逻辑
# ============================================

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
        echo "$(t 'unknown_option'): $1"
        exit 1
        ;;
    esac
done

# Define base URLs
BASE_URLS=(
    "https://raw.githubusercontent.com/KroMiose/nekro-agent/main/docker"
    "https://ep.nekro.ai/e/KroMiose/nekro-agent/main/docker"
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
        if ! curl -fsSL -m 30 -o "$output" "$url"; then
            echo "$(t 'download_failed_retry')"
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
    echo "$(t 'select_docker_mirror')"
    echo "    1) $(t 'docker_official')"
    echo "    2) $(t 'aliyun')"
    echo "    3) $(t 'azure_china')"

    read -r -p "$(t 'enter_option_default')" num
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
            >&2 echo "$(t 'unknown_option_exit')"
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
        echo "$(t 'warn_uninstall_docker')"
        for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove $pkg; done
    fi
    echo "$(t 'try_get_docker_script')"
    while [ "$attempt_num" -le "$max_retries" ]; do
        if content=$(curl -fsSL -m 30 https://get.docker.com); then
            echo "$(t 'docker_script_downloaded')"
            # 使用 sed 命令修改 sleep 以取消等待
            if printf '%s\n' "$content" | sed 's#sleep#test#g' | sh -s -- --mirror "$mirror"; then
                DOCKER_COMPOSE_CMD="docker compose"
                return 0
            else
                echo "$(t 'docker_install_failed')" >&2
                return 1
            fi
        else
            if [ "$attempt_num" -eq "$max_retries" ]; then
                echo "$(t 'docker_script_download_failed')" >&2
                return 1
            fi
            echo "$(t 'docker_script_download_retry')($((attempt_num + 1))/$max_retries)"
            sleep 1
        fi
        attempt_num=$((attempt_num + 1))
    done
    return 1
}

# Docker 备用安装方式
install_docker_fallback() {
    if ! command -v apt-get &>/dev/null; then
        echo "$(t 'pkg_manager_not_apt')"
        return 1
    fi
    echo "$(t 'updating_sources')"
    if ! sudo apt-get update; then
        echo "$(t 'error_update_sources')"
        return 1
    fi
    echo "$(t 'installing_docker')"
    if ! sudo apt-get install -y docker.io docker-compose; then
        echo "$(t 'error_docker_install')" >&2
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
        echo "$(t 'error_jq_not_installed')" >&2
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
            echo "$(t 'error_daemon_json_invalid')" >&2
            echo "$(t 'fix_or_delete_file')" >&2
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
                error("Error: daemon.json registry-mirrors exists but is not an array!")
        else
            .["registry-mirrors"] = ($new_mirrors_jq) + (.["registry-mirrors"] // [])
        end | .["registry-mirrors"] = ((.["registry-mirrors"] // []) | unique)'
    )

    # shellcheck disable=SC2181
    if [[ $? -ne 0 ]] || [[ -z "$updated_json" ]]; then
        echo "$(t 'error_jq_process_failed')" >&2
        return 1
    fi

    if echo "$updated_json" | sudo tee "$daemon_file" > /dev/null; then
        return 0
    fi
    echo "$(t 'error_write_daemon_json')" >&2
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
    echo "$(t 'nekro_depends_docker')"
    echo "$(t 'prefer_official_script')"
    if ! command -v apt-get &>/dev/null; then
        echo "$(t 'warn_manual_uninstall')"
    fi

    read -r -p "$(t 'confirm_install')" yn
    echo ""
    [ -z "$yn" ] && yn=y
    if ! [[ "$yn" =~ ^[Yy]$ ]]; then
        echo "$(t 'cancelled')" >&2
        exit 1
    fi
    echo "$(t 'installing_via_official')"
    select_docker_install_mirror
    if ! install_docker_via_official_script "$DOCKER_PKG_MIRROR"; then
        echo "$(t 'docker_install_failed')" >&2
        echo "$(t 'trying_fallback')"
        if ! install_docker_fallback; then
            echo "$(t 'install_failed_exit')" >&2
            exit 1
        fi
    fi
fi

# 设置应用目录 优先使用环境变量
if [ -z "$NEKRO_DATA_DIR" ]; then
    NEKRO_DATA_DIR=${NEKRO_DATA_DIR:-"${HOME}/srv/nekro_agent"}
fi

echo "$(t 'nekro_data_dir')$NEKRO_DATA_DIR"

export NEKRO_DATA_DIR=$NEKRO_DATA_DIR

# 创建应用目录
mkdir -p "$NEKRO_DATA_DIR" || {
    echo "$(t 'error_create_dir')"
    exit 1
}

# 设置开放目录权限
sudo chmod -R 777 "$NEKRO_DATA_DIR"

# 进入应用目录
cd "$NEKRO_DATA_DIR" || {
    echo "$(t 'error_enter_dir')"
    exit 1
}

# 如果当前目录没有 .env 文件，从仓库获取.env.example 并修改 .env 文件
if [ ! -f .env ]; then
    echo "$(t 'env_not_found')"
    if ! get_remote_file .env.example .env.example; then
        echo "$(t 'error_get_env_example')"
        exit 1
    fi
    if ! cp .env.example .env; then
        echo "$(t 'error_copy_env')"
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
    echo "$(t 'error_nekro_port_not_set')"
    exit 1
fi
export NEKRO_EXPOSE_PORT=$NEKRO_EXPOSE_PORT

if [ "$WITH_NAPCAT" ]; then
    NAPCAT_EXPOSE_PORT=$(grep -m1 '^NAPCAT_EXPOSE_PORT=' .env | cut -d '=' -f2)
    if [ -z "$NAPCAT_EXPOSE_PORT" ]; then
        echo "$(t 'error_napcat_port_not_set')"
        exit 1
    fi
    export NAPCAT_EXPOSE_PORT=$NAPCAT_EXPOSE_PORT
fi

read -r -p "$(t 'confirm_env_config')" yn
echo ""
[ -z "$yn" ] && yn=y
if ! [[ "$yn" =~ ^[Yy]$ ]]; then
    echo -e "$(t 'install_cancelled')"
    exit 0
fi

# 添加 Docker 镜像到 daemon.json
echo -n "$(t 'add_docker_mirrors')"
read -r yn
echo ""
[ -z "$yn" ] && yn=y
if [[ "$yn" =~ ^[Yy]$ ]]; then
    if ! command -v jq &>/dev.null; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        else
            echo "$(t 'pkg_manager_not_apt')"
        fi
    fi
    if add_docker_mirrors_prepend "${DOCKER_IMAGE_MIRRORS[@]}"; then
        sudo systemctl daemon-reload
        sudo systemctl restart docker
    else
        echo "$(t 'error_add_failed')" >&2
    fi
fi

# 拉取 docker-compose.yml 文件
if [ -z "$WITH_NAPCAT" ]; then
    read -r -p "$(t 'use_napcat')" yn
    echo ""
    [ -z "$yn" ] && yn=y
    if [[ "$yn" =~ ^[Yy]$ ]]; then
        WITH_NAPCAT=true
    else
        echo "$(t 'not_use_napcat')"
    fi
fi

if [ "$WITH_NAPCAT" ]; then
    echo "$(t 'will_run_napcat')"
    compose_file=docker-compose-x-napcat.yml
else
    compose_file=docker-compose.yml
fi

echo "$(t 'getting_compose_file')"
if ! get_remote_file "$compose_file" docker-compose.yml; then
    echo "$(t 'error_get_compose')"
    exit 1
fi

# 拉取服务镜像
echo "$(t 'pulling_images')"
if ! sudo bash -c "$DOCKER_COMPOSE_CMD --env-file .env pull"; then
    echo "$(t 'error_pull_images')"
    exit 1
fi

# 从.env文件加载环境变量
if [ -f .env ]; then
    # 使用 --env-file 参数而不是 export
    echo "$(t 'using_instance_name')${INSTANCE_NAME}"
    echo "$(t 'starting_service')"
    if ! sudo bash -c "$DOCKER_COMPOSE_CMD --env-file .env up -d"; then
        echo "$(t 'error_start_service')"
        exit 1
    fi
else
    echo "$(t 'error_env_not_exist')"
    exit 1
fi

# 拉取沙盒镜像
echo "$(t 'pulling_sandbox')"
if ! sudo docker pull kromiose/nekro-agent-sandbox; then
    echo "$(t 'error_pull_sandbox')"
    exit 1
fi

# 放行防火墙端口
echo "$(t 'need_allow_port') ${NEKRO_EXPOSE_PORT:-8021}/tcp..."
if [ "$WITH_NAPCAT" ]; then
    echo "$(t 'napcat_need_allow_port') ${NAPCAT_EXPOSE_PORT:-6099}/tcp..."
fi
if command -v ufw &>/dev/null; then
    echo -e "\n$(t 'configuring_firewall')"
    if ! sudo ufw allow "${NEKRO_EXPOSE_PORT:-8021}/tcp"; then
        echo "$(t 'warn_firewall_failed') ${NEKRO_EXPOSE_PORT:-8021}$(t 'warn_firewall_check')"
    fi

    if [ "$WITH_NAPCAT" ]; then
        if ! sudo ufw allow "${NAPCAT_EXPOSE_PORT:-6099}/tcp"; then
            echo "$(t 'warn_firewall_failed') ${NAPCAT_EXPOSE_PORT:-6099}$(t 'warn_firewall_check')"
        fi
    fi
fi

echo -e "\n$(t 'deployment_complete')"
echo "$(t 'view_logs')"
echo "  NekroAgent: 'sudo docker logs -f ${INSTANCE_NAME}nekro_agent'"
echo "  NapCat: 'sudo docker logs -f ${INSTANCE_NAME}napcat'"

# 显示重要的配置信息
echo -e "\n$(t 'important_config')"
ONEBOT_ACCESS_TOKEN=$(grep -m1 '^ONEBOT_ACCESS_TOKEN=' .env | cut -d '=' -f2)
NEKRO_ADMIN_PASSWORD=$(grep -m1 '^NEKRO_ADMIN_PASSWORD=' .env | cut -d '=' -f2)
QDRANT_API_KEY=$(grep -m1 '^QDRANT_API_KEY=' .env | cut -d '=' -f2)
echo "$(t 'onebot_token')${ONEBOT_ACCESS_TOKEN}"
echo "$(t 'admin_account')${NEKRO_ADMIN_PASSWORD}"

echo -e "\n$(t 'service_access')"
echo "$(t 'nekro_port')${NEKRO_EXPOSE_PORT:-8021}"
echo "$(t 'nekro_web_url')http://127.0.0.1:${NEKRO_EXPOSE_PORT:-8021}"
if [ "$WITH_NAPCAT" ]; then
    echo "$(t 'napcat_port')${NAPCAT_EXPOSE_PORT:-6099}"
else
    echo "$(t 'onebot_ws_url')ws://127.0.0.1:${NEKRO_EXPOSE_PORT:-8021}/onebot/v11/ws"
fi

echo -e "\n$(t 'notes')"
echo "$(t 'note_1')"
echo "$(t 'note_nekro_port')"
if [ "$WITH_NAPCAT" ]; then
    echo "$(t 'note_napcat_port')"
fi
echo "$(t 'note_2')"
echo "$(t 'note_3')"

echo -e "\n$(t 'install_complete')"
