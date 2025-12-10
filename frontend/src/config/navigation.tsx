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
} from '@mui/icons-material'
import { getAdapterNavigationConfigs } from './adapters'

export interface PageConfig {
  path: string
  text: string
  icon: JSX.Element
  parent?: string // 父菜单的 key
}

export interface MenuGroup {
  key: string
  text: string
  icon: JSX.Element
  children: PageConfig[]
}

// 集中的页面配置
export const PAGE_CONFIGS: (PageConfig | MenuGroup)[] = [
  {
    key: 'cloud',
    text: 'Nekro 云',
    icon: <CloudDownloadIcon />,
    children: [
      { path: '/cloud/telemetry', text: '社区观测', icon: <DashboardIcon />, parent: 'cloud' },
      { path: '/cloud/presets-market', text: '人设市场', icon: <FaceIcon />, parent: 'cloud' },
      { path: '/cloud/plugins-market', text: '插件市场', icon: <ExtensionIcon />, parent: 'cloud' },
    ],
  },
  { path: '/dashboard', text: '仪表盘', icon: <DashboardIcon /> },
  { path: '/chat-channel', text: '聊天管理', icon: <ChatIcon /> },
  { path: '/user-manager', text: '用户管理', icon: <GroupIcon /> },
  { path: '/presets', text: '人设管理', icon: <FaceIcon /> },
  {
    key: 'plugins',
    text: '插件管理',
    icon: <ExtensionIcon />,
    children: [
      {
        path: '/plugins/management',
        text: '插件管理',
        icon: <ExtensionIcon />,
        parent: 'plugins',
      },
      { path: '/plugins/editor', text: '插件编辑器', icon: <CodeIcon />, parent: 'plugins' },
    ],
  },
  { path: '/logs', text: '系统日志', icon: <TerminalIcon /> },
  { path: '/sandbox-logs', text: '沙盒日志', icon: <CodeIcon /> },
  {
    key: 'adapters',
    text: '适配器',
    icon: <HubIcon />,
    children: getAdapterNavigationConfigs(),
  },
  {
    key: 'settings',
    text: '系统配置',
    icon: <SettingsIcon />,
    children: [
      { path: '/settings/system', text: '基本配置', icon: <TuneIcon />, parent: 'settings' },
      { path: '/settings/model-groups', text: '模型组', icon: <StorageIcon />, parent: 'settings' },
      { path: '/settings/theme', text: '调色盘', icon: <PaletteIcon />, parent: 'settings' },
      { path: '/settings/space-cleanup', text: '空间回收', icon: <CleaningServicesIcon />, parent: 'settings' },
    ],
  },
  { path: '/profile', text: '个人中心', icon: <AccountCircleIcon /> },
]

// 转换配置为菜单项的工具函数
export const createMenuItems = () => {
  return PAGE_CONFIGS.map(config => {
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
  const allPages = PAGE_CONFIGS.flatMap(config =>
    'children' in config ? config.children : [config]
  )
  // 查找匹配的页面
  return allPages.find(
    page =>
      'path' in page &&
      (page.path === pathname || (pathname.startsWith(page.path) && page.path !== '/'))
  )
}

// 获取当前页面标题的工具函数
export const getCurrentTitleFromConfigs = (pathname: string) => {
  return getCurrentPageFromConfigs(pathname)?.text || '管理面板'
}
