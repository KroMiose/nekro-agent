import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../../../services/api/axios'
import {
  deploymentApi,
  type DeploymentJob,
  type DeploymentJobStatus,
  type DeploymentLogEntry,
  type DeploymentSseEvent,
  type DeploymentUpdateResponse,
} from '../../../services/api/deployment'
import { healthApi } from '../../../services/api/health'

const ACTIVE_JOB_STORAGE_KEY = 'nekro-deployment-active-job-v1'
const LOG_RENDER_LIMIT = 750
const RECOVERY_DELAY_MS = 3000
const MAX_STREAM_FAILURES = 2

const TERMINAL_STATUSES = new Set<DeploymentJobStatus>(['succeeded', 'failed', 'cancelled'])

export type DeploymentConnectionState =
  | 'idle'
  | 'connecting'
  | 'live'
  | 'waiting_for_backend'
  | 'polling'
  | 'job_missing'

interface StoredDeploymentTask {
  job_id: string
  client_request_id: string
  after_seq: number
  created_at: string
}

interface TrackingError {
  code: string
  message: string
}

const isStoredTask = (value: unknown): value is StoredDeploymentTask => {
  if (typeof value !== 'object' || value === null) return false
  const task = value as Partial<StoredDeploymentTask>
  return (
    typeof task.job_id === 'string' &&
    typeof task.client_request_id === 'string' &&
    typeof task.after_seq === 'number' &&
    Number.isFinite(task.after_seq) &&
    typeof task.created_at === 'string'
  )
}

const readStoredTask = (): StoredDeploymentTask | null => {
  try {
    const raw = localStorage.getItem(ACTIVE_JOB_STORAGE_KEY)
    if (!raw) return null
    const value: unknown = JSON.parse(raw)
    if (isStoredTask(value)) return value
    localStorage.removeItem(ACTIVE_JOB_STORAGE_KEY)
  } catch {
    localStorage.removeItem(ACTIVE_JOB_STORAGE_KEY)
  }
  return null
}

const persistTask = (task: StoredDeploymentTask | null) => {
  try {
    if (task) {
      localStorage.setItem(ACTIVE_JOB_STORAGE_KEY, JSON.stringify(task))
    } else {
      localStorage.removeItem(ACTIVE_JOB_STORAGE_KEY)
    }
  } catch {
    // Storage may be unavailable in private browsing or hardened environments.
  }
}

const toTrackingError = (error: unknown): TrackingError => {
  if (error instanceof ApiError) {
    return { code: error.type, message: error.message }
  }
  if (error instanceof Error) {
    return { code: error.name || 'UnknownError', message: error.message }
  }
  return { code: 'UnknownError', message: 'Unknown deployment tracking error' }
}

const isJobNotFound = (error: unknown): boolean =>
  error instanceof ApiError && error.type === 'job_not_found'

export const useDeploymentJob = (enabled: boolean, streamEnabled: boolean) => {
  const [activeTask, setActiveTask] = useState<StoredDeploymentTask | null>(() =>
    enabled ? readStoredTask() : null
  )
  const [job, setJob] = useState<DeploymentJob | null>(null)
  const [logs, setLogs] = useState<DeploymentLogEntry[]>([])
  const [connectionState, setConnectionState] = useState<DeploymentConnectionState>('idle')
  const [trackingError, setTrackingError] = useState<TrackingError | null>(null)
  const [isCancelling, setIsCancelling] = useState(false)
  const activeTaskRef = useRef<StoredDeploymentTask | null>(activeTask)
  const activeJobId = activeTask?.job_id

  const updateActiveTask = useCallback((task: StoredDeploymentTask | null) => {
    activeTaskRef.current = task
    setActiveTask(task)
    persistTask(task)
  }, [])

  const updateAfterSeq = useCallback((seq: number | null | undefined) => {
    if (seq === null || seq === undefined || !Number.isFinite(seq)) return
    const current = activeTaskRef.current
    if (!current || seq <= current.after_seq) return
    const next = { ...current, after_seq: seq }
    activeTaskRef.current = next
    setActiveTask(next)
    persistTask(next)
  }, [])

  const mergeLogs = useCallback(
    (entries: DeploymentLogEntry[]) => {
      if (entries.length === 0) return
      setLogs(current => {
        const bySeq = new Map(current.map(entry => [entry.seq, entry]))
        for (const entry of entries) {
          if (Number.isFinite(entry.seq)) bySeq.set(entry.seq, entry)
        }
        const merged = [...bySeq.values()].sort((left, right) => left.seq - right.seq)
        return merged.slice(-LOG_RENDER_LIMIT)
      })
      updateAfterSeq(Math.max(...entries.map(entry => entry.seq)))
    },
    [updateAfterSeq]
  )

  const startTracking = useCallback(
    (response: DeploymentUpdateResponse, clientRequestId: string) => {
      const task: StoredDeploymentTask = {
        job_id: response.job_id,
        client_request_id: clientRequestId,
        after_seq: 0,
        created_at: new Date().toISOString(),
      }
      setLogs([])
      setTrackingError(null)
      setJob({
        job_id: response.job_id,
        type: response.type,
        status: response.status,
        phase: response.phase ?? 'validate_instance',
        progress: null,
        error: null,
        result: null,
      })
      setConnectionState('connecting')
      updateActiveTask(task)
    },
    [updateActiveTask]
  )

  const dismissCompletedJob = useCallback(() => {
    if (activeTaskRef.current) return
    setJob(null)
    setLogs([])
    setTrackingError(null)
    setConnectionState('idle')
  }, [])

  const cancelActiveJob = useCallback(async () => {
    const task = activeTaskRef.current
    if (!task || isCancelling) return
    setIsCancelling(true)
    try {
      const response = await deploymentApi.cancelJob(task.job_id)
      setJob(current =>
        current
          ? { ...current, status: response.status, phase: response.phase ?? current.phase }
          : current
      )
    } finally {
      setIsCancelling(false)
    }
  }, [isCancelling])

  useEffect(() => {
    if (enabled) {
      if (!activeTaskRef.current) {
        const storedTask = readStoredTask()
        if (storedTask) {
          activeTaskRef.current = storedTask
          setActiveTask(storedTask)
        }
      }
    } else {
      activeTaskRef.current = null
      setActiveTask(null)
      setConnectionState('idle')
    }
  }, [enabled])

  useEffect(() => {
    if (!enabled || !activeJobId) return

    let disposed = false
    let timer: ReturnType<typeof setTimeout> | null = null
    let streamCleanup: (() => void) | null = null
    let streamFailures = 0

    const clearTimer = () => {
      if (timer !== null) {
        clearTimeout(timer)
        timer = null
      }
    }

    const stopStream = () => {
      streamCleanup?.()
      streamCleanup = null
    }

    const completeTracking = () => {
      clearTimer()
      stopStream()
      updateActiveTask(null)
      setConnectionState('idle')
    }

    const markJobMissing = (error: unknown) => {
      clearTimer()
      stopStream()
      updateActiveTask(null)
      setTrackingError(toTrackingError(error))
      setConnectionState('job_missing')
    }

    const mergeJobEvent = (event: DeploymentSseEvent) => {
      if (event.event === 'log') {
        mergeLogs([event.data])
        return
      }

      if ('seq' in event.data) updateAfterSeq(event.data.seq)

      if (event.event === 'job') {
        setJob(current =>
          current ? { ...current, status: event.data.status, phase: event.data.phase } : current
        )
        return
      }

      if (event.event === 'progress') {
        setJob(current => (current ? { ...current, progress: event.data } : current))
        return
      }

      if (event.event === 'result') {
        setJob(current =>
          current
            ? {
                ...current,
                status: event.data.status,
                phase: event.data.status === 'succeeded' ? 'finished' : current.phase,
                result: event.data.result ?? current.result,
                error: event.data.error ?? current.error,
              }
            : current
        )
        if (TERMINAL_STATUSES.has(event.data.status)) completeTracking()
      }
    }

    const refreshJobAndLogs = async (): Promise<boolean> => {
      const task = activeTaskRef.current
      if (!task) return false
      const nextJob = await deploymentApi.getJob(task.job_id)
      if (disposed) return false
      setJob(nextJob)

      const logResponse = await deploymentApi.getJobLogs(
        task.job_id,
        activeTaskRef.current?.after_seq
      )
      if (disposed) return false
      mergeLogs(logResponse.logs)
      updateAfterSeq(logResponse.next_after_seq)

      if (TERMINAL_STATUSES.has(nextJob.status)) {
        completeTracking()
        return false
      }
      return true
    }

    const scheduleRecovery = () => {
      if (disposed || timer !== null) return
      setConnectionState('waiting_for_backend')
      timer = setTimeout(() => {
        timer = null
        void recoverBackend()
      }, RECOVERY_DELAY_MS)
    }

    const schedulePolling = () => {
      if (disposed || timer !== null) return
      setConnectionState('polling')
      timer = setTimeout(() => {
        timer = null
        void pollJob()
      }, RECOVERY_DELAY_MS)
    }

    const handleStreamFailure = (error: unknown) => {
      if (disposed) return
      stopStream()
      streamFailures += 1
      const nextError = toTrackingError(error)
      setTrackingError(
        nextError.code === 'Error' || nextError.code === 'TypeError'
          ? { code: 'stream_disconnected', message: '' }
          : nextError
      )
      scheduleRecovery()
    }

    const startStream = () => {
      const task = activeTaskRef.current
      if (!task || disposed) return
      stopStream()
      setConnectionState('connecting')
      streamCleanup = deploymentApi.subscribeJobEvents(task.job_id, {
        afterSeq: task.after_seq,
        onEvent: event => {
          if (disposed) return
          setConnectionState('live')
          setTrackingError(null)
          if (event.event === 'error') {
            handleStreamFailure(
              new ApiError(event.data.code, event.data.message, null, event.data.details)
            )
            return
          }
          mergeJobEvent(event)
        },
        onError: handleStreamFailure,
      })
    }

    const recoverBackend = async () => {
      if (disposed) return
      try {
        await healthApi.check()
        const stillActive = await refreshJobAndLogs()
        if (!stillActive || disposed) return
        setTrackingError(null)
        if (streamEnabled && streamFailures < MAX_STREAM_FAILURES) {
          startStream()
        } else {
          schedulePolling()
        }
      } catch (error) {
        if (isJobNotFound(error)) {
          markJobMissing(error)
          return
        }
        setTrackingError(toTrackingError(error))
        scheduleRecovery()
      }
    }

    const pollJob = async () => {
      if (disposed) return
      try {
        const stillActive = await refreshJobAndLogs()
        if (!stillActive || disposed) return
        setTrackingError(null)
        schedulePolling()
      } catch (error) {
        if (isJobNotFound(error)) {
          markJobMissing(error)
          return
        }
        setTrackingError(toTrackingError(error))
        scheduleRecovery()
      }
    }

    const initialize = async () => {
      setConnectionState('connecting')
      try {
        const stillActive = await refreshJobAndLogs()
        if (!stillActive || disposed) return
        setTrackingError(null)
        if (streamEnabled) {
          startStream()
        } else {
          schedulePolling()
        }
      } catch (error) {
        if (isJobNotFound(error)) {
          markJobMissing(error)
          return
        }
        setTrackingError(toTrackingError(error))
        scheduleRecovery()
      }
    }

    void initialize()

    return () => {
      disposed = true
      clearTimer()
      stopStream()
    }
  }, [activeJobId, enabled, mergeLogs, streamEnabled, updateActiveTask, updateAfterSeq])

  return {
    activeTask,
    job,
    logs,
    connectionState,
    trackingError,
    isCancelling,
    startTracking,
    cancelActiveJob,
    dismissCompletedJob,
  }
}
