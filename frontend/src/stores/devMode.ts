import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

interface DevModeState {
  devMode: boolean
  setDevMode: (value: boolean) => void
  toggleDevMode: () => void
}

export const useDevModeStore = create<DevModeState>()(
  persist(
    (set, get) => ({
      devMode: false,
      setDevMode: (value: boolean) => set({ devMode: value }),
      toggleDevMode: () => set({ devMode: !get().devMode }),
    }),
    {
      name: 'nekro-agent-dev-mode',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
