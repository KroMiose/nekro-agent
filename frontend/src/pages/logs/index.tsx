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
  Alert,
  Button,
  Tooltip,
  IconButton,
  useMediaQuery,
  useTheme,
  Stack,
  Typography,
  Drawer,
  Fab,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { LogEntry, logsApi } from '../../services/api/logs'
import DownloadIcon from '@mui/icons-material/Download'
import FilterAltIcon from '@mui/icons-material/FilterAlt'
import CloseIcon from '@mui/icons-material/Close'

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
const INITIAL_LOGS_COUNT = 500

export default function LogsPage() {
  const [autoScroll, setAutoScroll] = useState(true)
  const [isAdvanced, setIsAdvanced] = useState(false)
  const [realtimeLogs, setRealtimeLogs] = useState<LogEntry[]>([])
  const [isDisconnected, setIsDisconnected] = useState(false)
  const [downloadLines, setDownloadLines] = useState<string>('1000')
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false)
  const tableContainerRef = useRef<HTMLDivElement>(null)
  const [filters, setFilters] = useState({
    level: '',
    source: '',
    message: '',
  })

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

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
    let cleanup: (() => void) | undefined

    const connect = () => {
      try {
        cleanup = logsApi.streamLogs(
          data => {
            if (!data) {
              return
            }
            try {
              const log = JSON.parse(data) as LogEntry
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
          },
          error => {
            console.error('EventSource error:', error)
            setIsDisconnected(true)
          }
        )
        setIsDisconnected(false)
      } catch (error) {
        console.error('Failed to create EventSource:', error)
        setIsDisconnected(true)
      }
    }

    connect()

    return () => {
      console.log('Closing real-time log subscription...')
      cleanup?.()
    }
  }, [filters.source])

  // 处理下载日志
  const handleDownloadLogs = () => {
    const lines = parseInt(downloadLines) || 1000
    logsApi.downloadLogs({
      lines,
      source: filters.source || undefined,
    })
  }

  // 过滤器内容组件
  const FilterContent = () => (
    <Stack spacing={2} sx={{ p: 2, width: isMobile ? '100%' : 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="subtitle1">日志过滤器</Typography>
        {isMobile && (
          <IconButton
            edge="end"
            color="inherit"
            onClick={() => setFilterDrawerOpen(false)}
            aria-label="关闭过滤器"
          >
            <CloseIcon />
          </IconButton>
        )}
      </Box>

      <TextField
        select
        label="日志级别"
        value={filters.level}
        onChange={e => setFilters(prev => ({ ...prev, level: e.target.value }))}
        size="small"
        fullWidth
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
        fullWidth
        renderInput={params => <TextField {...params} label="来源" size="small" />}
      />

      <TextField
        label="消息内容"
        value={filters.message}
        onChange={e => setFilters(prev => ({ ...prev, message: e.target.value }))}
        size="small"
        fullWidth
      />

      {/* 高级模式开关 */}
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

      {/* 自动滚动开关 */}
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

      {/* 下载日志组件 */}
      <Typography variant="subtitle2" sx={{ mt: 1 }}>
        日志下载
      </Typography>
      <Stack direction="row" spacing={1}>
        <TextField
          label="最近日志行数"
          type="number"
          value={downloadLines}
          onChange={e => setDownloadLines(e.target.value)}
          size="small"
          fullWidth
          InputProps={{
            inputProps: { min: 100, max: 10000 },
          }}
        />
        <Button
          variant="contained"
          color="primary"
          onClick={handleDownloadLogs}
          startIcon={<DownloadIcon />}
          size="small"
          sx={{
            width: '100px',
          }}
        >
          下载
        </Button>
      </Stack>

      {isMobile && (
        <Button
          variant="contained"
          fullWidth
          onClick={() => setFilterDrawerOpen(false)}
          sx={{ mt: 2 }}
        >
          应用过滤器
        </Button>
      )}
    </Stack>
  )

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 90px)',
      }}
    >
      {/* 连接状态提示 */}
      {isDisconnected && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          日志流连接已断开，正在尝试重新连接...
        </Alert>
      )}

      {/* 桌面版顶部工具栏 */}
      {!isMobile && (
        <Box
          sx={{
            display: 'flex',
            gap: 2,
            my: 1,
            pl: 1,
            flexShrink: 0,
            flexWrap: 'wrap',
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

          {/* 下载日志组件 */}
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="输入要下载的日志行数">
              <TextField
                label="最近日志行数"
                type="number"
                value={downloadLines}
                onChange={e => setDownloadLines(e.target.value)}
                size="small"
                sx={{ width: 120 }}
                InputProps={{
                  inputProps: { min: 100, max: 10000 },
                }}
              />
            </Tooltip>
            <Tooltip title="下载日志文件">
              <Button
                variant="contained"
                color="primary"
                onClick={handleDownloadLogs}
                startIcon={<DownloadIcon />}
                size="small"
              >
                下载最近日志
              </Button>
            </Tooltip>
          </Box>
        </Box>
      )}

      {/* 日志表格 */}
      <Paper
        elevation={3}
        sx={{ flexGrow: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
      >
        <TableContainer ref={tableContainerRef} sx={{ flexGrow: 1 }}>
          <Table stickyHeader size={isSmall ? 'small' : 'medium'}>
            <TableHead>
              <TableRow>
                <TableCell
                  width={isMobile ? '90px' : '180px'}
                  sx={{
                    minWidth: isMobile ? 90 : 180,
                    py: isSmall ? 1 : 1.5,
                  }}
                >
                  时间
                </TableCell>
                <TableCell
                  width={isMobile ? '60px' : '80px'}
                  sx={{
                    minWidth: isMobile ? 60 : 80,
                    py: isSmall ? 1 : 1.5,
                  }}
                >
                  级别
                </TableCell>
                <TableCell
                  sx={{
                    minWidth: isMobile ? 150 : 300,
                    py: isSmall ? 1 : 1.5,
                  }}
                >
                  消息
                </TableCell>
                {isAdvanced && !isMobile && (
                  <>
                    <TableCell
                      width="120px"
                      sx={{
                        minWidth: 120,
                        py: isSmall ? 1 : 1.5,
                      }}
                    >
                      来源
                    </TableCell>
                    <TableCell
                      width="180px"
                      sx={{
                        minWidth: 180,
                        py: isSmall ? 1 : 1.5,
                      }}
                    >
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
                    <TableCell
                      sx={{
                        whiteSpace: 'nowrap',
                        py: isSmall ? 0.75 : 1.5,
                        fontSize: isSmall ? '0.75rem' : 'inherit',
                      }}
                    >
                      {isMobile ? log.timestamp.split(' ')[1] : log.timestamp}
                    </TableCell>
                    <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
                      <Chip
                        label={log.level}
                        color={
                          LOG_LEVEL_COLORS[log.level as keyof typeof LOG_LEVEL_COLORS] || 'default'
                        }
                        size="small"
                        sx={{
                          height: isSmall ? 20 : 24,
                          fontSize: isSmall ? '0.65rem' : '0.75rem',
                          '& .MuiChip-label': {
                            px: isSmall ? 0.5 : 0.75,
                          },
                        }}
                      />
                    </TableCell>
                    <TableCell
                      sx={{
                        wordBreak: 'break-word',
                        py: isSmall ? 0.75 : 1.5,
                        fontSize: isSmall ? '0.75rem' : 'inherit',
                      }}
                    >
                      {log.message}
                    </TableCell>
                    {isAdvanced && !isMobile && (
                      <>
                        <TableCell
                          sx={{
                            whiteSpace: 'nowrap',
                            py: isSmall ? 0.75 : 1.5,
                            fontSize: isSmall ? '0.75rem' : 'inherit',
                          }}
                        >
                          {log.source}
                        </TableCell>
                        <TableCell
                          sx={{
                            whiteSpace: 'nowrap',
                            py: isSmall ? 0.75 : 1.5,
                            fontSize: isSmall ? '0.75rem' : 'inherit',
                          }}
                        >{`${log.function}:${log.line}`}</TableCell>
                      </>
                    )}
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 移动端过滤器抽屉 */}
      {isMobile && (
        <>
          <Drawer
            anchor="right"
            open={filterDrawerOpen}
            onClose={() => setFilterDrawerOpen(false)}
            sx={{
              '& .MuiDrawer-paper': {
                width: isSmall ? '85%' : '70%',
                maxWidth: 320,
              },
            }}
          >
            <FilterContent />
          </Drawer>

          {/* 过滤器按钮 */}
          <Fab
            color="primary"
            aria-label="过滤器"
            onClick={() => setFilterDrawerOpen(true)}
            sx={{
              position: 'fixed',
              bottom: 16,
              right: 16,
              zIndex: 1099,
            }}
            size={isSmall ? 'medium' : 'large'}
          >
            <FilterAltIcon />
          </Fab>
        </>
      )}
    </Box>
  )
}
