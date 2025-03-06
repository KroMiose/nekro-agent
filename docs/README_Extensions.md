# Nekro Agent 扩展列表

本文档介绍了 Nekro Agent 的各个扩展模块及其功能和配置说明～

## 🎯 基础扩展

### basic - 基础交互工具集

基础消息组件，提供核心的消息处理能力。

- **功能**:
  - 发送文本消息
  - 发送图片/文件
  - 获取用户头像
- **配置**: 无需额外配置

### status - 状态扩展

增强 Bot 的上下文状态记忆能力，动态修改自身群名片。

- **功能**:
  - 帮助 AI 记住自身状态变化信息
  - 自动修改群名片描述状态
- **配置**: 无需额外配置

### timer - 定时器扩展

允许 AI 设置定时器，在指定时间触发事件。

- **功能**:
  - 设置定时器，在指定时间触发事件
  - 支持立即触发
- **配置**: 无需额外配置

## 🎨 创意扩展

### artist - AI 绘图扩展

提供 AI 绘图能力，基于 Stable Diffusion。

- **功能**:
  - AI 自主绘制图片
  - 场景描述转绘图提示词
- **配置**:

```yaml
STABLE_DIFFUSION_API: "http://127.0.0.1:9999" # Stable Diffusion Web UI 访问地址
STABLE_DIFFUSION_PROXY: "" # 访问 Stable Diffusion 通过的代理
STABLE_DIFFUSION_USE_MODEL_GROUP: "default" # 生成绘图提示词使用的聊天模型组名称
```

### ai_voice - AI 语音扩展

支持 AI 使用 QQ 声聊角色发送语音。

- **功能**: 将文本转换为 AI 语音发送
- **配置**:

```yaml
AI_VOICE_CHARACTER: "lucy-voice-xueling" # 语音角色 使用 `/ai_voices` 命令查看支持的语音角色
```

## 🎲 娱乐扩展

### dice - 掷骰姬

提供掷骰子功能，用于随机事件判定。

- **功能**:
  - 事件检定
  - 随机结果生成
- **配置**: 无需额外配置

## 🔍 实用工具

### google_search - Google 搜索工具

让 AI 能够获取实时信息。

- **功能**: 通过 Google 搜索获取网络信息
- **配置**:

```yaml
GOOGLE_SEARCH_API_KEY: "" # Google Search API Key
GOOGLE_SEARCH_CX_KEY: "" # Google Search CX Key
GOOGLE_SEARCH_MAX_RESULTS: 3 # Google Search 最大结果数
DEFAULT_PROXY: "" # 默认代理 (仅会在必要时使用，填写格式: http://127.0.0.1:7890)
```

## 👑 群管理扩展

### group_honor - 群荣誉

允许 AI 管理群成员头衔。

- **功能**: 设置群成员专属头衔
- **要求**: Bot 需要群主权限

### judgement - 风纪委员

群管理工具集。

- **功能**:
  - 禁言管理
  - 不当行为监控
- **要求**:
  - Bot 需要群管理员权限
  - 建议配置 `ADMIN_CHAT_KEY` 接收管理通知

```yaml
ADMIN_CHAT_KEY: "" # 管理会话标识，用于接收管理通知
```

### emo - 表情包获取

提供表情包获取功能。

- **功能**: 让 AI 获取表情包
- **配置**: 

```yaml
EMO_API_URL: "https://v3.alapi.cn/api/doutu" # API的URL配置可填写其他API(需更改默认API设置)
EMO_API_TOKEN: "" # API Token密钥
EMO_API_KEYWORD: "" # 表情包类型
```

### acg_image_search - 二次元图片搜索

提供二次元图片搜索功能。

- **功能**: 让 AI 搜索二次元图片
- **配置**: 

```yaml
R18_CONFIG: false # 是否启用 R18 图片 开启后，图片会包含R18的图片
```


## 💡 使用说明

1. 在配置文件中启用需要的扩展：

```yaml
EXTENSION_MODULES:
  - extensions.basic # 基础消息组件 (提供基础沙盒消息处理能力)
  - extensions.judgement # 群聊禁言扩展 (需要管理员权限，该扩展对 AI 人设有一定影响)
  - extensions.status # 状态能力扩展 (增强 Bot 上下文重要信息记忆能力)
  - extensions.artist # 艺术扩展 (提供 AI 绘图能力 需要配置 Stable Diffusion 后端 API 地址)
  - extensions.group_honor # 群荣誉扩展 (允许 AI 授予群成员称号头衔)
  - extensions.ai_voice # AI 声聊扩展 (允许 AI 使用 QQ 声聊角色发送语音)
  - extensions.google_search # 谷歌搜索扩展 (允许 AI 使用谷歌搜索 需要配置谷歌 API 密钥)
  - extensions.timer # 定时器扩展 (允许 AI 设置定时器，在指定时间触发事件)
  - extensions.emo # 表情包获取扩展 (允许 AI 获取表情包)
  - extensions.acg_image_search # 二次元图片搜索扩展 (允许 AI 搜索二次元图片)
```

2. 根据扩展需求补充相应配置项

3. 重启 Nekro Agent 服务使配置生效

## ⚠️ 注意事项

- 部分扩展需要特定权限或外部服务支持
- 扩展的具体行为可能会受到 AI 人设的影响，同时扩展能力也会反向影响 AI 人设行为 (例如群管功能)
- 部分扩展会导致部分模型出现空返回 (例如二次元图片搜索扩展)
- 扩展列表不支持热重载配置，需要重启 Nekro Agent 服务使配置生效