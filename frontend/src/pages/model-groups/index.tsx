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
  styled,
  Switch,
  FormControlLabel,
  Tooltip,
  Chip,
  MenuItem,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Launch as LaunchIcon,
  Image as ImageIcon,
  Psychology as PsychologyIcon,
  Chat as ChatIcon,
  Code as CodeIcon,
  Brush as BrushIcon,
  EmojiObjects as EmojiObjectsIcon,
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
    MODEL_TYPE: 'chat',
    TEMPERATURE: null,
    TOP_P: null,
    TOP_K: null,
    PRESENCE_PENALTY: null,
    FREQUENCY_PENALTY: null,
    EXTRA_BODY: null,
    ENABLE_VISION: true,
    ENABLE_COT: false,
  })
  const [error, setError] = useState('')
  const [groupNameError, setGroupNameError] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // 获取模型类型列表
  const { data: modelTypes = [] } = useQuery({
    queryKey: ['model-types'],
    queryFn: () => configApi.getModelTypes(),
  })

  // 获取模型类型的图标
  const getModelTypeIcon = (type: string | undefined) => {
    if (!type) return <ChatIcon fontSize="small" />;
    
    const found = modelTypes.find(t => t.value === type);
    const iconName = found?.icon || "EmojiObjects";
    
    // 图标映射
    const iconMap: Record<string, React.ReactElement> = {
      "Chat": <ChatIcon fontSize="small" />,
      "Code": <CodeIcon fontSize="small" />,
      "Brush": <BrushIcon fontSize="small" />,
      "EmojiObjects": <EmojiObjectsIcon fontSize="small" />
    };
    
    return iconMap[iconName] || <EmojiObjectsIcon fontSize="small" />;
  }

  useEffect(() => {
    if (initialConfig) {
      setConfig({
        ...initialConfig,
        MODEL_TYPE: initialConfig.MODEL_TYPE || 'chat',
        ENABLE_VISION: initialConfig.ENABLE_VISION !== undefined ? initialConfig.ENABLE_VISION : true,
        ENABLE_COT: initialConfig.ENABLE_COT !== undefined ? initialConfig.ENABLE_COT : false,
      })
    } else {
      setConfig({
        CHAT_MODEL: '',
        CHAT_PROXY: '',
        BASE_URL: '',
        API_KEY: '',
        MODEL_TYPE: 'chat',
        TEMPERATURE: null,
        TOP_P: null,
        TOP_K: null,
        PRESENCE_PENALTY: null,
        FREQUENCY_PENALTY: null,
        EXTRA_BODY: null,
        ENABLE_VISION: true,
        ENABLE_COT: false,
      })
    }
  }, [initialConfig])

  // 验证组名的函数
  const validateGroupName = (name: string): boolean => {
    // 只排除会影响URL解析的特殊字符，包括百分号
    const invalidChars = /[\/\?&#=%]/;
    return name.trim().length > 0 && !invalidChars.test(name);
  }

  // 处理组名变更，添加验证
  const handleGroupNameChange = (name: string) => {
    // 如果为空，清除错误信息
    if (!name) {
      setGroupNameError('');
      onGroupNameChange(name);
      return;
    }
    
    // 验证组名格式
    if (!validateGroupName(name)) {
      setGroupNameError('组名不能包含URL特殊字符 (如 / ? & # = %)');
    } else {
      setGroupNameError('');
    }
    onGroupNameChange(name);
  }

  // 在提交前验证表单
  const handleSubmit = async () => {
    // 验证组名
    if (groupName && !validateGroupName(groupName)) {
      setGroupNameError('组名不能包含URL特殊字符 (如 / ? & # = %)');
      return;
    }
    
    // 检查空组名
    if (!groupName) {
      setGroupNameError('组名不能为空');
      return;
    }

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
        {!initialConfig && groupNameError && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {groupNameError}
          </Alert>
        )}
        <Stack spacing={2} className="mt-4">
          <TextField
            label="组名"
            value={groupName}
            onChange={e => handleGroupNameChange(e.target.value)}
            disabled={!!initialConfig}
            fullWidth
            autoComplete="off"
            required
            error={!!groupNameError}
            helperText={groupNameError || (groupName ? "" : "组名不能包含URL特殊字符 (如 / ? & # = %)，创建后不可修改")}
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
            select
            label="模型类型"
            value={config.MODEL_TYPE || 'chat'}
            onChange={e => setConfig({ ...config, MODEL_TYPE: e.target.value })}
            fullWidth
            size="small"
          >
            {modelTypes.map((type) => (
              <MenuItem key={type.value} value={type.value}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getModelTypeIcon(type.value)}
                  <Box sx={{ ml: 1 }}>
                    <Typography variant="body2">{type.label}</Typography>
                    {type.description && (
                      <Typography variant="caption" color="text.secondary">
                        {type.description}
                      </Typography>
                    )}
                  </Box>
                </Box>
              </MenuItem>
            ))}
          </TextField>
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

          {/* 模型功能选项 */}
          <Box className="border-t pt-2 mt-2">
            <Typography variant="subtitle2" className="mb-2">
              模型功能
            </Typography>
            <Stack direction="row" spacing={4}>
              <Tooltip title="启用模型视觉能力，需要模型支持多模态输入">
                <div>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.ENABLE_VISION}
                        onChange={e => setConfig({ ...config, ENABLE_VISION: e.target.checked })}
                        color="primary"
                      />
                    }
                    label="视觉能力"
                  />
                </div>
              </Tooltip>
              
              <Tooltip title="启用NA提供的思维链进行分析，如果模型原生支持请关闭">
                <div>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.ENABLE_COT}
                        onChange={e => setConfig({ ...config, ENABLE_COT: e.target.checked })}
                        color="primary"
                      />
                    }
                    label="外置思维链"
                  />
                </div>
              </Tooltip>
            </Stack>
          </Box>

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
        <Button 
          onClick={handleSubmit} 
          color="primary" 
          disabled={!!groupNameError || !groupName}
        >
          保存
        </Button>
      </DialogActions>
    </Dialog>
  )
}

const BlurredText = styled('div')`
  filter: blur(4px);
  transition: filter 0.2s ease-in-out;

  &:hover {
    filter: blur(0);
  }
`

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
  
  // 获取模型类型列表，用于显示模型类型名称
  const { data: modelTypes = [] } = useQuery({
    queryKey: ['model-types'],
    queryFn: () => configApi.getModelTypes(),
  })
  
  // 获取模型类型的显示名称
  const getModelTypeLabel = (type: string | undefined) => {
    if (!type) return '聊天';
    const found = modelTypes.find(t => t.value === type);
    return found ? found.label : type;
  }
  
  // 获取模型类型对应的颜色
  const getModelTypeColor = (type: string | undefined): "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" => {
    if (!type) return "primary";
    const found = modelTypes.find(t => t.value === type);
    const color = found?.color as "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" | undefined;
    
    // 确保返回值是有效的 MUI 颜色
    switch(color) {
      case "primary": return "primary";
      case "secondary": return "secondary";
      case "error": return "error";
      case "info": return "info";
      case "success": return "success";
      case "warning": return "warning";
      default: return "default";
    }
  }
  
  // 获取模型类型的图标
  const getModelTypeIcon = (type: string | undefined) => {
    if (!type) return <ChatIcon fontSize="small" />;
    
    const found = modelTypes.find(t => t.value === type);
    const iconName = found?.icon || "EmojiObjects";
    
    // 图标映射
    const iconMap: Record<string, React.ReactElement> = {
      "Chat": <ChatIcon fontSize="small" />,
      "Code": <CodeIcon fontSize="small" />,
      "Brush": <BrushIcon fontSize="small" />,
      "EmojiObjects": <EmojiObjectsIcon fontSize="small" />
    };
    
    return iconMap[iconName] || <EmojiObjectsIcon fontSize="small" />;
  }

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
          <Link href="https://api.nekro.top" target="_blank" rel="noopener">
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
                <TableCell width="12%">组名</TableCell>
                <TableCell width="12%">模型名称</TableCell>
                <TableCell width="10%">模型类型</TableCell>
                <TableCell width="20%">API地址</TableCell>
                <TableCell width="13%">代理地址</TableCell>
                <TableCell width="18%">功能</TableCell>
                <TableCell width="15%">操作</TableCell>
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
                  <TableCell>
                    <Chip
                      icon={getModelTypeIcon(config.MODEL_TYPE)}
                      label={getModelTypeLabel(config.MODEL_TYPE)}
                      size="small"
                      color={getModelTypeColor(config.MODEL_TYPE)}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <BlurredText>{config.BASE_URL}</BlurredText>
                  </TableCell>
                  <TableCell>{config.CHAT_PROXY || '-'}</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <Tooltip title={config.ENABLE_VISION ? "支持视觉功能" : "不支持视觉功能"}>
                        <Chip
                          icon={<ImageIcon fontSize="small" />}
                          label="视觉"
                          size="small"
                          color={config.ENABLE_VISION ? "primary" : "default"}
                          variant={config.ENABLE_VISION ? "filled" : "outlined"}
                        />
                      </Tooltip>
                      <Tooltip title={config.ENABLE_COT ? "启用思维链" : "未启用思维链"}>
                        <Chip
                          icon={<PsychologyIcon fontSize="small" />}
                          label="思维链"
                          size="small"
                          color={config.ENABLE_COT ? "secondary" : "default"}
                          variant={config.ENABLE_COT ? "filled" : "outlined"}
                        />
                      </Tooltip>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5} justifyContent="flex-start">
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
