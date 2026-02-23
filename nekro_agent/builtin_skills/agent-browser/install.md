# agent-browser 安装指南

> **nekro-cc-sandbox 用户**：`agent-browser` 和 Playwright Chromium 已预装，此文件仅在工具不可用时参考。

## 检查工具状态

```bash
# 检查 agent-browser 是否可用
agent-browser --version

# 检查 Playwright Chromium 是否已安装
echo $PLAYWRIGHT_BROWSERS_PATH
ls $PLAYWRIGHT_BROWSERS_PATH
```

## 安装 agent-browser

```bash
npm install -g agent-browser
```

## 安装 Playwright Chromium

```bash
# 方法一：使用 agent-browser 自带命令
agent-browser install --with-deps

# 方法二：直接使用 playwright
npm install -g playwright
playwright install chromium
playwright install-deps chromium
```

## 设置自定义浏览器路径

```bash
# 安装到指定目录（便于共享）
export PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
playwright install chromium
playwright install-deps chromium
chmod -R 755 /opt/playwright-browsers
```

## Linux 系统依赖

Playwright Chromium 在 Linux 上需要若干系统库，`playwright install-deps chromium` 会自动安装：
- libnss3, libatk1.0-0, libxcomposite1, libxdamage1 等

如无 root 权限，可尝试：
```bash
# 使用已安装的系统 Chromium（可能不兼容）
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 agent-browser open https://example.com
```

## 验证安装

```bash
agent-browser open https://example.com
agent-browser snapshot -i
agent-browser close
```
