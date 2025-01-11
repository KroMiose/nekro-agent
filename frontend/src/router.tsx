import { createBrowserRouter, Navigate } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import LoginPage from './pages/login'
import LogsPage from './pages/logs'
import SettingsPage from './pages/settings'
import ModelGroupsPage from './pages/model-groups'
import ExtensionsPage from './pages/extensions'
import NapCatPage from './pages/protocols/napcat'

const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/logs" />,
      },
      {
        path: 'logs',
        element: <LogsPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: 'settings/model-groups',
        element: <ModelGroupsPage />,
      },
      {
        path: 'extensions',
        element: <ExtensionsPage />,
      },
      {
        path: 'protocols/napcat',
        element: <NapCatPage />,
      },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
])

export default router
