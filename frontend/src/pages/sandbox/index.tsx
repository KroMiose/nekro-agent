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
  TablePagination,
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
  Snackbar,
  Alert,
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
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { sandboxApi } from '../../services/api/sandbox'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useColorMode } from '../../stores/theme'
import { getStopTypeColor, getStopTypeText } from '../../theme/utils'

export default function SandboxPage() {
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({})
  const { mode } = useColorMode()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const [copyMessage, setCopyMessage] = useState<string | null>(null)

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
      setCopyMessage('无内容可复制～');
      setTimeout(() => setCopyMessage(null), 3000);
      return;
    }
    
    navigator.clipboard.writeText(text)
      .then(() => {
        setCopyMessage(`${contentType}已复制到剪贴板喵～`);
        setTimeout(() => setCopyMessage(null), 3000);
      })
      .catch(() => {
        setCopyMessage('复制失败，请重试～');
        setTimeout(() => setCopyMessage(null), 3000);
      });
  };

  // 统计卡片渲染
  const renderStatsCards = () => (
    isMobile ? (
      <Grid container spacing={2} className="flex-shrink-0 mb-2">
        <Grid item xs={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography color="textSecondary" variant={isSmall ? "caption" : "body2"} className="mb-1">
                总执行次数
              </Typography>
              <Typography variant={isSmall ? "h5" : "h4"}>{stats?.total || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography color="textSecondary" variant={isSmall ? "caption" : "body2"} className="mb-1">
                成功次数
              </Typography>
              <Typography variant={isSmall ? "h5" : "h4"} color="success.main">
                {stats?.success || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography color="textSecondary" variant={isSmall ? "caption" : "body2"} className="mb-1">
                代理执行次数
              </Typography>
              <Typography variant={isSmall ? "h6" : "h5"} color="info.main">
                {stats?.agent_count || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography color="textSecondary" variant={isSmall ? "caption" : "body2"} className="mb-1">
                失败次数
              </Typography>
              <Typography variant={isSmall ? "h6" : "h5"} color="error.main">
                {stats?.failed || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              <Typography color="textSecondary" variant={isSmall ? "caption" : "body2"} className="mb-1">
                成功率
              </Typography>
              <Typography variant={isSmall ? "h6" : "h5"}>
                {stats?.success_rate || 0}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    ) : (
      <Stack direction="row" spacing={2} className="flex-shrink-0">
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              总执行次数
            </Typography>
            <Typography variant="h4">{stats?.total || 0}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              成功次数
            </Typography>
            <Typography variant="h4" color="success.main">
              {stats?.success || 0}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              代理执行次数
            </Typography>
            <Typography variant="h4" color="info.main">
              {stats?.agent_count || 0}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              失败次数
            </Typography>
            <Typography variant="h4" color="error.main">
              {stats?.failed || 0}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" className="mb-1">
              成功率
            </Typography>
            <Typography variant="h4">{stats?.success_rate || 0}%</Typography>
          </CardContent>
        </Card>
      </Stack>
    )
  );

  return (
    <Box className="h-[calc(100vh-90px)] flex flex-col gap-3 overflow-hidden p-2">
      {/* 统计卡片 */}
      {renderStatsCards()}

      {/* 日志表格 */}
      <Paper className="flex-1 flex flex-col overflow-hidden">
        <TableContainer className="flex-1 overflow-auto">
          <Table stickyHeader sx={{ tableLayout: 'fixed', minWidth: isMobile ? '600px' : '900px' }}>
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox" sx={{ 
                  width: isMobile ? '28px' : '48px', 
                  py: isSmall ? 1 : 1.5,
                  minWidth: isMobile ? '28px' : '48px',
                  maxWidth: isMobile ? '28px' : '48px'
                }} />
                <TableCell sx={{ 
                  width: isMobile ? '15%' : '10%', 
                  minWidth: isMobile ? '80px' : '100px', 
                  py: isSmall ? 1 : 1.5 
                }}>状态</TableCell>
                <TableCell sx={{ 
                  width: isMobile ? '18%' : '10%', 
                  minWidth: isMobile ? '90px' : '100px', 
                  py: isSmall ? 1 : 1.5 
                }}>停止类型</TableCell>
                {!isMobile && (
                  <TableCell sx={{ width: '12%', minWidth: '120px', py: isSmall ? 1 : 1.5 }}>触发用户</TableCell>
                )}
                <TableCell sx={{ width: isMobile ? '20%' : '15%', minWidth: isMobile ? '100px' : '160px', py: isSmall ? 1 : 1.5 }}>会话标识</TableCell>
                <TableCell sx={{ width: isMobile ? '20%' : '16%', minWidth: isMobile ? '80px' : '100px', py: isSmall ? 1 : 1.5 }}>使用模型</TableCell>
                {!isSmall && (
                  <TableCell sx={{ width: '160px', textAlign: 'left', py: isSmall ? 1 : 1.5 }}>
                    生成耗时 | 执行耗时
                  </TableCell>
                )}
                <TableCell sx={{ width: isMobile ? '20%' : '20%', minWidth: isMobile ? '90px' : '150px', py: isSmall ? 1 : 1.5 }}>执行时间</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading && !isPlaceholderData ? (
                <TableRow>
                  <TableCell colSpan={isMobile ? (isSmall ? 6 : 7) : 8} className="text-center py-3">
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : (
                logs?.items.map(log => (
                  <React.Fragment key={log.id}>
                    <TableRow 
                      hover
                      onClick={() => toggleRow(log.id)}
                      sx={{ 
                        cursor: 'pointer',
                        '&:hover': {
                          backgroundColor: theme => theme.palette.action.hover,
                        }
                      }}
                    >
                      <TableCell padding="checkbox" sx={{ 
                        py: isSmall ? 0.75 : 1.5,
                        width: isMobile ? '28px' : '48px', 
                        minWidth: isMobile ? '28px' : '48px',
                        maxWidth: isMobile ? '28px' : '48px'
                      }}>
                        <IconButton 
                          size="small" 
                          onClick={(e) => {
                            e.stopPropagation(); // 防止事件冒泡触发行点击
                            toggleRow(log.id);
                          }}
                        >
                          {expandedRows[log.id] ? (
                            <KeyboardArrowUpIcon fontSize={isSmall ? "small" : "medium"} />
                          ) : (
                            <KeyboardArrowDownIcon fontSize={isSmall ? "small" : "medium"} />
                          )}
                        </IconButton>
                      </TableCell>
                      <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
                        <Tooltip title={log.success ? '执行成功' : '执行失败'}>
                          <Chip
                            icon={log.success ? <CheckCircleIcon fontSize={isSmall ? "small" : "medium"} /> : <ErrorIcon fontSize={isSmall ? "small" : "medium"} />}
                            label={log.success ? '成功' : '失败'}
                            color={log.success ? 'success' : 'error'}
                            size="small"
                            sx={{ 
                              height: isSmall ? 20 : 24,
                              fontSize: isSmall ? '0.65rem' : '0.75rem',
                              '& .MuiChip-label': {
                                px: isSmall ? 0.5 : 0.75,
                              }
                            }}
                          />
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
                        <Chip
                          label={getStopTypeText(log.stop_type)}
                          color={getStopTypeColor(log.stop_type)}
                          size="small"
                          sx={{ 
                            height: isSmall ? 20 : 24,
                            fontSize: isSmall ? '0.65rem' : '0.75rem',
                            '& .MuiChip-label': {
                              px: isSmall ? 0.5 : 0.75,
                            }
                          }}
                        />
                      </TableCell>
                      {!isMobile && (
                        <TableCell sx={{ py: isSmall ? 0.75 : 1.5, fontSize: isSmall ? '0.75rem' : 'inherit' }}>{log.trigger_user_name}</TableCell>
                      )}
                      <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontFamily: 'monospace',
                            fontSize: isSmall ? '0.65rem' : '0.75rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}
                        >
                          {log.chat_key}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontSize: isSmall ? '0.7rem' : '0.875rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}
                        >
                          {log.use_model || '未知'}
                        </Typography>
                      </TableCell>
                      {!isSmall && (
                        <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
                          <Stack
                            direction="row"
                            alignItems="center"
                            sx={{
                              '& > *:first-of-type': { width: '50px', textAlign: 'right' },
                              '& > *:last-of-type': { width: '50px' },
                            }}
                          >
                            <Tooltip title="生成耗时">
                              <Typography
                                variant="body2"
                                sx={{
                                  color:
                                    log.generation_time_ms > 30000 ? 'warning.main' : 'info.main',
                                  fontSize: isSmall ? '0.7rem' : '0.875rem'
                                }}
                              >
                                {(log.generation_time_ms / 1000).toFixed(2)}s
                              </Typography>
                            </Tooltip>
                            <Typography variant="body2" color="textSecondary" sx={{ px: 1, fontSize: isSmall ? '0.7rem' : '0.875rem' }}>
                              |
                            </Typography>
                            <Tooltip title="执行耗时">
                              <Typography
                                variant="body2"
                                sx={{
                                  color: log.exec_time_ms > 10000 ? 'warning.main' : 'success.main',
                                  fontSize: isSmall ? '0.7rem' : '0.875rem'
                                }}
                              >
                                {log.exec_time_ms}ms
                              </Typography>
                            </Tooltip>
                          </Stack>
                        </TableCell>
                      )}
                      <TableCell sx={{ py: isSmall ? 0.75 : 1.5, fontSize: isSmall ? '0.7rem' : '0.875rem' }}>
                        {isMobile ? log.create_time.split(' ')[1] : log.create_time}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={isMobile ? (isSmall ? 6 : 7) : 8}>
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
                                  mb: 3,
                                  maxWidth: '100%',
                                  overflow: 'hidden',
                                  position: 'relative',
                                }}
                              >
                                <Stack
                                  direction="row"
                                  spacing={1}
                                  alignItems="center"
                                  sx={{ mb: 1 }}
                                >
                                  <PsychologyIcon color="info" fontSize={isSmall ? "small" : "medium"} />
                                  <Typography variant={isSmall ? "subtitle2" : "subtitle1"}>思维链信息：</Typography>
                                  <Tooltip title="复制思维链">
                                    <IconButton 
                                      size="small" 
                                      onClick={() => copyToClipboard(log.thought_chain, '思维链')}
                                      sx={{ ml: 'auto' }}
                                    >
                                      <ContentCopyIcon fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                </Stack>
                                <Paper
                                  variant="outlined"
                                  sx={{
                                    overflow: 'hidden',
                                    bgcolor: 'background.paper',
                                    maxWidth: '100%',
                                  }}
                                >
                                  <Box
                                    sx={{
                                      p: isSmall ? 1.5 : 2,
                                      maxWidth: '100%',
                                      overflow: 'hidden',
                                      '& pre': {
                                        margin: 0,
                                        whiteSpace: 'pre-wrap',
                                        wordBreak: 'break-all',
                                        overflowWrap: 'break-word',
                                        color: mode === 'dark' ? '#D4D4D4' : 'inherit',
                                        maxWidth: '100%',
                                        overflow: 'hidden',
                                        fontSize: isSmall ? '0.75rem' : '0.875rem',
                                      },
                                    }}
                                  >
                                    <pre>{log.thought_chain}</pre>
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
                                  flexWrap: 'wrap'
                                }}
                              >
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <CodeIcon color="info" fontSize={isSmall ? "small" : "medium"} />
                                  <Typography variant={isSmall ? "subtitle2" : "subtitle1"}>执行代码：</Typography>
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
                                <Box className="w-full overflow-auto">
                                  <SyntaxHighlighter
                                    language="python"
                                    style={mode === 'dark' ? vscDarkPlus : oneLight}
                                    showLineNumbers={true}
                                    customStyle={{
                                      margin: 0,
                                      padding: isSmall ? '12px' : '16px',
                                      maxHeight: isSmall ? '300px' : '400px',
                                      fontSize: isSmall ? '12px' : '14px',
                                      background: 'inherit',
                                    }}
                                    wrapLines={true}
                                    wrapLongLines={true}
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
                                    flexWrap: 'wrap'
                                  }}
                                >
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <TimerIcon color="info" fontSize={isSmall ? "small" : "medium"} />
                                    <Typography variant={isSmall ? "subtitle2" : "subtitle1"}>执行输出：</Typography>
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
                                  <Box className="w-full overflow-auto">
                                    <SyntaxHighlighter
                                      language="text"
                                      style={mode === 'dark' ? vscDarkPlus : oneLight}
                                      customStyle={{
                                        margin: 0,
                                        padding: isSmall ? '12px' : '16px',
                                        maxHeight: isSmall ? '200px' : '300px',
                                        fontSize: isSmall ? '12px' : '14px',
                                        background: 'inherit',
                                      }}
                                      wrapLines={true}
                                      wrapLongLines={true}
                                    >
                                      {log.outputs}
                                    </SyntaxHighlighter>
                                  </Box>
                                </Paper>
                              </Box>
                            )}
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </React.Fragment>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          rowsPerPageOptions={[10, 25, 50]}
          count={logs?.total || 0}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage={isSmall ? "每页" : "每页行数"}
          labelDisplayedRows={({ from, to, count }) => 
            isSmall 
              ? `${from}-${to}/${count}`
              : `${from}-${to} / 共${count}项`
          }
        />
      </Paper>
      
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
    </Box>
  )
}
