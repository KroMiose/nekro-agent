import {
  Home as HomeIcon,
  Settings as SettingsIcon,
  Engineering as EngineeringIcon,
  SmartToy as NapCatIcon,
  Terminal as LogsIcon,
} from '@mui/icons-material'
import { ReactElement } from 'react'

import AdapterHomePage from '../pages/adapter/AdapterHomePage'
import AdapterConfigPage from '../pages/adapter/AdapterConfigPage'
import AdapterAdvancedPage from '../pages/adapter/AdapterAdvancedPage'
import OneBotV11NapCatPage from '../pages/adapter/onebot_v11/napcat'
import OneBotV11LogsPage from '../pages/adapter/onebot_v11/logs'

export interface AdapterTabConfig {
  label: string
  value: string
  icon: ReactElement
  path: string
  component: ReactElement
}

export interface AdapterConfig {
  key: string
  tabs: AdapterTabConfig[]
}

// 适配器配置映射
export const ADAPTER_CONFIGS: Record<string, AdapterConfig> = {
  // OneBot V11 适配器配置
  onebot_v11: {
    key: 'onebot_v11',
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
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

  // 默认适配器配置（用于其他适配器）
  default: {
    key: 'default',
    tabs: [
      {
        label: '主页',
        value: 'home',
        icon: <HomeIcon fontSize="small" />,
        path: '',
        component: <AdapterHomePage />,
      },
      {
        label: '配置',
        value: 'config',
        icon: <SettingsIcon fontSize="small" />,
        path: 'config',
        component: <AdapterConfigPage />,
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
 * 获取适配器选项卡的完整路径
 * @param adapterKey 适配器key
 * @param tabPath 选项卡路径
 * @returns 完整路径
 */
export const getAdapterTabPath = (adapterKey: string, tabPath: string): string => {
  const basePath = `/adapters/${adapterKey}`
  return tabPath ? `${basePath}/${tabPath}` : basePath
}
