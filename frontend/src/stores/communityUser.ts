import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { cloudApi } from '../services/api/cloud'
import { ApiError } from '../services/api/axios'
import type { CommunityUserProfile } from '../services/api/cloud/auth'

type CommunityAccessStatus = 'unknown' | 'available' | 'missing_api_key' | 'error'

interface CommunityUserState {
  userInfo: CommunityUserProfile | null
  loading: boolean
  lastFetchTime: number | null
  accessStatus: CommunityAccessStatus
  fetchUserProfile: (force?: boolean) => Promise<void>
}

const CACHE_DURATION = 3600_000 // 1小时客户端缓存

const inferCommunityAccessStatus = (error: unknown): CommunityAccessStatus => {
  if (error instanceof ApiError) {
    const normalized = `${error.message} ${error.detail ?? ''}`.toLowerCase()
    if (normalized.includes('api key')) {
      return 'missing_api_key'
    }
  }

  return 'error'
}

export const useCommunityUserStore = create<CommunityUserState>()(
  persist(
    (set, get) => ({
      userInfo: null,
      loading: false,
      lastFetchTime: null,
      accessStatus: 'unknown',

      fetchUserProfile: async (force = false) => {
        const state = get()
        if (state.loading) return

        // 客户端缓存检查
        if (
          !force &&
          state.userInfo &&
          state.lastFetchTime &&
          Date.now() - state.lastFetchTime < CACHE_DURATION
        ) {
          if (state.accessStatus !== 'available') {
            set({ accessStatus: 'available' })
          }
          return
        }

        set({ loading: true })
        try {
          const userInfo = await cloudApi.auth.getCommunityUserProfile(force)
          set({
            userInfo,
            lastFetchTime: Date.now(),
            loading: false,
            accessStatus: 'available',
          })
        } catch (error) {
          set({
            userInfo: null,
            loading: false,
            accessStatus: inferCommunityAccessStatus(error),
          })
        }
      },
    }),
    {
      name: 'community-user-storage',
      partialize: state => ({
        userInfo: state.userInfo,
        lastFetchTime: state.lastFetchTime,
      }),
    }
  )
)
