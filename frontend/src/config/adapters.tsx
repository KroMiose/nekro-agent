import {
  Home as HomeIcon,
  Settings as SettingsIcon,
  Engineering as EngineeringIcon,
  SmartToy as NapCatIcon,
  Terminal as LogsIcon,
  SmartToy as SmartToyIcon,
  SportsEsports as SportsEsportsIcon,
  LiveTv as LiveTvIcon,
  Api as ApiIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  RadioButtonUnchecked as RadioButtonUncheckedIcon,
  Style as StyleIcon,
<<<<<<< HEAD
  QuestionAnswer as QuestionAnswerIcon,
  Chat as ChatIcon,
  Send as SendIcon,
=======
<<<<<<< HEAD
  QuestionAnswer as QuestionAnswerIcon,
  Chat as ChatIcon,
  Send as SendIcon,
=======
<<<<<<< HEAD
  QuestionAnswer as QuestionAnswerIcon,
  Chat as ChatIcon,
  Send as SendIcon,
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
} from '@mui/icons-material'
import { ReactElement } from 'react'
import { Theme } from '@mui/material'
import { Avatar, SxProps } from '@mui/material'
import { UI_STYLES } from '../theme/themeConfig'

import AdapterHomePage from '../pages/adapter/AdapterHomePage'
import AdapterConfigPage from '../pages/adapter/AdapterConfigPage'
import AdapterAdvancedPage from '../pages/adapter/AdapterAdvancedPage'
import AdapterOverrideConfigPage from '../pages/adapter/AdapterOverrideConfigPage'
import OneBotV11NapCatPage from '../pages/adapter/onebot_v11/napcat'
import OneBotV11LogsPage from '../pages/adapter/onebot_v11/logs'

export interface AdapterTabConfig {
  label: string
  value: string
  icon: ReactElement
  path: string
  component: ReactElement
}

// 适配器视觉配置
export interface AdapterVisualConfig {
  displayName: string // 显示名称
  iconText: string // 图标显示文本
  navIcon: ReactElement // 导航图标
  description?: string // 描述信息
  primaryColor?: string // 主色调
  tags?: string[] // 标签
}

export interface AdapterConfig {
  key: string
  visual: AdapterVisualConfig
  tabs: AdapterTabConfig[]
}

// 状态显示配置
export interface AdapterStatusDisplay {
  icon: ReactElement
  text: string
  color: 'success' | 'error' | 'warning' | 'default'
  getBgColor: (theme: Theme) => string
}

// 适配器配置映射
export const ADAPTER_CONFIGS: Record<string, AdapterConfig> = {
  // OneBot V11 适配器配置
  onebot_v11: {
    key: 'onebot_v11',
    visual: {
      displayName: 'OneBot V11',
      iconText: 'QQ',
      navIcon: <SmartToyIcon />,
      description: 'OneBot V11 协议适配器，支持 QQ 机器人通信',
      tags: ['QQ', 'OneBot', '聊天'],
    },
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '适配器配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
      },
      {
        label: '覆盖配置',
        value: 'overrides',
        icon: <StyleIcon fontSize="small" />,
        path: 'overrides',
        component: <AdapterOverrideConfigPage />,
      },
      {
        label: 'NapCat',
        value: 'napcat',
        icon: <NapCatIcon fontSize="small" />,
        path: 'napcat',
        component: <OneBotV11NapCatPage />,
      },
      {
        label: '容器日志',
        value: 'logs',
        icon: <LogsIcon fontSize="small" />,
        path: 'logs',
        component: <OneBotV11LogsPage />,
      },
      {
        label: '高级',
        value: 'advanced',
        icon: <EngineeringIcon fontSize="small" />,
        path: 'advanced',
        component: <AdapterAdvancedPage />,
      },
    ],
  },

  // Minecraft 适配器配置
  minecraft: {
    key: 'minecraft',
    visual: {
      displayName: 'Minecraft',
      iconText: 'MC',
      navIcon: <SportsEsportsIcon />,
      description: 'Minecraft 服务器适配器，支持游戏内聊天',
      tags: ['Minecraft', '游戏', '服务器'],
    },
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '适配器配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
      },
      {
        label: '覆盖配置',
        value: 'overrides',
        icon: <StyleIcon fontSize="small" />,
        path: 'overrides',
        component: <AdapterOverrideConfigPage />,
      },
      {
        label: '高级',
        value: 'advanced',
        icon: <EngineeringIcon fontSize="small" />,
        path: 'advanced',
        component: <AdapterAdvancedPage />,
      },
    ],
  },

  // Bilibili Live 适配器配置
  bilibili_live: {
    key: 'bilibili_live',
    visual: {
      displayName: 'Bilibili Live',
      iconText: 'B站',
      navIcon: <LiveTvIcon />,
      description: 'Bilibili 直播适配器，接收直播间弹幕和互动',
      tags: ['Bilibili', '直播', '弹幕'],
    },
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '适配器配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
      },
      {
        label: '覆盖配置',
        value: 'overrides',
        icon: <StyleIcon fontSize="small" />,
        path: 'overrides',
        component: <AdapterOverrideConfigPage />,
      },
      {
        label: '高级',
        value: 'advanced',
        icon: <EngineeringIcon fontSize="small" />,
        path: 'advanced',
        component: <AdapterAdvancedPage />,
      },
    ],
  },

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  // Discord 适配器配置
  discord: {
    key: 'discord',
    visual: {
      displayName: 'Discord',
      iconText: 'DC',
      navIcon: <QuestionAnswerIcon />,
      description: '连接到 Discord 平台的适配器，允许通过 Bot 与服务器和用户进行交互。',
      tags: ['Discord', '聊天', '社区', 'IM'],
    },
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '适配器配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
      },
      {
        label: '覆盖配置',
        value: 'overrides',
        icon: <StyleIcon fontSize="small" />,
        path: 'overrides',
        component: <AdapterOverrideConfigPage />,
      },
      {
        label: '高级',
        value: 'advanced',
        icon: <EngineeringIcon fontSize="small" />,
        path: 'advanced',
        component: <AdapterAdvancedPage />,
      },
    ],
  },

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  // SSE 适配器配置
  sse: {
    key: 'sse',
    visual: {
      displayName: 'SSE',
      iconText: 'SSE',
      navIcon: <ApiIcon />,
      description: '基于 Server-Sent Events 的通用 HTTP 适配器',
      tags: ['SSE', 'HTTP', 'API'],
    },
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '适配器配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
      },
      {
        label: '覆盖配置',
        value: 'overrides',
        icon: <StyleIcon fontSize="small" />,
        path: 'overrides',
        component: <AdapterOverrideConfigPage />,
      },
      {
        label: '高级',
        value: 'advanced',
        icon: <EngineeringIcon fontSize="small" />,
        path: 'advanced',
        component: <AdapterAdvancedPage />,
      },
    ],
  },

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  // WeChatPad 适配器配置
  wechatpad: {
    key: 'wechatpad',
    visual: {
      displayName: 'WeChatPad',
      iconText: '微信',
      navIcon: <ChatIcon />,
      description: 'WeChatPad 微信适配器，支持微信消息收发和群聊管理',
      tags: ['微信', 'WeChat', '聊天', 'IM'],
    },
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '适配器配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
      },
      {
        label: '覆盖配置',
        value: 'overrides',
        icon: <StyleIcon fontSize="small" />,
        path: 'overrides',
        component: <AdapterOverrideConfigPage />,
      },
      {
        label: '高级',
        value: 'advanced',
        icon: <EngineeringIcon fontSize="small" />,
        path: 'advanced',
        component: <AdapterAdvancedPage />,
      },
    ],
  },

  // Telegram 适配器配置
  telegram: {
    key: 'telegram',
    visual: {
      displayName: 'Telegram',
      iconText: 'TG',
      navIcon: <SendIcon />,
      description: 'Telegram 适配器，支持 Telegram 机器人通信',
      tags: ['Telegram', '聊天', 'IM'],
    },
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '适配器配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
      },
      {
        label: '覆盖配置',
        value: 'overrides',
        icon: <StyleIcon fontSize="small" />,
        path: 'overrides',
        component: <AdapterOverrideConfigPage />,
      },
      {
        label: '高级',
        value: 'advanced',
        icon: <EngineeringIcon fontSize="small" />,
        path: 'advanced',
        component: <AdapterAdvancedPage />,
      },
    ],
  },

  // // 企业微信智能机器人适配器配置
  // 目前企业微信智能机器人只能被动回复消息，暂不实现该适配器
  // 文档: https://developer.work.weixin.qq.com/document/path/101031
  // wxwork: {
  //   key: 'wxwork',
  //   visual: {
  //     displayName: 'WeWork Bot',
  //     iconText: '企微',
  //     navIcon: <ChatIcon />,
  //     description: '企业微信智能机器人适配器，支持在企业内部与成员进行智能交互',
  //     tags: ['企业微信', 'WeWork', '智能机器人', 'IM'],
  //   },
  //   tabs: [
  //     {
  //       label: '主页',
  //       value: 'home',
  //       icon: <HomeIcon fontSize="small" />,
  //       path: '',
  //       component: <AdapterHomePage />,
  //     },
  //     {
  //       label: '适配器配置',
  //       value: 'config',
  //       icon: <SettingsIcon fontSize="small" />,
  //       path: 'config',
  //       component: <AdapterConfigPage />,
  //     },
  //     {
  //       label: '覆盖配置',
  //       value: 'overrides',
  //       icon: <StyleIcon fontSize="small" />,
  //       path: 'overrides',
  //       component: <AdapterOverrideConfigPage />,
  //     },
  //     {
  //       label: '高级',
  //       value: 'advanced',
  //       icon: <EngineeringIcon fontSize="small" />,
  //       path: 'advanced',
  //       component: <AdapterAdvancedPage />,
  //     },
  //   ],
  // },

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  // 默认适配器配置（用于其他适配器）
  default: {
    key: 'default',
    visual: {
      displayName: '通用适配器',
      iconText: 'AD',
      navIcon: <SettingsIcon />,
      description: '通用适配器配置',
      tags: ['通用'],
    },
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '适配器配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
      },
      {
        label: '覆盖配置',
        value: 'overrides',
        icon: <StyleIcon fontSize="small" />,
        path: 'overrides',
        component: <AdapterOverrideConfigPage />,
      },
      {
        label: '高级',
        value: 'advanced',
        icon: <EngineeringIcon fontSize="small" />,
        path: 'advanced',
        component: <AdapterAdvancedPage />,
      },
    ],
  },
}

/**
 * 获取适配器的选项卡配置
 * @param adapterKey 适配器key
 * @returns 适配器选项卡配置
 */
export const getAdapterConfig = (adapterKey: string): AdapterConfig => {
  return ADAPTER_CONFIGS[adapterKey] || ADAPTER_CONFIGS.default
}

/**
 * 获取适配器的视觉配置
 * @param adapterKey 适配器key
 * @returns 适配器视觉配置
 */
export const getAdapterVisualConfig = (adapterKey: string): AdapterVisualConfig => {
  const config = getAdapterConfig(adapterKey)
  return config.visual
}

/**
 * 获取适配器图标文本
 * @param adapterKey 适配器key
 * @returns 图标文本
 */
export const getAdapterIconText = (adapterKey: string): string => {
  const visual = getAdapterVisualConfig(adapterKey)
  return visual.iconText
}

/**
 * 获取适配器显示名称
 * @param adapterKey 适配器key
 * @returns 显示名称
 */
export const getAdapterDisplayName = (adapterKey: string): string => {
  const visual = getAdapterVisualConfig(adapterKey)
  return visual.displayName
}

/**
 * 获取适配器选项卡的完整路径
 * @param adapterKey 适配器key
 * @param tabPath 选项卡路径
 * @returns 完整路径
 */
export const getAdapterTabPath = (adapterKey: string, tabPath: string): string => {
  const basePath = `/adapters/${adapterKey}`
  return tabPath ? `${basePath}/${tabPath}` : basePath
}

/**
 * 获取所有适配器的导航配置
 * @returns 导航配置数组
 */
export const getAdapterNavigationConfigs = () => {
  return Object.values(ADAPTER_CONFIGS)
    .filter(config => config.key !== 'default')
    .map(config => ({
      path: `/adapters/${config.key}`,
      text: config.visual.displayName,
      icon: config.visual.navIcon,
      parent: 'adapters',
    }))
}

/**
 * 获取适配器状态显示配置
 * @param status 状态字符串
 * @returns 状态显示配置
 */
export const getAdapterStatusDisplay = (status: string): AdapterStatusDisplay => {
  switch (status) {
    case 'loaded':
      return {
        icon: <CheckCircleIcon color="success" fontSize="small" />,
        text: '已加载',
        color: 'success',
        getBgColor: (theme: Theme) => theme.palette.success.main,
      }
    case 'failed':
      return {
        icon: <ErrorIcon color="error" fontSize="small" />,
        text: '加载失败',
        color: 'error',
        getBgColor: (theme: Theme) => theme.palette.error.main,
      }
    case 'disabled':
      return {
        icon: <WarningIcon color="warning" fontSize="small" />,
        text: '已禁用',
        color: 'warning',
        getBgColor: (theme: Theme) => theme.palette.warning.main,
      }
    default:
      return {
        icon: <RadioButtonUncheckedIcon color="disabled" fontSize="small" />,
        text: '未知',
        color: 'default',
        getBgColor: (theme: Theme) => theme.palette.grey[500],
      }
  }
}

/**
 * 创建适配器图标组件
 * @param adapterKey 适配器key
 * @param theme MUI主题对象
 * @param size 图标大小，默认48
 * @returns Avatar组件
 */
export const createAdapterIcon = (
  adapterKey: string,
  theme: Theme,
  size: number = 48
): ReactElement => {
  const iconText = getAdapterIconText(adapterKey)

  const iconSx: SxProps<Theme> = {
    width: size,
    height: size,
    fontSize: size < 40 ? '0.875rem' : '1.5rem',
    background: UI_STYLES.getGradient('card'),
    backdropFilter: 'blur(8px)',
    border: UI_STYLES.BORDERS.CARD.DEFAULT,
    color: theme.palette.text.primary,
  }

  return <Avatar sx={iconSx}>{iconText}</Avatar>
}
