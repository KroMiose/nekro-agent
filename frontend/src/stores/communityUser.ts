import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { cloudApi } from '../services/api/cloud'
import type { CommunityUserProfile } from '../services/api/cloud/auth'

interface CommunityUserState {
  userInfo: CommunityUserProfile | null
  loading: boolean
  lastFetchTime: number | null
  fetchUserProfile: (force?: boolean) => Promise<void>
}

const CACHE_DURATION = 3600_000 // 1小时客户端缓存

export const useCommunityUserStore = create<CommunityUserState>()(
  persist(
    (set, get) => ({
      userInfo: null,
      loading: false,
      lastFetchTime: null,

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
          return
        }

        set({ loading: true })
        try {
          const userInfo = await cloudApi.auth.getCommunityUserProfile(force)
          set({ userInfo, lastFetchTime: Date.now(), loading: false })
        } catch {
          set({ loading: false })
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
