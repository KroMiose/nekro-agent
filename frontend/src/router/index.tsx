import { createHashRouter, Navigate } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import LoginPage from '../pages/login'
import LogsPage from '../pages/logs'
import SettingsPage from '../pages/settings'
import SettingsLayout from '../pages/settings/Layout'
import ModelGroupsPage from '../pages/model-groups'
import ExtensionsPage from '../pages/extensions'
import NapCatPage from '../pages/protocols/napcat'
import SandboxPage from '../pages/sandbox'

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
        element: <LogsPage />,
      },
      {
        path: 'logs',
        element: <LogsPage />,
      },
      {
        path: 'extensions',
        element: <ExtensionsPage />,
      },
      {
        path: 'sandbox-logs',
        element: <SandboxPage />,
      },
      {
        path: 'protocols/napcat',
        element: <NapCatPage />,
      },
      {
        path: 'settings',
        element: <SettingsLayout />,
        children: [
          {
            path: '',
            element: <SettingsPage />,
          },
          {
            path: 'model-groups',
            element: <ModelGroupsPage />,
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
