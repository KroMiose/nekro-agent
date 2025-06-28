import { useState, useEffect, useRef, useMemo, memo, useCallback } from 'react'
import {
  Box,
  Paper,
  FormControlLabel,
  Switch,
  TextField,
  Chip,
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
  Divider,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { LogEntry, logsApi } from '../../services/api/logs'
import DownloadIcon from '@mui/icons-material/Download'
import FilterAltIcon from '@mui/icons-material/FilterAlt'
import CloseIcon from '@mui/icons-material/Close'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import {
  LOG_TABLE_STYLES,
  CHIP_VARIANTS,
  UNIFIED_TABLE_STYLES,
  getAlphaColor,
} from '../../theme/themeApi'
import { FixedSizeList as List } from 'react-window'
import AutoSizer from 'react-virtualized-auto-sizer'
import NekroDialog from '../../components/common/NekroDialog'

const MAX_REALTIME_LOGS = 1000
const INITIAL_LOGS_COUNT = 500
const ROW_HEIGHT = 36 // 固定行高
const LOG_UPDATE_INTERVAL = 250 // 实时日志更新间隔 (ms)

// 拆分并优化的 TableHeader 组件
const TableHeader = memo(
  ({
    isMobile,
    isSmall,
    isAdvanced,
  }: {
    isMobile: boolean
    isSmall: boolean
    isAdvanced: boolean
  }) => {
    const theme = useTheme()
    return (
      <Box
        sx={{
          display: 'flex',
          borderBottom: `1px solid ${theme.palette.divider}`,
          py: 1,
          px: 2,
          ...UNIFIED_TABLE_STYLES.header,
        }}
      >
        <Box
          sx={{
            flex: isMobile ? '0 0 90px' : '0 0 120px',
            fontSize: isSmall ? '0.75rem' : '0.8rem',
          }}
        >
          时间
        </Box>
        <Box
          sx={{
            flex: '0 0 100px',
            fontSize: isSmall ? '0.75rem' : '0.8rem',
            textAlign: 'center',
          }}
        >
          级别
        </Box>
        <Box
          sx={{
            flex: '1 1 auto',
            fontSize: isSmall ? '0.75rem' : '0.8rem',
            ml: 1,
          }}
        >
          消息
        </Box>
        {isAdvanced && !isMobile && (
          <Box
            sx={{
              flex: '0 0 100px',
              fontSize: isSmall ? '0.75rem' : '0.8rem',
              ml: 1,
              textAlign: 'right',
              pr: 2,
            }}
          >
            来源
          </Box>
        )}
      </Box>
    )
  }
)
TableHeader.displayName = 'TableHeader'

// 拆分并优化的 LogRow 组件
const LogRow = memo(
  ({
    style,
    log,
    isMobile,
    isSmall,
    isAdvanced,
    onLogClick,
  }: {
    style: React.CSSProperties
    log: LogEntry
    isMobile: boolean
    isSmall: boolean
    isAdvanced: boolean
    onLogClick: (log: LogEntry) => void
  }) => {
    const theme = useTheme()
    const severityColor =
      (LOG_TABLE_STYLES.SEVERITY as Record<string, { backgroundColor: string }>)[log.level]
        ?.backgroundColor || 'transparent'

    return (
      <Box
        style={{ ...style, width: '100%' }}
        onClick={() => onLogClick(log)}
        sx={{
          cursor: 'pointer',
          '&:hover': {
            backgroundColor: LOG_TABLE_STYLES.ROW.HOVER,
          },
          borderBottom: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          alignItems: 'center',
          pl: 1,
          width: '100%',
          ...UNIFIED_TABLE_STYLES.row,
        }}
      >
        <Box
          sx={{
            width: 4,
            height: ROW_HEIGHT - 2,
            backgroundColor: severityColor,
            borderRadius: '2px',
            mr: 1,
          }}
        />
        <Box
          sx={{
            flex: isMobile ? '0 0 90px' : '0 0 120px',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            fontSize: isSmall ? '0.7rem' : '0.75rem',
            color: theme.palette.text.secondary,
          }}
        >
          {isMobile ? log.timestamp.split(' ')[1] : log.timestamp}
        </Box>
        <Box
          sx={{ flex: '0 0 100px', textAlign: 'center', display: 'flex', justifyContent: 'center' }}
        >
          <Chip
            label={log.level}
            size="small"
            sx={{
              ...CHIP_VARIANTS.getLogLevelChip(log.level, isSmall),
              height: isSmall ? 18 : 20,
              minWidth: '40px',
              '.MuiChip-label': {
                px: 1,
                fontSize: isSmall ? '0.6rem' : '0.65rem',
                lineHeight: 1,
                textAlign: 'center',
              },
            }}
          />
        </Box>
        <Box
          sx={{
            flex: '1 1 auto',
            overflow: 'hidden',
            whiteSpace: 'nowrap',
            textOverflow: 'ellipsis',
            fontSize: isSmall ? '0.75rem' : '0.8rem',
            ml: 1,
          }}
        >
          {log.message}
        </Box>
        {isAdvanced && !isMobile && (
          <Box
            sx={{
              flex: '0 0 100px',
              overflow: 'hidden',
              whiteSpace: 'nowrap',
              textOverflow: 'ellipsis',
              fontSize: isSmall ? '0.7rem' : '0.75rem',
              color: theme.palette.text.secondary,
              ml: 1,
              textAlign: 'right',
              pr: 2,
            }}
          >
            {log.source}
          </Box>
        )}
      </Box>
    )
  }
)
LogRow.displayName = 'LogRow'

export default function LogsPage() {
  const [autoScroll, setAutoScroll] = useState(true)
  const [isAdvanced, setIsAdvanced] = useState(false)
  const [realtimeLogs, setRealtimeLogs] = useState<LogEntry[]>([])
  const [isDisconnected, setIsDisconnected] = useState(false)
  const [downloadLines, setDownloadLines] = useState<string>('1000')
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false)
  const listRef = useRef<List>(null)
  const [filters, setFilters] = useState({
    level: '',
    source: '',
    message: '',
  })
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [downloadConfirmOpen, setDownloadConfirmOpen] = useState(false)
  const logQueue = useRef<LogEntry[]>([])

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  const { data: sources = [] } = useQuery({
    queryKey: ['log-sources'],
    queryFn: () => logsApi.getSources(),
    refetchInterval: 5000,
  })

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

  useEffect(() => {
    if (initialLogs.length > 0) {
      setRealtimeLogs(initialLogs)
    }
  }, [initialLogs])

  const filteredLogs = useMemo(() => {
    const lowerCaseMessage = filters.message.toLowerCase()
    return realtimeLogs.filter(
      log =>
        (!filters.level || log.level === filters.level) &&
        (!lowerCaseMessage || log.message.toLowerCase().includes(lowerCaseMessage))
    )
  }, [realtimeLogs, filters])

  useEffect(() => {
    if (autoScroll && listRef.current && filteredLogs.length > 0) {
      setTimeout(() => {
        listRef.current?.scrollToItem(filteredLogs.length - 1, 'end')
      }, 50)
    }
  }, [filteredLogs, autoScroll])

  useEffect(() => {
    let cleanup: (() => void) | undefined
    const intervalId = setInterval(() => {
      if (logQueue.current.length > 0) {
        const newLogs = [...logQueue.current]
        logQueue.current = []
        setRealtimeLogs(prev => [...prev, ...newLogs].slice(-MAX_REALTIME_LOGS))
      }
    }, LOG_UPDATE_INTERVAL)

    const connect = () => {
      try {
        cleanup = logsApi.streamLogs(
          data => {
            if (!data) return
            try {
              const log = JSON.parse(data) as LogEntry
              const sourceMatch = !filters.source || log.source === filters.source
              if (sourceMatch) {
                logQueue.current.push(log)
              }
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
      cleanup?.()
      clearInterval(intervalId)
    }
  }, [filters.source])

  const handleDownloadLogs = () => {
    setDownloadConfirmOpen(true)
  }

  const confirmDownloadLogs = () => {
    const lines = parseInt(downloadLines) || 1000
    logsApi.downloadLogs({
      lines,
      source: filters.source || undefined,
    })
    setDownloadConfirmOpen(false)
  }

  const handleLogClick = useCallback((log: LogEntry) => {
    setSelectedLog(log)
    setDialogOpen(true)
  }, [])

  const copyLogContent = (log: LogEntry) => {
    const logText = `${log.timestamp} [${log.level}] [${log.source}] ${log.message}`
    navigator.clipboard.writeText(logText).then(
      () => console.log('Log copied to clipboard'),
      err => console.error('Could not copy log: ', err)
    )
  }

  // 拆分并优化的 FilterContent 组件
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
        {Object.keys(LOG_TABLE_STYLES.SEVERITY).map(level => (
          <MenuItem key={level} value={level}>
            {level}
          </MenuItem>
        ))}
      </TextField>

      <Autocomplete
        options={sources}
        value={filters.source}
        onChange={(_, newValue: string | null) => {
          setRealtimeLogs([]) // 切换源时清空日志
          logQueue.current = [] // 并清空队列
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

  const renderRow = useCallback(
    ({ index, style }: { index: number; style: React.CSSProperties }) => {
      const log = filteredLogs[index]
      if (!log) return null
      return (
        <LogRow
          style={style}
          log={log}
          isMobile={isMobile}
          isSmall={isSmall}
          isAdvanced={isAdvanced}
          onLogClick={handleLogClick}
        />
      )
    },
    [filteredLogs, isMobile, isSmall, isAdvanced, handleLogClick]
  )

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 64px)',
        p: 2,
      }}
    >
      {isDisconnected && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          日志流连接已断开，正在尝试重新连接...
        </Alert>
      )}

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
            {Object.keys(LOG_TABLE_STYLES.SEVERITY).map(level => (
              <MenuItem key={level} value={level}>
                {level}
              </MenuItem>
            ))}
          </TextField>
          <Autocomplete
            options={sources}
            value={filters.source}
            onChange={(_, newValue: string | null) => {
              setRealtimeLogs([]) // 切换源时清空日志
              logQueue.current = [] // 并清空队列
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

      <Paper
        elevation={3}
        sx={{
          flexGrow: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          ...UNIFIED_TABLE_STYLES.paper,
        }}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
          <TableHeader isMobile={isMobile} isSmall={isSmall} isAdvanced={isAdvanced} />
          <Box
            sx={{
              flexGrow: 1,
              overflow: 'hidden',
              ...UNIFIED_TABLE_STYLES.tableViewport,
            }}
          >
            <AutoSizer>
              {({ height, width }) => (
                <List
                  ref={listRef}
                  height={height}
                  width={width + 20}
                  itemCount={filteredLogs.length}
                  itemSize={ROW_HEIGHT}
                  overscanCount={20}
                  style={{
                    overflowX: 'hidden',
                  }}
                >
                  {renderRow}
                </List>
              )}
            </AutoSizer>
          </Box>
        </Box>
      </Paper>

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

      <NekroDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
        dividers
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              label={selectedLog?.level}
              size="small"
              sx={selectedLog ? CHIP_VARIANTS.getLogLevelChip(selectedLog.level, false) : {}}
            />
            <Typography variant="h6">日志详情</Typography>
          </Box>
        }
        titleActions={
          selectedLog && (
            <IconButton
              onClick={() => copyLogContent(selectedLog)}
              size="small"
              title="复制日志内容"
              sx={{ mr: 1 }}
            >
              <ContentCopyIcon fontSize="small" />
            </IconButton>
          )
        }
        actions={
          <Button
            onClick={() => setDialogOpen(false)}
            variant="contained"
            color="primary"
            size="small"
          >
            关闭
          </Button>
        }
      >
        {selectedLog && (
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold', width: 80 }}>
                时间:
              </Typography>
              <Typography variant="body2">{selectedLog.timestamp}</Typography>
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold', width: 80 }}>
                来源:
              </Typography>
              <Typography variant="body2" sx={{ flex: 1 }}>
                {selectedLog.source}
              </Typography>
            </Box>

            {isAdvanced && (
              <>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', width: 80 }}>
                    模块:
                  </Typography>
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {selectedLog.function}
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', width: 80 }}>
                    位置:
                  </Typography>
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    行 {selectedLog.line}
                  </Typography>
                </Box>
              </>
            )}

            <Divider />

            <Box>
              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                消息内容:
              </Typography>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  backgroundColor: getAlphaColor(
                    theme.palette.mode === 'dark'
                      ? theme.palette.background.paper
                      : theme.palette.background.default,
                    0.05
                  ),
                  maxHeight: '50vh',
                  overflow: 'auto',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  borderRadius: 1,
                  borderColor: 'divider',
                }}
              >
                {selectedLog.message}
              </Paper>
            </Box>
          </Stack>
        )}
      </NekroDialog>

      <NekroDialog
        open={downloadConfirmOpen}
        onClose={() => setDownloadConfirmOpen(false)}
        title="确认下载日志"
        maxWidth="sm"
        dividers
        actions={
          <>
            <Button onClick={() => setDownloadConfirmOpen(false)}>再想想</Button>
            <Button onClick={confirmDownloadLogs} variant="contained" color="warning">
              我已知晓风险，继续下载
            </Button>
          </>
        }
      >
        <Alert severity="warning" sx={{ mb: 2 }}>
          <strong>请注意！日志文件可能包含敏感信息！</strong>
        </Alert>
        <Typography variant="body1" gutterBottom>
          日志中可能包含您的 API 密钥、用户信息、聊天信息或其他隐私数据。
        </Typography>
        <Typography variant="body1">
          为了您的信息安全，请<b>不要</b>
          将未经处理的日志文件直接发送给未受信任的对象或上传到公开平台。
        </Typography>
      </NekroDialog>
    </Box>
  )
}
