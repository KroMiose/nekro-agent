import axios from './axios'
import { createEventStream } from './utils/stream'

// 后端返回数据结构
interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

// 仪表盘概览数据接口
export interface DashboardOverview {
  total_messages: number
  active_sessions: number
  unique_users: number
  total_sandbox_calls: number
  success_calls: number
  failed_calls: number
  success_rate: number
}

// 趋势数据点接口
export interface TrendDataPoint extends Record<string, number | string> {
  timestamp: string
}

// 分布数据接口
export interface DistributionItem {
  label: string
  value: number
  percentage: number
}

// 排名数据接口
export interface RankingItem {
  id: string
  name: string
  value: number
  avatar?: string
}

// 实时数据接口
export interface RealTimeDataPoint {
  timestamp: string
  recent_messages: number
  recent_sandbox_calls: number
  recent_success_calls: number
  recent_avg_exec_time: number
}

// 分布数据响应接口
export interface DistributionsResponse {
  stop_type: DistributionItem[]
  message_type: DistributionItem[]
}

// 仪表盘API服务
export const dashboardApi = {
  // 获取概览数据
  getOverview: async (params: { time_range: string }): Promise<DashboardOverview> => {
    const response = await axios.get<ApiResponse<DashboardOverview>>('/dashboard/overview', { params })
    return response.data.data
  },

  // 获取趋势数据
  getTrends: async (params: {
    metrics: string
    time_range: string
    interval: string
  }): Promise<TrendDataPoint[]> => {
    const response = await axios.get<ApiResponse<TrendDataPoint[]>>('/dashboard/trends', { params })
    return response.data.data
  },

  // 获取排名数据
  getActiveRanking: async (params: {
    ranking_type: string
    time_range: string
    limit?: number
  }): Promise<RankingItem[]> => {
    const response = await axios.get<ApiResponse<RankingItem[]>>('/dashboard/ranking', { params })
    return response.data.data
  },

  // 获取所有分布数据
  getDistributions: async (params: {
    time_range: string
  }): Promise<DistributionsResponse> => {
    const response = await axios.get<ApiResponse<DistributionsResponse>>('/dashboard/distributions', { params })
    return response.data.data
  },

  // 创建实时统计数据流
  createStatsStream: (onMessage: (data: string) => void, granularity: number = 10) => {
    return createEventStream({
      endpoint: `/dashboard/stats/stream?granularity=${granularity}`,
      onMessage,
      onError: (error) => console.error('仪表盘数据流错误:', error)
    })
  }
} 