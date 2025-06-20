import { lazy, ComponentType, ReactElement } from 'react'
import { createHashRouter, Navigate } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import AdapterLayout from '../layouts/AdapterLayout'
import LoginPage from '../pages/login'

// 创建一个包装器组件来处理懒加载，这样就不会有lint错误了
const lazyLoad = (importFn: () => Promise<{ default: ComponentType }>): ReactElement => {
  const LazyComponent = lazy(importFn)
  return <LazyComponent />
}

const router = createHashRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <MainLayout />,
    errorElement: <Navigate to="/login" />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" />,
      },
      {
        path: 'dashboard',
        element: lazyLoad(() => import('../pages/dashboard')),
      },
      {
        path: 'chat-channel',
        element: lazyLoad(() => import('../pages/chat-channel')),
      },
      {
        path: 'user-manager',
        element: lazyLoad(() => import('../pages/user-manager')),
      },
      {
        path: 'presets',
        element: lazyLoad(() => import('../pages/presets')),
      },
      {
        path: 'logs',
        element: lazyLoad(() => import('../pages/logs')),
      },
      {
        path: 'plugins',
        children: [
          {
            path: 'management',
            element: lazyLoad(() => import('../pages/plugins/management')),
          },
          {
            path: 'editor',
            element: lazyLoad(() => import('../pages/plugins/editor')),
          },
        ],
      },
      {
        path: 'sandbox-logs',
        element: lazyLoad(() => import('../pages/sandbox')),
      },
      {
        path: 'adapters/:adapterKey',
        element: <AdapterLayout />,
        children: [
          {
            index: true,
            element: lazyLoad(() => import('../pages/adapter/AdapterTabPage')),
          },
          {
            path: '*',
            element: lazyLoad(() => import('../pages/adapter/AdapterTabPage')),
          },
        ],
      },
      {
        path: 'settings',
        children: [
          {
            path: 'system',
            element: lazyLoad(() => import('../pages/settings/system')),
          },
          {
            path: 'model-groups',
            element: lazyLoad(() => import('../pages/settings/model_group')),
          },
          {
            path: 'theme',
            element: lazyLoad(() => import('../pages/settings/theme')),
          },
        ],
      },
      {
        path: 'profile',
        element: lazyLoad(() => import('../pages/profile')),
      },
      {
        path: 'cloud/telemetry',
        element: lazyLoad(() => import('../pages/cloud/telemetry')),
      },
      {
        path: 'cloud/presets-market',
        element: lazyLoad(() => import('../pages/cloud/presets_market')),
      },
      {
        path: 'cloud/plugins-market',
        element: lazyLoad(() => import('../pages/cloud/plugins_market')),
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" />,
  },
])

export default router
