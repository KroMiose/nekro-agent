import axios from '../axios'

export interface CommunityStats {
  totalInstances: number
  activeInstances: number
  totalUsers: number
  totalSessions: number
  totalMessages: number
  totalSandboxCalls: number
  versionDistribution: {
    version: string
    count: number
  }[]
  newInstancesTrend: {
    date: string
    count: number
  }[]
  lastUpdated: string
}

export const telemetryApi = {
  getCommunityStats: async (): Promise<CommunityStats> => {
    const response = await axios.get<CommunityStats>('/cloud/telemetry/community-stats')
    return response.data
  },
}
