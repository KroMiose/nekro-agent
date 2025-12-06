<<<<<<< HEAD
import { lazy, ComponentType, Suspense } from 'react'
import { createHashRouter, Navigate } from 'react-router-dom'
import { CircularProgress, Box } from '@mui/material'
=======
<<<<<<< HEAD
import { lazy, ComponentType, Suspense } from 'react'
import { createHashRouter, Navigate } from 'react-router-dom'
import { CircularProgress, Box } from '@mui/material'
=======
<<<<<<< HEAD
import { lazy, ComponentType, Suspense } from 'react'
import { createHashRouter, Navigate } from 'react-router-dom'
import { CircularProgress, Box } from '@mui/material'
=======
import { lazy, ComponentType, ReactElement } from 'react'
import { createHashRouter, Navigate } from 'react-router-dom'
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
import MainLayout from '../layouts/MainLayout'
import AdapterLayout from '../layouts/AdapterLayout'
import LoginPage from '../pages/login'

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
// 创建一个包装器组件来处理懒加载，这样就不会有lint错误了
const lazyLoad = (importFn: () => Promise<{ default: ComponentType }>): ReactElement => {
  const LazyComponent = lazy(importFn)
  return <LazyComponent />
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
            index: true,
            element: <Navigate to="management" />,
          },
          {
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
        element: lazyLoad(() => import('../pages/settings')),
        children: [
          {
            index: true,
            element: <Navigate to="system" />,
          },
          {
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
        children: [
          {
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
          {
            path: 'pypi',
            element: lazyLoad(() => import('../pages/settings/pypi')),
          },
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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

<<<<<<< HEAD
export default router
=======
<<<<<<< HEAD
export default router
=======
<<<<<<< HEAD
export default router
=======
export default router
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
