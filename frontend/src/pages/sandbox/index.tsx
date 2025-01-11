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
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { sandboxApi } from '../../services/api/sandbox'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

export default function SandboxPage() {
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({})

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
    <Box>
      {/* 统计卡片 */}
      <Stack direction="row" spacing={3} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              总执行次数
            </Typography>
            <Typography variant="h4">{stats?.total || 0}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              成功次数
            </Typography>
            <Typography variant="h4" color="success.main">
              {stats?.success || 0}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              失败次数
            </Typography>
            <Typography variant="h4" color="error.main">
              {stats?.failed || 0}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              成功率
            </Typography>
            <Typography variant="h4">{stats?.success_rate || 0}%</Typography>
          </CardContent>
        </Card>
      </Stack>

      {/* 日志表格 */}
      <Paper elevation={3}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox" />
                <TableCell>状态</TableCell>
                <TableCell>触发用户</TableCell>
                <TableCell>会话标识</TableCell>
                <TableCell>执行时间</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading && !isPlaceholderData ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 3 }}>
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : (
                (isPlaceholderData ? logs?.items : logs?.items)?.map(log => (
                  <React.Fragment key={log.id}>
                    <TableRow hover>
                      <TableCell padding="checkbox">
                        <IconButton size="small" onClick={() => toggleRow(log.id)}>
                          {expandedRows[log.id] ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                      </TableCell>
                      <TableCell>
                        <Tooltip title={log.success ? '执行成功' : '执行失败'}>
                          <Chip
                            icon={log.success ? <CheckCircleIcon /> : <ErrorIcon />}
                            label={log.success ? '成功' : '失败'}
                            color={log.success ? 'success' : 'error'}
                            size="small"
                            variant="outlined"
                          />
                        </Tooltip>
                      </TableCell>
                      <TableCell>{log.trigger_user_name}</TableCell>
                      <TableCell>{log.chat_key}</TableCell>
                      <TableCell>{log.create_time}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell
                        style={{
                          paddingBottom: 0,
                          paddingTop: 0,
                        }}
                        colSpan={6}
                        sx={{
                          maxWidth: 0,
                          width: '100%',
                          '& pre': {
                            maxWidth: 'none !important',
                          },
                        }}
                      >
                        <Collapse in={expandedRows[log.id]} timeout="auto" unmountOnExit>
                          <Box sx={{ margin: 2 }}>
                            <Typography variant="subtitle2" gutterBottom component="div">
                              执行代码：
                            </Typography>
                            <Box>
                              <SyntaxHighlighter
                                language="python"
                                style={vscDarkPlus}
                                showLineNumbers={true}
                                customStyle={{
                                  margin: 0,
                                  borderRadius: '4px',
                                  maxHeight: '400px',
                                  fontSize: '14px',
                                  overflow: 'auto',
                                }}
                              >
                                {log.code_text}
                              </SyntaxHighlighter>
                            </Box>

                            {log.outputs && (
                              <>
                                <Typography variant="subtitle2" gutterBottom component="div">
                                  执行输出：
                                </Typography>
                                <Box>
                                  <SyntaxHighlighter
                                    language="text"
                                    style={vscDarkPlus}
                                    customStyle={{
                                      margin: 0,
                                      borderRadius: '4px',
                                      maxHeight: '300px',
                                      fontSize: '14px',
                                      backgroundColor: '#1E1E1E',
                                      overflow: 'auto',
                                    }}
                                  >
                                    {log.outputs}
                                  </SyntaxHighlighter>
                                </Box>
                              </>
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
          rowsPerPageOptions={[10, 25, 50]}
          component="div"
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
