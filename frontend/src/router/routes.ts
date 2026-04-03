export const WORKSPACE_DETAIL_TABS = [
  'overview',
  'sandbox',
  'comm',
  'memory',
  'extensions',
  'mcp',
  'prompt',
  'config',
] as const

export type WorkspaceDetailTab = (typeof WORKSPACE_DETAIL_TABS)[number]

export const DEFAULT_WORKSPACE_DETAIL_TAB: WorkspaceDetailTab = 'overview'

export const isWorkspaceDetailTab = (value: string | null | undefined): value is WorkspaceDetailTab =>
  value !== undefined && value !== null && WORKSPACE_DETAIL_TABS.includes(value as WorkspaceDetailTab)

export const workspaceListPath = () => '/workspace'

export const workspaceDetailPath = (
  workspaceId: number | string,
  tab: WorkspaceDetailTab = DEFAULT_WORKSPACE_DETAIL_TAB
) => `/workspace/${workspaceId}/${tab}`

export const pluginsManagementPath = (pluginId?: string | null) =>
  pluginId ? `/plugins/management/${encodeURIComponent(pluginId)}` : '/plugins/management'

export const CHAT_CHANNEL_DETAIL_TABS = [
  'message-history',
  'override-settings',
  'basic-info',
  'plugin-data',
] as const

export type ChatChannelDetailTab = (typeof CHAT_CHANNEL_DETAIL_TABS)[number]

export const DEFAULT_CHAT_CHANNEL_DETAIL_TAB: ChatChannelDetailTab = 'message-history'

export const isChatChannelDetailTab = (value: string | null | undefined): value is ChatChannelDetailTab =>
  value !== undefined && value !== null && CHAT_CHANNEL_DETAIL_TABS.includes(value as ChatChannelDetailTab)

export const chatChannelPath = (chatKey?: string | null, tab?: ChatChannelDetailTab | null) =>
  chatKey
    ? tab
      ? `/chat-channel/${encodeURIComponent(chatKey)}/${tab}`
      : `/chat-channel/${encodeURIComponent(chatKey)}`
    : '/chat-channel'

export const loginPath = (redirectTo?: string | null) =>
  redirectTo ? `/login?redirect=${encodeURIComponent(redirectTo)}` : '/login'

export const sanitizeRedirectTarget = (target: string | null | undefined) => {
  if (!target) return null
  if (!target.startsWith('/')) return null
  if (target.startsWith('//')) return null
  if (target.startsWith('/login')) return null
  return target
}

/**
 * 当前应用 path（仅 pathname，不含 query/hash）。
 * 用于登录重定向等场景，避免 redirect 参数内包含 ?/& 导致 URL 被截断或解析错误。
 */
export const getCurrentAppPath = () => {
  if (typeof window === 'undefined') return '/'

  const hash = window.location.hash
  if (!hash.startsWith('#')) return '/'

  const currentPath = hash.slice(1)
  const pathnameOnly = currentPath.split('?')[0]
  return pathnameOnly || '/'
}
