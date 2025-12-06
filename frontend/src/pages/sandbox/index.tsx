import React, { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Card,
  CardContent,
  IconButton,
  Collapse,
  Tooltip,
  Stack,
  CircularProgress,
  useMediaQuery,
  useTheme,
  Grid,
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
  Snackbar,
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  Alert,
  SxProps,
  Theme,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from '@mui/material'
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Timer as TimerIcon,
  Psychology as PsychologyIcon,
  Code as CodeIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
  ContentCopy as ContentCopyIcon,
  Speed as SpeedIcon,
  Bolt as BoltIcon,
  AccessTime as AccessTimeIcon,
  KeyboardDoubleArrowRight as KeyboardDoubleArrowRightIcon,
  Functions as FunctionsIcon,
  Abc as AbcIcon,
  Visibility as VisibilityIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { sandboxApi, SandboxCodeExtData } from '../../services/api/sandbox'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useColorMode } from '../../stores/theme'
import { getStopTypeColor, getStopTypeText } from '../../theme/utils'
import { CHIP_VARIANTS, UNIFIED_TABLE_STYLES, CARD_VARIANTS } from '../../theme/variants'
import TablePaginationStyled from '../../components/common/TablePaginationStyled'
import { useDevModeStore } from '../../stores/devMode'
<<<<<<< HEAD
import { useNotification } from '../../hooks/useNotification'
=======
<<<<<<< HEAD
import { useNotification } from '../../hooks/useNotification'
=======
<<<<<<< HEAD
import { useNotification } from '../../hooks/useNotification'
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

// 添加共用的内容区样式
const sharedContentStyles: SxProps<Theme> = {
  width: '100%',
  maxWidth: '100%',
  overflow: 'hidden',
  position: 'relative',
  wordBreak: 'break-word',
  overflowWrap: 'break-word',
}

// 共用的滚动区域样式
const scrollableContentStyles: SxProps<Theme> = {
  width: '100%',
  maxWidth: '100%',
  overflow: 'auto',
  '&::-webkit-scrollbar': {
    width: '6px',
    height: '6px',
  },
  '&::-webkit-scrollbar-thumb': {
    backgroundColor: theme =>
      theme.palette.mode === 'dark' ? 'rgba(255, 235, 235, 0.16)' : 'rgba(0, 0, 0, 0.2)',
    borderRadius: '3px',
  },
}

interface LogContentDialogProps {
  open: boolean
  onClose: () => void
  logPath: string
}

interface LogMessageContentItem {
  type: 'text' | 'image_url'
  text?: string
  image_url?: {
    url: string
  }
}

interface LogMessage {
  role: string
  content: string | LogMessageContentItem[]
}

interface FullLogData {
  request: {
    messages: LogMessage[]
  }
  response: {
    thought_chain: string
    content: string
  }
}

function LogContentDialog({ open, onClose, logPath }: LogContentDialogProps) {
  const { data, isLoading, error } = useQuery<FullLogData, Error>({
    queryKey: ['sandbox-log-content', logPath],
    queryFn: () => sandboxApi.getLogContent(logPath),
    enabled: open, // Only fetch when the dialog is open
  })
  const { mode } = useColorMode()

  const unescapeNewlines = (text: string | undefined | null) => {
    if (!text) return ''
    return text.replace(/\\n/g, '\n')
  }

  const renderContent = () => {
    if (isLoading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )
    }

    if (error) {
      return <Alert severity="error">Failed to load log content: {error.message}</Alert>
    }

    if (!data) {
      return <Alert severity="warning">No content available.</Alert>
    }

    // Custom renderer for JSON content to handle images
    const renderJsonAsComponent = (jsonData: FullLogData) => {
      if (!jsonData.request || !Array.isArray(jsonData.request.messages)) {
        return (
          <SyntaxHighlighter
            language="json"
            style={mode === 'dark' ? vscDarkPlus : oneLight}
            wrapLines
            wrapLongLines
            customStyle={{ background: 'transparent' }}
          >
            {JSON.stringify(jsonData, null, 2)}
          </SyntaxHighlighter>
        )
      }

      return (
        <Box>
          <Typography variant="h6" gutterBottom>
            Request Details
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, mb: 2, ...scrollableContentStyles }}>
            {jsonData.request.messages.map((msg: LogMessage, index: number) => (
              <Box key={index} sx={{ mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                  Role: {msg.role}
                </Typography>
                {Array.isArray(msg.content) ? (
                  msg.content.map((contentItem: LogMessageContentItem, itemIndex: number) => (
                    <Box key={itemIndex} sx={{ mt: 1 }}>
                      {contentItem.type === 'text' && (
                        <Typography sx={{ whiteSpace: 'pre-wrap' }}>
                          {unescapeNewlines(contentItem.text)}
                        </Typography>
                      )}
                      {contentItem.type === 'image_url' && contentItem.image_url && (
                        <Box>
                          <Typography variant="caption">Image URL:</Typography>
                          <img
                            src={contentItem.image_url.url}
                            alt="log content"
                            style={{
                              maxWidth: '100%',
                              maxHeight: '300px',
                              display: 'block',
                              marginTop: '8px',
                            }}
                          />
                        </Box>
                      )}
                    </Box>
                  ))
                ) : (
                  <Typography sx={{ whiteSpace: 'pre-wrap' }}>
                    {unescapeNewlines(msg.content as string)}
                  </Typography>
                )}
              </Box>
            ))}
          </Paper>

          <Typography variant="h6" gutterBottom>
            Response
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, ...scrollableContentStyles }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
              Thought Chain:
            </Typography>
            <pre
              style={{
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: '200px',
                overflowY: 'auto',
              }}
            >
              {unescapeNewlines(jsonData.response.thought_chain) || '<Empty>'}
            </pre>
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mt: 2 }}>
              Content:
            </Typography>
            <pre
              style={{
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                overflowWrap: 'break-word',
              }}
            >
              {unescapeNewlines(jsonData.response.content) || '<Empty>'}
            </pre>
          </Paper>
        </Box>
      )
    }

    return renderJsonAsComponent(data)
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>View Log Content</DialogTitle>
      <DialogContent dividers sx={scrollableContentStyles}>
        {renderContent()}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}

export default function SandboxPage() {
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({})
  const { mode } = useColorMode()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
<<<<<<< HEAD
  const notification = useNotification()
=======
<<<<<<< HEAD
  const notification = useNotification()
=======
<<<<<<< HEAD
  const notification = useNotification()
=======
  const [copyMessage, setCopyMessage] = useState<string | null>(null)
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  const { devMode } = useDevModeStore()
  const [logViewerOpen, setLogViewerOpen] = useState(false)
  const [selectedLogPath, setSelectedLogPath] = useState<string | null>(null)

  const formatNumber = (num: number | undefined | null) => {
    if (num === undefined || num === null || isNaN(num)) return 'N/A'
    return num.toLocaleString()
  }

  const getPerformanceColor = (
    value: number | undefined | null,
    thresholds: { error: number; warning: number },
    direction: 'higherIsBetter' | 'lowerIsBetter'
  ): string => {
    if (value === undefined || value === null || isNaN(value) || value <= 0) {
      return 'text.secondary' // Default/grey color for N/A
    }

    if (direction === 'lowerIsBetter') {
      if (value > thresholds.error) return 'error.main'
      if (value > thresholds.warning) return 'warning.main'
      return 'success.main'
    }

    // direction === 'higherIsBetter'
    if (value < thresholds.error) return 'error.main'
    if (value < thresholds.warning) return 'warning.main'
    return 'success.main'
  }

  const { data: stats } = useQuery({
    queryKey: ['sandbox-stats'],
    queryFn: () => sandboxApi.getStats(),
  })

  const {
    data: logs,
    isLoading,
    isPlaceholderData,
  } = useQuery({
    queryKey: ['sandbox-logs', page, rowsPerPage],
    queryFn: () =>
      sandboxApi.getLogs({
        page: page + 1,
        page_size: rowsPerPage,
      }),
    placeholderData: logs => logs,
  })

  const handleChangePage = (_: unknown, newPage: number) => {
    setPage(newPage)
  }

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10))
    setPage(0)
  }

  const toggleRow = (id: number) => {
    setExpandedRows(prev => ({
      ...prev,
      [id]: !prev[id],
    }))
  }

  // 复制内容到剪贴板函数
  const copyToClipboard = (text: string | null, contentType: string) => {
    if (!text) {
<<<<<<< HEAD
      notification.warning('无内容可复制')
=======
<<<<<<< HEAD
      notification.warning('无内容可复制')
=======
<<<<<<< HEAD
      notification.warning('无内容可复制')
=======
      setCopyMessage('无内容可复制')
      setTimeout(() => setCopyMessage(null), 3000)
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
      return
    }

    navigator.clipboard
      .writeText(text)
      .then(() => {
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
        notification.success(`${contentType}已复制到剪贴板`)
      })
      .catch(() => {
        notification.error('复制失败，请重试')
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
        setCopyMessage(`${contentType}已复制到剪贴板`)
        setTimeout(() => setCopyMessage(null), 3000)
      })
      .catch(() => {
        setCopyMessage('复制失败，请重试')
        setTimeout(() => setCopyMessage(null), 3000)
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
      })
  }

  // 统计卡片渲染
  const renderStatsCards = () =>
    isMobile ? (
      <Grid container spacing={2} className="flex-shrink-0 mb-2">
        <Grid item xs={6}>
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography
                color="textSecondary"
                variant={isSmall ? 'caption' : 'body2'}
                className="mb-1"
              >
                总执行次数
              </Typography>
              <Typography variant={isSmall ? 'h5' : 'h4'}>{stats?.total || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6}>
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography
                color="textSecondary"
                variant={isSmall ? 'caption' : 'body2'}
                className="mb-1"
              >
                成功次数
              </Typography>
              <Typography variant={isSmall ? 'h5' : 'h4'} color="success.main">
                {stats?.success || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography
                color="textSecondary"
                variant={isSmall ? 'caption' : 'body2'}
                className="mb-1"
              >
                代理执行次数
              </Typography>
              <Typography variant={isSmall ? 'h6' : 'h5'} color="info.main">
                {stats?.agent_count || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography
                color="textSecondary"
                variant={isSmall ? 'caption' : 'body2'}
                className="mb-1"
              >
                失败次数
              </Typography>
              <Typography variant={isSmall ? 'h6' : 'h5'} color="error.main">
                {stats?.failed || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography
                color="textSecondary"
                variant={isSmall ? 'caption' : 'body2'}
                className="mb-1"
              >
                沙盒执行成功率
              </Typography>
              <Typography variant={isSmall ? 'h6' : 'h5'}>{stats?.success_rate || 0}%</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    ) : (
      <Stack direction="row" spacing={2} className="flex-shrink-0" sx={{ width: '100%' }}>
        <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              总执行次数
            </Typography>
            <Typography variant="h4">{stats?.total || 0}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              成功次数
            </Typography>
            <Typography variant="h4" color="success.main">
              {stats?.success || 0}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              代理执行次数
            </Typography>
            <Typography variant="h4" color="info.main">
              {stats?.agent_count || 0}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              失败次数
            </Typography>
            <Typography variant="h4" color="error.main">
              {stats?.failed || 0}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              沙盒执行成功率
            </Typography>
            <Typography variant="h4">{stats?.success_rate || 0}%</Typography>
          </CardContent>
        </Card>
      </Stack>
    )

  return (
    <Box sx={{ ...UNIFIED_TABLE_STYLES.tableLayoutContainer, p: 2 }}>
      {/* 统计卡片 */}
      {renderStatsCards()}

      {/* 日志表格 */}
      <Paper sx={UNIFIED_TABLE_STYLES.tableContentContainer}>
        <TableContainer sx={UNIFIED_TABLE_STYLES.tableViewport}>
          <Table stickyHeader size={isSmall ? 'small' : 'medium'}>
            <TableHead>
              <TableRow>
                <TableCell
                  padding="checkbox"
                  sx={{
                    width: isMobile ? '28px' : '48px',
                    py: isSmall ? 1 : 1.5,
                    minWidth: isMobile ? '28px' : '48px',
                    maxWidth: isMobile ? '28px' : '48px',
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                />
                <TableCell
                  sx={{
                    width: '8%',
                    minWidth: '60px',
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  状态
                </TableCell>
                <TableCell
                  sx={{
                    width: '8%',
                    minWidth: '60px',
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  停止类型
                </TableCell>
                {!isMobile && (
                  <TableCell
                    sx={{
                      width: '12%',
                      minWidth: '120px',
                      py: isSmall ? 1 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                    }}
                  >
                    触发用户
                  </TableCell>
                )}
                <TableCell
                  sx={{
                    width: isMobile ? '15%' : '15%',
                    minWidth: isMobile ? '90px' : '150px',
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
<<<<<<< HEAD
                  聊天标识
=======
<<<<<<< HEAD
                  聊天标识
=======
<<<<<<< HEAD
                  聊天标识
=======
                  会话标识
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
                </TableCell>
                <TableCell
                  sx={{
                    width: isMobile ? '23%' : '22%',
                    minWidth: isMobile ? '120px' : '180px',
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  使用模型
                </TableCell>
                <TableCell
                  sx={{
                    width: isMobile ? '23%' : '150px',
                    textAlign: 'left',
                    py: isSmall ? 1 : 1.5,
                    minWidth: isMobile ? '110px' : '150px',
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {isMobile ? '耗时(生成|执行)' : '生成耗时 | 执行耗时'}
                </TableCell>
                <TableCell
                  sx={{
                    width: '8%',
                    minWidth: '60px',
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  模式
                </TableCell>
                <TableCell
                  sx={{
                    width: isMobile ? '12%' : '15%',
                    minWidth: isMobile ? '70px' : '120px',
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  执行时间
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading && !isPlaceholderData ? (
                <TableRow>
                  <TableCell colSpan={isMobile ? 8 : 9} className="text-center py-3">
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : (
                logs?.items.map(log => {
                  let extraData: SandboxCodeExtData | null = null
                  if (log.extra_data) {
                    try {
                      extraData = JSON.parse(log.extra_data)
                    } catch (e) {
                      console.error('Failed to parse extra_data', e)
                    }
                  }

                  const isStream = extraData?.stream_mode ?? false

                  // Get performance colors
                  const firstTokenColor = getPerformanceColor(
                    extraData?.first_token_cost_ms,
                    { error: 60000, warning: 10000 },
                    'lowerIsBetter'
                  )
                  const tokensPerSecondColor = getPerformanceColor(
                    extraData?.speed_tokens_per_second,
                    { error: 5, warning: 20 },
                    'higherIsBetter'
                  )
                  const charsPerSecondColor = getPerformanceColor(
                    extraData?.speed_chars_per_second,
                    { error: 10, warning: 40 },
                    'higherIsBetter'
                  )

                  const performanceTooltip = (
                    <Box sx={{ p: 1, maxWidth: 420 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        性能详情
                      </Typography>
                      <Grid container spacing={1}>
                        <Grid item xs={6}>
                          <Typography variant="body2">首 Token 耗时:</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color={firstTokenColor}>
                            {isStream
                              ? extraData
                                ? `${extraData.first_token_cost_ms}ms`
                                : 'N/A'
                              : '不支持'}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2">速度 (Token/s):</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color={tokensPerSecondColor}>
                            {extraData && extraData.speed_tokens_per_second > 0
                              ? extraData.speed_tokens_per_second.toFixed(2)
                              : 'N/A'}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2">速度 (字符/s):</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color={charsPerSecondColor}>
                            {extraData?.speed_chars_per_second &&
                            extraData.speed_chars_per_second > 0
                              ? extraData.speed_chars_per_second
                              : 'N/A'}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2">Token 数 (输入/输出/总和):</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            {extraData && extraData.token_consumption > 0 ? (
                              <>
                                {`${formatNumber(extraData.token_input)} / ${formatNumber(
                                  extraData.token_output
                                )} / `}
                                <Typography
                                  component="span"
                                  color="success.main"
                                  sx={{ fontWeight: 'bold' }}
                                >
                                  {formatNumber(extraData.token_consumption)}
                                </Typography>
                              </>
                            ) : (
                              'N/A'
                            )}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2">字符数 (输入/输出/总和):</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            {extraData && extraData.chars_count_total > 0 ? (
                              <>
                                {`${formatNumber(extraData.chars_count_input)} / ${formatNumber(
                                  extraData.chars_count_output
                                )} / `}
                                <Typography
                                  component="span"
                                  color="success.main"
                                  sx={{ fontWeight: 'bold' }}
                                >
                                  {formatNumber(extraData.chars_count_total)}
                                </Typography>
                              </>
                            ) : (
                              'N/A'
                            )}
                          </Typography>
                        </Grid>
                      </Grid>
                    </Box>
                  )

                  return (
                    <React.Fragment key={log.id}>
                      <TableRow
                        hover
                        onClick={() => toggleRow(log.id)}
                        sx={{
                          cursor: 'pointer',
                          minHeight: isMobile ? '60px' : 'inherit',
                          '& > td': isMobile
                            ? {
                                verticalAlign: 'top',
                                paddingTop: isSmall ? '8px' : '12px',
                              }
                            : {},
                          ...(UNIFIED_TABLE_STYLES.row as SxProps<Theme>),
                        }}
                      >
                        <TableCell
                          padding="checkbox"
                          sx={{
                            py: isSmall ? 0.75 : 1.5,
                            width: isMobile ? '28px' : '48px',
                            minWidth: isMobile ? '28px' : '48px',
                            maxWidth: isMobile ? '28px' : '48px',
                            ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                          }}
                        >
                          <IconButton
                            size="small"
                            onClick={e => {
                              e.stopPropagation() // 防止事件冒泡触发行点击
                              toggleRow(log.id)
                            }}
                          >
                            {expandedRows[log.id] ? (
                              <KeyboardArrowUpIcon fontSize={isSmall ? 'small' : 'medium'} />
                            ) : (
                              <KeyboardArrowDownIcon fontSize={isSmall ? 'small' : 'medium'} />
                            )}
                          </IconButton>
                        </TableCell>
                        <TableCell
                          sx={{
                            py: isSmall ? 0.75 : 1.5,
                            ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                          }}
                        >
                          <Tooltip title={log.success ? '执行成功' : '执行失败'}>
                            <Chip
                              icon={
                                log.success ? (
                                  <CheckCircleIcon fontSize={isSmall ? 'small' : 'medium'} />
                                ) : (
                                  <ErrorIcon fontSize={isSmall ? 'small' : 'medium'} />
                                )
                              }
                              label={log.success ? '成功' : '失败'}
                              color={log.success ? 'success' : 'error'}
                              size="small"
                              sx={CHIP_VARIANTS.base(isSmall)}
                            />
                          </Tooltip>
                        </TableCell>
                        <TableCell
                          sx={{
                            py: isSmall ? 0.75 : 1.5,
                            ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                          }}
                        >
                          <Chip
                            label={getStopTypeText(log.stop_type)}
                            color={getStopTypeColor(log.stop_type)}
                            size="small"
                            sx={CHIP_VARIANTS.getStopTypeChip(log.stop_type, isSmall)}
                          />
                        </TableCell>
                        {!isMobile && (
                          <TableCell
                            sx={{
                              py: isSmall ? 0.75 : 1.5,
                              fontSize: isSmall ? '0.75rem' : 'inherit',
                              ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                            }}
                          >
                            {log.trigger_user_name}
                          </TableCell>
                        )}
                        <TableCell
                          sx={{
                            py: isSmall ? 0.75 : 1.5,
                            ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                          }}
                        >
                          <Typography
                            variant="body2"
                            sx={{
                              fontFamily: 'monospace',
                              fontSize: isSmall ? '0.65rem' : '0.75rem',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                          >
                            {log.chat_key}
                          </Typography>
                        </TableCell>
                        <TableCell
                          sx={{
                            py: isSmall ? 0.75 : 1.5,
                            height: isMobile ? 'auto' : 'inherit',
                            minHeight: isMobile ? '48px' : 'inherit',
                            ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                          }}
                        >
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: isSmall ? '0.7rem' : '0.875rem',
                              overflow: 'hidden',
                              textOverflow: isMobile ? 'clip' : 'ellipsis',
                              whiteSpace: isMobile ? 'normal' : 'nowrap',
                              wordBreak: isMobile ? 'break-word' : 'normal',
                              maxWidth: '100%',
                              fontFamily: 'monospace',
                              lineHeight: isMobile ? 1.2 : 'normal',
                              display: '-webkit-box',
                              WebkitLineClamp: isMobile ? 3 : 1,
                              WebkitBoxOrient: 'vertical',
                              pr: isMobile ? 0.5 : 0,
                            }}
                          >
                            {log.use_model || '未知'}
                          </Typography>
                        </TableCell>
                        <TableCell
                          sx={{
                            py: isSmall ? 0.75 : 1.5,
                            ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                          }}
                        >
                          <Stack
                            direction="row"
                            alignItems="center"
                            spacing={isMobile ? 0.5 : 1}
                            sx={{
                              '& > *:first-of-type': {
                                width: isMobile ? '35px' : '50px',
                                textAlign: 'right',
                                fontSize: isMobile ? '0.65rem' : isSmall ? '0.7rem' : '0.875rem',
                              },
                              '& > *:last-of-type': {
                                width: isMobile ? '35px' : '50px',
                                fontSize: isMobile ? '0.65rem' : isSmall ? '0.7rem' : '0.875rem',
                              },
                            }}
                          >
                            <Tooltip title="生成耗时">
                              <Typography
                                variant="body2"
                                sx={{
                                  color:
                                    log.generation_time_ms > 30000 ? 'warning.main' : 'info.main',
                                  fontSize: 'inherit',
                                }}
                              >
                                {(log.generation_time_ms / 1000).toFixed(isMobile ? 1 : 2)}s
                              </Typography>
                            </Tooltip>
                            <Typography
                              variant="body2"
                              color="textSecondary"
                              sx={{
                                px: isMobile ? 0.5 : 1,
                                fontSize: 'inherit',
                              }}
                            >
                              |
                            </Typography>
                            <Tooltip title="执行耗时">
                              <Typography
                                variant="body2"
                                sx={{
                                  color: log.exec_time_ms > 10000 ? 'warning.main' : 'success.main',
                                  fontSize: 'inherit',
                                }}
                              >
                                {isMobile && log.exec_time_ms > 1000
                                  ? `${(log.exec_time_ms / 1000).toFixed(1)}s`
                                  : `${log.exec_time_ms}ms`}
                              </Typography>
                            </Tooltip>
                          </Stack>
                        </TableCell>
                        <TableCell
                          sx={{
                            py: isSmall ? 0.75 : 1.5,
                            ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                          }}
                        >
                          {extraData ? (
                            <Tooltip title={performanceTooltip}>
                              <Chip
                                label={isStream ? '流式' : '非流式'}
                                size="small"
                                sx={CHIP_VARIANTS.getStreamModeChip(isStream, isSmall)}
                              />
                            </Tooltip>
                          ) : (
                            <Chip
                              label="未知"
                              size="small"
                              sx={CHIP_VARIANTS.getStopTypeChip(-1, isSmall)}
                            />
                          )}
                        </TableCell>
                        <TableCell
                          sx={{
                            py: isSmall ? 0.75 : 1.5,
                            fontSize: isSmall ? '0.7rem' : '0.875rem',
                            ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                          }}
                        >
                          {isMobile ? log.create_time.split(' ')[1] : log.create_time}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell
                          style={{ paddingBottom: 0, paddingTop: 0 }}
                          colSpan={isMobile ? 8 : 9}
                        >
                          <Collapse in={expandedRows[log.id]} timeout="auto" unmountOnExit>
                            <Box
                              sx={{
                                py: 2,
                                px: isMobile ? 2 : 3,
                                maxWidth: '100%',
                                overflow: 'hidden',
                              }}
                            >
                              {/* 思维链信息 */}
                              {log.thought_chain && (
                                <Box
                                  sx={{
                                    ...sharedContentStyles,
                                    mb: 3,
                                  }}
                                >
                                  <Stack
                                    direction="row"
                                    spacing={1}
                                    alignItems="center"
                                    sx={{ mb: 1, justifyContent: 'space-between' }}
                                  >
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                      <PsychologyIcon
                                        color="info"
                                        fontSize={isSmall ? 'small' : 'medium'}
                                      />
                                      <Typography variant={isSmall ? 'subtitle2' : 'subtitle1'}>
                                        思维链信息：
                                      </Typography>
                                    </Box>
                                    <Tooltip title="复制思维链">
                                      <IconButton
                                        size="small"
                                        onClick={() => copyToClipboard(log.thought_chain, '思维链')}
                                      >
                                        <ContentCopyIcon fontSize="small" />
                                      </IconButton>
                                    </Tooltip>
                                  </Stack>
                                  <Paper
                                    variant="outlined"
                                    sx={{
                                      width: '100%',
                                      overflow: 'hidden',
                                      bgcolor: 'background.paper',
                                    }}
                                  >
                                    <Box
                                      sx={{
                                        ...scrollableContentStyles,
                                        p: isSmall ? 1.5 : 2,
                                        maxHeight: isSmall ? '200px' : '300px',
                                      }}
                                    >
                                      <pre
                                        style={{
                                          margin: 0,
                                          whiteSpace: 'pre-wrap',
                                          wordBreak: 'break-word',
                                          overflowWrap: 'break-word',
                                          color: theme.palette.text.primary,
                                          maxWidth: '100%',
                                          fontSize: isSmall ? '0.75rem' : '0.875rem',
                                        }}
                                      >
                                        {log.thought_chain}
                                      </pre>
                                    </Box>
                                  </Paper>
                                </Box>
                              )}

                              {/* 执行代码 */}
                              <Box className="mb-3 max-w-full overflow-hidden">
                                <Stack
                                  direction="row"
                                  spacing={1}
                                  alignItems="center"
                                  className="mb-1"
                                  sx={{
                                    justifyContent: 'space-between',
                                    flexWrap: 'wrap',
                                  }}
                                >
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CodeIcon
                                      color="info"
                                      fontSize={isSmall ? 'small' : 'medium'}
                                    />
                                    <Typography variant={isSmall ? 'subtitle2' : 'subtitle1'}>
                                      执行代码：
                                    </Typography>
                                  </Box>
                                  <Tooltip title="复制代码">
                                    <IconButton
                                      size="small"
                                      onClick={() => copyToClipboard(log.code_text, '代码')}
                                    >
                                      <ContentCopyIcon fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                </Stack>
                                <Paper variant="outlined" className="overflow-hidden w-full">
                                  <Box
                                    className="w-full overflow-auto"
                                    sx={{
                                      maxHeight: isSmall ? '300px' : '400px',
                                      '&::-webkit-scrollbar': {
                                        width: '6px',
                                        height: '6px',
                                      },
                                      '&::-webkit-scrollbar-thumb': {
                                        backgroundColor:
                                          theme.palette.mode === 'dark'
                                            ? 'rgba(255, 235, 235, 0.16)'
                                            : 'rgba(0, 0, 0, 0.2)',
                                        borderRadius: '3px',
                                      },
                                    }}
                                  >
                                    <SyntaxHighlighter
                                      language="python"
                                      style={mode === 'dark' ? vscDarkPlus : oneLight}
                                      showLineNumbers={true}
                                      customStyle={{
                                        margin: 0,
                                        padding: isSmall ? '12px' : '16px',
                                        maxHeight: 'none',
                                        fontSize: isSmall ? '12px' : '14px',
                                        background: 'inherit',
                                        width: '100%',
                                        tableLayout: 'fixed',
                                        display: 'table',
                                      }}
                                      wrapLines={true}
                                      wrapLongLines={true}
                                      lineNumberStyle={{
                                        minWidth: '3em',
                                        width: '3em',
                                        textAlign: 'right',
                                        paddingRight: '0.5em',
                                        userSelect: 'none',
                                        display: 'table-cell',
                                        borderRight: `1px solid ${theme.palette.divider}`,
                                        color: theme.palette.text.secondary,
                                      }}
                                      lineProps={() => ({
                                        style: {
                                          display: 'table-row',
                                        },
                                      })}
                                      codeTagProps={{
                                        style: {
                                          display: 'table-cell',
                                          paddingLeft: '0.5em',
                                          whiteSpace: 'pre-wrap',
                                          wordBreak: 'break-word',
                                          width: '100%',
                                          overflow: 'hidden',
                                        },
                                      }}
                                    >
                                      {log.code_text}
                                    </SyntaxHighlighter>
                                  </Box>
                                </Paper>
                              </Box>

                              {/* 执行输出 */}
                              {log.outputs && (
                                <Box>
                                  <Stack
                                    direction="row"
                                    spacing={1}
                                    alignItems="center"
                                    className="mb-1"
                                    sx={{
                                      justifyContent: 'space-between',
                                      flexWrap: 'wrap',
                                    }}
                                  >
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                      <TimerIcon
                                        color="info"
                                        fontSize={isSmall ? 'small' : 'medium'}
                                      />
                                      <Typography variant={isSmall ? 'subtitle2' : 'subtitle1'}>
                                        执行输出：
                                      </Typography>
                                    </Box>
                                    <Tooltip title="复制输出">
                                      <IconButton
                                        size="small"
                                        onClick={() => copyToClipboard(log.outputs, '执行输出')}
                                      >
                                        <ContentCopyIcon fontSize="small" />
                                      </IconButton>
                                    </Tooltip>
                                  </Stack>
                                  <Paper variant="outlined" className="overflow-hidden w-full">
                                    <Box
                                      className="w-full overflow-auto"
                                      sx={{
                                        maxHeight: isSmall ? '200px' : '300px',
                                        '&::-webkit-scrollbar': {
                                          width: '6px',
                                          height: '6px',
                                        },
                                        '&::-webkit-scrollbar-thumb': {
                                          backgroundColor:
                                            theme.palette.mode === 'dark'
                                              ? 'rgba(255, 235, 235, 0.16)'
                                              : 'rgba(0, 0, 0, 0.2)',
                                          borderRadius: '3px',
                                        },
                                      }}
                                    >
                                      <SyntaxHighlighter
                                        language="text"
                                        style={mode === 'dark' ? vscDarkPlus : oneLight}
                                        showLineNumbers={true}
                                        customStyle={{
                                          margin: 0,
                                          padding: isSmall ? '12px' : '16px',
                                          maxHeight: 'none',
                                          fontSize: isSmall ? '12px' : '14px',
                                          background: 'inherit',
                                          width: '100%',
                                          tableLayout: 'fixed',
                                          display: 'table',
                                        }}
                                        wrapLines={true}
                                        wrapLongLines={true}
                                        lineNumberStyle={{
                                          minWidth: '2em',
                                          width: '2em',
                                          textAlign: 'right',
                                          paddingRight: '0.5em',
                                          userSelect: 'none',
                                          display: 'table-cell',
                                          borderRight: `1px solid ${theme.palette.divider}`,
                                          color: theme.palette.text.secondary,
                                        }}
                                        lineProps={() => ({
                                          style: {
                                            display: 'table-row',
                                          },
                                        })}
                                        codeTagProps={{
                                          style: {
                                            display: 'table-cell',
                                            paddingLeft: '0.5em',
                                            whiteSpace: 'pre-wrap',
                                            wordBreak: 'break-word',
                                            width: '100%',
                                            overflow: 'hidden',
                                          },
                                        }}
                                      >
                                        {log.outputs}
                                      </SyntaxHighlighter>
                                    </Box>
                                  </Paper>
                                </Box>
                              )}

                              {/* 性能信息 */}
                              {extraData && (
                                <Box className="mt-3 max-w-full overflow-hidden">
                                  <Stack
                                    direction="row"
                                    spacing={1}
                                    alignItems="center"
                                    className="mb-1"
                                  >
                                    <SpeedIcon
                                      color="info"
                                      fontSize={isSmall ? 'small' : 'medium'}
                                    />
                                    <Typography variant={isSmall ? 'subtitle2' : 'subtitle1'}>
                                      性能信息：
                                    </Typography>
                                  </Stack>
                                  <Paper variant="outlined" className="overflow-hidden w-full">
                                    <Box sx={{ p: isSmall ? 1.5 : 2 }}>
                                      <Grid container spacing={2}>
                                        <Grid item xs={12} sm={6} md={4}>
                                          <Stack direction="row" alignItems="center" spacing={1}>
                                            <AccessTimeIcon fontSize="small" color="secondary" />
                                            <Typography variant="body2">
                                              首 Token 耗时:
                                              <Typography
                                                component="span"
                                                color={firstTokenColor}
                                                sx={{ ml: 1 }}
                                              >
                                                {extraData?.stream_mode
                                                  ? `${extraData.first_token_cost_ms}ms`
                                                  : '不支持'}
                                              </Typography>
                                            </Typography>
                                          </Stack>
                                        </Grid>
                                        <Grid item xs={12} sm={6} md={4}>
                                          <Stack direction="row" alignItems="center" spacing={1}>
                                            <BoltIcon fontSize="small" color="secondary" />
                                            <Typography variant="body2">
                                              速度 (Token/s):
                                              <Typography
                                                component="span"
                                                color={tokensPerSecondColor}
                                                sx={{ ml: 1 }}
                                              >
                                                {extraData && extraData.speed_tokens_per_second > 0
                                                  ? extraData.speed_tokens_per_second.toFixed(2)
                                                  : 'N/A'}
                                              </Typography>
                                            </Typography>
                                          </Stack>
                                        </Grid>
                                        <Grid item xs={12} sm={6} md={4}>
                                          <Stack direction="row" alignItems="center" spacing={1}>
                                            <KeyboardDoubleArrowRightIcon
                                              fontSize="small"
                                              color="secondary"
                                            />
                                            <Typography variant="body2">
                                              速度 (字符/s):
                                              <Typography
                                                component="span"
                                                color={charsPerSecondColor}
                                                sx={{ ml: 1 }}
                                              >
                                                {extraData?.speed_chars_per_second &&
                                                extraData.speed_chars_per_second > 0
                                                  ? extraData.speed_chars_per_second
                                                  : 'N/A'}
                                              </Typography>
                                            </Typography>
                                          </Stack>
                                        </Grid>
                                        <Grid item xs={12} sm={6} md={4}>
                                          <Stack direction="row" alignItems="center" spacing={1}>
                                            <FunctionsIcon fontSize="small" color="secondary" />
                                            <Typography variant="body2">
                                              Token 数 (输入/输出/总和):
                                              <Typography
                                                component="span"
                                                color="text.secondary"
                                                sx={{ ml: 1 }}
                                              >
                                                {extraData && extraData.token_consumption > 0 ? (
                                                  <>
                                                    {`${formatNumber(
                                                      extraData.token_input
                                                    )} / ${formatNumber(
                                                      extraData.token_output
                                                    )} / `}
                                                    <Typography
                                                      component="span"
                                                      color="success.main"
                                                      sx={{ fontWeight: 'bold' }}
                                                    >
                                                      {formatNumber(extraData.token_consumption)}
                                                    </Typography>
                                                  </>
                                                ) : (
                                                  'N/A'
                                                )}
                                              </Typography>
                                            </Typography>
                                          </Stack>
                                        </Grid>
                                        <Grid item xs={12} sm={6} md={4}>
                                          <Stack direction="row" alignItems="center" spacing={1}>
                                            <AbcIcon fontSize="small" color="secondary" />
                                            <Typography variant="body2">
                                              字符数 (输入/输出/总和):
                                              <Typography
                                                component="span"
                                                color="text.secondary"
                                                sx={{ ml: 1 }}
                                              >
                                                {extraData && extraData.chars_count_total > 0 ? (
                                                  <>
                                                    {`${formatNumber(
                                                      extraData.chars_count_input
                                                    )} / ${formatNumber(
                                                      extraData.chars_count_output
                                                    )} / `}
                                                    <Typography
                                                      component="span"
                                                      color="success.main"
                                                      sx={{ fontWeight: 'bold' }}
                                                    >
                                                      {formatNumber(extraData.chars_count_total)}
                                                    </Typography>
                                                  </>
                                                ) : (
                                                  'N/A'
                                                )}
                                              </Typography>
                                            </Typography>
                                          </Stack>
                                        </Grid>
                                      </Grid>
                                    </Box>
                                  </Paper>
                                </Box>
                              )}

                              {/* 开发者工具 */}
                              {devMode && extraData?.log_path && (
                                <Box sx={{ my: 2 }}>
                                  <Button
                                    variant="outlined"
                                    color="secondary"
                                    size="small"
                                    startIcon={<VisibilityIcon />}
                                    onClick={e => {
                                      e.stopPropagation()
                                      setSelectedLogPath(extraData?.log_path || null)
                                      setLogViewerOpen(true)
                                    }}
                                  >
                                    查看详细请求日志
                                  </Button>
                                </Box>
                              )}
                            </Box>
                          </Collapse>
                        </TableCell>
                      </TableRow>
                    </React.Fragment>
                  )
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePaginationStyled
          rowsPerPageOptions={[10, 25, 50]}
          component="div"
          count={logs?.total || 0}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          loading={isLoading}
          showFirstLastPageButtons={true}
        />
      </Paper>

      {/* 日志内容查看器 */}
      {selectedLogPath && (
        <LogContentDialog
          open={logViewerOpen}
          onClose={() => {
            setLogViewerOpen(false)
            setSelectedLogPath(null)
          }}
          logPath={selectedLogPath}
        />
      )}
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======

      {/* 复制成功提示 */}
      <Snackbar
        open={!!copyMessage}
        autoHideDuration={3000}
        onClose={() => setCopyMessage(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setCopyMessage(null)}
          severity="success"
          variant="filled"
          sx={{ width: '100%' }}
        >
          {copyMessage}
        </Alert>
      </Snackbar>
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
    </Box>
  )
}
