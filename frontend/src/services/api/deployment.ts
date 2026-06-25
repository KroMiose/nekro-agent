import axios from './axios'
import { createEventStream } from './utils/stream'

export type DeploymentJobStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancel_requested'
  | 'cancelled'

export type DeploymentJobType = 'update' | 'backup' | 'restore'

export type DeploymentPhase =
  | 'validate_instance'
  | 'backup'
  | 'switch_channel'
  | 'pull_images'
  | 'restart_services'
  | 'pull_sandbox'
  | 'verify'
  | 'finished'

export interface DeploymentUnavailableReason {
  code: string
  message: string
}

export interface DeploymentSupports {
  update?: boolean
  preview?: boolean
  rollback?: boolean
  backup?: boolean
  restore?: boolean
  restore_pre_preview?: boolean
  cancel?: boolean
  log_stream?: boolean
  daemon_update?: boolean
  [key: string]: boolean | undefined
}

export interface DeploymentCapabilities {
  enabled: boolean
  provider: string | null
  platform: string
  protocol_version: string | null
  instance_id: string | null
  supports: DeploymentSupports
  limits: Record<string, unknown>
  unavailable_reason: DeploymentUnavailableReason | null
}

export interface DeploymentInstance {
  channel: string | null
  image: string | null
  container_status: string | null
  app_health: string | null
  docker_ok: boolean
  compose_ok: boolean
}

export interface DeploymentAgentVersion {
  current_version: string
  latest_version: string | null
  update_available: boolean
  checked: boolean
  error_code: string | null
  error_message: string | null
}

export interface DeploymentUpdateRequest {
  channel: 'stable' | 'preview' | 'rollback'
  backup: boolean
  update_sandbox: boolean
  update_cc_sandbox: boolean
  restore_pre_preview: boolean
  client_request_id: string
}

export interface DeploymentCreateBackupRequest {
  name?: string
  client_request_id: string
}

export interface DeploymentRestoreRequest {
  backup_id: string
  client_request_id: string
}

export interface DeploymentUpdateResponse {
  job_id: string
  type?: DeploymentJobType
  status: DeploymentJobStatus
  phase?: DeploymentPhase
  message?: string
}

export interface DeploymentBackupSummary {
  backup_id: string
  filename: string
  name: string | null
  created_at: string
  size_bytes: number
}

export interface DeploymentBackupsResponse {
  backups: DeploymentBackupSummary[]
}

export interface DeploymentJobProgress {
  current: number | null
  total: number | null
  label: string
}

export interface DeploymentJobError {
  code: string
  message: string
  details?: Record<string, unknown>
}

export interface DeploymentJobResult {
  channel?: string
  image?: string
  app_health?: string
  [key: string]: unknown
}

export interface DeploymentJob {
  job_id: string
  type?: DeploymentJobType
  status: DeploymentJobStatus
  phase: DeploymentPhase
  progress: DeploymentJobProgress | null
  created_at?: string | null
  started_at?: string | null
  finished_at?: string | null
  exit_code?: number | null
  error: DeploymentJobError | null
  result: DeploymentJobResult | null
}

export interface DeploymentLogEntry {
  seq: number
  ts?: string
  level: string
  stream: string
  line: string
}

export interface DeploymentJobLogsResponse {
  job_id: string
  logs: DeploymentLogEntry[]
  next_after_seq: number | null
}

export type DeploymentSseEventName = 'job' | 'progress' | 'log' | 'result' | 'error'

export type DeploymentSseEvent =
  | { event: 'job'; data: { seq?: number; status: DeploymentJobStatus; phase: DeploymentPhase } }
  | { event: 'progress'; data: { seq?: number } & DeploymentJobProgress }
  | { event: 'log'; data: DeploymentLogEntry }
  | {
      event: 'result'
      data: {
        seq?: number
        status: 'succeeded' | 'failed' | 'cancelled'
        result?: DeploymentJobResult
        error?: DeploymentJobError
      }
    }
  | { event: 'error'; data: DeploymentJobError }

const parseSseEvent = (eventName: string, rawData: string): DeploymentSseEvent | null => {
  if (!['job', 'progress', 'log', 'result', 'error'].includes(eventName)) {
    return null
  }

  try {
    const data: unknown = JSON.parse(rawData)
    if (typeof data !== 'object' || data === null) {
      return null
    }
    return { event: eventName, data } as DeploymentSseEvent
  } catch {
    return null
  }
}

export const deploymentApi = {
  getCapabilities: async () => {
    const response = await axios.get<DeploymentCapabilities>('/deployment/capabilities')
    return response.data
  },

  getInstance: async () => {
    const response = await axios.get<DeploymentInstance>('/deployment/instance')
    return response.data
  },

  getAgentVersion: async () => {
    const response = await axios.get<DeploymentAgentVersion>('/deployment/agent-version')
    return response.data
  },

  createUpdate: async (request: DeploymentUpdateRequest) => {
    const response = await axios.post<DeploymentUpdateResponse>('/deployment/update', request)
    return response.data
  },

  listBackups: async (limit = 50) => {
    const response = await axios.get<DeploymentBackupsResponse>('/deployment/backups', {
      params: { limit },
    })
    return response.data
  },

  createBackup: async (request: DeploymentCreateBackupRequest) => {
    const response = await axios.post<DeploymentUpdateResponse>('/deployment/backup', request)
    return response.data
  },

  createRestore: async (request: DeploymentRestoreRequest) => {
    const response = await axios.post<DeploymentUpdateResponse>('/deployment/restore', request)
    return response.data
  },

  getJob: async (jobId: string) => {
    const response = await axios.get<DeploymentJob>(`/deployment/jobs/${encodeURIComponent(jobId)}`)
    return response.data
  },

  getJobLogs: async (jobId: string, afterSeq?: number, limit = 1000) => {
    const response = await axios.get<DeploymentJobLogsResponse>(
      `/deployment/jobs/${encodeURIComponent(jobId)}/logs`,
      { params: { after_seq: afterSeq, limit } }
    )
    return response.data
  },

  subscribeJobEvents: (
    jobId: string,
    options: {
      afterSeq?: number
      onEvent: (event: DeploymentSseEvent) => void
      onError: (error: Error) => void
    }
  ) => {
    const query = options.afterSeq === undefined ? '' : `?after_seq=${options.afterSeq}`
    return createEventStream({
      endpoint: `/deployment/jobs/${encodeURIComponent(jobId)}/events${query}`,
      autoReconnect: false,
      onEvent: (eventName, data) => {
        const event = parseSseEvent(eventName, data)
        if (event) options.onEvent(event)
      },
      onError: options.onError,
    })
  },

  cancelJob: async (jobId: string) => {
    const response = await axios.post<DeploymentUpdateResponse>(
      `/deployment/jobs/${encodeURIComponent(jobId)}/cancel`
    )
    return response.data
  },
}
