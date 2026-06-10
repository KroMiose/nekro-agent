import { type ReactElement } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/auth'
import { loginPath } from './routes'

export default function RequireAuth({ children }: { children: ReactElement }) {
  const location = useLocation()
  const token = useAuthStore(state => state.token)

  if (!token) {
    return <Navigate to={loginPath(`${location.pathname}${location.search}`)} replace />
  }

  return children
}
