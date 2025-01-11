import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserInfo } from '../services/api/auth'

interface AuthState {
  token: string | null
  userInfo: UserInfo | null
  setToken: (token: string | null) => void
  setUserInfo: (userInfo: UserInfo | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    set => ({
      token: null,
      userInfo: null,
      setToken: token => {
        console.log('Setting token:', token ? '***' : 'null')
        set({ token })
      },
      setUserInfo: userInfo => {
        console.log('Setting user info:', userInfo)
        set({ userInfo })
      },
      logout: () => {
        console.log('Logging out')
        set({ token: null, userInfo: null })
      },
    }),
    {
      name: 'auth-storage',
    }
  )
)
