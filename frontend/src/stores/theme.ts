import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ColorModeState {
  mode: 'light' | 'dark'
  toggleColorMode: () => void
}

export const useColorMode = create<ColorModeState>()(
  persist(
    set => ({
      mode: 'light',
      toggleColorMode: () => set(state => ({ mode: state.mode === 'light' ? 'dark' : 'light' })),
    }),
    {
      name: 'color-mode',
    }
  )
)
