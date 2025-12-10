import axios from './axios'

// 资源类型枚举
export enum ResourceType {
  USER_UPLOADS = 'user_uploads',
  SANDBOX_SHARED = 'sandbox_shared',
  SANDBOX_PIP_CACHE = 'sandbox_pip_cache',
  SANDBOX_PACKAGES = 'sandbox_packages',
  PLUGIN_DYNAMIC_PACKAGES = 'plugin_dynamic_packages',
  PROMPT_LOGS = 'prompt_logs',
  PROMPT_ERROR_LOGS = 'prompt_error_logs',
  NAPCAT_TEMP = 'napcat_temp',
  PLUGIN_DATA = 'plugin_data',
  APP_LOGS = 'app_logs',
  OTHER_DATA = 'other_data',
}

// 扫描状态枚举
export enum ScanStatus {
  IDLE = 'idle',
  SCANNING = 'scanning',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

// 清理状态枚举
export enum CleanupStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

// 文件信息
export interface FileInfo {
  relative_path: string
  name: string
  size: number
  created_time: number
  modified_time: number
  chat_key?: string
  plugin_key?: string
}

// 聊天资源信息
export interface ChatResourceInfo {
  chat_key: string
  chat_name?: string
  total_size: number
  file_count: number
  files: FileInfo[]
}

// 插件资源信息
export interface PluginResourceInfo {
  plugin_key: string
  plugin_name?: string
  total_size: number
  file_count: number
}

// 资源分类
export interface ResourceCategory {
  resource_type: ResourceType
  display_name: string
  description: string
  total_size: number
  file_count: number
  can_cleanup: boolean
  risk_level: string
  risk_message?: string
  supports_time_filter: boolean
  chat_resources: ChatResourceInfo[]
  plugin_resources: PluginResourceInfo[]
}

// 磁盘信息
export interface DiskInfo {
  total_space: number
  used_space: number
  free_space: number
  data_dir_size: number
  data_dir_path: string
}

// 扫描摘要
export interface ScanSummary {
  total_size: number
  total_files: number
  start_time?: string
  end_time?: string
  duration_seconds?: number
  scanned_categories: number
}

// 扫描结果
export interface ScanResult {
  scan_id: string
  status: ScanStatus
  disk_info?: DiskInfo
  categories: ResourceCategory[]
  summary: ScanSummary
  error_message?: string
}

// 扫描状态响应
export interface ScanStatusResponse {
  status: ScanStatus
  progress: number
  current_category?: string
  message?: string
}

// 清理请求
export interface CleanupRequest {
  resource_types: ResourceType[]
  chat_keys?: string[]
  before_date?: string
  dry_run?: boolean
}

// 清理进度
export interface CleanupProgress {
  task_id: string
  status: CleanupStatus
  progress: number
  processed_files: number
  total_files: number
  freed_space: number
  current_file?: string
  message?: string
}

// 清理结果
export interface CleanupResult {
  task_id: string
  status: CleanupStatus
  total_files: number
  deleted_files: number
  failed_files: number
  freed_space: number
  start_time?: string
  end_time?: string
  duration_seconds?: number
  error_message?: string
  failed_file_list: string[]
}

export const spaceCleanupApi = {
  // 启动扫描
  startScan: async (): Promise<{ scan_id: string }> => {
    const response = await axios.post<{ data: { scan_id: string } }>('/space-cleanup/scan/start')
    return response.data.data
  },

  // 获取扫描状态
  getScanStatus: async (): Promise<ScanStatusResponse> => {
    const response = await axios.get<{ data: ScanStatusResponse }>('/space-cleanup/scan/status')
    return response.data.data
  },

  // 获取扫描结果
  getScanResult: async (): Promise<ScanResult> => {
    const response = await axios.get<{ data: ScanResult }>('/space-cleanup/scan/result')
    return response.data.data
  },

  // 启动清理
  startCleanup: async (request: CleanupRequest): Promise<{ task_id: string }> => {
    const response = await axios.post<{ data: { task_id: string } }>(
      '/space-cleanup/cleanup/start',
      request
    )
    return response.data.data
  },

  // 获取清理进度
  getCleanupProgress: async (taskId: string): Promise<CleanupProgress> => {
    const response = await axios.get<{ data: CleanupProgress }>(
      `/space-cleanup/cleanup/progress/${taskId}`
    )
    return response.data.data
  },

  // 获取清理结果
  getCleanupResult: async (taskId: string): Promise<CleanupResult> => {
    const response = await axios.get<{ data: CleanupResult }>(
      `/space-cleanup/cleanup/result/${taskId}`
    )
    return response.data.data
  },

  // 获取磁盘信息
  getDiskInfo: async (): Promise<DiskInfo> => {
    const response = await axios.get<{ data: DiskInfo }>('/space-cleanup/disk-info')
    return response.data.data
  },

  // 从缓存加载扫描结果
  loadScanResultFromCache: async (): Promise<ScanResult> => {
    const response = await axios.get<{ data: ScanResult }>('/space-cleanup/scan/load-cache')
    return response.data.data
  },

  // 获取扫描进度
  getScanProgress: async (): Promise<{ status: string; progress: number; message?: string }> => {
    const response = await axios.get<{
      data: { status: string; progress: number; message?: string }
    }>('/space-cleanup/scan/progress')
    return response.data.data
  },
}

// 格式化字节大小
export function formatBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 B'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

// 格式化时长
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)} 秒`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${minutes} 分 ${secs} 秒`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours} 小时 ${minutes} 分`
  }
}
