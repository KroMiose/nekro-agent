import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Stack,
  Alert,
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
  useTheme,
  useMediaQuery,
  SxProps,
  Theme,
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
  ContentCopy as ContentCopyIcon,
} from '@mui/icons-material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ModelGroupConfig } from '../../services/api/config'
import { unifiedConfigApi } from '../../services/api/unified-config'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'

interface EditDialogProps {
  open: boolean
  onClose: () => void
  groupName: string
  initialConfig?: ModelGroupConfig
  onSubmit: (groupName: string, config: ModelGroupConfig) => Promise<void>
  onGroupNameChange: (name: string) => void
  isCopy?: boolean
  existingGroups: Record<string, ModelGroupConfig>
}

function EditDialog({
  open,
  onClose,
  groupName,
  initialConfig,
  onSubmit,
  onGroupNameChange,
  isCopy,
  existingGroups,
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
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  // 获取模型类型列表
  const { data: modelTypes = [] } = useQuery({
    queryKey: ['model-types'],
    queryFn: () => unifiedConfigApi.getModelTypes(),
  })

  // 获取模型类型的图标
  const getModelTypeIcon = (type: string | undefined) => {
    if (!type) return <ChatIcon fontSize="small" />

    const found = modelTypes.find(t => t.value === type)
    const iconName = found?.icon || 'EmojiObjects'

    // 图标映射
    const iconMap: Record<string, React.ReactElement> = {
      Chat: <ChatIcon fontSize="small" />,
      Code: <CodeIcon fontSize="small" />,
      Brush: <BrushIcon fontSize="small" />,
      EmojiObjects: <EmojiObjectsIcon fontSize="small" />,
    }

    return iconMap[iconName] || <EmojiObjectsIcon fontSize="small" />
  }

  useEffect(() => {
    if (initialConfig) {
      setConfig({
        ...initialConfig,
        MODEL_TYPE: initialConfig.MODEL_TYPE || 'chat',
        ENABLE_VISION:
          initialConfig.ENABLE_VISION !== undefined ? initialConfig.ENABLE_VISION : true,
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
    const invalidChars = /[/\\?&#=%]/
    return name.trim().length > 0 && !invalidChars.test(name)
  }

  // 处理组名变更，添加验证
  const handleGroupNameChange = (name: string) => {
    // 如果为空，清除错误信息
    if (!name) {
      setGroupNameError('')
      onGroupNameChange(name)
      return
    }

    // 验证组名格式
    if (!validateGroupName(name)) {
      setGroupNameError('组名不能包含URL特殊字符 (如 / ? & # = %)')
    }
    // 验证组名是否已存在
    else if (existingGroups[name] && (isCopy || !initialConfig)) {
      // 当创建新组或复制时，检查名称是否已存在
      setGroupNameError(`模型组名称 "${name}" 已存在，请使用其他名称`)
    } else {
      setGroupNameError('')
    }
    onGroupNameChange(name)
  }

  // 在提交前验证表单
  const handleSubmit = async () => {
    // 验证组名
    if (groupName && !validateGroupName(groupName)) {
      setGroupNameError('组名不能包含URL特殊字符 (如 / ? & # = %)')
      return
    }

    // 检查空组名
    if (!groupName) {
      setGroupNameError('组名不能为空')
      return
    }

    // 检查名称是否已存在（对于新建或复制的情况）
    if (existingGroups[groupName] && (isCopy || !initialConfig)) {
      setGroupNameError(`模型组名称 "${groupName}" 已存在，请使用其他名称`)
      return
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
      <DialogTitle>
        {isCopy ? '复制模型组' : initialConfig && !isCopy ? '编辑模型组' : '新建模型组'}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} className="mt-4">
          <TextField
            label="组名"
            value={groupName}
            onChange={e => handleGroupNameChange(e.target.value)}
            disabled={!!initialConfig && !isCopy}
            fullWidth
            autoComplete="off"
            required
            error={!!groupNameError}
            helperText={
              groupNameError ||
              (groupName
                ? ''
                : isCopy
                  ? '请为复制的模型组设置一个新名称'
                  : '组名不能包含URL特殊字符 (如 / ? & # = %)，创建后不可修改')
            }
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
            size={isSmall ? 'small' : 'medium'}
          >
            {modelTypes.map(type => (
              <MenuItem key={type.value} value={type.value}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getModelTypeIcon(type.value)}
                  <Box sx={{ ml: 1 }}>
                    <Typography variant="body2" sx={{ fontSize: isSmall ? '0.8rem' : 'inherit' }}>
                      {type.label}
                    </Typography>
                    {type.description && (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontSize: isSmall ? '0.7rem' : 'inherit' }}
                      >
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
            size={isSmall ? 'small' : 'medium'}
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
            size={isSmall ? 'small' : 'medium'}
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
            type="text"
            fullWidth
            autoComplete="off"
            size={isSmall ? 'small' : 'medium'}
            name={`apikey_${Math.random().toString(36).slice(2)}`}
            inputProps={{
              autoComplete: 'new-password',
              form: {
                autoComplete: 'off',
              },
              style: !showApiKey
                ? ({
                    '-webkit-text-security': 'disc',
                    'text-security': 'disc',
                  } as React.CSSProperties)
                : undefined,
            }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowApiKey(!showApiKey)}
                    edge="end"
                    size={isSmall ? 'small' : 'medium'}
                  >
                    {showApiKey ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          {/* 模型功能选项 */}
          <Box className="border-t pt-2 mt-2">
            <Typography
              variant="subtitle2"
              className="mb-2"
              sx={{ fontSize: isSmall ? '0.8rem' : 'inherit' }}
            >
              模型功能
            </Typography>
            <Stack direction={isMobile ? 'column' : 'row'} spacing={isMobile ? 1 : 4}>
              <Tooltip title="启用模型视觉能力，需要模型支持多模态输入">
                <div>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.ENABLE_VISION}
                        onChange={e => setConfig({ ...config, ENABLE_VISION: e.target.checked })}
                        color="primary"
                        size={isSmall ? 'small' : 'medium'}
                      />
                    }
                    label={
                      <Typography sx={{ fontSize: isSmall ? '0.8rem' : 'inherit' }}>
                        视觉能力
                      </Typography>
                    }
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
                        size={isSmall ? 'small' : 'medium'}
                      />
                    }
                    label={
                      <Typography sx={{ fontSize: isSmall ? '0.8rem' : 'inherit' }}>
                        外置思维链
                      </Typography>
                    }
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
            size={isSmall ? 'small' : 'medium'}
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
                size={isSmall ? 'small' : 'medium'}
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
                size={isSmall ? 'small' : 'medium'}
                inputProps={{ step: 0.1, min: 0, max: 1 }}
                helperText="控制输出的多样性 (0-1)"
              />
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
                size={isSmall ? 'small' : 'medium'}
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
                size={isSmall ? 'small' : 'medium'}
                inputProps={{ step: 0.1, min: -2, max: 2 }}
                helperText="基于生成文本中出现的内容频率对新内容的惩罚，越大越倾向产生多样回复 (-2 到 2)"
              />
              <TextField
                label="Extra Body (JSON)"
                value={config.EXTRA_BODY ?? ''}
                onChange={e => setConfig({ ...config, EXTRA_BODY: e.target.value || null })}
                fullWidth
                size={isSmall ? 'small' : 'medium'}
                multiline
                rows={3}
                helperText="额外的请求参数 (JSON 格式)"
              />
            </Stack>
          )}

          {error && <Alert severity="error">{error}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={onClose}
          sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
        >
          取消
        </Button>
        <Button
          onClick={handleSubmit}
          color="primary"
          disabled={!!groupNameError || !groupName}
          sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
        >
          {isCopy ? '创建副本' : '保存'}
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
  const notification = useNotification()
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingGroup, setEditingGroup] = useState<{
    name: string
    config?: ModelGroupConfig
    isCopy?: boolean
  }>({
    name: '',
  })
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingGroupName, setDeletingGroupName] = useState('')
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  const { data: modelGroups = {} } = useQuery({
    queryKey: ['model-groups'],
    queryFn: () => unifiedConfigApi.getModelGroups(),
  })

  // 获取模型类型列表，用于显示模型类型名称
  const { data: modelTypes = [] } = useQuery({
    queryKey: ['model-types'],
    queryFn: () => unifiedConfigApi.getModelTypes(),
  })

  // 获取模型类型的显示名称
  const getModelTypeLabel = (type: string | undefined) => {
    if (!type) return '聊天'
    const found = modelTypes.find(t => t.value === type)
    return found ? found.label : type
  }

  // 获取模型类型对应的颜色
  const getModelTypeColor = (
    type: string | undefined
  ): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    if (!type) return 'primary'
    const found = modelTypes.find(t => t.value === type)
    const color = found?.color as
      | 'default'
      | 'primary'
      | 'secondary'
      | 'error'
      | 'info'
      | 'success'
      | 'warning'
      | undefined

    // 确保返回值是有效的 MUI 颜色
    switch (color) {
      case 'primary':
        return 'primary'
      case 'secondary':
        return 'secondary'
      case 'error':
        return 'error'
      case 'info':
        return 'info'
      case 'success':
        return 'success'
      case 'warning':
        return 'warning'
      default:
        return 'default'
    }
  }

  // 获取模型类型的图标
  const getModelTypeIcon = (type: string | undefined) => {
    if (!type) return <ChatIcon fontSize="small" />

    const found = modelTypes.find(t => t.value === type)
    const iconName = found?.icon || 'EmojiObjects'

    // 图标映射
    const iconMap: Record<string, React.ReactElement> = {
      Chat: <ChatIcon fontSize="small" />,
      Code: <CodeIcon fontSize="small" />,
      Brush: <BrushIcon fontSize="small" />,
      EmojiObjects: <EmojiObjectsIcon fontSize="small" />,
    }

    return iconMap[iconName] || <EmojiObjectsIcon fontSize="small" />
  }

  const handleAdd = () => {
    setEditingGroup({ name: '' })
    setEditDialogOpen(true)
  }

  const handleEdit = (name: string) => {
    setEditingGroup({ name, config: modelGroups[name] })
    setEditDialogOpen(true)
  }

  // 添加复制模型组功能
  const handleCopy = (name: string) => {
    setEditingGroup({
      name: name,
      config: { ...modelGroups[name] },
      isCopy: true,
    })
    setEditDialogOpen(true)
  }

  const handleDelete = async (name: string) => {
    try {
      await unifiedConfigApi.deleteModelGroup(name)
      notification.success(`模型组 "${name}" 已删除！`)
      queryClient.invalidateQueries({ queryKey: ['model-groups'] })
      setDeleteDialogOpen(false)
    } catch (error) {
      if (error instanceof Error) {
        notification.error(error.message)
      } else {
        notification.error('删除失败')
      }
    }
  }

  // 确认删除
  const confirmDelete = (name: string) => {
    setDeletingGroupName(name)
    setDeleteDialogOpen(true)
  }

  const handleSubmit = async (groupName: string, config: ModelGroupConfig) => {
    // 检查新模型组名称是否已存在
    if (modelGroups[groupName] && !editingGroup.isCopy && editingGroup.name === groupName) {
      // 如果是编辑已有模型组，允许相同名称
      await unifiedConfigApi.updateModelGroup(groupName, config)
      notification.success('保存模型配置成功')
    } else if (!modelGroups[groupName]) {
      // 如果是新建或复制模型组，名称必须不存在
      await unifiedConfigApi.updateModelGroup(groupName, config)
      notification.success(
        editingGroup.isCopy ? `模型组 "${groupName}" 复制模型配置成功` : '保存模型配置成功'
      )
    } else {
      // 如果是已有名称
      notification.error(`模型组名称 "${groupName}" 已存在，请换一个名称～ (>﹏<)`)
      return
    }

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
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        p: 2,
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
          flexWrap: 'wrap',
          gap: 1,
        }}
      >
        <Alert severity="info">
          需要 API 密钥？可访问{' '}
          <Link href="https://api.nekro.ai" target="_blank" rel="noopener">
            Nekro 合作中转
          </Link>{' '}
          获取专属密钥哦～
        </Alert>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAdd}
          size={isSmall ? 'small' : 'medium'}
          sx={{
            ml: isMobile ? 0 : 'auto',
            minWidth: { xs: 120, sm: 140 },
            minHeight: { xs: 36, sm: 40 },
          }}
        >
          新建模型组
        </Button>
      </Box>

      {/* 表格容器 */}
      <Paper
        elevation={3}
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          overflow: 'hidden',
          ...(UNIFIED_TABLE_STYLES.paper as SxProps<Theme>),
        }}
      >
        <TableContainer
          sx={{
            flex: 1,
            overflow: 'auto',
            ...(UNIFIED_TABLE_STYLES.scrollbar as SxProps<Theme>),
          }}
        >
          <Table
            stickyHeader
            size={isSmall ? 'small' : 'medium'}
            sx={{ minWidth: isMobile ? 650 : 900 }}
          >
            <TableHead>
              <TableRow>
                <TableCell
                  width={isMobile ? '15%' : '12%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  组名
                </TableCell>
                <TableCell
                  width={isMobile ? '18%' : '15%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  模型名称
                </TableCell>
                <TableCell
                  width={isMobile ? '15%' : '10%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  模型类型
                </TableCell>
                {!isSmall && (
                  <TableCell
                    width="18%"
                    sx={{
                      py: isSmall ? 1 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                    }}
                  >
                    API地址
                  </TableCell>
                )}
                {!isMobile && (
                  <TableCell
                    width="15%"
                    sx={{
                      py: isSmall ? 1 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                    }}
                  >
                    代理地址
                  </TableCell>
                )}
                <TableCell
                  width={isMobile ? '23%' : '15%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  功能
                </TableCell>
                <TableCell
                  width={isMobile ? '30%' : '15%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  操作
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(modelGroups).map(([name, config]) => (
                <TableRow key={name} sx={UNIFIED_TABLE_STYLES.row as SxProps<Theme>}>
                  <TableCell
                    sx={{
                      py: isSmall ? 0.75 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                    }}
                  >
                    <Typography
                      className={name === 'default' ? 'font-bold' : ''}
                      variant="subtitle2"
                      sx={{ fontSize: isSmall ? '0.75rem' : 'inherit' }}
                    >
                      {name}
                    </Typography>
                  </TableCell>
                  <TableCell
                    sx={{
                      py: isSmall ? 0.75 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: isSmall ? '0.75rem' : 'inherit',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        maxWidth: isMobile ? 120 : 180,
                      }}
                    >
                      {config.CHAT_MODEL}
                    </Typography>
                  </TableCell>
                  <TableCell
                    sx={{
                      py: isSmall ? 0.75 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                    }}
                  >
                    <Chip
                      icon={getModelTypeIcon(config.MODEL_TYPE)}
                      label={getModelTypeLabel(config.MODEL_TYPE)}
                      size="small"
                      color={getModelTypeColor(config.MODEL_TYPE)}
                      variant="outlined"
                      sx={{
                        height: isSmall ? 20 : 24,
                        fontSize: isSmall ? '0.65rem' : '0.75rem',
                        '& .MuiChip-label': {
                          px: isSmall ? 0.5 : 0.75,
                        },
                      }}
                    />
                  </TableCell>
                  {!isSmall && (
                    <TableCell
                      sx={{
                        py: isSmall ? 0.75 : 1.5,
                        ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                      }}
                    >
                      <BlurredText>{config.BASE_URL}</BlurredText>
                    </TableCell>
                  )}
                  {!isMobile && (
                    <TableCell
                      sx={{
                        py: isSmall ? 0.75 : 1.5,
                        ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                      }}
                    >
                      <Typography
                        variant="body2"
                        sx={{
                          fontSize: isSmall ? '0.75rem' : 'inherit',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {config.CHAT_PROXY || '-'}
                      </Typography>
                    </TableCell>
                  )}
                  <TableCell
                    sx={{
                      py: isSmall ? 0.75 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                    }}
                  >
                    <Stack direction="row" spacing={0.5} flexWrap={isSmall ? 'wrap' : 'nowrap'}>
                      <Tooltip title={config.ENABLE_VISION ? '支持视觉功能' : '不支持视觉功能'}>
                        <Chip
                          icon={<ImageIcon fontSize="small" />}
                          label="视觉"
                          size="small"
                          color={config.ENABLE_VISION ? 'primary' : 'default'}
                          variant={config.ENABLE_VISION ? 'filled' : 'outlined'}
                          sx={{
                            height: isSmall ? 20 : 24,
                            fontSize: isSmall ? '0.65rem' : '0.75rem',
                            '& .MuiChip-label': {
                              px: isSmall ? 0.5 : 0.75,
                            },
                            '& .MuiChip-icon': {
                              fontSize: isSmall ? '0.9rem' : '1rem',
                              ml: isSmall ? 0.3 : 0.5,
                            },
                          }}
                        />
                      </Tooltip>
                      <Tooltip title={config.ENABLE_COT ? '启用思维链' : '未启用思维链'}>
                        <Chip
                          icon={<PsychologyIcon fontSize="small" />}
                          label="思维链"
                          size="small"
                          color={config.ENABLE_COT ? 'secondary' : 'default'}
                          variant={config.ENABLE_COT ? 'filled' : 'outlined'}
                          sx={{
                            height: isSmall ? 20 : 24,
                            fontSize: isSmall ? '0.65rem' : '0.75rem',
                            '& .MuiChip-label': {
                              px: isSmall ? 0.5 : 0.75,
                            },
                            '& .MuiChip-icon': {
                              fontSize: isSmall ? '0.9rem' : '1rem',
                              ml: isSmall ? 0.3 : 0.5,
                            },
                          }}
                        />
                      </Tooltip>
                    </Stack>
                  </TableCell>
                  <TableCell
                    sx={{
                      py: isSmall ? 0.75 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                    }}
                  >
                    <Stack
                      direction="row"
                      spacing={0.5}
                      justifyContent="flex-start"
                      flexWrap={isSmall ? 'wrap' : 'nowrap'}
                    >
                      <Tooltip title="访问API提供商" arrow>
                        <IconButton
                          onClick={() => window.open(getBaseUrl(config.BASE_URL), '_blank')}
                          size="small"
                          color="success"
                          disabled={!config.BASE_URL}
                          sx={{ p: isSmall ? 0.5 : 1 }}
                        >
                          <LaunchIcon fontSize={isSmall ? 'small' : 'medium'} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="编辑模型组" arrow>
                        <IconButton
                          onClick={() => handleEdit(name)}
                          size="small"
                          color="warning"
                          sx={{ p: isSmall ? 0.5 : 1 }}
                        >
                          <EditIcon fontSize={isSmall ? 'small' : 'medium'} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="复制模型组" arrow>
                        <IconButton
                          onClick={() => handleCopy(name)}
                          size="small"
                          color="info"
                          sx={{ p: isSmall ? 0.5 : 1 }}
                        >
                          <ContentCopyIcon fontSize={isSmall ? 'small' : 'medium'} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip
                        title={name === 'default' ? '默认模型组不可删除' : '删除模型组'}
                        arrow
                      >
                        <span>
                          <IconButton
                            onClick={() => name !== 'default' && confirmDelete(name)}
                            size="small"
                            color="error"
                            disabled={name === 'default'}
                            sx={{ p: isSmall ? 0.5 : 1 }}
                          >
                            <DeleteIcon fontSize={isSmall ? 'small' : 'medium'} />
                          </IconButton>
                        </span>
                      </Tooltip>
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
        isCopy={editingGroup.isCopy}
        existingGroups={modelGroups}
      />

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>确认删除模型组</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: isSmall ? '0.9rem' : 'inherit' }}>
            确定要删除模型组 "{deletingGroupName}" 吗？此操作不可恢复！
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setDeleteDialogOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            取消
          </Button>
          <Button
            onClick={() => handleDelete(deletingGroupName)}
            color="error"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            确认删除
          </Button>
        </DialogActions>
      </Dialog>

    </Box>
  )
}
