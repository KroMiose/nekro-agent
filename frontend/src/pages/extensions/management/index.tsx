import { useState } from 'react'
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
  IconButton,
  Collapse,
} from '@mui/material'
import {
  KeyboardArrowDown as KeyboardArrowDownIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { extensionsApi } from '../../../services/api/extensions'

interface Method {
  name: string
  type: 'tool' | 'behavior' | 'agent'
  description: string
}

interface Extension {
  name: string
  version: string
  description: string
  author: string
  methods: Method[]
  is_enabled: boolean
}

// 扩展方法类型对应的颜色
const METHOD_TYPE_COLORS = {
  tool: 'primary',
  behavior: 'success',
  agent: 'warning',
} as const

// 扩展行组件
function ExtensionRow({ extension }: { extension: Extension }) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell>
          <IconButton size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
              {extension.name}
            </Typography>
          </Box>
        </TableCell>
        <TableCell>{extension.version}</TableCell>
        <TableCell>{extension.description}</TableCell>
        <TableCell>{extension.author}</TableCell>
        <TableCell>
          <Chip
            label={extension.is_enabled ? '已启用' : '已禁用'}
            color={extension.is_enabled ? 'success' : 'default'}
            size="small"
          />
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>
              <Typography variant="h6" gutterBottom component="div">
                扩展方法
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>方法名</TableCell>
                    <TableCell>类型</TableCell>
                    <TableCell>描述提示词</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {extension.methods.map(method => (
                    <TableRow key={method.name}>
                      <TableCell component="th" scope="row">
                        <Typography
                          variant="body2"
                          sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}
                        >
                          {method.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={method.type}
                          color={METHOD_TYPE_COLORS[method.type]}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>{method.description}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  )
}

export default function ExtensionsManagementPage() {
  // 获取扩展列表
  const { data: extensions = [] } = useQuery({
    queryKey: ['extensions'],
    queryFn: () => extensionsApi.getExtensions(),
  })

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 120px)',
      }}
    >
      {/* 表格容器 */}
      <Paper
        elevation={3}
        sx={{
          flexGrow: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <TableContainer sx={{ flexGrow: 1 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell width="50px" />
                <TableCell width="200px">扩展名称</TableCell>
                <TableCell width="100px">版本</TableCell>
                <TableCell>描述</TableCell>
                <TableCell width="120px">作者</TableCell>
                <TableCell width="100px">状态</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {extensions.map((extension: Extension) => (
                <ExtensionRow key={extension.name} extension={extension} />
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  )
} 