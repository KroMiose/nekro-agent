#!/bin/ash

# ============================================
# Language Selection / 语言选择
# ============================================

# 选择语言
select_language() {
    echo "================================================"
    echo "Please select language / 请选择语言:"
    echo "  1) English"
    echo "  2) 简体中文"
    echo "================================================"
    read -r -p "Enter option / 输入选项 (1/2, default: 2): " lang_choice
    echo ""
    
    case "$lang_choice" in
        1) LANG_SELECTED="en" ;;
        2) LANG_SELECTED="zh" ;;
        "") LANG_SELECTED="zh" ;;  # 默认中文
        *) LANG_SELECTED="zh" ;;
    esac
}

select_language

# ============================================
# Translation Function / 翻译函数
# ============================================

t() {
    local key="$1"
    if [ "$LANG_SELECTED" = "en" ]; then
        case "$key" in
            # 通用
            "unknown_option") echo "Unknown option" ;;
            "download_failed") echo "Download failed, trying other sources..." ;;
            "yes_no") echo "[Y/n]" ;;
            
            # Docker 镜像源
            "config_docker_mirror") echo "Configuring Docker registry mirrors..." ;;
            "backup_config") echo "Backed up original config to" ;;
            "mirror_config_done") echo "Docker registry mirrors configured" ;;
            "mirror_list") echo "Mirror list:" ;;
            "restart_docker") echo "Restarting Docker service..." ;;
            "docker_restart_done") echo "Docker service restarted" ;;
            "docker_restart_fail") echo "Docker service restart failed, please restart manually" ;;
            "remove_mirror_config") echo "Removing Docker registry mirror configuration..." ;;
            "restore_original") echo "Restored original configuration" ;;
            "removed_mirror") echo "Removed mirror configuration" ;;
            
            # Docker Compose 安装
            "install_compose") echo "Installing Docker Compose..." ;;
            "install_via_opkg") echo "Installing Docker Compose via opkg..." ;;
            "compose_install_ok") echo "Docker Compose installed successfully" ;;
            "opkg_fail_retry") echo "opkg installation failed, trying other methods..." ;;
            "install_via_binary") echo "Installing Docker Compose via binary..." ;;
            "unsupported_arch") echo "Unsupported architecture" ;;
            "download_compose") echo "Downloading Docker Compose" ;;
            "compose_download_fail") echo "Docker Compose download failed" ;;
            
            # Docker 环境检查
            "error_docker_not_installed") echo "Error: Docker is not installed" ;;
            "check_system") echo "iStoreOS should have Docker pre-installed, please check your system" ;;
            "use_compose_plugin") echo "Using Docker Compose Plugin" ;;
            "use_compose_standalone") echo "Using Docker Compose Standalone" ;;
            "compose_not_found") echo "Docker Compose not installed, trying to install..." ;;
            "compose_install_done") echo "Docker Compose installation complete" ;;
            "error_compose_install_fail") echo "Error: Docker Compose installation failed" ;;
            "please_install_compose") echo "Please install Docker Compose manually and try again" ;;
            
            # Docker 空间检查
            "check_docker_space") echo "Checking Docker storage space..." ;;
            "docker_root_dir") echo "Current Docker directory" ;;
            "available_space") echo "Available space" ;;
            "warn_low_space") echo "Warning: Docker root directory has insufficient space (less than 3GB)" ;;
            "need_more_space") echo "NekroAgent requires more storage space, recommend migrating Docker directory to larger storage" ;;
            "install_cancelled_space") echo "Installation cancelled, please migrate Docker directory first and run the install script again" ;;
            
            # Docker 环境
            "check_docker_env") echo "Checking Docker environment..." ;;
            
            # 目录和配置
            "error_create_dir") echo "Error: Cannot create application directory, please check your permissions." ;;
            "error_enter_dir") echo "Error: Cannot enter application directory" ;;
            "env_not_found") echo ".env file not found, getting .env.example from repository..." ;;
            "error_get_env") echo "Error: Cannot get .env.example file, please check network connection or create .env file manually." ;;
            "error_copy_env") echo "Error: Cannot copy .env.example to .env" ;;
            "generate_token") echo "Generating" ;;
            "error_generate_random") echo "Error: Cannot generate random string" ;;
            "error_port_not_set") echo "Error: not set in .env file" ;;
            
            # 用户确认
            "confirm_env") echo "Please check and modify .env configuration as needed. Continue with installation?" ;;
            "install_cancelled") echo "Installation cancelled..." ;;
            "config_mirror_prompt") echo "Configure Docker registry mirrors? (Recommended for China network)" ;;
            "use_napcat") echo "Use napcat service together?" ;;
            "not_use_napcat") echo "Not using napcat service" ;;
            "will_run_napcat") echo "Will run napcat service together" ;;
            
            # 拉取镜像
            "get_compose_file") echo "Getting docker-compose.yml file..." ;;
            "error_get_compose") echo "Error: Cannot pull docker-compose.yml file, please check your network connection." ;;
            "pull_images") echo "Pulling service images..." ;;
            "error_pull_images") echo "Error: Cannot pull service images, please check your network connection." ;;
            "using_instance") echo "Using instance name" ;;
            "starting_service") echo "Starting main service..." ;;
            "error_start_service") echo "Error: Cannot start main service, please check Docker Compose configuration." ;;
            "error_env_not_exist") echo "Error: .env file does not exist" ;;
            "pull_sandbox") echo "Pulling sandbox image..." ;;
            "error_pull_sandbox") echo "Error: Cannot pull sandbox image, please check your network connection." ;;
            
            # 防火墙
            "need_allow_port") echo "NekroAgent main service needs to allow port" ;;
            "napcat_need_port") echo "NapCat service needs to allow port" ;;
            "config_firewall") echo "Configuring firewall..." ;;
            "added_firewall_rule") echo "Added firewall rule" ;;
            "firewall_exists") echo "firewall rule already exists" ;;
            "restart_firewall") echo "Restarting firewall service..." ;;
            "firewall_restart_done") echo "Firewall restarted" ;;
            
            # 完成信息
            "docker_storage_info") echo "=== Docker Storage Info ===" ;;
            "unknown") echo "Unknown" ;;
            "storage_usage") echo "Storage usage:" ;;
            "cannot_get_storage") echo "Cannot get storage info" ;;
            "deploy_complete") echo "=== Deployment Complete! ===" ;;
            "important_config") echo "=== Important Configuration ===" ;;
            "onebot_token") echo "OneBot Access Token" ;;
            "admin_account") echo "Admin Account: admin | Password" ;;
            "service_access") echo "=== Service Access Info ===" ;;
            "main_port") echo "NekroAgent Main Service Port" ;;
            "local_url") echo "Local URL" ;;
            "lan_url") echo "LAN URL" ;;
            "replace_ip_hint") echo "Please replace 127.0.0.1 with your router IP" ;;
            "napcat_port") echo "NapCat Service Port" ;;
            "onebot_ws") echo "OneBot WebSocket URL" ;;
            
            # 注意事项
            "notes") echo "=== Notes ===" ;;
            "note_1") echo "1. Router firewall rules have been automatically configured" ;;
            "note_2") echo "2. To access from external network, replace 127.0.0.1 with your router IP" ;;
            "note_3") echo "3. Application data stored in" ;;
            
            # 镜像源保留
            "warn_overwrite_config") echo "Warning: Existing daemon.json will be overwritten. Original settings may be lost." ;;
            "backup_kept_hint") echo "Backup saved at" ;;
            "keep_mirror") echo "Keep Docker registry mirror configuration?" ;;
            "mirror_kept") echo "Mirror configuration kept (backup preserved)" ;;
            
            # 完成
            "install_complete") echo "Installation complete! Enjoy!" ;;
            
            *) echo "$key" ;;
        esac
    else
        case "$key" in
            # 通用
            "unknown_option") echo "未知选项" ;;
            "download_failed") echo "下载失败，尝试其他源..." ;;
            "yes_no") echo "[Y/n]" ;;
            
            # Docker 镜像源
            "config_docker_mirror") echo "配置 Docker 镜像源..." ;;
            "backup_config") echo "已备份原配置到" ;;
            "mirror_config_done") echo "Docker 镜像源配置完成" ;;
            "mirror_list") echo "镜像源列表:" ;;
            "restart_docker") echo "重启 Docker 服务..." ;;
            "docker_restart_done") echo "Docker 服务重启完成" ;;
            "docker_restart_fail") echo "Docker 服务重启失败，请手动重启" ;;
            "remove_mirror_config") echo "移除 Docker 镜像源配置..." ;;
            "restore_original") echo "已恢复原始配置" ;;
            "removed_mirror") echo "已移除镜像源配置" ;;
            
            # Docker Compose 安装
            "install_compose") echo "正在安装 Docker Compose..." ;;
            "install_via_opkg") echo "通过 opkg 安装 Docker Compose..." ;;
            "compose_install_ok") echo "Docker Compose 安装成功" ;;
            "opkg_fail_retry") echo "opkg 安装失败，尝试其他方法..." ;;
            "install_via_binary") echo "通过二进制文件安装 Docker Compose..." ;;
            "unsupported_arch") echo "不支持的架构" ;;
            "download_compose") echo "下载 Docker Compose" ;;
            "compose_download_fail") echo "Docker Compose 下载失败" ;;
            
            # Docker 环境检查
            "error_docker_not_installed") echo "错误: Docker 未安装" ;;
            "check_system") echo "iStoreOS 应该自带 Docker，请检查系统是否正常" ;;
            "use_compose_plugin") echo "使用 Docker Compose Plugin" ;;
            "use_compose_standalone") echo "使用 Docker Compose Standalone" ;;
            "compose_not_found") echo "Docker Compose 未安装，正在尝试安装..." ;;
            "compose_install_done") echo "Docker Compose 安装完成" ;;
            "error_compose_install_fail") echo "错误: Docker Compose 安装失败" ;;
            "please_install_compose") echo "请手动安装 Docker Compose 后重试" ;;
            
            # Docker 空间检查
            "check_docker_space") echo "检查 Docker 存储空间..." ;;
            "docker_root_dir") echo "当前 Docker 目录" ;;
            "available_space") echo "可用空间" ;;
            "warn_low_space") echo "警告: Docker 根目录可用空间不足 (小于 3GB)" ;;
            "need_more_space") echo "NekroAgent 需要较多存储空间，建议先迁移 Docker 目录到更大的存储空间" ;;
            "install_cancelled_space") echo "安装已取消，请先迁移 Docker 目录后再运行安装脚本" ;;
            
            # Docker 环境
            "check_docker_env") echo "检查 Docker 环境..." ;;
            
            # 目录和配置
            "error_create_dir") echo "Error: 无法创建应用目录，请检查您的权限配置。" ;;
            "error_enter_dir") echo "Error: 无法进入应用目录" ;;
            "env_not_found") echo "未找到.env文件，正在从仓库获取.env.example..." ;;
            "error_get_env") echo "Error: 无法获取.env.example文件，请检查网络连接或手动创建.env文件。" ;;
            "error_copy_env") echo "Error: 无法将文件 .env.example 复制为 .env" ;;
            "generate_token") echo "生成" ;;
            "error_generate_random") echo "Error: 无法生成随机字符串" ;;
            "error_port_not_set") echo "Error: 未在 .env 文件中设置" ;;
            
            # 用户确认
            "confirm_env") echo "请检查并按需修改.env文件中的配置，未修改则按照默认配置安装，确认是否继续安装？" ;;
            "install_cancelled") echo "安装已取消..." ;;
            "config_mirror_prompt") echo "是否配置 Docker 镜像源加速？(国内网络推荐)" ;;
            "use_napcat") echo "是否同时使用 napcat 服务？" ;;
            "not_use_napcat") echo "不使用 napcat 服务" ;;
            "will_run_napcat") echo "将同时运行 napcat 服务" ;;
            
            # 拉取镜像
            "get_compose_file") echo "正在获取 docker-compose.yml 文件..." ;;
            "error_get_compose") echo "Error: 无法拉取 docker-compose.yml 文件，请检查您的网络连接。" ;;
            "pull_images") echo "拉取服务镜像..." ;;
            "error_pull_images") echo "Error: 无法拉取服务镜像，请检查您的网络连接。" ;;
            "using_instance") echo "使用实例名称" ;;
            "starting_service") echo "启动主服务中..." ;;
            "error_start_service") echo "Error: 无法启动主服务，请检查 Docker Compose 配置。" ;;
            "error_env_not_exist") echo "Error: .env 文件不存在" ;;
            "pull_sandbox") echo "拉取沙盒镜像..." ;;
            "error_pull_sandbox") echo "Error: 无法拉取沙盒镜像，请检查您的网络连接。" ;;
            
            # 防火墙
            "need_allow_port") echo "NekroAgent 主服务需放行端口" ;;
            "napcat_need_port") echo "NapCat 服务需放行端口" ;;
            "config_firewall") echo "正在配置防火墙..." ;;
            "added_firewall_rule") echo "已添加防火墙规则" ;;
            "firewall_exists") echo "防火墙规则已存在" ;;
            "restart_firewall") echo "重启防火墙服务..." ;;
            "firewall_restart_done") echo "防火墙重启完成" ;;
            
            # 完成信息
            "docker_storage_info") echo "=== Docker 存储信息 ===" ;;
            "unknown") echo "未知" ;;
            "storage_usage") echo "存储使用情况:" ;;
            "cannot_get_storage") echo "无法获取存储信息" ;;
            "deploy_complete") echo "=== 部署完成！===" ;;
            "important_config") echo "=== 重要配置信息 ===" ;;
            "onebot_token") echo "OneBot 访问令牌" ;;
            "admin_account") echo "管理员账号: admin | 密码" ;;
            "service_access") echo "=== 服务访问信息 ===" ;;
            "main_port") echo "NekroAgent 主服务端口" ;;
            "local_url") echo "本地访问地址" ;;
            "lan_url") echo "局域网访问地址" ;;
            "replace_ip_hint") echo "请使用路由器IP替换127.0.0.1" ;;
            "napcat_port") echo "NapCat 服务端口" ;;
            "onebot_ws") echo "OneBot WebSocket 连接地址" ;;
            
            # 注意事项
            "notes") echo "=== 注意事项 ===" ;;
            "note_1") echo "1. 软路由防火墙规则已自动配置" ;;
            "note_2") echo "2. 如果需要从外部访问，请将上述地址中的 127.0.0.1 替换为您的路由器IP" ;;
            "note_3") echo "3. 应用数据存储在" ;;
            
            # 镜像源保留
            "warn_overwrite_config") echo "警告: 现有 daemon.json 将被覆盖，原有设置可能丢失。" ;;
            "backup_kept_hint") echo "备份已保存至" ;;
            "keep_mirror") echo "是否保留 Docker 镜像源配置？" ;;
            "mirror_kept") echo "镜像源配置已保留 (备份已保留)" ;;
            
            # 完成
            "install_complete") echo "安装完成！祝您使用愉快！" ;;
            
            *) echo "$key" ;;
        esac
    fi
}

# ============================================
# Original Script Logic
# ============================================

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
        echo "$(t 'unknown_option'): $1"
        exit 1
        ;;
    esac
done

# Define base URLs
BASE_URLS="https://raw.githubusercontent.com/KroMiose/nekro-agent/main/docker https://ep.nekro.ai/e/KroMiose/nekro-agent/main/docker"

# Docker 镜像源列表
DOCKER_IMAGE_MIRRORS="
https://docker.m.daocloud.io
https://docker.1ms.run
https://ccr.ccs.tencentyun.com
"

# 镜像源配置状态
DOCKER_MIRROR_CONFIGURED=""

# 下载文件
get_remote_file() {
    local filename=$1
    local output=$2
    for base_url in $BASE_URLS; do
        url=${base_url}/${filename}
        if ! wget -q -O "$output" "$url" 2>/dev/null; then
            echo "$(t 'download_failed')"
            continue
        fi
        return 0
    done
    return 1
}

# 生成随机字符串的函数（兼容软路由环境）
generate_random_string() {
    local length=$1
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 $((length * 2)) | tr -dc 'a-zA-Z0-9' | head -c "$length"
    elif [ -c /dev/urandom ]; then
        dd if=/dev/urandom bs=1 count=$((length * 2)) 2>/dev/null | tr -dc 'a-zA-Z0-9' | head -c "$length"
    else
        date +%s%N | md5sum | head -c "$length"
    fi
}

# 配置 Docker 镜像源
configure_docker_mirrors() {
    local daemon_file="/etc/docker/daemon.json"
    
    echo "$(t 'config_docker_mirror')"
    
    local mirrors_json=""
    for mirror in $DOCKER_IMAGE_MIRRORS; do
        [ -z "$mirror" ] && continue
        [ -n "$mirrors_json" ] && mirrors_json="$mirrors_json,"
        mirrors_json="${mirrors_json}\"${mirror}\""
    done
    
    if [ -f "$daemon_file" ] && [ ! -f "$daemon_file.wrtinstall.bak" ]; then
        echo "⚠ $(t 'warn_overwrite_config')"
        cp "$daemon_file" "$daemon_file.wrtinstall.bak"
        echo "$(t 'backup_config') $daemon_file.wrtinstall.bak"
    fi
    
    mkdir -p /etc/docker
    cat > "$daemon_file" << EOF
{
  "registry-mirrors": [$mirrors_json]
}
EOF
    
    echo "✓ $(t 'mirror_config_done')"
    echo "$(t 'mirror_list')"
    for mirror in $DOCKER_IMAGE_MIRRORS; do
        [ -n "$mirror" ] && echo "  - $mirror"
    done
    
    echo "$(t 'restart_docker')"
    if /etc/init.d/dockerd restart >/dev/null 2>&1; then
        echo "✓ $(t 'docker_restart_done')"
        sleep 2
    else
        echo "⚠ $(t 'docker_restart_fail')"
    fi
}

# 移除 Docker 镜像源配置
remove_docker_mirrors() {
    local daemon_file="/etc/docker/daemon.json"
    
    echo "$(t 'remove_mirror_config')"
    
    if [ -f "$daemon_file.wrtinstall.bak" ]; then
        mv "$daemon_file.wrtinstall.bak" "$daemon_file"
        echo "✓ $(t 'restore_original')"
    else
        rm -f "$daemon_file"
        echo "✓ $(t 'removed_mirror')"
    fi
    
    echo "$(t 'restart_docker')"
    if /etc/init.d/dockerd restart >/dev/null 2>&1; then
        echo "✓ $(t 'docker_restart_done')"
    else
        echo "⚠ $(t 'docker_restart_fail')"
    fi
}

# 安装 Docker Compose
install_docker_compose() {
    echo "$(t 'install_compose')"
    
    if command -v opkg >/dev/null 2>&1; then
        echo "$(t 'install_via_opkg')"
        opkg update
        if opkg install docker-compose; then
            echo "✓ $(t 'compose_install_ok')"
            DOCKER_COMPOSE_CMD="docker-compose"
            return 0
        else
            echo "$(t 'opkg_fail_retry')"
        fi
    fi
    
    echo "$(t 'install_via_binary')"
    
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64) arch="x86_64" ;;
        aarch64) arch="aarch64" ;;
        armv7l) arch="armv7" ;;
        *)
            echo "$(t 'unsupported_arch'): $arch"
            return 1
            ;;
    esac
    
    local version
    version=$(wget -qO- https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    
    if [ -z "$version" ]; then
        version="v2.24.0"
    fi
    
    local download_url="https://github.com/docker/compose/releases/download/${version}/docker-compose-linux-${arch}"
    
    echo "$(t 'download_compose') ${version} for ${arch}..."
    mkdir -p /usr/local/bin
    if wget -q -O /usr/local/bin/docker-compose "$download_url"; then
        chmod +x /usr/local/bin/docker-compose
        DOCKER_COMPOSE_CMD="docker-compose"
        echo "✓ $(t 'compose_install_ok')"
        return 0
    else
        echo "✗ $(t 'compose_download_fail')"
        return 1
    fi
}

# 检查 Docker 环境
check_docker_environment() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "$(t 'error_docker_not_installed')"
        echo "$(t 'check_system')"
        exit 1
    fi
    
    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
        echo "✓ $(t 'use_compose_plugin')"
    elif command -v docker-compose >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker-compose"
        echo "✓ $(t 'use_compose_standalone')"
    else
        echo "$(t 'compose_not_found')"
        if install_docker_compose; then
            echo "✓ $(t 'compose_install_done')"
        else
            echo "$(t 'error_compose_install_fail')"
            echo "$(t 'please_install_compose')"
            exit 1
        fi
    fi
}

# 检查 Docker 存储空间
check_docker_space() {
    echo "$(t 'check_docker_space')"
    
    local docker_root
    docker_root=$(docker info 2>/dev/null | grep "Docker Root Dir" | cut -d ':' -f2 | tr -d ' ' || echo "/overlay/upper/opt/docker")
    
    local available_kb
    if [ -d "$docker_root" ]; then
        available_kb=$(df "$docker_root" 2>/dev/null | awk 'NR==2 {print $4}' | grep -E '^[0-9]+$' || echo "0")
    else
        available_kb="0"
    fi
    
    local available_mb=$((available_kb / 1024))
    local available_gb=$((available_mb / 1024))
    
    echo "$(t 'docker_root_dir'): $docker_root"
    echo "$(t 'available_space'): ${available_gb}GB (${available_mb}MB)"
    
    if [ "$available_mb" -lt 3072 ]; then
        echo ""
        echo "⚠️  $(t 'warn_low_space')"
        echo "$(t 'need_more_space')"
        echo "$(t 'install_cancelled_space')"
        exit 1
    fi
}

# 检查防火墙规则是否存在
check_firewall_rule_exists() {
    local rule_name=$1
    local dest_port=$2
    
    uci show firewall | awk -v rule_name="$rule_name" -v dest_port="$dest_port" '
    /^firewall\.@rule\[[0-9]+\]\.name=/ {
        current_name = substr($0, index($0, "=")+2)
        gsub(/\x27/, "", current_name)
        name_matched = (current_name == rule_name)
    }
    /^firewall\.@rule\[[0-9]+\]\.dest_port=/ {
        current_port = substr($0, index($0, "=")+2)
        gsub(/\x27/, "", current_port)
        port_matched = (current_port == dest_port)
        
        if (name_matched && port_matched) {
            found = 1
            exit 0
        }
        
        name_matched = 0
        port_matched = 0
    }
    END {
        exit !found
    }' >/dev/null 2>&1
    
    return $?
}

# 获取局域网IP地址（排除 Docker 网络）
get_lan_ip() {
    local ip
    
    if command -v uci >/dev/null 2>&1; then
        ip=$(uci get network.lan.ipaddr 2>/dev/null)
        if [ -n "$ip" ]; then
            echo "$ip"
            return
        fi
    fi
    
    ip=$(ip addr show br-lan 2>/dev/null | grep -E 'inet ' | awk '{print $2}' | cut -d'/' -f1 | head -1)
    if [ -n "$ip" ]; then
        echo "$ip"
        return
    fi
    
    ip=$(ip addr show | grep -v -E '(docker|br-[0-9a-f]+|veth)' | grep -E 'inet (192\.168|10\.|172\.(1[6-9]|2[0-9]|3[01]))' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d'/' -f1)
    
    echo "$ip"
}

# ============================================
# Main Script
# ============================================

DOCKER_COMPOSE_CMD=""

echo "$(t 'check_docker_env')"
check_docker_environment

check_docker_space

if [ -z "$NEKRO_DATA_DIR" ]; then
    NEKRO_DATA_DIR=${NEKRO_DATA_DIR:-"${HOME}/srv/nekro_agent"}
fi

echo "NEKRO_DATA_DIR: $NEKRO_DATA_DIR"

export NEKRO_DATA_DIR=$NEKRO_DATA_DIR

mkdir -p "$NEKRO_DATA_DIR" || {
    echo "$(t 'error_create_dir') $NEKRO_DATA_DIR"
    exit 1
}

chmod -R 777 "$NEKRO_DATA_DIR"

cd "$NEKRO_DATA_DIR" || {
    echo "$(t 'error_enter_dir') $NEKRO_DATA_DIR"
    exit 1
}

if [ ! -f .env ]; then
    echo "$(t 'env_not_found')"
    if ! get_remote_file .env.example .env.example; then
        echo "$(t 'error_get_env')"
        exit 1
    fi
    if ! cp .env.example .env; then
        echo "$(t 'error_copy_env')"
        exit 1
    fi
fi

if grep -q "^NEKRO_DATA_DIR=" .env; then
    sed -i "s|^NEKRO_DATA_DIR=.*|NEKRO_DATA_DIR=${NEKRO_DATA_DIR}|" .env
else
    echo "NEKRO_DATA_DIR=${NEKRO_DATA_DIR}" >>.env
fi

ONEBOT_ACCESS_TOKEN=$(grep -m1 '^ONEBOT_ACCESS_TOKEN' .env | cut -d '=' -f2)
if [ -z "$ONEBOT_ACCESS_TOKEN" ]; then
    echo "$(t 'generate_token') ONEBOT_ACCESS_TOKEN..."
    ONEBOT_ACCESS_TOKEN=$(generate_random_string 32)
    if [ -z "$ONEBOT_ACCESS_TOKEN" ]; then
        echo "$(t 'error_generate_random') ONEBOT_ACCESS_TOKEN"
        exit 1
    fi
    sed -i "s|^ONEBOT_ACCESS_TOKEN=.*|ONEBOT_ACCESS_TOKEN=${ONEBOT_ACCESS_TOKEN}|" .env
fi

NEKRO_ADMIN_PASSWORD=$(grep -m1 '^NEKRO_ADMIN_PASSWORD=' .env | cut -d '=' -f2)
if [ -z "$NEKRO_ADMIN_PASSWORD" ]; then
    echo "$(t 'generate_token') NEKRO_ADMIN_PASSWORD..."
    NEKRO_ADMIN_PASSWORD=$(generate_random_string 16)
    if [ -z "$NEKRO_ADMIN_PASSWORD" ]; then
        echo "$(t 'error_generate_random') NEKRO_ADMIN_PASSWORD"
        exit 1
    fi
    sed -i "s|^NEKRO_ADMIN_PASSWORD=.*|NEKRO_ADMIN_PASSWORD=${NEKRO_ADMIN_PASSWORD}|" .env
fi

QDRANT_API_KEY=$(grep -m1 '^QDRANT_API_KEY=' .env | cut -d '=' -f2)
if [ -z "$QDRANT_API_KEY" ]; then
    echo "$(t 'generate_token') QDRANT_API_KEY..."
    QDRANT_API_KEY=$(generate_random_string 32)
    if [ -z "$QDRANT_API_KEY" ]; then
        echo "$(t 'error_generate_random') QDRANT_API_KEY"
        exit 1
    fi
    sed -i "s|^QDRANT_API_KEY=.*|QDRANT_API_KEY=${QDRANT_API_KEY}|" .env
fi

INSTANCE_NAME=$(grep -m1 '^INSTANCE_NAME=' .env | cut -d '=' -f2)
export INSTANCE_NAME=${INSTANCE_NAME:-""}

NEKRO_EXPOSE_PORT=$(grep -m1 '^NEKRO_EXPOSE_PORT=' .env | cut -d '=' -f2)
if [ -z "$NEKRO_EXPOSE_PORT" ]; then
    echo "NEKRO_EXPOSE_PORT $(t 'error_port_not_set')"
    exit 1
fi
export NEKRO_EXPOSE_PORT=$NEKRO_EXPOSE_PORT

if [ "$WITH_NAPCAT" = "true" ]; then
    NAPCAT_EXPOSE_PORT=$(grep -m1 '^NAPCAT_EXPOSE_PORT=' .env | cut -d '=' -f2)
    if [ -z "$NAPCAT_EXPOSE_PORT" ]; then
        echo "NAPCAT_EXPOSE_PORT $(t 'error_port_not_set')"
        exit 1
    fi
    export NAPCAT_EXPOSE_PORT=$NAPCAT_EXPOSE_PORT
fi

read -r -p "$(t 'confirm_env') $(t 'yes_no') " yn
echo ""
[ -z "$yn" ] && yn=y
if ! echo "$yn" | grep -q "^[Yy]"; then
    echo "$(t 'install_cancelled')"
    exit 0
fi

read -r -p "$(t 'config_mirror_prompt') $(t 'yes_no') " yn
echo ""
[ -z "$yn" ] && yn=y
if echo "$yn" | grep -q "^[Yy]"; then
    DOCKER_MIRROR_CONFIGURED=true
    configure_docker_mirrors
fi

if [ -z "$WITH_NAPCAT" ]; then
    read -r -p "$(t 'use_napcat') $(t 'yes_no') " yn
    echo ""
    [ -z "$yn" ] && yn=y
    if echo "$yn" | grep -q "^[Yy]"; then
        WITH_NAPCAT=true
    else
        echo "$(t 'not_use_napcat')"
    fi
fi

if [ "$WITH_NAPCAT" = "true" ]; then
    echo "$(t 'will_run_napcat')"
    compose_file=docker-compose-x-napcat.yml
else
    compose_file=docker-compose.yml
fi

echo "$(t 'get_compose_file')"
if ! get_remote_file "$compose_file" docker-compose.yml; then
    echo "$(t 'error_get_compose')"
    exit 1
fi

echo "$(t 'pull_images')"
if ! $DOCKER_COMPOSE_CMD --env-file .env pull; then
    echo "$(t 'error_pull_images')"
    exit 1
fi

if [ -f .env ]; then
    echo "$(t 'using_instance'): ${INSTANCE_NAME}"
    echo "$(t 'starting_service')"
    if ! $DOCKER_COMPOSE_CMD --env-file .env up -d; then
        echo "$(t 'error_start_service')"
        exit 1
    fi
else
    echo "$(t 'error_env_not_exist')"
    exit 1
fi

echo "$(t 'pull_sandbox')"
if ! docker pull kromiose/nekro-agent-sandbox; then
    echo "$(t 'error_pull_sandbox')"
    exit 1
fi

echo "$(t 'need_allow_port') ${NEKRO_EXPOSE_PORT:-8021}/tcp..."
if [ "$WITH_NAPCAT" = "true" ]; then
    echo "$(t 'napcat_need_port') ${NAPCAT_EXPOSE_PORT:-6099}/tcp..."
fi

if command -v uci >/dev/null 2>&1; then
    echo "$(t 'config_firewall')"
    
    if ! check_firewall_rule_exists "NekroAgent" "${NEKRO_EXPOSE_PORT:-8021}"; then
        uci add firewall rule
        uci set firewall.@rule[-1].name="NekroAgent"
        uci set firewall.@rule[-1].src="wan"
        uci set firewall.@rule[-1].proto="tcp"
        uci set firewall.@rule[-1].dest_port="${NEKRO_EXPOSE_PORT:-8021}"
        uci set firewall.@rule[-1].target="ACCEPT"
        echo "$(t 'added_firewall_rule') NekroAgent"
    else
        echo "NekroAgent $(t 'firewall_exists')"
    fi

    if [ "$WITH_NAPCAT" = "true" ]; then
        if ! check_firewall_rule_exists "NapCat" "${NAPCAT_EXPOSE_PORT:-6099}"; then
            uci add firewall rule
            uci set firewall.@rule[-1].name="NapCat"
            uci set firewall.@rule[-1].src="wan"
            uci set firewall.@rule[-1].proto="tcp"
            uci set firewall.@rule[-1].dest_port="${NAPCAT_EXPOSE_PORT:-6099}"
            uci set firewall.@rule[-1].target="ACCEPT"
            echo "$(t 'added_firewall_rule') NapCat"
        else
            echo "NapCat $(t 'firewall_exists')"
        fi
    fi
    
    uci commit firewall
    echo "$(t 'restart_firewall')"
    /etc/init.d/firewall restart >/dev/null 2>&1 && echo "$(t 'firewall_restart_done')"
fi

LAN_IP=$(get_lan_ip)

echo "$(t 'docker_storage_info')"
docker_root=$(docker info 2>/dev/null | grep "Docker Root Dir" | cut -d ':' -f2 | tr -d ' ' || echo "$(t 'unknown')")
echo "$(t 'docker_root_dir'): $docker_root"

echo "$(t 'storage_usage')"
df -h "$docker_root" 2>/dev/null || echo "$(t 'cannot_get_storage')"

echo "$(t 'deploy_complete')"

echo "$(t 'important_config')"
ONEBOT_ACCESS_TOKEN=$(grep -m1 '^ONEBOT_ACCESS_TOKEN=' .env | cut -d '=' -f2)
NEKRO_ADMIN_PASSWORD=$(grep -m1 '^NEKRO_ADMIN_PASSWORD=' .env | cut -d '=' -f2)
echo "$(t 'onebot_token'): ${ONEBOT_ACCESS_TOKEN}"
echo "$(t 'admin_account'): ${NEKRO_ADMIN_PASSWORD}"

echo "$(t 'service_access')"
echo "$(t 'main_port'): ${NEKRO_EXPOSE_PORT:-8021}"
echo "NekroAgent Web $(t 'local_url'): http://127.0.0.1:${NEKRO_EXPOSE_PORT:-8021}"

if [ -n "$LAN_IP" ]; then
    echo "NekroAgent Web $(t 'lan_url'): http://${LAN_IP}:${NEKRO_EXPOSE_PORT:-8021}"
else
    echo "NekroAgent Web $(t 'lan_url'): $(t 'replace_ip_hint')"
fi

if [ "$WITH_NAPCAT" = "true" ]; then
    echo "$(t 'napcat_port'): ${NAPCAT_EXPOSE_PORT:-6099}"
    echo "NapCat $(t 'local_url'): http://127.0.0.1:${NAPCAT_EXPOSE_PORT:-6099}"
    if [ -n "$LAN_IP" ]; then
        echo "NapCat $(t 'lan_url'): http://${LAN_IP}:${NAPCAT_EXPOSE_PORT:-6099}"
    else
        echo "NapCat $(t 'lan_url'): $(t 'replace_ip_hint')"
    fi
else
    echo "$(t 'onebot_ws'): ws://127.0.0.1:${NEKRO_EXPOSE_PORT:-8021}/onebot/v11/ws"
    if [ -n "$LAN_IP" ]; then
        echo "$(t 'onebot_ws') (LAN): ws://${LAN_IP}:${NEKRO_EXPOSE_PORT:-8021}/onebot/v11/ws"
    else
        echo "$(t 'onebot_ws') (LAN): $(t 'replace_ip_hint')"
    fi
fi

echo "$(t 'notes')"
echo "$(t 'note_1')"
echo "$(t 'note_2')"
echo "$(t 'note_3'): $NEKRO_DATA_DIR"

if [ "$DOCKER_MIRROR_CONFIGURED" = "true" ]; then
    echo ""
    read -r -p "$(t 'keep_mirror') $(t 'yes_no') " yn
    echo ""
    [ -z "$yn" ] && yn=y
    if echo "$yn" | grep -q "^[Yy]"; then
        echo "✓ $(t 'mirror_kept')"
        if [ -f /etc/docker/daemon.json.wrtinstall.bak ]; then
            echo "$(t 'backup_kept_hint'): /etc/docker/daemon.json.wrtinstall.bak"
        fi
    else
        remove_docker_mirrors
    fi
fi

echo "$(t 'install_complete')"