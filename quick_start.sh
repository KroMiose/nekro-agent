#!/bin/bash

# 一键部署 nekro-agent 插件脚本

# 更新软件源
echo "正在更新软件源..."
sudo apt-get update

# 检查 Docker 是否已安装 (未安装则询问是否安装)
if ! command -v docker &>/dev/null; then
    read -p "Docker 未安装，是否安装？[Y/n] " answer
    if [[ $answer == "Y" || $answer == "y" || $answer == "" ]]; then
        echo "正在安装 Docker..."
        sudo apt-get install docker.io -y
    else
        echo "Error: Docker 未安装。请先安装 Docker 后再运行该脚本。"
        echo "安装命令: sudo apt-get install docker.io"
        exit 1
    fi
fi

# 检查 Docker Compose 是否已安装 (未安装则询问是否安装)
if ! command -v docker-compose &>/dev/null; then
    read -p "Docker Compose 未安装，是否安装？[Y/n] " answer
    if [[ $answer == "Y" || $answer == "y" || $answer == "" ]]; then
        echo "正在安装 Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    else
        echo "Error: Docker Compose 未安装。请先安装 Docker Compose 后再运行该脚本。"
        echo "安装命令: sudo curl -L https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose"
        exit 1
    fi
fi

# 设置应用目录
APP_DIR="${HOME}/srv/nekro_agent"

# 创建应用目录
mkdir -p $APP_DIR

# 进入应用目录
cd $APP_DIR

# 提前配置好沙盒目录权限
mkdir -p $APP_DIR/sandboxes
sudo chmod 777 $APP_DIR/sandboxes

# 拉取 docker-compose.yml 文件
echo "正在拉取 docker-compose.yml 文件..."
wget https://raw.githubusercontent.com/KroMiose/nekro-agent/main/docker-compose.yml -O docker-compose.yml

# 设置 NEKRO_DATA_DIR 环境变量
export NEKRO_DATA_DIR=$APP_DIR

# 启动主服务
echo "启动主服务中..."
sudo -E docker-compose up -d

# 拉取沙盒镜像
echo "拉取沙盒镜像..."
sudo docker pull kromiose/nekro-agent-sandbox

echo "部署完成！你可以通过 sudo docker logs -f nekro_agent 来查看 Nekro Agent 服务日志。"

# 提示用户修改配置文件
CONFIG_FILE="${APP_DIR}/configs/config.dev.yaml"
echo "请根据需要编辑配置文件: $CONFIG_FILE"
echo "编辑后可通过以下命令重启 nekro-agent 容器:"
echo "cd $APP_DIR && sudo -E docker-compose restart nekro_agent"

# 提示用户连接协议端
echo "请使用 OneBot 协议客户端登录机器人并使用反向 WebSocket 连接方式。"
echo "示例 WebSocket 地址: ws://127.0.0.1:8021/onebot/v11/ws"

echo "安装完成！"
