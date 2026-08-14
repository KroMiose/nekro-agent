import { type ReactElement, useEffect } from 'react'
import { Box, CircularProgress } from '@mui/material'
import { Navigate, useLocation } from 'react-router-dom'
import { authApi } from '../services/api/auth'
import { useAuthStore } from '../stores/auth'
import { loginPath } from './routes'

export default function RequireAuth({ children }: { children: ReactElement }) {
  const location = useLocation()
  const token = useAuthStore(state => state.token)
  const validatedToken = useAuthStore(state => state.validatedToken)
  const isValidating = useAuthStore(state => state.isValidating)
  const validateSession = useAuthStore(state => state.validateSession)

  useEffect(() => {
    if (!token) return
    void validateSession(authApi.getUserInfo)
  }, [token, validateSession])

  if (!token) {
    return <Navigate to={loginPath(`${location.pathname}${location.search}`)} replace />
  }

  if (isValidating || validatedToken !== token) {
    return (
      <Box
        sx={{
          alignItems: 'center',
          display: 'flex',
          justifyContent: 'center',
          minHeight: '100dvh',
          width: '100%',
        }}
      >
        <CircularProgress />
      </Box>
    )
  }

  return children
}
