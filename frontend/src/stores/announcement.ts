import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { cloudApi } from '../services/api/cloud'
import type { AnnouncementDetail, AnnouncementSummary } from '../services/api/cloud/announcement'

interface AnnouncementState {
  items: AnnouncementSummary[]
  loading: boolean
  lastFetchTime: number | null
  // 已读公告 ID 集合
  readIds: string[]
  // 当前查看的公告详情
  currentDetail: AnnouncementDetail | null
  detailLoading: boolean
  // 公告最后更新时间（由遥测接口返回，内存不持久化）
  lastKnownUpdatedAt: string | null

  fetchLatest: (force?: boolean) => Promise<void>
  fetchDetail: (id: string) => Promise<void>
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  clearDetail: () => void
  unreadCount: () => number
  checkForUpdates: () => Promise<void>
}

const CACHE_DURATION = 600_000 // 10分钟

export const useAnnouncementStore = create<AnnouncementState>()(
  persist(
    (set, get) => ({
      items: [],
      loading: false,
      lastFetchTime: null,
      readIds: [],
      currentDetail: null,
      detailLoading: false,
      lastKnownUpdatedAt: null,

      fetchLatest: async (force = false) => {
        const state = get()
        if (state.loading) return

        if (
          !force &&
          state.lastFetchTime &&
          Date.now() - state.lastFetchTime < CACHE_DURATION
        ) {
          return
        }

        set({ loading: true })
        try {
          const items = await cloudApi.announcement.getLatestAnnouncements(5, force)
          set({ items, lastFetchTime: Date.now(), loading: false })
        } catch {
          set({ loading: false })
        }
      },

      fetchDetail: async (id: string) => {
        set({ detailLoading: true, currentDetail: null })
        try {
          const detail = await cloudApi.announcement.getAnnouncementDetail(id)
          set({ currentDetail: detail, detailLoading: false })
          // 查看详情即标记已读
          get().markAsRead(id)
        } catch {
          set({ detailLoading: false })
        }
      },

      markAsRead: (id: string) => {
        const { readIds } = get()
        if (!readIds.includes(id)) {
          set({ readIds: [...readIds, id] })
        }
      },

      markAllAsRead: () => {
        const { items } = get()
        set({ readIds: items.map(item => item.id) })
      },

      clearDetail: () => {
        set({ currentDetail: null })
      },

      unreadCount: () => {
        const { items, readIds } = get()
        return items.filter(item => !readIds.includes(item.id)).length
      },

      checkForUpdates: async () => {
        try {
          const updatedAt = await cloudApi.announcement.getAnnouncementUpdatedAt()
          const { lastKnownUpdatedAt } = get()
          if (updatedAt && updatedAt !== lastKnownUpdatedAt) {
            set({ lastKnownUpdatedAt: updatedAt })
            await get().fetchLatest(true)
          }
        } catch {
          // 静默失败
        }
      },
    }),
    {
      name: 'announcement-storage',
      partialize: state => ({
        readIds: state.readIds,
      }),
    }
  )
)
