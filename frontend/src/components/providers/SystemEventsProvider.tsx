import type { ReactNode } from 'react'
import { SystemEventsContext } from '../../contexts/SystemEventsContext'
import { useSystemEvents } from '../../hooks/useSystemEvents'

export default function SystemEventsProvider({ children }: { children: ReactNode }) {
  const systemEvents = useSystemEvents()
  return (
    <SystemEventsContext.Provider value={systemEvents}>
      {children}
    </SystemEventsContext.Provider>
  )
}
