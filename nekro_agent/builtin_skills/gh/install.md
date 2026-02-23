# gh CLI 安装指南

> **nekro-cc-sandbox 用户**：`gh` 已预装，此文件仅在工具不可用时参考。

## Linux (Debian/Ubuntu) — 官方 apt 源

```bash
mkdir -p /etc/apt/keyrings
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
apt-get update && apt-get install -y gh
```

## macOS

```bash
brew install gh
```

## 二进制安装（无 root 权限）

```bash
# 从 GitHub Releases 下载最新版
GH_VERSION=$(curl -s https://api.github.com/repos/cli/cli/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d 'v')
curl -L "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" | tar xz
mv gh_*_linux_amd64/bin/gh /usr/local/bin/gh
```

## 验证安装

```bash
gh --version
gh auth status
```
