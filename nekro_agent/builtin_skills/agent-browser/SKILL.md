---
name: agent-browser
description: 使用此技能进行浏览器自动化操作，包括网页抓取、表单填写、UI 测试和任何 Web 交互任务。
version: 2.0.0
allowed-tools: Read,Bash
---

# agent-browser 浏览器自动化指南

> **环境提示**：`agent-browser` 及 Playwright Chromium 已在 nekro-cc-sandbox 中预装（`PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers`），可直接使用。如遇安装问题，请读取本技能目录下的 `install.md`。

## 基本工作流

```bash
agent-browser open <url>      # 打开页面
agent-browser snapshot -i     # 获取交互元素快照（返回带 ref 的元素树）
agent-browser click @e1       # 通过 ref 点击元素
agent-browser fill @e2 "文本" # 填写表单
agent-browser screenshot      # 截图
agent-browser close           # 关闭浏览器
```

## 快照（核心功能）

```bash
agent-browser snapshot              # 完整可访问性树
agent-browser snapshot -i           # 仅交互元素（推荐，节省 token）
agent-browser snapshot -c           # 紧凑模式（移除空元素）
agent-browser snapshot -d 3         # 限制深度为 3 层
agent-browser snapshot -s "#main"   # 限定 CSS 选择器范围
```

快照输出示例：
```
@e1 [heading] "Example Domain" [level=1]
@e2 [button] "Submit"
@e3 [input type="email"] placeholder="Email"
@e4 [link] "Learn more"
```

> **重要**：页面导航或元素变化后，refs 会失效，必须重新执行 snapshot 获取新 refs。

## 元素交互

```bash
agent-browser click @e1             # 点击（使用 ref）
agent-browser fill @e2 "文本"      # 清空并填写（表单推荐）
agent-browser type @e3 "追加"      # 追加输入
agent-browser press Enter           # 按键
agent-browser hover @e4             # 悬停
agent-browser select @e5 "选项值"  # 选择下拉选项
agent-browser check @e6             # 勾选复选框
agent-browser scroll down 300       # 滚动（up/down/left/right，单位 px）
```

## 语义定位器（备选）

```bash
agent-browser find role button click --name "Submit"
agent-browser find label "Email" fill "user@example.com"
agent-browser find placeholder "搜索..." fill "关键词"
agent-browser find text "登录" click
```

## 获取页面信息

```bash
agent-browser get text @e1          # 获取文本内容
agent-browser get value @e2         # 获取输入框值
agent-browser get attr @e3 href     # 获取属性
agent-browser get title             # 获取页面标题
agent-browser get url               # 获取当前 URL
```

## 等待与导航

```bash
agent-browser wait --text "欢迎"   # 等待文本出现
agent-browser wait --load           # 等待页面加载完成
agent-browser wait 2000             # 等待 2 秒
agent-browser wait --url "**/dash"  # 等待 URL 匹配
agent-browser back                  # 后退
agent-browser reload                # 刷新
```

## 截图与调试

```bash
agent-browser screenshot page.png             # 截图
agent-browser screenshot full.png --full      # 截取完整页面
agent-browser pdf report.pdf                  # 保存为 PDF
agent-browser eval "document.title"           # 执行 JavaScript
agent-browser console                         # 查看控制台消息
```

## 会话管理（多实例隔离）

```bash
# 不同会话完全隔离（cookie、localStorage、登录状态）
agent-browser --session user1 open site-a.com
agent-browser --session user2 open site-b.com

# 持久化登录状态
agent-browser --profile ~/.my-profile open myapp.com
```

## 最佳实践

1. **始终用 `-i` 标志**：只获取交互元素，大幅减少 token 消耗
2. **导航后重新快照**：click/fill 触发页面变化后必须重新 `snapshot`
3. **用 `-s` 限定范围**：复杂页面只关注目标区域
4. **优先用 `fill` 而非 `type`**：`fill` 先清空再输入，更适合表单
5. **用语义定位器作备选**：`find role/label` 比 CSS 选择器更稳定

## 常见错误

| 错误 | 解决方案 |
|------|----------|
| "Executable doesn't exist" | 读取 `install.md` 安装 Playwright Chromium |
| Ref 无效 | 重新执行 `agent-browser snapshot` |
| 元素找不到 | 改用 `find` 语义定位器 |
| 页面加载超时 | 使用 `agent-browser wait --load` |
