import { createContext, useContext } from 'react'
import { EMPTY_SYSTEM_EVENTS, type SystemEvents } from '../hooks/useSystemEvents'

export const SystemEventsContext = createContext<SystemEvents>(EMPTY_SYSTEM_EVENTS)

export function useSystemEventsContext(): SystemEvents {
  return useContext(SystemEventsContext)
}
