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
} from '@mui/material'
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Timer as TimerIcon,
  Psychology as PsychologyIcon,
  Code as CodeIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
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

  return (
    <Box className="h-[calc(100vh-90px)] flex flex-col gap-3 overflow-hidden p-2">
      {/* 统计卡片 */}
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

      {/* 日志表格 */}
      <Paper className="flex-1 flex flex-col overflow-hidden">
        <TableContainer className="flex-1 overflow-auto">
          <Table stickyHeader sx={{ tableLayout: 'fixed', minWidth: '900px' }}>
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox" sx={{ width: '48px' }} />
                <TableCell sx={{ width: '10%', minWidth: '100px' }}>状态</TableCell>
                <TableCell sx={{ width: '10%', minWidth: '100px' }}>停止类型</TableCell>
                <TableCell sx={{ width: '12%', minWidth: '120px' }}>触发用户</TableCell>
                <TableCell sx={{ width: '15%', minWidth: '160px' }}>会话标识</TableCell>
                <TableCell sx={{ width: '16%', minWidth: '100px' }}>使用模型</TableCell>
                <TableCell sx={{ width: '160px', textAlign: 'left' }}>
                  生成耗时 | 执行耗时
                </TableCell>
                <TableCell sx={{ width: '20%', minWidth: '150px' }}>执行时间</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading && !isPlaceholderData ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-3">
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : (
                logs?.items.map(log => (
                  <React.Fragment key={log.id}>
                    <TableRow hover>
                      <TableCell padding="checkbox">
                        <IconButton size="small" onClick={() => toggleRow(log.id)}>
                          {expandedRows[log.id] ? (
                            <KeyboardArrowUpIcon />
                          ) : (
                            <KeyboardArrowDownIcon />
                          )}
                        </IconButton>
                      </TableCell>
                      <TableCell>
                        <Tooltip title={log.success ? '执行成功' : '执行失败'}>
                          <Chip
                            icon={log.success ? <CheckCircleIcon /> : <ErrorIcon />}
                            label={log.success ? '成功' : '失败'}
                            color={log.success ? 'success' : 'error'}
                            size="small"
                          />
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getStopTypeText(log.stop_type)}
                          color={getStopTypeColor(log.stop_type)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{log.trigger_user_name}</TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {log.chat_key}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{log.use_model || '未知'}</Typography>
                      </TableCell>
                      <TableCell>
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
                              }}
                            >
                              {(log.generation_time_ms / 1000).toFixed(2)}s
                            </Typography>
                          </Tooltip>
                          <Typography variant="body2" color="textSecondary" sx={{ px: 1 }}>
                            |
                          </Typography>
                          <Tooltip title="执行耗时">
                            <Typography
                              variant="body2"
                              sx={{
                                color: log.exec_time_ms > 10000 ? 'warning.main' : 'success.main',
                              }}
                            >
                              {log.exec_time_ms}ms
                            </Typography>
                          </Tooltip>
                        </Stack>
                      </TableCell>
                      <TableCell>{log.create_time}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={8}>
                        <Collapse in={expandedRows[log.id]} timeout="auto" unmountOnExit>
                          <Box
                            sx={{
                              py: 2,
                              px: 3,
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
                                }}
                              >
                                <Stack
                                  direction="row"
                                  spacing={1}
                                  alignItems="center"
                                  sx={{ mb: 1 }}
                                >
                                  <PsychologyIcon color="info" />
                                  <Typography variant="subtitle1">思维链信息：</Typography>
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
                                      p: 2,
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
                              >
                                <CodeIcon color="info" />
                                <Typography variant="subtitle1">执行代码：</Typography>
                              </Stack>
                              <Paper variant="outlined" className="overflow-hidden w-full">
                                <Box className="w-full overflow-auto">
                                  <SyntaxHighlighter
                                    language="python"
                                    style={mode === 'dark' ? vscDarkPlus : oneLight}
                                    showLineNumbers={true}
                                    customStyle={{
                                      margin: 0,
                                      padding: '16px',
                                      maxHeight: '400px',
                                      fontSize: '14px',
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
                                >
                                  <TimerIcon color="info" />
                                  <Typography variant="subtitle1">执行输出：</Typography>
                                </Stack>
                                <Paper variant="outlined" className="overflow-hidden w-full">
                                  <Box className="w-full overflow-auto">
                                    <SyntaxHighlighter
                                      language="text"
                                      style={mode === 'dark' ? vscDarkPlus : oneLight}
                                      customStyle={{
                                        margin: 0,
                                        padding: '16px',
                                        maxHeight: '300px',
                                        fontSize: '14px',
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
          labelRowsPerPage="每页行数"
        />
      </Paper>
    </Box>
  )
}
