import axios from './axios'
import { createEventStream } from './utils/stream'

/** 镜像拉取 SSE 消息结构 */
export type ImagePullMessage =
  | { type: 'progress'; layer: string; status: string }
  | { type: 'done'; data: string }
  | { type: 'error'; data: string }

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
  // 聚合信息
  channel_count: number
  channel_names: string[]          // chat_key 列表
  channel_display_names: string[]  // 频道显示名（channel_name 或 fallback 到 chat_key）
  skill_count: number
  mcp_count: number
  cc_model_preset_name: string | null
}

export interface WorkspaceDetail extends WorkspaceSummary {
  container_id: string | null
  last_heartbeat: string | null
  last_error: string | null
  metadata: Record<string, unknown>
  cc_model_preset_id?: number | null
  primary_channel_chat_key?: string | null
}

export interface SandboxStatus {
  workspace_id: number
  status: string
  container_name: string | null
  container_id: string | null
  host_port: number | null
  session_id: string | null
  tools: string[] | null
  cc_version: string | null
  claude_code_version: string | null
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
  source: 'builtin' | 'user' | 'repo'
  repo_name?: string | null
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
  description: string
  is_primary: boolean
}

export interface ChannelAnnotationUpdateBody {
  chat_key: string
  description: string
  is_primary: boolean
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

export interface PromptLayerItem {
  key: string
  title: string
  target: 'cc' | 'na' | 'shared'
  maintainer: 'manual' | 'cc' | 'na' | 'manual+cc' | 'manual+na'
  content: string
  description: string
  editable_by_cc: boolean
  auto_inject: boolean
  updated_at: string | null
  updated_by: string | null
}

export interface PromptComposerResponse {
  claude_md_content: string
  claude_md_extra: string
  na_context: PromptLayerItem
  shared_manual_rules: PromptLayerItem
  na_manual_rules: PromptLayerItem
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

// ── MCP 结构化类型 ──

export type McpServerType = 'stdio' | 'sse' | 'http'

export interface McpServerConfig {
  name: string
  type: McpServerType
  enabled: boolean
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  headers?: Record<string, string>
}

export interface McpEnvKeyDef {
  key: string
  description: string
  required: boolean
}

export interface McpRegistryItem {
  id: string
  name: string
  description: string
  icon?: string
  type: McpServerType
  command?: string
  args?: string[]
  env_keys?: McpEnvKeyDef[]
  url?: string
  tags?: string[]
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
    const response = await axios.get<{ channels: BoundChannel[] }>(`/workspaces/${id}/channels`)
    return response.data.channels
  },

  bindChannel: async (id: number, chatKey: string): Promise<void> => {
    await axios.post(`/workspaces/${id}/channels`, { chat_key: chatKey })
  },

  unbindChannel: async (id: number, chatKey: string): Promise<void> => {
    await axios.delete(`/workspaces/${id}/channels/${chatKey}`)
  },

  updateChannelAnnotation: async (id: number, body: ChannelAnnotationUpdateBody): Promise<void> => {
    await axios.put(`/workspaces/${id}/channel-annotations`, body)
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

  checkSandboxImage: async (id: number): Promise<{ image: string; exists: boolean }> => {
    const response = await axios.get<{ image: string; exists: boolean }>(`/workspaces/${id}/sandbox/image/check`)
    return response.data
  },

  streamPullSandboxImage: (
    id: number,
    onMessage: (msg: ImagePullMessage) => void,
    onError?: (err: Error) => void,
  ): (() => void) => {
    return createEventStream({
      endpoint: `/workspaces/${id}/sandbox/image/pull/stream`,
      method: 'POST',
      onMessage: (raw) => {
        try {
          onMessage(JSON.parse(raw) as ImagePullMessage)
        } catch {
          onMessage({ type: 'progress', layer: '', status: raw })
        }
      },
      onError,
    })
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

  // MCP 结构化操作
  getMcpServers: async (id: number): Promise<McpServerConfig[]> => {
    const response = await axios.get<{ servers: McpServerConfig[] }>(`/workspaces/${id}/mcp/servers`)
    return response.data.servers
  },

  addMcpServer: async (id: number, server: McpServerConfig): Promise<void> => {
    await axios.post(`/workspaces/${id}/mcp/servers`, server)
  },

  updateMcpServer: async (id: number, oldName: string, server: McpServerConfig): Promise<void> => {
    await axios.put(`/workspaces/${id}/mcp/servers/${encodeURIComponent(oldName)}`, server)
  },

  deleteMcpServer: async (id: number, name: string): Promise<void> => {
    await axios.delete(`/workspaces/${id}/mcp/servers/${encodeURIComponent(name)}`)
  },

  syncMcpToSandbox: async (id: number): Promise<void> => {
    await axios.post(`/workspaces/${id}/mcp/sync`)
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

  // CLAUDE.md
  getClaudeMd: async (id: number): Promise<{ content: string; extra: string }> => {
    const response = await axios.get<{ content: string; extra: string }>(`/workspaces/${id}/claude-md`)
    return response.data
  },

  updateClaudeMdExtra: async (id: number, extra: string): Promise<void> => {
    await axios.put(`/workspaces/${id}/claude-md-extra`, { extra })
  },

  getPromptComposer: async (id: number): Promise<PromptComposerResponse> => {
    const response = await axios.get<PromptComposerResponse>(`/workspaces/${id}/prompt-composer`)
    return response.data
  },

  updatePromptComposerNaContext: async (id: number, content: string): Promise<void> => {
    await axios.put(`/workspaces/${id}/prompt-composer/na-context`, { content })
  },

  updatePromptComposerSharedRules: async (id: number, content: string): Promise<void> => {
    await axios.put(`/workspaces/${id}/prompt-composer/shared-manual-rules`, { content })
  },

  updatePromptComposerNaRules: async (id: number, content: string): Promise<void> => {
    await axios.put(`/workspaces/${id}/prompt-composer/na-manual-rules`, { content })
  },
}

// MCP 注册表 API
export const mcpApi = {
  getRegistry: async (): Promise<McpRegistryItem[]> => {
    const response = await axios.get<McpRegistryItem[]>('/mcp/registry')
    return response.data
  },

  getAutoInject: async (): Promise<McpServerConfig[]> => {
    const response = await axios.get<{ servers: McpServerConfig[] }>('/mcp/auto-inject')
    return response.data.servers
  },

  setAutoInject: async (servers: McpServerConfig[]): Promise<void> => {
    await axios.put('/mcp/auto-inject', { servers })
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

export interface SkillDirEntry {
  name: string
  rel_path: string
  type: 'file' | 'dir'
  size: number | null
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

  getAutoInject: async (): Promise<string[]> => {
    const response = await axios.get<{ skills: string[] }>('/skills/auto-inject')
    return response.data.skills
  },

  setAutoInject: async (skills: string[]): Promise<void> => {
    await axios.put('/skills/auto-inject', { skills })
  },

  getDir: async (name: string, source: 'builtin' | 'user' | 'repo' = 'user'): Promise<SkillDirEntry[]> => {
    const response = await axios.get<{ entries: SkillDirEntry[] }>('/skills/dir', {
      params: { name, source },
    })
    return response.data.entries
  },

  saveFile: async (path: string, content: string): Promise<void> => {
    await axios.put('/skills/file', { path, content })
  },

  syncToWorkspaces: async (skillId: string): Promise<{ synced_count: number }> => {
    const response = await axios.post<{ ok: boolean; synced_count: number }>('/skills/sync-to-workspaces', {
      skill_id: skillId,
    })
    return response.data
  },
}

// 仓库订阅 API
export interface RepoMeta {
  repo_name: string
  repo_url: string | null
  repo_branch: string | null
  subscribed_at: string | null
  skill_count: number
}

export const repoApi = {
  list: async (): Promise<RepoMeta[]> => {
    const response = await axios.get<{ repos: RepoMeta[] }>('/skills/repos')
    return response.data.repos
  },

  subscribe: async (repoUrl: string, repoName: string): Promise<void> => {
    await axios.post('/skills/repos/subscribe', { repo_url: repoUrl, repo_name: repoName })
  },

  pull: async (repoName: string): Promise<string> => {
    const response = await axios.post<{ ok: boolean; output: string }>(`/skills/repos/${encodeURIComponent(repoName)}/pull`)
    return response.data.output
  },

  unsubscribe: async (repoName: string): Promise<void> => {
    await axios.delete(`/skills/repos/${encodeURIComponent(repoName)}`)
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

export interface DynamicSkillDirEntry {
  name: string
  rel_path: string
  type: 'file' | 'dir'
  size?: number | null
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

  promote: async (workspaceId: number, dirName: string, force = false): Promise<void> => {
    await axios.post(`/workspaces/${workspaceId}/dynamic-skills/${dirName}/promote`, { force })
  },

  getDir: async (workspaceId: number, dirName: string): Promise<DynamicSkillDirEntry[]> => {
    const response = await axios.get<{ entries: DynamicSkillDirEntry[] }>(`/workspaces/${workspaceId}/dynamic-skills/${dirName}/dir`)
    return response.data.entries
  },

  getFile: async (workspaceId: number, dirName: string, relPath: string): Promise<string> => {
    const response = await axios.get<DynamicSkillContent>(`/workspaces/${workspaceId}/dynamic-skills/${dirName}/file`, {
      params: { rel_path: relPath },
    })
    return response.data.content
  },

  saveFile: async (workspaceId: number, dirName: string, relPath: string, content: string): Promise<void> => {
    await axios.put(`/workspaces/${workspaceId}/dynamic-skills/${dirName}/file`, { rel_path: relPath, content })
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

  getFile: async (name: string, path: string): Promise<string> => {
    const response = await axios.get<{ readme: string }>(`/skills/builtin/${name}/file`, {
      params: { path },
    })
    return response.data.readme
  },
}

// 记忆系统 API
export interface MemoryDataStats {
  paragraph_count: number
  episodic_count: number
  semantic_count: number
  entity_count: number
  relation_count: number
  reinforcement_count_7d: number
}

export interface MemoryParagraphData {
  id: number
  summary: string
  content: string
  memory_source: string
  cognitive_type: string
  knowledge_type: string
  base_weight: number
  effective_weight: number
  event_time: string | null
  origin_kind: string
  origin_chat_key: string | null
  create_time: string
}

export interface MemoryEntityData {
  id: number
  entity_type: string
  canonical_name: string
  appearance_count: number
  source_hint: string
  update_time: string
}

export interface MemoryRelationData {
  id: number
  subject_entity_id: number
  subject_name: string
  predicate: string
  object_entity_id: number
  object_name: string
  memory_source: string
  cognitive_type: string
  base_weight: number
  effective_weight: number
  paragraph_id: number | null
  update_time: string
}

export interface MemoryDataResponse {
  stats: MemoryDataStats
  paragraphs: MemoryParagraphData[]
  entities: MemoryEntityData[]
  relations: MemoryRelationData[]
}

export interface MemoryListItem {
  id: number
  memory_type: 'paragraph' | 'entity' | 'relation' | 'episode'
  title: string
  subtitle: string
  status: string
  cognitive_type: string | null
  base_weight: number | null
  effective_weight: number | null
  event_time: string | null
  create_time: string
  update_time: string
}

export interface MemoryListResponse {
  total: number
  items: MemoryListItem[]
}

export interface MemoryDetailResponse {
  memory_type: 'paragraph' | 'entity' | 'relation' | 'episode'
  data: Record<string, unknown>
}

export interface MemoryTraceMessage {
  id: number
  message_id: string
  sender_nickname: string
  content_text: string
  send_timestamp: number
}

export interface MemoryTraceResponse {
  paragraph: Record<string, unknown>
  messages: MemoryTraceMessage[]
  entities: MemoryEntityData[]
  relations: MemoryRelationData[]
}

export interface MemoryPruneResponse {
  paragraphs_pruned: number
  relations_pruned: number
  entities_pruned: number
}

export interface MemoryRebuildChannelStatus {
  chat_key: string
  status: string
  upper_bound_message_db_id: number
  initial_cursor_db_id: number
  last_cursor_db_id: number
  message_count_total: number
  messages_processed: number
  completed: boolean
  progress_ratio: number
  last_error?: string | null
}

export interface MemoryRebuildStartResponse {
  job_id: string
  reused: boolean
  status: string
  message: string
}

export interface MemoryRebuildStatus {
  workspace_id: number
  job_id?: string | null
  is_running: boolean
  status: 'idle' | 'running' | 'completed' | 'failed' | string
  phase?: string | null
  started_at: string | null
  finished_at: string | null
  cutoff: string | null
  semantic_replayed: boolean
  cancel_requested: boolean
  current_chat_key?: string | null
  last_heartbeat_at?: string | null
  failure_code?: string | null
  failure_reason?: string | null
  overall_progress_percent: number
  total_channels: number
  completed_channels: number
  total_messages_processed: number
  channels: MemoryRebuildChannelStatus[]
}

export interface MemoryGraphNode {
  id: string
  memory_type: 'paragraph' | 'entity' | 'relation' | 'episode'
  ref_id: number
  label: string
  subtitle: string
  status: 'active' | 'inactive'
  cognitive_type: string | null
  weight: number
  size: number
  importance: number
  paragraph_id: number | null
  metadata: Record<string, unknown>
}

export interface MemoryGraphEdge {
  id: string
  source: string
  target: string
  edge_type: 'relation_subject' | 'relation_object' | 'relation_paragraph' | 'paragraph_entity' | 'episode_paragraph' | 'episode_entity'
  label: string
  weight: number
  strength: number
  status: 'active' | 'inactive'
  cognitive_type: string | null
  metadata: Record<string, unknown>
}

export interface MemoryGraphResponse {
  generated_at: string
  node_count: number
  edge_count: number
  nodes: MemoryGraphNode[]
  edges: MemoryGraphEdge[]
}

export interface MemoryListParams {
  memory_type?: 'paragraph' | 'entity' | 'relation' | 'episode'
  status?: 'active' | 'inactive'
  cognitive_type?: 'episodic' | 'semantic'
  time_from?: string
  time_to?: string
  sort_by?: 'update_time' | 'create_time' | 'effective_weight'
  order?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export const memoryApi = {
  getData: async (workspaceId: number, limit = 20): Promise<MemoryDataResponse> => {
    const response = await axios.get<MemoryDataResponse>(`/workspaces/${workspaceId}/memory/data`, {
      params: { limit },
    })
    return response.data
  },

  getGraph: async (
    workspaceId: number,
    limit = 240,
    includeInactive = false,
    timeFrom?: string,
    timeTo?: string,
  ): Promise<MemoryGraphResponse> => {
    const response = await axios.get<MemoryGraphResponse>(`/workspaces/${workspaceId}/memory/graph`, {
      params: { limit, include_inactive: includeInactive, time_from: timeFrom, time_to: timeTo },
    })
    return response.data
  },

  list: async (workspaceId: number, params: MemoryListParams = {}): Promise<MemoryListResponse> => {
    const response = await axios.get<MemoryListResponse>(`/workspaces/${workspaceId}/memory/list`, {
      params: {
        memory_type: params.memory_type,
        status: params.status,
        cognitive_type: params.cognitive_type,
        time_from: params.time_from,
        time_to: params.time_to,
        sort_by: params.sort_by,
        order: params.order,
        limit: params.limit ?? 100,
        offset: params.offset ?? 0,
      },
    })
    return response.data
  },

  detail: async (
    workspaceId: number,
    memoryType: 'paragraph' | 'entity' | 'relation' | 'episode',
    memoryId: number,
  ): Promise<MemoryDetailResponse> => {
    const response = await axios.get<MemoryDetailResponse>(`/workspaces/${workspaceId}/memory/${memoryType}/${memoryId}`)
    return response.data
  },

  reinforce: async (
    workspaceId: number,
    memoryType: 'paragraph' | 'entity' | 'relation' | 'episode',
    memoryId: number,
    boost = 0.2,
  ): Promise<void> => {
    await axios.post(`/workspaces/${workspaceId}/memory/${memoryType}/${memoryId}/reinforce`, null, {
      params: { boost },
    })
  },

  demote: async (
    workspaceId: number,
    memoryType: 'paragraph' | 'entity' | 'relation' | 'episode',
    memoryId: number,
    delta = 0.2,
  ): Promise<void> => {
    await axios.post(`/workspaces/${workspaceId}/memory/${memoryType}/${memoryId}/demote`, null, {
      params: { delta },
    })
  },

  freeze: async (
    workspaceId: number,
    memoryType: 'paragraph' | 'entity' | 'relation' | 'episode',
    memoryId: number,
  ): Promise<void> => {
    await axios.post(`/workspaces/${workspaceId}/memory/${memoryType}/${memoryId}/freeze`)
  },

  unfreeze: async (
    workspaceId: number,
    memoryType: 'paragraph' | 'entity' | 'relation' | 'episode',
    memoryId: number,
  ): Promise<void> => {
    await axios.post(`/workspaces/${workspaceId}/memory/${memoryType}/${memoryId}/unfreeze`)
  },

  protect: async (
    workspaceId: number,
    memoryType: 'paragraph' | 'entity' | 'relation' | 'episode',
    memoryId: number,
    protectedFlag = true,
  ): Promise<void> => {
    await axios.post(`/workspaces/${workspaceId}/memory/${memoryType}/${memoryId}/protect`, null, {
      params: { protected: protectedFlag },
    })
  },

  trace: async (workspaceId: number, memoryId: number): Promise<MemoryTraceResponse> => {
    const response = await axios.get<MemoryTraceResponse>(`/workspaces/${workspaceId}/memory/paragraph/${memoryId}/trace`)
    return response.data
  },

  remove: async (
    workspaceId: number,
    memoryType: 'paragraph' | 'entity' | 'relation' | 'episode',
    memoryId: number,
  ): Promise<void> => {
    await axios.delete(`/workspaces/${workspaceId}/memory/${memoryType}/${memoryId}`)
  },

  resetMemory: async (workspaceId: number): Promise<void> => {
    await axios.post(`/workspaces/${workspaceId}/memory/reset`)
  },

  rebuildMemory: async (workspaceId: number): Promise<MemoryRebuildStartResponse> => {
    const response = await axios.post<MemoryRebuildStartResponse>(`/workspaces/${workspaceId}/memory/rebuild`)
    return response.data
  },

  cancelRebuildMemory: async (workspaceId: number): Promise<MemoryRebuildStartResponse> => {
    const response = await axios.post<MemoryRebuildStartResponse>(`/workspaces/${workspaceId}/memory/rebuild/cancel`)
    return response.data
  },

  getRebuildStatus: async (workspaceId: number): Promise<MemoryRebuildStatus> => {
    const response = await axios.get<MemoryRebuildStatus>(`/workspaces/${workspaceId}/memory/rebuild/status`)
    return response.data
  },

  prune: async (workspaceId: number): Promise<MemoryPruneResponse> => {
    const response = await axios.post<MemoryPruneResponse>(`/workspaces/${workspaceId}/memory/prune`)
    return response.data
  },

  edit: async (
    workspaceId: number,
    memoryType: 'paragraph' | 'entity' | 'relation' | 'episode',
    memoryId: number,
    payload: { summary?: string; content?: string },
  ): Promise<void> => {
    await axios.put(`/workspaces/${workspaceId}/memory/${memoryType}/${memoryId}`, payload)
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

export type CommDirection = 'NA_TO_CC' | 'CC_TO_NA' | 'USER_TO_CC' | 'SYSTEM' | 'TOOL_CALL' | 'TOOL_RESULT' | 'CC_STATUS'

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

export interface WorkspaceCommQueueTask {
  task_id: string | null
  source_chat_key: string | null
  started_at: number | null
  enqueued_at: number | null
}

export interface WorkspaceCommQueueResponse {
  current_task: WorkspaceCommQueueTask | null
  queued_tasks: WorkspaceCommQueueTask[]
  queue_length: number
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

  getQueue: async (wsId: number): Promise<WorkspaceCommQueueResponse> => {
    const r = await axios.get<WorkspaceCommQueueResponse>(
      `/workspaces/${wsId}/comm/queue`,
    )
    return r.data
  },

  forceCancel: async (wsId: number): Promise<{ cancelled: boolean }> => {
    const r = await axios.delete<{ cancelled: boolean }>(`/workspaces/${wsId}/comm/queue/current`)
    return r.data
  },
}

export const streamCommLog = (
  wsId: number,
  onMessage: (entry: CommLogEntry) => void,
  onError?: (err: Error) => void,
  onReconnect?: () => void,
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
    onReconnect,
  })
}
