import { useState, useEffect, useRef, useMemo } from 'react'
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
  // 日志详情对话框状态
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

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

  // 过滤后的日志数据
  const filteredLogs = useMemo(() => {
    return realtimeLogs.filter(
      log =>
        (!filters.level || log.level === filters.level) &&
        (!filters.message || log.message.toLowerCase().includes(filters.message.toLowerCase()))
    )
  }, [realtimeLogs, filters])

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && listRef.current && filteredLogs.length > 0) {
      // 添加一个小延迟确保列表已经完全渲染
      setTimeout(() => {
        listRef.current?.scrollToItem(filteredLogs.length - 1, 'end')
      }, 50)
    }
  }, [filteredLogs, autoScroll])

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

  // 处理日志点击，打开详情对话框
  const handleLogClick = (log: LogEntry) => {
    setSelectedLog(log)
    setDialogOpen(true)
  }

  // 复制日志内容
  const copyLogContent = (log: LogEntry) => {
    const logText = `${log.timestamp} [${log.level}] [${log.source}] ${log.message}`
    navigator.clipboard.writeText(logText).then(
      () => {
        console.log('Log copied to clipboard')
      },
      err => {
        console.error('Could not copy log: ', err)
      }
    )
  }

  // 表头组件
  const TableHeader = () => (
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
          flex: '0 0 100px', // 固定宽度，确保一致性
          fontSize: isSmall ? '0.75rem' : '0.8rem',
          textAlign: 'center', // 居中对齐
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
            textAlign: 'right', // 右对齐，与内容保持一致
            pr: 2, // 右侧内边距，确保文本不会贴边
          }}
        >
          来源
        </Box>
      )}
    </Box>
  )

  // 日志行渲染器
  const LogRow = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const log = filteredLogs[index]

    // 根据日志级别获取样式
    const severityColor =
      (LOG_TABLE_STYLES.SEVERITY as Record<string, { backgroundColor: string }>)[log.level]
        ?.backgroundColor || 'transparent'

    return (
      <Box
        style={{ ...style, width: '100%' }}
        onClick={() => handleLogClick(log)}
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
        {/* 左侧日志级别条 */}
        <Box
          sx={{
            width: 4,
            height: ROW_HEIGHT - 2,
            backgroundColor: severityColor,
            borderRadius: '2px',
            mr: 1,
          }}
        />

        {/* 时间 */}
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

        {/* 级别标签 */}
        <Box
          sx={{ flex: '0 0 100px', textAlign: 'center', display: 'flex', justifyContent: 'center' }}
        >
          {' '}
          {/* 与表头保持一致 */}
          <Chip
            label={log.level}
            size="small"
            sx={{
              ...CHIP_VARIANTS.getLogLevelChip(log.level, isSmall),
              height: isSmall ? 18 : 20,
              minWidth: '40px', // 设置最小宽度确保一致性
              '.MuiChip-label': {
                px: 1,
                fontSize: isSmall ? '0.6rem' : '0.65rem',
                lineHeight: 1,
                textAlign: 'center', // 确保文本居中
              },
            }}
          />
        </Box>

        {/* 消息 */}
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

        {/* 仅在高级模式显示来源 */}
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
              textAlign: 'right', // 右对齐，与表头保持一致
              pr: 2, // 右侧内边距，确保文本不会贴边
            }}
          >
            {log.source}
          </Box>
        )}
      </Box>
    )
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
        p: 2,
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

      {/* 日志表格 - 使用虚拟滚动 */}
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
          <TableHeader />
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
                  {LogRow}
                </List>
              )}
            </AutoSizer>
          </Box>
        </Box>
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

      {/* 日志详情对话框 - 使用通用NekroDialog组件 */}
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
    </Box>
  )
}
