# 表情包插件 Emotion

Emotion 是一个 Nekro Agent 表情包管理插件，提供表情包收藏、语义搜索、分类图库、Web 管理、图床同步和 Agent 工具调用能力。插件使用 Qdrant 向量数据库保存表情语义索引，支持通过自然语言查找合适的表情包。

## 注意 本插件与内置插件同源，存在冲突，开启本插件请关闭内置的表情插件！

## 功能特性

- 表情包收藏：支持从 URL 或本地上传路径收藏图片/GIF。
- 语义搜索：使用嵌入模型生成向量并在 Qdrant 中检索相似表情。
- 宽松匹配：向量结果不足时，可根据描述、标签、分类进行补充匹配。
- 备用标记匹配：可通过标签和分类标记补充命中结果。
- 高置信度标记：搜索结果会根据配置阈值标注高置信度结果。
- 重复检测：收藏时可通过文件哈希检测重复表情，避免重复入库。
- 分类图库：支持按场景分类管理图库，图片统一存放在 `emotions/` 根目录，分类由元数据和类别描述维护。
- Web 管理：提供分类、图片、表情元数据的可视化管理页面。
- WebUI 分页：图片列表和表情元数据支持分页显示，避免大量图片时页面卡顿。
- WebUI 自动化分类：可手动调用视觉模型，为未分类或缺少描述的图片补全描述、标签、分类并写入向量数据库。
- WebUI 图库去重：可手动按文件内容 MD5 删除重复图片，并同步清理元数据和向量索引。
- AI 收藏控制：可通过配置禁止 Agent 自行收藏新表情，使其只能使用图库中已有表情。
- 批量操作：支持批量删除、批量移动、批量复制分类图片。
- 拖拽管理：WebUI 支持图片拖拽移动到目标分类。
- 图床同步：支持 StarDots 和 Cloudflare R2 的上传、下载、双向同步与覆盖同步。
- 访问密钥：WebUI 和 API 可启用访问密钥保护。
- 实时生效：分类描述、标签、图片分类元数据等修改会实时反映到搜索和 prompt 中。

## 目录结构

```text
emotion/
├── __init__.py
├── plugin.py
├── constants.py
├── gallery.py
└── image_host.py
```

- `plugin.py`：插件入口，包含配置、命令、沙盒工具、Web 路由、向量索引逻辑。
- `constants.py`：默认分类描述和支持的图片格式。
- `gallery.py`：分类图库、目录同步、图片上传、批量移动/复制逻辑。
- `image_host.py`：图床同步服务和服务商适配。

运行时数据目录由插件数据路径自动维护：

```text
插件数据目录/
├── emotions/         # 统一图库目录，所有图片文件都直接存放在这里
└── emotions_data.json # 分类描述数据，由 WebUI 和同步按钮维护
```

当前版本统一使用 `emotions/` 根目录保存 AI 收藏表情和 WebUI 上传的图片，分类信息记录在表情元数据中，不再通过子文件夹表示分类。

## 基础配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `MAX_RECENT_EMOTION_COUNT` | `5` | prompt 中展示的最近表情数量 |
| `MAX_SEARCH_RESULTS` | `3` | 搜索返回结果数量 |
| `EMBEDDING_MODEL` | `text-embedding` | 嵌入模型组名称 |
| `VISION_MODEL` | `default` | WebUI 自动化分类使用的视觉模型组，需为启用视觉能力的 chat 模型组 |
| `AUTO_CLASSIFY_BATCH_LIMIT` | `20` | WebUI 自动化分类单次最多处理的图片数量 |
| `EMBEDDING_DIMENSION` | `1024` | 嵌入向量维度，需与模型一致 |
| `STRICT_EMOTION_COLLECT` | `False` | 是否严格限制收藏非表情图片 |
| `ALLOW_AI_COLLECT_EMOTION` | `True` | 是否允许 AI 通过 `collect_emotion` 自行收藏新表情，关闭后只能使用已有图库表情 |
| `EMBEDDING_REQUEST_TIMEOUT` | `5` | 嵌入请求超时时间，单位秒 |
| `IMAGE_DOWNLOAD_TIMEOUT` | `30` | 图片下载超时时间，单位秒 |

## 匹配相关配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `ENABLE_LOOSE_MATCH` | `True` | 开启描述、标签、分类的宽松补充匹配 |
| `ENABLE_FALLBACK_TAG_MATCH` | `True` | 开启标签和分类备用匹配 |
| `ENABLE_DUPLICATE_EMOTION_DETECTION` | `True` | 收藏时启用文件哈希重复检测 |
| `SIMILARITY_THRESHOLD` | `0.45` | 向量搜索直接命中的最低相似度 |
| `HIGH_CONFIDENCE_THRESHOLD` | `0.78` | 高置信度结果阈值 |
| `LOOSE_MATCH_MIN_SCORE` | `0.34` | 宽松匹配结果最低分 |

## 分类图库配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `ENABLE_CATEGORY_GALLERY` | `True` | 启用 WebUI 分类、类别描述和表情分类元数据管理；图片仍统一保存在 `emotions/` 根目录 |
| `DEFAULT_CATEGORY_DESCRIPTIONS` | 内置默认分类 | 用于同步 WebUI 分类列表和分类描述，不会创建分类文件夹 |
| `WEB_MANAGER_ENABLE_UPLOAD` | `True` | 是否允许 WebUI 上传图片到统一图库 |
| `WEBUI_ACCESS_KEY` | 空 | 设置后 WebUI 会显示登录页面，输入访问密钥验证后进入管理页 |

分类信息会自动同步：

- 点击 WebUI 的“同步图库类别描述”会将配置中的 `DEFAULT_CATEGORY_DESCRIPTIONS` 写入分类描述数据。
- 图片文件始终直接存放在 `emotions/` 根目录，不再通过子文件夹表示分类。
- prompt 会自动展示当前分类描述、分类图片数量和未分类图片数量。
- AI 收藏表情时会优先根据描述、情绪、用途从可用分类中选择 `category`；如果未传分类，后端会根据描述和标签做关键词兜底分类。
- 无需手动编辑 `emotions_data.json`。

## 图床配置

本插件支持 **StarDots** 和 **Cloudflare R2** 两种图床。图床配置是可选的，不配置图床时，表情收藏、统一图库和 Web 管理仍可正常使用，只有云端同步相关功能不可用。

| 配置项 | 说明 |
| --- | --- |
| `IMAGE_HOST_PROVIDER` | 图床提供商，可选 `disabled`、`stardots`、`cloudflare_r2`，分别表示不使用图床、使用 StarDots、使用 Cloudflare R2 |
| `STARDOTS_KEY` | StarDots Key |
| `STARDOTS_SECRET` | StarDots Secret |
| `STARDOTS_SPACE` | StarDots 空间名 |
| `R2_ACCOUNT_ID` | Cloudflare R2 账号 ID |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 Access Key ID |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 Secret Access Key |
| `R2_BUCKET_NAME` | Cloudflare R2 存储桶名称 |
| `R2_PUBLIC_URL` | 可选，自定义 CDN 或公开访问域名 |

图床同步围绕统一图库目录工作，会读取 `emotions/` 根目录下的本地图片并和远端服务进行对比。插件会维护上传记录文件，用于判断本地和远端图片状态。

### StarDots 图床注册与配置

StarDots 国内访问相对友好，免费账户通常足够用于同步表情包图片。

1. 注册或登录 StarDots 账号。
2. 创建一个空间。
3. 记录空间名称，并填入插件配置 `STARDOTS_SPACE`。
4. 在 StarDots 控制台进入“开放 API”或类似入口。
5. 进入“密钥”页面并生成密钥。
6. 将生成的 API Key 填入 `STARDOTS_KEY`。
7. 将生成的 API Secret 填入 `STARDOTS_SECRET`。
8. 将 `IMAGE_HOST_PROVIDER` 切换为 `stardots`。
9. 保存配置后，可使用 `emo_sync status` 检查图床同步状态。

需要填写的配置示例：

```yaml
IMAGE_HOST_PROVIDER: "stardots"
STARDOTS_KEY: "your_api_key"
STARDOTS_SECRET: "your_api_secret"
STARDOTS_SPACE: "your_space_name"
```

### Cloudflare R2 图床注册与配置

Cloudflare R2 国际访问相对友好，适合需要自定义域名或全球 CDN 的场景。

1. 注册或登录 Cloudflare 账号。
2. 进入 Cloudflare Dashboard。
3. 进入 R2 页面。
4. 点击 `Create bucket` 创建存储桶。
5. 记录存储桶名称，并填入 `R2_BUCKET_NAME`。
6. 在 R2 页面点击 `Manage R2 API Tokens`。
7. 点击 `Create API Token` 创建 R2 API 凭证。
8. 记录生成的 `Access Key ID`，填入 `R2_ACCESS_KEY_ID`。
9. 记录生成的 `Secret Access Key`，填入 `R2_SECRET_ACCESS_KEY`。
10. 在 R2 页面右上角找到 `Account ID`，填入 `R2_ACCOUNT_ID`。
11. 如果绑定了自定义域名或启用了公开访问域名，可将域名填入 `R2_PUBLIC_URL`。
12. 将 `IMAGE_HOST_PROVIDER` 切换为 `cloudflare_r2`。
13. 保存配置后，可使用 `emo_sync status` 检查图床同步状态。

需要填写的配置示例：

```yaml
IMAGE_HOST_PROVIDER: "cloudflare_r2"
R2_ACCOUNT_ID: "your_account_id"
R2_ACCESS_KEY_ID: "your_access_key_id"
R2_SECRET_ACCESS_KEY: "your_secret_access_key"
R2_BUCKET_NAME: "your_bucket_name"
R2_PUBLIC_URL: "https://你的域名.com"
```

`R2_PUBLIC_URL` 是可选项。如果配置了自定义 CDN 域名或公开访问域名，插件会优先使用该地址作为图片访问地址。

Cloudflare R2 的常见优势：

- 免费额度适合轻量图库同步。
- 支持自定义域名。
- 支持全球 CDN 加速。
- 插件会维护上传记录，避免重复上传相同文件。

### 支持的图床方法

| 方法 | 说明 |
| --- | --- |
| 查看概览 | 显示当前图床服务商、本地图片数量、本地占用空间、云端图片数量和云端占用空间 |
| 查看同步状态 | 对比本地图库和云端图片，统计仅本地存在、仅云端存在、本地和云端都存在的图片 |
| 上传本地图片 | 将 `emotions/` 中尚未上传到图床的图片上传到当前服务商 |
| 下载云端图片 | 将云端存在但本地缺失的图片下载回 `emotions/` 目录 |
| 双向同步 | 先上传本地缺失图片，再下载云端缺失图片，让本地和云端尽量保持一致 |
| 本地覆盖云端 | 以本地 `emotions/` 为准覆盖远端，适合确认本地图库是最新版本时使用 |
| 云端覆盖本地 | 以远端图床为准覆盖本地，适合确认云端图库是最新版本时使用 |

### 图床同步命令

| 命令 | 说明 |
| --- | --- |
| `emo_sync status` | 查看同步状态 |
| `emo_sync upload` | 上传本地图库到图床 |
| `emo_sync download` | 从图床下载缺失图片 |
| `emo_sync sync_all` | 双向同步本地和云端 |
| `emo_sync overwrite_to_remote` | 使用本地图库覆盖云端 |
| `emo_sync overwrite_from_remote` | 使用云端图库覆盖本地 |

### 服务商说明

- `disabled`：不使用图床。执行图床同步命令时会提示切换到可用服务商。
- `stardots`：使用 StarDots，同步前需要配置 `STARDOTS_KEY`、`STARDOTS_SECRET` 和 `STARDOTS_SPACE`。
- `cloudflare_r2`：使用 Cloudflare R2，同步前需要配置 R2 账号、密钥、存储桶等信息。`R2_PUBLIC_URL` 可用于返回自定义访问地址。

## 命令说明

命令默认需要超级用户权限。

| 命令 | 说明 |
| --- | --- |
| `emo_search <关键词>` | 语义搜索表情包，并展示匹配来源、置信度和图片 |
| `emo_stats` | 查看表情包总数、向量数量和标签统计 |
| `emo_list [页码]` | 分页列出已收藏表情包，默认预览图片 |
| `emo_gallery` / `emo_categories` | 查看分类及图片数量 |
| `emo_category_update <分类> <描述>` | 新增或更新分类描述 |
| `emo_category_clear <分类>` | 清空指定分类图库图片，但保留分类描述 |
| `emo_sync <任务>` | 执行图床同步任务 |
| `emo_migrate` | 规范表情元数据路径为 `emotions/` 根目录文件名，并刷新向量 payload |
| `emo_gallery_check` / `emo_check` | 验证统一图库状态，检查缺失文件、路径引用和未入库图库图片 |
| `emo_reindex -y` | 重建全部表情包向量索引 |

`emo_sync` 支持的任务：

- `status`：查看同步状态。
- `upload`：上传本地图库到图床。
- `download`：从图床下载缺失图片。
- `sync_all`：双向同步。
- `overwrite_to_remote`：本地覆盖云端。
- `overwrite_from_remote`：云端覆盖本地。

## Agent 工具

插件会向 Agent 暴露以下能力：

- `collect_emotion`：收藏表情包并写入向量索引。
- `update_emotion`：更新表情描述、标签和分类，并实时更新向量索引。
- `remove_emotion`：删除表情包和对应向量索引。
- `search_emotion`：按文本描述搜索表情包，返回多模态结果。

搜索结果会标注：

- `vector`：向量命中。
- `fallback tag/loose`：备用标签或宽松文本命中。
- `high confidence`：达到高置信度阈值。
- `normal confidence`：普通置信度。

## Web 管理

WebUI 挂载在插件路由下，访问路径为：

```text
/plugins/KroMiose.emotion/
```

如果你的 Nekro Agent 面板地址是 `http://127.0.0.1:8021`，完整访问地址通常是：

```text
http://127.0.0.1:8021/plugins/KroMiose.emotion/
```

插件挂载 Web 管理页面，可用于：

- 查看图床服务商、云端图片数量和云端空间占用。
- 查看、创建和修改分类。
- 上传分类图片。
- 拖拽移动图片。
- 批量移动、复制、删除图片。
- 分页查看图片列表和表情元数据，图片较多时可切换每页数量。
- 搜索和滚动浏览分类栏，分类较多时也能快速定位。
- 手动执行自动化分类，调用视觉模型为未分类或缺少描述的图片补全描述、标签、分类，并写入向量数据库。
- 手动执行图库去重，按文件内容 MD5 删除重复图片，并同步清理元数据和 Qdrant 向量索引。
- 查看已收藏表情元数据。
- 编辑表情描述、标签和分类。
- 在页面上方查看操作结果反馈，可展开、收起或清空结果。

如果设置了 `WEBUI_ACCESS_KEY`，打开 WebUI 时会先显示访问验证页面。输入正确访问密钥后即可进入管理页，验证通过的密钥会保存在当前浏览器本地存储中，后续管理操作会自动携带登录状态。

### WebUI 自动化分类

自动化分类用于整理已经存在于 `emotions/` 目录中的图片。点击 WebUI 顶部工具栏的“自动化分类”后，插件会扫描以下图片：

- 没有元数据的图片。
- 没有表情描述的图片。
- 描述仍等于文件名的图片。
- 没有分类的图片。

插件会调用 `VISION_MODEL` 指定的视觉模型识别图片内容，生成中文描述、标签和分类，然后写入表情元数据并更新 Qdrant 向量数据库。单次最多处理数量由 `AUTO_CLASSIFY_BATCH_LIMIT` 控制。

使用前请确认：

- `VISION_MODEL` 指向支持视觉的 chat 模型组。
- 模型组已启用视觉能力。
- Qdrant 向量数据库可用。

### WebUI 图库去重

点击 WebUI 顶部工具栏的“图库去重”后，插件会按文件内容 MD5 扫描 `emotions/` 目录：

- 相同 MD5 视为重复图片。
- 每组重复图片保留第一张。
- 删除后续重复文件。
- 同步删除对应表情元数据。
- 同步清理 `recent_emotion_ids` 和 Qdrant 向量索引。

该功能会真实删除本地重复文件，建议在执行图床覆盖同步或大量整理前先确认当前图库状态。

## Prompt 自动维护

插件的 prompt 注入会自动读取当前运行时数据：

- 最近收藏表情来自插件存储。
- 已收藏表情目录统计来自实际存在的表情文件和分类元数据。
- 分类图库列表来自 `emotions/` 目录、表情元数据和 `emotions_data.json` 自动同步结果。
- 新增、删除、移动分类描述或调整图片分类元数据后，无需重启或手动添加 prompt。

这意味着只要通过 WebUI、命令或插件工具更新分类描述和图片分类元数据，Agent 看到的可用分类和图库摘要就会自动更新。

## 使用建议

1. 先确认嵌入模型组和嵌入维度配置正确。
2. 收藏表情时尽量提供清晰描述和稳定标签。
3. AI 收藏和 WebUI 上传都会统一写入 `emotions/` 根目录；没有分类元数据的图片会显示在 WebUI 的“未分类”中。
4. 如果不希望 AI 自动扩充图库，可关闭 `ALLOW_AI_COLLECT_EMOTION`，让 Agent 只能搜索和使用已有图库表情。
5. 如果希望 WebUI 仅自己可访问，请配置 `WEBUI_ACCESS_KEY`。
6. 修改大量图片或元数据后，可使用 `emo_reindex -y` 重建索引。
7. 对已有图片批量补全描述和分类时，优先使用 WebUI 的“自动化分类”；批量清理重复文件时，可使用“图库去重”。

## 注意事项

- 插件依赖 Qdrant 向量数据库，语义搜索需要 Qdrant 客户端可用。
- 嵌入维度必须和所选嵌入模型输出维度一致。
- 严格表情包模式开启后，Agent 会更倾向于拒绝收藏截图、照片等非表情内容。
- 关闭 `ALLOW_AI_COLLECT_EMOTION` 后，Agent 即使尝试调用 `collect_emotion` 也会被后端拦截，只能使用图库已有表情。
- WebUI 自动化分类会调用视觉模型并更新向量数据库，请确认视觉模型组和 Qdrant 状态正常。
- 图床同步涉及远端删除或覆盖任务时，请先使用 `emo_sync status` 检查状态。
- WebUI 访问密钥为空时不启用访问保护。
