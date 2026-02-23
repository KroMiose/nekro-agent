---
name: skill-creator
description: 使用此技能创建新的 Claude Code 技能。根据用户或 NA 的需求，设计并保存自定义技能到 ~/.claude/skills/dynamic/ 目录，运行 /skill-creator 开始创建。
version: 1.0.0
allowed-tools: Read,Write,Bash
---

# 技能创建器

此技能帮助你为 Claude Code 创建新的自定义技能。

## 使用方法

运行 `/skill-creator` 进入交互式技能创建工作流。

## 工作原理

1. 分析用户请求或任务模式
2. 设计带有适当 frontmatter 的新技能
3. 将技能文件写入 `~/.claude/skills/dynamic/`
4. 新技能通过热加载立即可用

## 技能文件格式

```markdown
---
name: 技能名称
description: 技能功能描述，以及何时应当调用此技能（用于自动调用判断）
allowed-tools: Read,Write,Bash,Edit
---

# 技能标题

当此技能被调用时，Claude 的执行指令...
```

## 多文件技能（推荐结构）

复杂技能可拆分为多个文件，提升可维护性：

```
~/.claude/skills/dynamic/
└── my-skill/
    ├── SKILL.md        # 主技能文件（核心指令，保持简洁）
    ├── reference.md    # 参考文档（AI 按需读取）
    └── examples.md     # 示例（AI 按需读取）
```

主 SKILL.md 应包含 `Read` 工具权限，以便 AI 在需要时读取附属文件：
```
allowed-tools: Read,Bash
```

## 动态技能目录

动态技能保存在 `~/.claude/skills/dynamic/`，这是工作区私有技能，在会话之间持久保存。

## 何时使用

- 发现某类任务需要重复执行固定流程
- 需要将领域知识封装为可调用的技能
- 想要创建特定工作场景的操作指南
