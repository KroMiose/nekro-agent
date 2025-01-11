import { create } from 'zustand'

interface AppState {
  isConnected: boolean
  setConnected: (connected: boolean) => void
}

export const useAppStore = create<AppState>(set => ({
  isConnected: true,
  setConnected: connected => set({ isConnected: connected }),
}))
