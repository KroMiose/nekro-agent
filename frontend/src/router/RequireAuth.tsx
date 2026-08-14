import { type ReactElement, useEffect, useState } from 'react'
import { Box, CircularProgress } from '@mui/material'
import { Navigate, useLocation } from 'react-router-dom'
import { authApi, type UserInfo } from '../services/api/auth'
import { useAuthStore } from '../stores/auth'
import { loginPath } from './routes'

interface SessionValidationRequest {
  token: string
  promise: Promise<UserInfo>
}

let sessionValidationRequest: SessionValidationRequest | null = null

function validateSession(token: string): Promise<UserInfo> {
  if (sessionValidationRequest?.token === token) {
    return sessionValidationRequest.promise
  }

  const promise = authApi.getUserInfo()
  sessionValidationRequest = { token, promise }

  const clearRequest = () => {
    if (sessionValidationRequest?.promise === promise) {
      sessionValidationRequest = null
    }
  }
  void promise.then(clearRequest, clearRequest)

  return promise
}

export default function RequireAuth({ children }: { children: ReactElement }) {
  const location = useLocation()
  const token = useAuthStore(state => state.token)
  const setUserInfo = useAuthStore(state => state.setUserInfo)
  const [validatedToken, setValidatedToken] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return

    let cancelled = false
    validateSession(token)
      .then(userInfo => {
        if (cancelled || useAuthStore.getState().token !== token) return
        setUserInfo(userInfo)
        setValidatedToken(token)
      })
      .catch(() => {
        if (cancelled || useAuthStore.getState().token !== token) return
        // Non-authentication failures should not permanently block the application.
        // A 401 clears the token in the Axios interceptor before reaching this branch.
        setValidatedToken(token)
      })

    return () => {
      cancelled = true
    }
  }, [setUserInfo, token])

  if (!token) {
    return <Navigate to={loginPath(`${location.pathname}${location.search}`)} replace />
  }

  if (validatedToken !== token) {
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
