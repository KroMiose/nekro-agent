import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserInfo } from '../services/api/auth'

interface AuthState {
  token: string | null
  userInfo: UserInfo | null
  validatedToken: string | null
  isValidating: boolean
  setToken: (token: string | null) => void
  setUserInfo: (userInfo: UserInfo | null) => void
  validateSession: (fetchUserInfo: () => Promise<UserInfo>) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => {
      let sessionValidationRequest: { token: string; promise: Promise<UserInfo> } | null = null

      return {
        token: null,
        userInfo: null,
        validatedToken: null,
        isValidating: false,
        setToken: token => {
          set(state => ({
            token,
            validatedToken: state.token === token ? state.validatedToken : null,
          }))
        },
        setUserInfo: userInfo => {
          set({ userInfo })
        },
        validateSession: async fetchUserInfo => {
          const token = get().token
          if (!token) {
            set({ isValidating: false, validatedToken: null })
            return
          }
          if (get().validatedToken === token) return

          if (sessionValidationRequest?.token === token) {
            try {
              await sessionValidationRequest.promise
            } catch {
              // The original request owns auth failure handling and state updates.
            }
            return
          }

          set({ isValidating: true })
          const promise = fetchUserInfo()
          sessionValidationRequest = { token, promise }

          try {
            const userInfo = await promise
            if (get().token !== token) return
            set({ userInfo, validatedToken: token })
          } catch {
            if (get().token !== token) return
            // Non-authentication failures should not permanently block the application.
            // A 401 clears the token in the Axios interceptor before reaching this branch.
            set({ validatedToken: token })
          } finally {
            if (sessionValidationRequest?.promise === promise) {
              sessionValidationRequest = null
            }
            if (get().token === token) {
              set({ isValidating: false })
            }
          }
        },
        logout: () => {
          set({ token: null, userInfo: null, validatedToken: null, isValidating: false })
        },
      }
    },
    {
      name: 'auth-storage',
      partialize: state => ({
        token: state.token,
        userInfo: state.userInfo,
      }),
    }
  )
)
