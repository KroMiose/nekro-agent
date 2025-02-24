# Nekro-Agent 开发环境配置指南 (Windows) 🛠️

## 目录
1. [基础环境配置](#1-基础环境配置) 🖥️
2. [项目初始化](#2-项目初始化) 📥
3. [数据库配置](#3-数据库配置) 🐘
4. [前端环境配置](#4-前端环境配置) 🌐
5. [Docker 沙盒环境](#5-docker-沙盒环境) 🐳
6. [启动项目](#6-启动项目) 🚀

> **📌 注意事项**  
> 1. 所有命令行操作建议在 PowerShell 中执行 💻
> 2. 若遇到端口冲突，请检查 8021/5432 端口占用 🔍
> 3. 遇到问题欢迎 [加群](https://jq.qq.com/?_wv=1027&k=71t9iCT7) 讨论📚

---

## 1 基础环境配置

### 1.1 Python 环境 🐍
```bash
# 检查 Python 版本（需 3.9+）
python --version
```
> **⚠️ 推荐版本**  
> 建议使用 Python 3.10

---

## 2 项目初始化

### 2.1 克隆仓库 📂
```bash
git clone https://github.com/KroMiose/nekro-agent.git
cd nekro-agent
```

### 2.2 安装依赖 🔧
```bash
# 安装 poetry 📦
pip install poetry

# 配置虚拟环境到项目目录（可选）
poetry config virtualenvs.in-project true

# 安装项目依赖 🧩
poetry install
```

---

## 3 数据库配置

### 3.1 安装 PostgreSQL
1. 访问 [PostgreSQL 官网](https://www.postgresql.org/download/windows/) 🌍
2. 下载最新 15.x 版本安装包 📥
3. 安装时：
   - 🔑 设置管理员密码（请牢记）
   - 🚪 保持默认端口 5432
   - ❌ 取消勾选"Stack Builder"

### 3.2 数据库初始化
1. 打开 SQL Shell (psql) 或 pgAdmin 🖥️
2. 执行以下 SQL 命令：
```sql
-- 创建数据库 📂
CREATE DATABASE nekro_db;
```

### 3.3 修改项目配置 ⚙️
编辑 `./data/config/nekro-agent.yaml`：
```yaml
POSTGRES_HOST: localhost
POSTGRES_PORT: 5432
POSTGRES_USER: postgres
POSTGRES_PASSWORD: your_password
POSTGRES_DATABASE: nekro_db
```

---

## 4 前端环境配置

### 4.1 安装 Node.js
1. 访问 [Node.js 官网](https://nodejs.org/) 🌍
2. 下载 20.x LTS 版本（.msi 格式）📥
3. 安装时勾选 **Add to PATH** 选项 ✅

### 4.2 配置 pnpm
```powershell
# 全局安装 pnpm 📦
npm install -g pnpm

# 设置镜像加速 ⚡
pnpm config set registry https://registry.npmmirror.com
```

### 4.3 安装前端依赖 🛠️
```powershell
cd frontend

# 安装依赖 🧩
pnpm install
```

---

## 5 Docker 沙盒环境

### 5.1 安装 Docker Desktop
1. 访问 [Docker 官网](https://www.docker.com/products/docker-desktop/) 🌍
2. 下载 Windows 版本并安装 📥
3. 启动后右下角出现鲸鱼图标即成功 ✅
4. （可选）在设置中启用 WSL2 后端提升性能 ⚡

### 5.2 拉取沙盒镜像
```powershell
# 拉取镜像 📦
docker pull kromiose/nekro-agent-sandbox:latest

# 验证镜像 ✅
docker images | findstr "nekro-agent-sandbox"
```

---

## 6 启动项目

## 设置WebUI密码
> **⚠️ 提示**
> 由于nekro_agent的webui密码是被存放在环境变量而非数据库，需要在环境变量中设置密码

1.打开文件资源管理器找到"此电脑", 右键点击 "属性", 找到"高级系统设置", 并点击"环境变量", 在环境变量中添加以下内容:
名称:NEKRO_ADMIN_PASSWORD
值:你想要设置的密码
2.点击"确定"保存设置并退出

### VS Code 调试
1. 打开项目根目录 📂
2. 按 `F5` 启动调试 ⚡
3. 观察终端输出是否正常 👀

#### 或命令行启动
```bash
poetry run bot
```

### 启动前端
1.使用pnpm dev启动
```bash
cd ./frontend
pnpm dev
```
当看到如下日志时，即可在浏览器访问 🌐 👉 `http://localhost:xxxx`
```
  VITE vx.x.x  ready in xxx ms

  ➜  Local:   http://localhost:xxxx/ <-这里是端口号
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```
---
## 结束

至此教程已结束，请自行选用合适的协议端进行连接

