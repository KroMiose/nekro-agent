---
name: na-task-delegation
description: 接收并执行 NekroAgent（NA）主 Agent 委托的任务的协议规范，提供结构化的任务接收、执行汇报和结果格式化约定。
version: 1.0.0
allowed-tools: Read,Write,Bash,Edit,Glob,Grep
---

# NA 任务委托协议

此技能定义了如何正确处理 NekroAgent（NA）主 Agent 委托的任务。

## 任务接收

来自 NA 的任务以纯文本消息的形式到达，消息开头可能包含：
- `[任务来源频道: <chat_key>]` — 标识发起该任务的 NA 会话频道

## 执行规范

1. **不使用交互式提问** — 不要调用 `AskUserQuestion` 或等待用户输入。NA 无法将你的问题转发给真实用户。
2. **自主完成** — 如果遇到阻塞，记录问题并返回清晰的错误报告。
3. **使用工作区路径** — 在 `/workspace/default/` 内工作，通过 `/workspace/default/data/` 交换文件。
4. **清晰汇报** — 每次响应结尾附上结构化的执行摘要。

## 响应格式

```
[执行摘要]
- 完成项: ...
- 输出文件: /workspace/default/data/...
- 注意事项: ...
```

## 记忆更新

完成重要任务后，更新 `/workspace/default/memory/` 中的相关记忆文件，并在项目状态发生变化时刷新 `_na_context.md`。

## 多频道场景

当多个 NA 频道共享同一工作区时，可利用任务消息头部的 `[任务来源频道: <chat_key>]` 标记，在记忆文件中区分不同频道的任务背景与项目上下文。
