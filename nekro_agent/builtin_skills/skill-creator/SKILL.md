---
name: skill-creator
description: 创建新的 Claude Code 技能，修改和优化已有技能。当用户想从头创建技能、将当前工作流封装为技能、优化已有技能的内容或触发描述时使用此技能。即使用户没有明确说"技能"，当他们想把某个重复工作流程固定下来时也应使用。
allowed-tools: Read,Write,Bash
---

# 技能创建器

帮助用户创建、修改和优化 Claude Code 技能。

## 核心流程

1. 理解用户意图（想让技能做什么、何时触发、期望输出）
2. 编写符合规范的 SKILL.md
3. 保存到 `~/.claude/skills/dynamic/` 目录
4. 验证技能可被正确解析

按用户的实际需求灵活执行——可以跳过不需要的步骤。

---

## SKILL.md 格式规范（必须严格遵守）

### Frontmatter 格式

SKILL.md 必须以 YAML frontmatter 开头。frontmatter 用 `---` 行包裹，首行必须是 `---`，不能有前导空行或空格。

```
---
name: my-skill-name
description: 技能功能描述，以及何时应当调用此技能
allowed-tools: Read,Write,Bash
---
```

**严格要求**：

- 第一行必须是 `---`（三个连字符，无前导空格）
- 最后一行必须是 `---`（独立一行）
- 每个字段占一行，格式为 `key: value`
- 冒号后必须有一个空格
- 值中不要使用引号包裹，除非值本身包含特殊字符
- frontmatter 与正文之间应有一个空行

### 必填字段

| 字段 | 要求 | 说明 |
|------|------|------|
| `name` | **必填** | 技能标识符。仅限小写字母、数字和连字符，最长 64 字符。不能以连字符开头或结尾。示例：`code-reviewer`、`api-client-gen` |
| `description` | **必填** | 技能做什么 + 何时触发。最长 1024 字符。这是自动触发的唯一判断依据，必须写清楚触发场景 |

### 可选字段

| 字段 | 说明 |
|------|------|
| `allowed-tools` | 技能激活时允许使用的工具列表，逗号分隔。常用：`Read`、`Write`、`Bash`、`Edit`、`Grep`、`Glob` |
| `version` | 版本号，如 `1.0.0` |

### name 字段规则

合法：`code-reviewer`、`api-gen`、`my-skill-2`
非法：`Code_Reviewer`（大写和下划线）、`-my-skill`（连字符开头）、`my skill`（空格）

### description 字段写法指南

description 是技能能否被正确触发的关键。遵循以下原则：

1. **先说做什么，再说何时用**：`生成 API 客户端代码。当用户需要根据 OpenAPI/Swagger 规范生成 HTTP 客户端、REST API 封装、或类型定义时使用。`

2. **包含用户可能使用的关键词**：把用户自然语言中会用到的词写进去，即使不是技术术语。

3. **适度"主动"**：Claude 倾向于不触发技能，所以 description 应该稍微宽泛一些。例如，不要只写 `处理 PDF 文件`，而应写 `处理 PDF 文件。当用户提到 PDF、文档转换、表格提取、文件合并、表单填写，或需要处理任何扫描文档时都应使用此技能。`

4. **不要在 description 中写使用说明**：description 仅用于触发判断，具体指令放在正文中。

---

## 正文编写原则

### 用祈使句，解释原因而非堆砌规则

不好：`你必须始终使用 TypeScript。绝对不允许使用 JavaScript。`
好：`使用 TypeScript 编写，因为项目需要类型安全来减少运行时错误。`

### 保持简洁，仅写 Claude 不知道的内容

Claude 已经知道如何编程、如何使用工具。不需要解释基础概念，只需要写：
- 项目特有的约定和模式
- 需要遵循的特定工作流程
- 预期的输出格式（如有要求）

### 输出格式用模板定义

如果技能有固定的输出格式，提供明确的模板：

```markdown
## 输出格式
生成的报告必须使用以下结构：
# [标题]
## 摘要
## 发现
## 建议
```

### 控制在 500 行以内

SKILL.md 正文应控制在 500 行以内。超过时，将详细内容拆分到附属文件。

---

## 多文件技能结构

复杂技能应拆分为多个文件：

```
my-skill/
├── SKILL.md           # 主文件（核心指令，保持简洁）
├── reference.md       # 参考文档（按需加载）
├── examples.md        # 示例（按需加载）
└── scripts/
    └── helper.py      # 可执行脚本（直接运行，无需加载到上下文）
```

在 SKILL.md 中明确引用附属文件，告诉 Claude 什么时候该读取它们：

```markdown
## 参考资料
- 完整 API 文档见 [reference.md](reference.md)
- 使用示例见 [examples.md](examples.md)
```

---

## 完整示例

### 示例 1：简单技能

```
---
name: commit-message
description: 生成规范的 Git 提交信息。当用户完成代码修改想要提交、需要写 commit message、或提到 conventional commits 时使用。
allowed-tools: Read,Bash
---

根据暂存区的变更生成提交信息。

## 流程

1. 运行 `git diff --cached --stat` 查看变更概览
2. 运行 `git diff --cached` 查看具体变更
3. 分析变更的性质（新功能、修复、重构等）
4. 生成符合 Conventional Commits 格式的提交信息

## 提交信息格式

类型(范围): 简要描述

- feat: 新功能
- fix: 修复
- refactor: 重构
- docs: 文档
- test: 测试
- chore: 构建/工具

范围是可选的，用于标识影响的模块。描述用祈使语气，不超过 72 字符。
```

### 示例 2：多文件技能

主文件 `SKILL.md`：
```
---
name: api-client-gen
description: 根据 OpenAPI 规范生成类型安全的 API 客户端代码。当用户需要生成 HTTP 客户端、REST API 封装、SDK、或从 Swagger/OpenAPI 文档创建类型定义时使用。
allowed-tools: Read,Write,Bash
---

根据 OpenAPI/Swagger 规范生成类型安全的 API 客户端。

## 流程

1. 读取用户提供的 OpenAPI 规范文件
2. 分析 endpoints、schemas 和认证方式
3. 根据目标语言生成客户端代码
4. 包含类型定义、错误处理和认证逻辑

## 支持的语言

根据项目上下文自动检测，或由用户指定。
参考各语言的具体模板见 [reference.md](reference.md)。
```

---

## 保存位置

将技能保存到 `~/.claude/skills/dynamic/` 目录：

```bash
mkdir -p ~/.claude/skills/dynamic/my-skill-name
```

动态技能在会话之间持久保存，创建后立即可用。

## 创建后验证

技能创建完成后，读取生成的 SKILL.md 并验证：
1. 第一行是否为 `---`
2. frontmatter 中是否包含 `name` 和 `description` 字段
3. name 是否符合命名规则（小写字母、数字、连字符）
4. description 是否清晰描述了功能和触发场景
5. 第二个 `---` 是否独立成行
6. frontmatter 之后是否有正文内容
