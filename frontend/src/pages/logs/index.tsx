import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Paper,
  FormControlLabel,
  Switch,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  TextField,
  Autocomplete,
  MenuItem,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { LogEntry, logsApi } from '../../services/api/logs'

const LOG_LEVEL_COLORS = {
  ERROR: 'error',
  WARNING: 'warning',
  SUCCESS: 'success',
  INFO: 'info',
  DEBUG: 'secondary',
  TRACE: 'default',
  CRITICAL: 'error',
} as const

const MAX_REALTIME_LOGS = 1000
const INITIAL_LOGS_COUNT = 100

export default function LogsPage() {
  const [autoScroll, setAutoScroll] = useState(true)
  const [isAdvanced, setIsAdvanced] = useState(false)
  const [realtimeLogs, setRealtimeLogs] = useState<LogEntry[]>([])
  const tableContainerRef = useRef<HTMLDivElement>(null)
  const [filters, setFilters] = useState({
    level: '',
    source: '',
    message: '',
  })

  // 获取日志来源列表
  const { data: sources = [] } = useQuery({
    queryKey: ['log-sources'],
    queryFn: () => logsApi.getSources(),
    refetchInterval: 5000,
  })

  // 获取初始实时日志
  const { data: initialLogs = [] } = useQuery({
    queryKey: ['initial-logs', filters.source],
    queryFn: async () => {
      const response = await logsApi.getLogs({
        page: 1,
        pageSize: INITIAL_LOGS_COUNT,
        source: filters.source || undefined,
      })
      return response.logs
    },
  })

  // 初始化日志数据
  useEffect(() => {
    if (initialLogs.length > 0) {
      setRealtimeLogs(initialLogs)
    }
  }, [initialLogs])

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && tableContainerRef.current) {
      const container = tableContainerRef.current
      container.scrollTop = container.scrollHeight
    }
  }, [realtimeLogs, autoScroll])

  // 实时日志订阅
  useEffect(() => {
    console.log('Starting real-time log subscription...')
    let eventSource: EventSource

    try {
      eventSource = logsApi.streamLogs()

      eventSource.onmessage = event => {
        try {
          const jsonStr = event.data.replace(/^data:\s*/, '')
          const log = JSON.parse(jsonStr) as LogEntry
          setRealtimeLogs(prev => {
            const isDuplicate = prev.some(
              existingLog =>
                existingLog.timestamp === log.timestamp && existingLog.message === log.message
            )
            const sourceMatch = !filters.source || log.source === filters.source
            if (isDuplicate || !sourceMatch) {
              return prev
            }
            return [...prev, log].slice(-MAX_REALTIME_LOGS)
          })
        } catch (error) {
          console.error('Failed to parse log data:', error)
        }
      }

      eventSource.onerror = error => {
        console.error('EventSource failed:', error)
        eventSource.close()
      }
    } catch (error) {
      console.error('Failed to create EventSource:', error)
    }

    return () => {
      console.log('Closing real-time log subscription...')
      eventSource?.close()
    }
  }, [filters.source])

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 120px)',
      }}
    >
      {/* 顶部工具栏 */}
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          mb: 2,
          flexShrink: 0,
        }}
      >
        <FormControlLabel
          control={
            <Switch
              checked={isAdvanced}
              onChange={e => setIsAdvanced(e.target.checked)}
              color="primary"
            />
          }
          label="高级模式"
        />
        <FormControlLabel
          control={
            <Switch
              checked={autoScroll}
              onChange={e => setAutoScroll(e.target.checked)}
              color="primary"
            />
          }
          label="自动滚动"
        />
        <TextField
          select
          label="日志级别"
          value={filters.level}
          onChange={e => setFilters(prev => ({ ...prev, level: e.target.value }))}
          size="small"
          sx={{ width: 120 }}
        >
          <MenuItem value="">全部</MenuItem>
          {Object.keys(LOG_LEVEL_COLORS).map(level => (
            <MenuItem key={level} value={level}>
              {level}
            </MenuItem>
          ))}
        </TextField>
        <Autocomplete
          options={sources}
          value={filters.source}
          onChange={(_, newValue: string | null) => {
            setFilters(prev => ({
              ...prev,
              source: newValue || '',
            }))
          }}
          sx={{ width: 200 }}
          renderInput={params => <TextField {...params} label="来源" size="small" />}
        />
        <TextField
          label="消息内容"
          value={filters.message}
          onChange={e => setFilters(prev => ({ ...prev, message: e.target.value }))}
          size="small"
          sx={{ flexGrow: 1 }}
        />
      </Box>

      {/* 日志表格 */}
      <Paper
        elevation={3}
        sx={{ flexGrow: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
      >
        <TableContainer ref={tableContainerRef} sx={{ flexGrow: 1 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell width="180px" sx={{ minWidth: 180 }}>
                  时间
                </TableCell>
                <TableCell width="80px" sx={{ minWidth: 80 }}>
                  级别
                </TableCell>
                <TableCell sx={{ minWidth: 300 }}>消息</TableCell>
                {isAdvanced && (
                  <>
                    <TableCell width="120px" sx={{ minWidth: 120 }}>
                      来源
                    </TableCell>
                    <TableCell width="180px" sx={{ minWidth: 180 }}>
                      位置
                    </TableCell>
                  </>
                )}
              </TableRow>
            </TableHead>
            <TableBody>
              {realtimeLogs
                .filter(
                  log =>
                    (!filters.level || log.level === filters.level) &&
                    (!filters.message ||
                      log.message.toLowerCase().includes(filters.message.toLowerCase()))
                )
                .map((log, index) => (
                  <TableRow key={index}>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{log.timestamp}</TableCell>
                    <TableCell>
                      <Chip
                        label={log.level}
                        color={
                          LOG_LEVEL_COLORS[log.level as keyof typeof LOG_LEVEL_COLORS] || 'default'
                        }
                        size="small"
                      />
                    </TableCell>
                    <TableCell sx={{ wordBreak: 'break-word' }}>{log.message}</TableCell>
                    {isAdvanced && (
                      <>
                        <TableCell sx={{ whiteSpace: 'nowrap' }}>{log.source}</TableCell>
                        <TableCell
                          sx={{ whiteSpace: 'nowrap' }}
                        >{`${log.function}:${log.line}`}</TableCell>
                      </>
                    )}
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  )
}
