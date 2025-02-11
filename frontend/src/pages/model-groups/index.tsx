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
    TEMPERATURE: null,
    TOP_P: null,
    TOP_K: null,
    PRESENCE_PENALTY: null,
    FREQUENCY_PENALTY: null,
    EXTRA_BODY: null,
  })
  const [error, setError] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    if (initialConfig) {
      setConfig(initialConfig)
    } else {
      setConfig({
        CHAT_MODEL: '',
        CHAT_PROXY: '',
        BASE_URL: '',
        API_KEY: '',
        TEMPERATURE: null,
        TOP_P: null,
        TOP_K: null,
        PRESENCE_PENALTY: null,
        FREQUENCY_PENALTY: null,
        EXTRA_BODY: null,
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
        <Stack spacing={2} className="mt-4">
          <TextField
            label="组名"
            value={groupName}
            onChange={e => onGroupNameChange(e.target.value)}
            disabled={!!initialConfig}
            fullWidth
            autoComplete="off"
            required
            inputProps={{
              autoComplete: 'new-password',
              form: {
                autoComplete: 'off',
              },
            }}
          />
          <TextField
            label="模型名称"
            value={config.CHAT_MODEL}
            onChange={e => setConfig({ ...config, CHAT_MODEL: e.target.value })}
            fullWidth
            autoComplete="off"
            inputProps={{
              autoComplete: 'new-password',
              form: {
                autoComplete: 'off',
              },
            }}
          />
          <TextField
            label="代理地址"
            value={config.CHAT_PROXY}
            onChange={e => setConfig({ ...config, CHAT_PROXY: e.target.value })}
            fullWidth
            autoComplete="off"
            inputProps={{
              autoComplete: 'new-password',
              form: {
                autoComplete: 'off',
              },
            }}
          />
          <TextField
            label="API地址"
            value={config.BASE_URL}
            onChange={e => setConfig({ ...config, BASE_URL: e.target.value })}
            fullWidth
            autoComplete="off"
            inputProps={{
              autoComplete: 'new-password',
              form: {
                autoComplete: 'off',
              },
            }}
          />
          <TextField
            label="API密钥"
            value={config.API_KEY}
            onChange={e => setConfig({ ...config, API_KEY: e.target.value })}
            type={showApiKey ? 'text' : 'password'}
            fullWidth
            autoComplete="off"
            inputProps={{
              autoComplete: 'new-password',
              form: {
                autoComplete: 'off',
              },
            }}
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

          {/* 高级选项折叠面板 */}
          <Button
            onClick={() => setShowAdvanced(!showAdvanced)}
            variant="text"
            className="self-start"
          >
            {showAdvanced ? '收起高级选项 ▼' : '展开高级选项 ▶'}
          </Button>

          {showAdvanced && (
            <Stack spacing={2} className="pl-4 border-l-2 border-gray-200">
              <TextField
                label="Temperature"
                type="number"
                value={config.TEMPERATURE ?? ''}
                onChange={e =>
                  setConfig({
                    ...config,
                    TEMPERATURE: e.target.value ? parseFloat(e.target.value) : null,
                  })
                }
                fullWidth
                inputProps={{ step: 0.1, min: 0, max: 2 }}
                helperText="控制输出的随机性 (0-2)"
              />
              <TextField
                label="Top P"
                type="number"
                value={config.TOP_P ?? ''}
                onChange={e =>
                  setConfig({
                    ...config,
                    TOP_P: e.target.value ? parseFloat(e.target.value) : null,
                  })
                }
                fullWidth
                inputProps={{ step: 0.1, min: 0, max: 1 }}
                helperText="控制输出的多样性 (0-1)"
              />
              {/* <TextField
                label="Top K"
                type="number"
                value={config.TOP_K ?? ''}
                onChange={e =>
                  setConfig({
                    ...config,
                    TOP_K: e.target.value ? parseFloat(e.target.value) : null,
                  })
                }
                fullWidth
                inputProps={{ step: 1, min: 0 }}
                helperText="控制考虑的 top tokens 数量"
              /> */}
              <TextField
                label="Presence Penalty"
                type="number"
                value={config.PRESENCE_PENALTY ?? ''}
                onChange={e =>
                  setConfig({
                    ...config,
                    PRESENCE_PENALTY: e.target.value ? parseFloat(e.target.value) : null,
                  })
                }
                fullWidth
                inputProps={{ step: 0.1, min: -2, max: 2 }}
                helperText="基于生成文本中已出现的内容对新内容的惩罚，越大越倾向产生新话题 (-2 到 2)"
              />
              <TextField
                label="Frequency Penalty"
                type="number"
                value={config.FREQUENCY_PENALTY ?? ''}
                onChange={e =>
                  setConfig({
                    ...config,
                    FREQUENCY_PENALTY: e.target.value ? parseFloat(e.target.value) : null,
                  })
                }
                fullWidth
                inputProps={{ step: 0.1, min: -2, max: 2 }}
                helperText="基于生成文本中出现的内容频率对新内容的惩罚，越大越倾向产生多样回复 (-2 到 2)"
              />
              <TextField
                label="Extra Body (JSON)"
                value={config.EXTRA_BODY ?? ''}
                onChange={e => setConfig({ ...config, EXTRA_BODY: e.target.value || null })}
                fullWidth
                multiline
                rows={3}
                helperText="额外的请求参数 (JSON 格式)"
              />
            </Stack>
          )}

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
    <Box className="h-full flex flex-col overflow-hidden">
      {/* 顶部工具栏 */}
      <Box className="flex justify-between items-center mb-4 flex-shrink-0">
        <Alert severity="info" className="mr-4">
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
      <Paper className="flex-1 flex flex-col min-h-0 overflow-hidden" elevation={3}>
        <TableContainer className="flex-1 overflow-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell className="w-[15%]">组名</TableCell>
                <TableCell className="w-[20%]">模型名称</TableCell>
                <TableCell className="w-[35%]">API地址</TableCell>
                <TableCell className="w-[20%]">代理地址</TableCell>
                <TableCell className="w-[10%] text-right">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(modelGroups).map(([name, config]) => (
                <TableRow key={name}>
                  <TableCell>
                    <Typography
                      className={name === 'default' ? 'font-bold' : ''}
                      variant="subtitle2"
                    >
                      {name}
                    </Typography>
                  </TableCell>
                  <TableCell>{config.CHAT_MODEL}</TableCell>
                  <TableCell>{config.BASE_URL}</TableCell>
                  <TableCell>{config.CHAT_PROXY || '-'}</TableCell>
                  <TableCell className="text-right">
                    <Stack direction="row" spacing={1} className="justify-end">
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
        <Alert onClose={() => setMessage('')} severity="info" variant="filled" className="w-full">
          {message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
