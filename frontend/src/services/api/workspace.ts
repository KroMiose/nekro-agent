import axios from './axios'
import { createEventStream } from './utils/stream'

export interface WorkspaceSummary {
  id: number
  name: string
  description: string
  status: 'active' | 'stopped' | 'failed' | 'deleting'
  sandbox_image: string
  sandbox_version: string
  container_name: string | null
  host_port: number | null
  runtime_policy: 'agent' | 'relaxed' | 'strict'
  create_time: string
  update_time: string
}

export interface WorkspaceDetail extends WorkspaceSummary {
  container_id: string | null
  last_heartbeat: string | null
  last_error: string | null
  metadata: Record<string, unknown>
  cc_model_preset_id?: number | null
}

export interface SandboxStatus {
  workspace_id: number
  status: string
  container_name: string | null
  container_id: string | null
  host_port: number | null
  session_id: string | null
  tools: string[] | null
}

export interface SkillItem {
  name: string
  description: string
  docs?: string[]  // 附属文档文件名列表，如 ["install.md"]
}

export interface AllSkillItem {
  name: string
  display_name: string
  description: string
  source: 'builtin' | 'user'
}

export interface AllSkillsResponse {
  total: number
  items: AllSkillItem[]
}

export interface SkillListResponse {
  total: number
  items: SkillItem[]
}

export interface BoundChannel {
  chat_key: string
}

export interface CreateWorkspaceBody {
  name: string
  description?: string
  runtime_policy?: 'agent' | 'relaxed' | 'strict'
}

export interface WorkspaceEnvVar {
  key: string
  value: string
  description: string
}

export interface WorkspaceEnvVarsResponse {
  env_vars: WorkspaceEnvVar[]
}

export interface UpdateWorkspaceBody {
  name?: string
  description?: string
  sandbox_image?: string
  runtime_policy?: 'agent' | 'relaxed' | 'strict'
}

export interface WorkspaceListResponse {
  total: number
  items: WorkspaceSummary[]
}

export const workspaceApi = {
  // 工作区 CRUD
  getList: async (): Promise<WorkspaceSummary[]> => {
    const response = await axios.get<WorkspaceListResponse>('/workspaces/list')
    return response.data.items
  },

  create: async (body: CreateWorkspaceBody): Promise<WorkspaceDetail> => {
    const response = await axios.post<WorkspaceDetail>('/workspaces', body)
    return response.data
  },

  getDetail: async (id: number): Promise<WorkspaceDetail> => {
    const response = await axios.get<WorkspaceDetail>(`/workspaces/${id}`)
    return response.data
  },

  update: async (id: number, body: UpdateWorkspaceBody): Promise<WorkspaceDetail> => {
    const response = await axios.patch<WorkspaceDetail>(`/workspaces/${id}`, body)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await axios.delete(`/workspaces/${id}`)
  },

  // 频道绑定
  getBoundChannels: async (id: number): Promise<BoundChannel[]> => {
    const response = await axios.get<{ channels: string[] }>(`/workspaces/${id}/channels`)
    return response.data.channels.map(ch => ({ chat_key: ch }))
  },

  bindChannel: async (id: number, chatKey: string): Promise<void> => {
    await axios.post(`/workspaces/${id}/channels`, { chat_key: chatKey })
  },

  unbindChannel: async (id: number, chatKey: string): Promise<void> => {
    await axios.delete(`/workspaces/${id}/channels/${chatKey}`)
  },

  // 沙盒操作
  sandboxStart: async (id: number): Promise<void> => {
    await axios.post(`/workspaces/${id}/sandbox/start`)
  },

  sandboxStop: async (id: number): Promise<void> => {
    await axios.post(`/workspaces/${id}/sandbox/stop`)
  },

  sandboxRestart: async (id: number): Promise<void> => {
    await axios.post(`/workspaces/${id}/sandbox/restart`)
  },

  sandboxRebuild: async (id: number): Promise<void> => {
    await axios.post(`/workspaces/${id}/sandbox/rebuild`)
  },

  getSandboxStatus: async (id: number): Promise<SandboxStatus> => {
    const response = await axios.get<SandboxStatus>(`/workspaces/${id}/sandbox/status`)
    return response.data
  },

  getSandboxLogs: async (id: number, tail: number = 100): Promise<string> => {
    const response = await axios.get<{ logs: string }>(`/workspaces/${id}/sandbox/logs`, {
      params: { tail },
    })
    return response.data.logs
  },

  // Session
  resetSession: async (id: number): Promise<void> => {
    await axios.post(`/workspaces/${id}/session/reset`)
  },

  // 工具
  getTools: async (id: number): Promise<string[]> => {
    const response = await axios.get<{ tools: string[] }>(`/workspaces/${id}/tools`)
    return response.data.tools
  },

  refreshTools: async (id: number): Promise<string[]> => {
    const response = await axios.post<{ tools: string[] }>(`/workspaces/${id}/tools/refresh`)
    return response.data.tools
  },

  // Skills
  getWorkspaceSkills: async (id: number): Promise<string[]> => {
    const response = await axios.get<{ skills: string[] }>(`/workspaces/${id}/skills`)
    return response.data.skills
  },

  updateWorkspaceSkills: async (id: number, skills: string[]): Promise<void> => {
    await axios.put(`/workspaces/${id}/skills`, { skills })
  },

  syncSkill: async (id: number, skillName: string): Promise<void> => {
    await axios.post(`/workspaces/${id}/skills/${encodeURIComponent(skillName)}/sync`)
  },

  // MCP
  getMcpConfig: async (id: number): Promise<Record<string, unknown>> => {
    const response = await axios.get<{ mcp_config: Record<string, unknown> }>(
      `/workspaces/${id}/mcp`
    )
    return response.data.mcp_config
  },

  updateMcpConfig: async (id: number, mcpConfig: Record<string, unknown>): Promise<void> => {
    await axios.put(`/workspaces/${id}/mcp`, { mcp_config: mcpConfig })
  },

  // CC 模型预设
  getCCModelPreset: async (id: number): Promise<{ preset_id: number | null; config_json: Record<string, unknown> | null }> => {
    const response = await axios.get<{ preset_id: number | null; config_json: Record<string, unknown> | null }>(
      `/workspaces/${id}/cc-model-preset`
    )
    return response.data
  },

  setCCModelPreset: async (id: number, presetId: number | null): Promise<void> => {
    await axios.put(`/workspaces/${id}/cc-model-preset`, { cc_model_preset_id: presetId })
  },

  // 环境变量
  getEnvVars: async (id: number): Promise<WorkspaceEnvVar[]> => {
    const response = await axios.get<WorkspaceEnvVarsResponse>(`/workspaces/${id}/env-vars`)
    return response.data.env_vars
  },

  updateEnvVars: async (id: number, envVars: WorkspaceEnvVar[]): Promise<void> => {
    await axios.put(`/workspaces/${id}/env-vars`, { env_vars: envVars })
  },
}

// Skills 库 API
export interface SkillTreeNode {
  name: string
  path: string
  type: 'skill' | 'repo' | 'dir' | 'doc'
  skill_name?: string | null
  skill_description?: string | null
  has_git: boolean
  repo_url?: string | null
  repo_branch?: string | null
  children?: SkillTreeNode[] | null
}

export interface SkillTreeResponse {
  nodes: SkillTreeNode[]
}

export const skillsLibraryApi = {
  getTree: async (): Promise<SkillTreeNode[]> => {
    const response = await axios.get<SkillTreeResponse>('/skills/tree')
    return response.data.nodes
  },

  getAll: async (): Promise<AllSkillItem[]> => {
    const response = await axios.get<AllSkillsResponse>('/skills/all')
    return response.data.items
  },

  getList: async (): Promise<SkillListResponse> => {
    const response = await axios.get<SkillListResponse>('/skills')
    return response.data
  },

  getContent: async (path: string): Promise<string> => {
    const response = await axios.get<{ readme: string }>('/skills/content', { params: { path } })
    return response.data.readme
  },

  getFile: async (path: string): Promise<string> => {
    const response = await axios.get<{ readme: string }>('/skills/file', { params: { path } })
    return response.data.readme
  },

  clone: async (repoUrl: string, targetDir: string): Promise<void> => {
    await axios.post('/skills/clone', { repo_url: repoUrl, target_dir: targetDir })
  },

  pull: async (path: string): Promise<string> => {
    const response = await axios.post<{ ok: boolean; output: string }>('/skills/pull', { path })
    return response.data.output
  },

  upload: async (file: File): Promise<void> => {
    const formData = new FormData()
    formData.append('file', file)
    await axios.post('/skills', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  delete: async (name: string): Promise<void> => {
    await axios.delete(`/skills/${name}`)
  },

  getReadme: async (name: string): Promise<string> => {
    const response = await axios.get<{ readme: string }>(`/skills/${name}/readme`)
    return response.data.readme
  },
}

// 动态 Skill API（工作区级）
export interface DynamicSkillItem {
  dir_name: string
  name: string
  description: string
}

export interface DynamicSkillListResponse {
  total: number
  items: DynamicSkillItem[]
}

export interface DynamicSkillContent {
  dir_name: string
  content: string
}

export const dynamicSkillApi = {
  list: async (workspaceId: number): Promise<DynamicSkillItem[]> => {
    const response = await axios.get<DynamicSkillListResponse>(`/workspaces/${workspaceId}/dynamic-skills`)
    return response.data.items
  },

  get: async (workspaceId: number, dirName: string): Promise<DynamicSkillContent> => {
    const response = await axios.get<DynamicSkillContent>(`/workspaces/${workspaceId}/dynamic-skills/${dirName}`)
    return response.data
  },

  put: async (workspaceId: number, dirName: string, content: string): Promise<void> => {
    await axios.put(`/workspaces/${workspaceId}/dynamic-skills/${dirName}`, { content })
  },

  delete: async (workspaceId: number, dirName: string): Promise<void> => {
    await axios.delete(`/workspaces/${workspaceId}/dynamic-skills/${dirName}`)
  },

  promote: async (workspaceId: number, dirName: string): Promise<void> => {
    await axios.post(`/workspaces/${workspaceId}/dynamic-skills/${dirName}/promote`)
  },
}

// 内置 Skill API
export const builtinSkillApi = {
  getList: async (): Promise<SkillItem[]> => {
    const response = await axios.get<SkillListResponse>('/skills/builtin')
    return response.data.items
  },

  getContent: async (name: string): Promise<string> => {
    const response = await axios.get<{ readme: string }>(`/skills/builtin/${name}`)
    return response.data.readme
  },

  getDoc: async (name: string, filename: string): Promise<string> => {
    const response = await axios.get<{ readme: string }>(`/skills/builtin/${name}/doc`, {
      params: { filename },
    })
    return response.data.readme
  },
}

// 记忆系统 API
export interface MemoryFileMeta {
  path: string
  title: string
  category: string
  tags: string[]
  shared: boolean
  updated: string
}

export interface MemoryTreeNode {
  name: string
  type: 'file' | 'dir'
  path: string
  meta: MemoryFileMeta | null
  children: MemoryTreeNode[] | null
}

export interface MemoryFileContent {
  path: string
  raw: string
  content: string
  meta: MemoryFileMeta
}

export const memoryApi = {
  getTree: async (workspaceId: number): Promise<MemoryTreeNode[]> => {
    const response = await axios.get<{ nodes: MemoryTreeNode[] }>(`/workspaces/${workspaceId}/memory/tree`)
    return response.data.nodes
  },

  getFile: async (workspaceId: number, path: string): Promise<MemoryFileContent> => {
    const response = await axios.get<MemoryFileContent>(`/workspaces/${workspaceId}/memory/file`, {
      params: { path },
    })
    return response.data
  },

  putFile: async (workspaceId: number, path: string, raw: string): Promise<void> => {
    await axios.put(`/workspaces/${workspaceId}/memory/file`, { path, raw })
  },

  deleteFile: async (workspaceId: number, path: string): Promise<void> => {
    await axios.delete(`/workspaces/${workspaceId}/memory/file`, { params: { path } })
  },

  getNaContext: async (workspaceId: number): Promise<string> => {
    const response = await axios.get<{ content: string }>(`/workspaces/${workspaceId}/memory/na-context`)
    return response.data.content
  },

  putNaContext: async (workspaceId: number, content: string): Promise<void> => {
    await axios.put(`/workspaces/${workspaceId}/memory/na-context`, { content })
  },

  resetMemory: async (workspaceId: number): Promise<void> => {
    await axios.post(`/workspaces/${workspaceId}/memory/reset`)
  },
}

// 日志 SSE 流
export const streamSandboxLogs = (
  id: number,
  onMessage: (data: string, type: 'log' | 'error' | 'info') => void,
  onError?: (err: Error) => void,
): (() => void) => {
  return createEventStream({
    endpoint: `/workspaces/${id}/sandbox/logs/stream`,
    onMessage: (raw) => {
      try {
        const msg = JSON.parse(raw) as { type: 'log' | 'error' | 'info'; data: string }
        onMessage(msg.data, msg.type)
      } catch {
        onMessage(raw, 'log')
      }
    },
    onError,
  })
}

// 终端 WebSocket URL
export const getSandboxTerminalWsUrl = (id: number): string => {
  // 获取 base URL 并构造 WS URL
  const apiBase = (window.location.origin + '/api').replace('http://', 'ws://').replace('https://', 'wss://')
  return `${apiBase}/workspaces/${id}/sandbox/terminal`
}

// ── 沙盒通讯日志 ────────────────────────────────────────────────────────────

export type CommDirection = 'NA_TO_CC' | 'CC_TO_NA' | 'USER_TO_CC' | 'SYSTEM' | 'TOOL_CALL' | 'TOOL_RESULT'

export interface CommLogEntry {
  id: number
  workspace_id: number
  direction: CommDirection
  source_chat_key: string
  content: string
  is_streaming: boolean
  task_id: string | null
  create_time: string
}

export interface CommHistoryResponse {
  total: number
  items: CommLogEntry[]
}

export const commApi = {
  getHistory: async (wsId: number, limit = 100, beforeId?: number): Promise<CommHistoryResponse> => {
    const params: Record<string, unknown> = { limit }
    if (beforeId !== undefined) params.before_id = beforeId
    const r = await axios.get<CommHistoryResponse>(`/workspaces/${wsId}/comm/history`, { params })
    return r.data
  },

  sendToCC: async (wsId: number, content: string): Promise<{ ok: boolean; reply: string }> => {
    const r = await axios.post<{ ok: boolean; reply: string }>(`/workspaces/${wsId}/comm/send`, { content })
    return r.data
  },
}

export const streamCommLog = (
  wsId: number,
  onMessage: (entry: CommLogEntry) => void,
  onError?: (err: Error) => void,
): (() => void) => {
  return createEventStream({
    endpoint: `/workspaces/${wsId}/comm/stream`,
    onMessage: (raw) => {
      try {
        onMessage(JSON.parse(raw) as CommLogEntry)
      } catch {
        // ignore malformed events
      }
    },
    onError,
  })
}
