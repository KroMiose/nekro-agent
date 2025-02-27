import { createHashRouter, Navigate } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import LoginPage from '../pages/login'
import LogsPage from '../pages/logs'
import SettingsPage from '../pages/settings'
import SettingsLayout from '../pages/settings/Layout'
import ModelGroupsPage from '../pages/model-groups'
import ExtensionsManagementPage from '../pages/extensions/management'
import ExtensionsEditorPage from '../pages/extensions/editor'
import NapCatPage from '../pages/protocols/napcat'
import SandboxPage from '../pages/sandbox'
import ProfilePage from '../pages/profile'
import DashboardPage from '../pages/dashboard'
import ChatChannelPage from '../pages/chat-channel'
import UserManagerPage from '../pages/user-manager'

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
        element: <DashboardPage />,
      },
      {
        path: 'chat-channel',
        element: <ChatChannelPage />,
      },
      {
        path: 'user-manager',
        element: <UserManagerPage />,
      },
      {
        path: 'logs',
        element: <LogsPage />,
      },
      {
        path: 'extensions',
        children: [
          {
            path: 'management',
            element: <ExtensionsManagementPage />,
          },
          {
            path: 'editor',
            element: <ExtensionsEditorPage />,
          },
        ],
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
      {
        path: 'profile',
        element: <ProfilePage />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" />,
  },
])

export default router
