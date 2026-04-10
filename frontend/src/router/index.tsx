import { lazy, ComponentType, Suspense } from 'react'
import { createHashRouter, Navigate } from 'react-router-dom'
import { CircularProgress, Box } from '@mui/material'
import MainLayout from '../layouts/MainLayout'
import AdapterLayout from '../layouts/AdapterLayout'
import LoginPage from '../pages/login'

// 创建一个包装器组件来处理懒加载和加载状态
const lazyLoad = (importFn: () => Promise<{ default: ComponentType }>) => {
  const LazyComponent = lazy(importFn)
  return (
    <Suspense 
      fallback={
        <Box 
          sx={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            height: '100%',
            minHeight: 200 
          }}
        >
          <CircularProgress />
        </Box>
      }
    >
      <LazyComponent />
    </Suspense>
  )
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
        children: [
          {
            index: true,
            element: <Navigate to="management" replace />,
          },
          {
            path: 'management',
            element: lazyLoad(() => import('../pages/chat-channel')),
          },
          {
            path: 'management/:chatKey',
            element: lazyLoad(() => import('../pages/chat-channel')),
          },
          {
            path: 'announcement',
            element: lazyLoad(() => import('../pages/chat-channel/announcement')),
          },
        ],
      },
      {
        path: 'chat-channel/:chatKey',
        element: lazyLoad(() => import('../pages/chat-channel')),
      },
      {
        path: 'chat-channel/:chatKey/:tab',
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
            index: true,
            element: <Navigate to="management" />,
          },
          {
            path: 'management',
            element: lazyLoad(() => import('../pages/plugins/management')),
          },
          {
            path: 'management/:pluginId',
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
        path: 'adapters',
        children: [
          {
            index: true,
            element: lazyLoad(() => import('../pages/adapter')),
          },
          {
            path: ':adapterKey',
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
        ],
      },
      {
        path: 'settings',
        element: lazyLoad(() => import('../pages/settings')),
        children: [
          {
            index: true,
            element: <Navigate to="system" />,
          },
          {
            path: 'models',
            element: lazyLoad(() => import('../pages/settings/models')),
          },
          {
            path: 'system',
            element: lazyLoad(() => import('../pages/settings/system')),
          },
          {
            path: 'model-groups',
            element: <Navigate to="/settings/models?tab=basic" replace />,
          },
          {
            path: 'theme',
            element: lazyLoad(() => import('../pages/settings/theme')),
          },
          {
            path: 'space-cleanup',
            element: lazyLoad(() => import('../pages/settings/space-cleanup')),
          },
          {
            path: 'commands',
            element: lazyLoad(() => import('../pages/settings/commands')),
          },
        ],
      },
      {
        path: 'commands',
        children: [
          {
            index: true,
            element: <Navigate to="/settings/commands" replace />,
          },
          {
            path: 'management',
            element: <Navigate to="/settings/commands" replace />,
          },
          {
            path: 'output',
            element: <Navigate to="/settings/commands?focus=execute" replace />,
          },
        ],
      },
      {
        path: 'profile',
        element: lazyLoad(() => import('../pages/cloud/profile')),
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
      {
        path: 'cloud/profile',
        element: <Navigate to="/profile" replace />,
      },
      {
        path: 'workspace',
        children: [
          {
            index: true,
            element: lazyLoad(() => import('../pages/workspace')),
          },
          {
            path: 'resources',
            element: lazyLoad(() => import('../pages/workspace/resources')),
          },
          {
            path: 'skills',
            element: lazyLoad(() => import('../pages/workspace/skills')),
          },
          {
            path: 'cc-models',
            element: <Navigate to="/settings/models?tab=cc" replace />,
          },
          {
            path: 'mcp-services',
            element: lazyLoad(() => import('../pages/workspace/mcp-services')),
          },
          {
            path: 'kb-library',
            element: lazyLoad(() => import('../pages/workspace/kb-library')),
          },
          {
            path: 'timers',
            element: lazyLoad(() => import('../pages/workspace/timers')),
          },
          {
            path: ':id',
            children: [
              {
                index: true,
                element: <Navigate to="overview" replace />,
              },
              {
                path: ':tab',
                element: lazyLoad(() => import('../pages/workspace/detail')),
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" />,
  },
])

export default router
