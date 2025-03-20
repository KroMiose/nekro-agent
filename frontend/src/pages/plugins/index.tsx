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
  Button,
  CircularProgress,
} from '@mui/material'
import {
  KeyboardArrowDown as KeyboardArrowDownIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { pluginsApi, Plugin, MethodType } from '../../services/api/plugins'
import { useNavigate } from 'react-router-dom'

// 扩展方法类型对应的颜色
const METHOD_TYPE_COLORS: Record<MethodType, 'primary' | 'success' | 'warning' | 'info'> = {
  tool: 'primary',
  behavior: 'success',
  agent: 'warning',
  multimodal_agent: 'info',
}

// 扩展行组件
function PluginRow({ plugin }: { plugin: Plugin }) {
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
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
            {plugin.name}
          </Typography>
        </TableCell>
        <TableCell>{plugin.version}</TableCell>
        <TableCell>{plugin.description}</TableCell>
        <TableCell>{plugin.author}</TableCell>
        <TableCell>
          <Chip
            label={plugin.enabled ? '已启用' : '已禁用'}
            color={plugin.enabled ? 'success' : 'default'}
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
                  {plugin.methods.map(method => (
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

export default function PluginsPage() {
  const navigate = useNavigate()
  
  // 获取扩展列表
  const { data: plugins = [], isLoading } = useQuery({
    queryKey: ['plugins'],
    queryFn: () => pluginsApi.getPlugins(),
  })

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 120px)',
        gap: 2,
      }}
    >
      {/* 顶部操作区 */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button 
          variant="contained" 
          startIcon={<SettingsIcon />}
          onClick={() => navigate('/plugins/management')}
        >
          插件管理
        </Button>
      </Box>
      
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
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
          </Box>
        ) : (
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
                {plugins.map(plugin => (
                  <PluginRow key={plugin.id} plugin={plugin} />
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  )
}
