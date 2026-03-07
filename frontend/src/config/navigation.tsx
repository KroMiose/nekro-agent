import {
  Terminal as TerminalIcon,
  Settings as SettingsIcon,
  Storage as StorageIcon,
  Tune as TuneIcon,
  Extension as ExtensionIcon,
  Chat as ChatIcon,
  Code as CodeIcon,
  Dashboard as DashboardIcon,
  Group as GroupIcon,
  Face as FaceIcon,
  AccountCircle as AccountCircleIcon,
  CloudDownload as CloudDownloadIcon,
  Palette as PaletteIcon,
  Hub as HubIcon,
  CleaningServices as CleaningServicesIcon,
  Workspaces as WorkspacesIcon,
  ListAlt as ListAltIcon,
} from '@mui/icons-material'
import { getAdapterNavigationConfigs } from './adapters'
import i18next from './i18n'

export interface PageConfig {
  path: string
  text: string
  translationKey?: string // 翻译键（可选，适配器配置可能没有）
  icon: JSX.Element
  parent?: string // 父菜单的 key
}

export interface MenuGroup {
  key: string
  text: string
  translationKey?: string // 翻译键（可选，适配器配置可能没有）
  icon: JSX.Element
  children: PageConfig[]
}

// 获取翻译的辅助函数
const t = (key: string) => i18next.t(key, { ns: 'navigation' })

// 获取页面配置（动态生成以支持语言切换）
export const getPageConfigs = (): (PageConfig | MenuGroup)[] => [
  {
    key: 'cloud',
    text: t('menu.cloud'),
    translationKey: 'menu.cloud',
    icon: <CloudDownloadIcon />,
    children: [
      {
        path: '/cloud/telemetry',
        text: t('menu.telemetry'),
        translationKey: 'menu.telemetry',
        icon: <DashboardIcon />,
        parent: 'cloud',
      },
      {
        path: '/cloud/presets-market',
        text: t('menu.presetsMarket'),
        translationKey: 'menu.presetsMarket',
        icon: <FaceIcon />,
        parent: 'cloud',
      },
      {
        path: '/cloud/plugins-market',
        text: t('menu.pluginsMarket'),
        translationKey: 'menu.pluginsMarket',
        icon: <ExtensionIcon />,
        parent: 'cloud',
      },
    ],
  },
  {
    path: '/dashboard',
    text: t('menu.dashboard'),
    translationKey: 'menu.dashboard',
    icon: <DashboardIcon />,
  },
  {
    path: '/chat-channel',
    text: t('menu.chatChannel'),
    translationKey: 'menu.chatChannel',
    icon: <ChatIcon />,
  },
  {
    path: '/user-manager',
    text: t('menu.userManager'),
    translationKey: 'menu.userManager',
    icon: <GroupIcon />,
  },
  {
    path: '/presets',
    text: t('menu.presets'),
    translationKey: 'menu.presets',
    icon: <FaceIcon />,
  },
  {
    key: 'plugins',
    text: t('menu.plugins'),
    translationKey: 'menu.plugins',
    icon: <ExtensionIcon />,
    children: [
      {
        path: '/plugins/management',
        text: t('menu.pluginManagement'),
        translationKey: 'menu.pluginManagement',
        icon: <ExtensionIcon />,
        parent: 'plugins',
      },
      {
        path: '/plugins/editor',
        text: t('menu.pluginEditor'),
        translationKey: 'menu.pluginEditor',
        icon: <CodeIcon />,
        parent: 'plugins',
      },
    ],
  },
  {
    path: '/logs',
    text: t('menu.logs'),
    translationKey: 'menu.logs',
    icon: <TerminalIcon />,
  },
  {
    key: 'workspace',
    text: t('menu.workspace'),
    translationKey: 'menu.workspace',
    icon: <WorkspacesIcon />,
    children: [
      {
        path: '/workspace',
        text: t('menu.workspaceList'),
        translationKey: 'menu.workspaceList',
        icon: <WorkspacesIcon />,
        parent: 'workspace',
      },
      {
        path: '/workspace/skills',
        text: t('menu.skillsLibrary'),
        translationKey: 'menu.skillsLibrary',
        icon: <ExtensionIcon />,
        parent: 'workspace',
      },
      {
        path: '/workspace/cc-models',
        text: t('menu.ccModels'),
        translationKey: 'menu.ccModels',
        icon: <StorageIcon />,
        parent: 'workspace',
      },
    ],
  },
  {
    path: '/sandbox-logs',
    text: t('menu.sandboxLogs'),
    translationKey: 'menu.sandboxLogs',
    icon: <CodeIcon />,
  },
  {
    key: 'adapters',
    text: t('menu.adapters'),
    translationKey: 'menu.adapters',
    icon: <HubIcon />,
    children: getAdapterNavigationConfigs(),
  },
  {
    key: 'settings',
    text: t('menu.settings'),
    translationKey: 'menu.settings',
    icon: <SettingsIcon />,
    children: [
      {
        path: '/settings/system',
        text: t('menu.systemSettings'),
        translationKey: 'menu.systemSettings',
        icon: <TuneIcon />,
        parent: 'settings',
      },
      {
        path: '/settings/model-groups',
        text: t('menu.modelGroups'),
        translationKey: 'menu.modelGroups',
        icon: <StorageIcon />,
        parent: 'settings',
      },
      {
        path: '/settings/theme',
        text: t('menu.theme'),
        translationKey: 'menu.theme',
        icon: <PaletteIcon />,
        parent: 'settings',
      },
      {
        path: '/settings/space-cleanup',
        text: t('menu.spaceCleanup'),
        translationKey: 'menu.spaceCleanup',
        icon: <CleaningServicesIcon />,
        parent: 'settings',
      },
    ],
  },
  {
    key: 'commands',
    text: t('menu.commandSystem'),
    translationKey: 'menu.commandSystem',
    icon: <ListAltIcon />,
    children: [
      {
        path: '/commands/management',
        text: t('menu.commands'),
        translationKey: 'menu.commands',
        icon: <ListAltIcon />,
        parent: 'commands',
      },
      {
        path: '/commands/output',
        text: t('menu.commandOutput'),
        translationKey: 'menu.commandOutput',
        icon: <TerminalIcon />,
        parent: 'commands',
      },
    ],
  },
  {
    path: '/profile',
    text: t('menu.profile'),
    translationKey: 'menu.profile',
    icon: <AccountCircleIcon />,
  },
]

// 为了向后兼容，保留 PAGE_CONFIGS（但建议使用 getPageConfigs）
export const PAGE_CONFIGS = getPageConfigs()

// 转换配置为菜单项的工具函数
export const createMenuItems = () => {
  return getPageConfigs().map(config => {
    if ('children' in config) {
      return {
        text: config.text,
        icon: config.icon,
        path: undefined,
        key: config.key,
        children: config.children.map(child => ({
          text: child.text,
          icon: child.icon,
          path: child.path,
        })),
      }
    }
    return {
      text: config.text,
      icon: config.icon,
      path: config.path,
    }
  })
}

// 获取当前页面信息的工具函数
export const getCurrentPageFromConfigs = (pathname: string) => {
  // 扁平化所有页面配置
  const allPages = getPageConfigs().flatMap(config =>
    'children' in config ? config.children : [config]
  )
  // 最长路径优先匹配：避免短路径（如 /workspace）在访问长路径（如 /workspace/skills）时也高亮
  const matches = allPages.filter(
    page =>
      'path' in page &&
      (page.path === pathname || pathname.startsWith((page as PageConfig).path + '/'))
  )
  return matches.sort(
    (a, b) => ((b as PageConfig).path?.length ?? 0) - ((a as PageConfig).path?.length ?? 0)
  )[0]
}

// 获取当前页面标题的工具函数
export const getCurrentTitleFromConfigs = (pathname: string) => {
  const page = getCurrentPageFromConfigs(pathname)
  if (page && 'translationKey' in page && page.translationKey) {
    return t(page.translationKey)
  }
  return t('menu.defaultTitle')
}
