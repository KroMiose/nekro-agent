import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Stack,
  Alert,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
  Link,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Launch as LaunchIcon,
} from '@mui/icons-material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { configApi, ModelGroupConfig } from '../../services/api/config'

interface EditDialogProps {
  open: boolean
  onClose: () => void
  groupName: string
  initialConfig?: ModelGroupConfig
  onSubmit: (groupName: string, config: ModelGroupConfig) => Promise<void>
  onGroupNameChange: (name: string) => void
}

function EditDialog({
  open,
  onClose,
  groupName,
  initialConfig,
  onSubmit,
  onGroupNameChange,
}: EditDialogProps) {
  const [config, setConfig] = useState<ModelGroupConfig>({
    CHAT_MODEL: '',
    CHAT_PROXY: '',
    BASE_URL: '',
    API_KEY: '',
  })
  const [error, setError] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)

  // 当initialConfig变化时更新表单
  useEffect(() => {
    if (initialConfig) {
      setConfig(initialConfig)
    } else {
      setConfig({
        CHAT_MODEL: '',
        CHAT_PROXY: '',
        BASE_URL: '',
        API_KEY: '',
      })
    }
  }, [initialConfig])

  const handleSubmit = async () => {
    try {
      await onSubmit(groupName, config)
      onClose()
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message)
      } else {
        setError('保存失败')
      }
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{initialConfig ? '编辑模型组' : '新建模型组'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 2 }}>
          <TextField
            label="组名"
            value={groupName}
            onChange={e => onGroupNameChange(e.target.value)}
            disabled={!!initialConfig}
            fullWidth
            autoComplete="off"
            required
          />
          <TextField
            label="模型名称"
            value={config.CHAT_MODEL}
            onChange={e => setConfig({ ...config, CHAT_MODEL: e.target.value })}
            fullWidth
            autoComplete="off"
          />
          <TextField
            label="代理地址"
            value={config.CHAT_PROXY}
            onChange={e => setConfig({ ...config, CHAT_PROXY: e.target.value })}
            fullWidth
            autoComplete="off"
          />
          <TextField
            label="API地址"
            value={config.BASE_URL}
            onChange={e => setConfig({ ...config, BASE_URL: e.target.value })}
            fullWidth
            autoComplete="off"
          />
          <TextField
            label="API密钥"
            value={config.API_KEY}
            onChange={e => setConfig({ ...config, API_KEY: e.target.value })}
            type={showApiKey ? 'text' : 'password'}
            fullWidth
            autoComplete="off"
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowApiKey(!showApiKey)} edge="end">
                    {showApiKey ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          {error && <Alert severity="error">{error}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>取消</Button>
        <Button onClick={handleSubmit} color="primary">
          保存
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default function ModelGroupsPage() {
  const queryClient = useQueryClient()
  const [message, setMessage] = useState('')
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingGroup, setEditingGroup] = useState<{ name: string; config?: ModelGroupConfig }>({
    name: '',
  })

  // 获取模型组列表
  const { data: modelGroups = {} } = useQuery({
    queryKey: ['model-groups'],
    queryFn: () => configApi.getModelGroups(),
  })

  const handleAdd = () => {
    setEditingGroup({ name: '' })
    setEditDialogOpen(true)
  }

  const handleEdit = (name: string) => {
    setEditingGroup({ name, config: modelGroups[name] })
    setEditDialogOpen(true)
  }

  const handleDelete = async (name: string) => {
    try {
      await configApi.deleteModelGroup(name)
      setMessage('删除成功')
      queryClient.invalidateQueries({ queryKey: ['model-groups'] })
    } catch (error) {
      if (error instanceof Error) {
        setMessage(error.message)
      } else {
        setMessage('删除失败')
      }
    }
  }

  const handleSubmit = async (groupName: string, config: ModelGroupConfig) => {
    await configApi.updateModelGroup(groupName, config)
    setMessage('保存成功')
    queryClient.invalidateQueries({ queryKey: ['model-groups'] })
  }

  const getBaseUrl = (url: string) => {
    try {
      const urlObj = new URL(url)
      return `${urlObj.protocol}//${urlObj.host}`
    } catch {
      return ''
    }
  }

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
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 2,
          flexShrink: 0,
        }}
      >
        <Alert severity="info" sx={{ mr: 2 }}>
          需要 API 密钥？可访问{' '}
          <Link href="https://one.nekro.top" target="_blank" rel="noopener">
            Nekro 合作中转
          </Link>{' '}
          获取专属密钥喵～
        </Alert>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleAdd}>
          新建模型组
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
        <TableContainer sx={{ flexGrow: 1 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell width="15%">组名</TableCell>
                <TableCell width="20%">模型名称</TableCell>
                <TableCell width="35%">API地址</TableCell>
                <TableCell width="20%">代理地址</TableCell>
                <TableCell width="10%" align="right">
                  操作
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(modelGroups).map(([name, config]) => (
                <TableRow key={name}>
                  <TableCell>
                    <Typography
                      variant="subtitle2"
                      sx={{ fontWeight: name === 'default' ? 'bold' : 'normal' }}
                    >
                      {name}
                    </Typography>
                  </TableCell>
                  <TableCell>{config.CHAT_MODEL}</TableCell>
                  <TableCell>{config.BASE_URL}</TableCell>
                  <TableCell>{config.CHAT_PROXY || '-'}</TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <IconButton
                        onClick={() => window.open(getBaseUrl(config.BASE_URL), '_blank')}
                        size="small"
                        color="primary"
                        disabled={!config.BASE_URL}
                      >
                        <LaunchIcon />
                      </IconButton>
                      <IconButton onClick={() => handleEdit(name)} size="small" color="primary">
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        onClick={() => handleDelete(name)}
                        size="small"
                        color="error"
                        disabled={name === 'default'}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 对话框和提示保持不变 */}
      <EditDialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        groupName={editingGroup.name}
        initialConfig={editingGroup.config}
        onSubmit={handleSubmit}
        onGroupNameChange={name => setEditingGroup(prev => ({ ...prev, name }))}
      />

      <Snackbar
        open={!!message}
        autoHideDuration={3000}
        onClose={() => setMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setMessage('')}
          severity="info"
          variant="filled"
          sx={{ width: '100%' }}
        >
          {message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
