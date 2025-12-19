import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Autocomplete,
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
  CircularProgress,
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
import { Trans } from 'react-i18next'
import { ModelGroupConfig } from '../../services/api/config'
import { unifiedConfigApi } from '../../services/api/unified-config'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'

// 常用的 OpenAI 兼容供应商地址（可扩展）
// 注意：供应商名称通过翻译键动态获取，见 EditDialog 组件内部
const OPENAI_COMPAT_PROVIDERS: Array<{ key: string; url: string }> = [
  { key: 'nekroAI', url: 'https://api.nekro.ai/v1' },
  { key: 'googleGemini', url: 'https://generativelanguage.googleapis.com/v1beta/openai' },
  { key: 'tongyiQianwen', url: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { key: 'doubao', url: 'https://ark.cn-beijing.volces.com/api/v3' },
  { key: 'kimi', url: 'https://api.moonshot.cn/v1' },
  { key: 'zhipuQingyan', url: 'https://open.bigmodel.cn/api/paas/v4' },
  { key: 'baiduQianfan', url: 'https://qianfan.baidubce.com/v2' },
  { key: 'iflytekSpark', url: 'https://spark-api-open.xf-yun.com/v1' },
  { key: 'baichuan', url: 'https://api.baichuan-ai.com/v1' },
  { key: 'tencentHunyuan', url: 'https://api.hunyuan.cloud.tencent.com/v1' },
  { key: 'sensetimeRixin', url: 'https://api.sensenova.cn/compatible-mode/v1' },
]

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
  const notification = useNotification()
  const { t } = useTranslation('settings')

  const [modelOptions, setModelOptions] = useState<string[]>([])
  const [fetchingModels, setFetchingModels] = useState(false)

  // 统一输入尺寸与高度，确保按钮与输入框一致
  const inputSize: 'small' | 'medium' = isSmall ? 'small' : 'medium'
  const inputHeight = isSmall ? 40 : 56

  const canFetchModels = Boolean(config.BASE_URL && config.API_KEY && !fetchingModels)
  const fetchTooltipTitle = canFetchModels ? '' : t('modelGroup.helpers.fetchPrecondition')

  // 供应商快捷选项 - 使用翻译获取名称
  const providerOptions = OPENAI_COMPAT_PROVIDERS.map(p => p.url)
  const providerMetaByUrl = new Map(
    OPENAI_COMPAT_PROVIDERS.map(p => [
      p.url,
      t(`modelGroup.providers.${p.key}`) || p.key,
    ])
  )

  interface OpenAIModelListResponse {
    data?: Array<string | { id?: string }>
    models?: Array<string | { id?: string }>
  }

  const buildModelsUrl = (base: string): string => {
    const trimmed = base.trim().replace(/\/$/, '')
    return `${trimmed}/models`
  }

  const parseModelIds = (payload: OpenAIModelListResponse): string[] => {
    const pick = (arr: Array<string | { id?: string }> | undefined) =>
      (arr || [])
        .map(m => (typeof m === 'string' ? m : typeof m.id === 'string' ? m.id : undefined))
        .filter((x): x is string => typeof x === 'string')

    const fromData = pick(payload.data)
    const fromModels = pick(payload.models)
    return Array.from(new Set([...fromData, ...fromModels])).sort()
  }

  const fetchAvailableModels = async () => {
    if (!config.BASE_URL || !config.API_KEY) return
    const url = buildModelsUrl(config.BASE_URL)
    setFetchingModels(true)
    try {
      const resp = await fetch(url, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${config.API_KEY}`,
          'Content-Type': 'application/json',
        },
      })
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      const data: OpenAIModelListResponse = await resp.json()
      const models = parseModelIds(data)
      setModelOptions(models)
      setModelOptions(models)
      if (models.length > 0) {
        notification.success(t('modelGroup.validation.fetchSuccess', { count: models.length }))
      } else {
        notification.info(t('modelGroup.validation.fetchEmpty'))
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t('common.unknownError', { ns: 'common' })
      notification.error(t('modelGroup.validation.fetchError', { error: message }))
    } finally {
      setFetchingModels(false)
    }
  }

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
  }, [initialConfig, open, isCopy])

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
      setGroupNameError(t('modelGroup.validation.nameInvalid'))
    }
    // 验证组名是否已存在
    else if (existingGroups[name] && (isCopy || !initialConfig)) {
      // 当创建新组或复制时，检查名称是否已存在
      setGroupNameError(t('modelGroup.validation.nameExists', { name }))
    } else {
      setGroupNameError('')
    }
    onGroupNameChange(name)
  }

  // 在提交前验证表单
  const handleSubmit = async () => {
    // 去除首尾空白，防止误提交
    const trimmedGroupName = groupName.trim()
    const sanitizedConfig: ModelGroupConfig = {
      ...config,
      CHAT_MODEL: (config.CHAT_MODEL || '').trim(),
      CHAT_PROXY: (config.CHAT_PROXY || '').trim(),
      BASE_URL: (config.BASE_URL || '').trim(),
      API_KEY: (config.API_KEY || '').trim(),
      MODEL_TYPE: (config.MODEL_TYPE || 'chat').trim(),
      EXTRA_BODY: config.EXTRA_BODY ? config.EXTRA_BODY.trim() || null : null,
    }

    // 验证组名
    if (trimmedGroupName && !validateGroupName(trimmedGroupName)) {
      setGroupNameError(t('modelGroup.validation.nameInvalid'))
      return
    }

    // 检查空组名
    if (!trimmedGroupName) {
      setGroupNameError(t('modelGroup.validation.nameRequired'))
      return
    }

    // 检查名称是否已存在（对于新建或复制的情况）
    if (existingGroups[trimmedGroupName] && (isCopy || !initialConfig)) {
      setGroupNameError(t('modelGroup.validation.nameExists', { name: groupName }))
      return
    }

    try {
      await onSubmit(trimmedGroupName, sanitizedConfig)
      onClose()
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message)
      } else {
        setError(t('modelGroup.actions.saveFailed'))
      }
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {isCopy
          ? t('modelGroup.dialog.copyTitle')
          : initialConfig && !isCopy
            ? t('modelGroup.dialog.editTitle')
            : t('modelGroup.dialog.createTitle')}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} className="mt-4">
          <TextField
            label={t('modelGroup.form.groupName')}
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
                  ? t('modelGroup.helpers.nameCopy')
                  : t('modelGroup.helpers.nameChar'))
            }
            inputProps={{
              autoComplete: 'new-password',
              form: {
                autoComplete: 'off',
              },
            }}
          />
          <Autocomplete
            freeSolo
            options={providerOptions}
            value={config.BASE_URL}
            onChange={(_, newValue) => {
              if (typeof newValue === 'string') {
                setConfig({ ...config, BASE_URL: newValue })
              }
            }}
            onInputChange={(_, newInputValue) => {
              setConfig({ ...config, BASE_URL: newInputValue })
            }}
            renderOption={(props, option) => (
              <li {...props} key={option}>
                <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                  <Typography variant="body2">
                    {providerMetaByUrl.get(option) || t('common.custom', { ns: 'common' })}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {option}
                  </Typography>
                </Box>
              </li>
            )}
            renderInput={params => (
              <TextField
                {...params}
                label={t('modelGroup.form.apiAddress')}
                placeholder={t('modelGroup.placeholders.apiAddress')}
                autoComplete="off"
                size={inputSize}
                inputProps={{
                  ...params.inputProps,
                  autoComplete: 'new-password',
                  form: {
                    autoComplete: 'off',
                  },
                }}
                helperText={t('modelGroup.helpers.apiAddress')}
              />
            )}
          />
          <TextField
            label={t('modelGroup.form.apiKey')}
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
          <TextField
            label={t('modelGroup.form.proxyAddress')}
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
          <Stack direction={isMobile ? 'column' : 'row'} spacing={1} alignItems="flex-start">
            <Box sx={{ flex: 1 }}>
              <Autocomplete
                freeSolo
                options={modelOptions}
                value={config.CHAT_MODEL}
                onChange={(_, newValue) => {
                  if (typeof newValue === 'string') {
                    setConfig({ ...config, CHAT_MODEL: newValue })
                  }
                }}
                onInputChange={(_, newInputValue) => {
                  setConfig({ ...config, CHAT_MODEL: newInputValue })
                }}
                renderInput={params => (
                  <TextField
                    {...params}
                    label={t('modelGroup.form.modelName')}
                    autoComplete="off"
                    helperText={t('modelGroup.helpers.modelName')}
                    inputProps={{
                      ...params.inputProps,
                      autoComplete: 'new-password',
                      form: {
                        autoComplete: 'off',
                      },
                    }}
                    size={inputSize}
                  />
                )}
              />
            </Box>
            <Tooltip title={fetchTooltipTitle}>
              <span>
                <Button
                  variant="outlined"
                  onClick={fetchAvailableModels}
                  disabled={!canFetchModels}
                  size={inputSize}
                  sx={{ whiteSpace: 'nowrap', height: inputHeight }}
                >
                  {fetchingModels ? (
                    <>
                      <CircularProgress size={16} sx={{ mr: 1 }} />{' '}
                      {t('modelGroup.actions.fetching')}
                    </>
                  ) : (
                    t('modelGroup.actions.fetchModels')
                  )}
                </Button>
              </span>
            </Tooltip>
          </Stack>
          <TextField
            select
            label={t('modelGroup.form.modelType')}
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

          {/* 模型功能选项 */}
          <Box className="border-t pt-2 mt-2">
            <Typography
              variant="subtitle2"
              className="mb-2"
              sx={{ fontSize: isSmall ? '0.8rem' : 'inherit' }}
            >
              {t('modelGroup.helpers.modelCapabilities') || 'Model Capabilities'}
            </Typography>
            <Stack direction={isMobile ? 'column' : 'row'} spacing={isMobile ? 1 : 4}>
              <Tooltip title={t('modelGroup.helpers.vision')}>
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
                        {t('modelGroup.form.vision')}
                      </Typography>
                    }
                  />
                </div>
              </Tooltip>

              <Tooltip title={t('modelGroup.helpers.cot')}>
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
                        {t('modelGroup.form.cot')}
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
            {showAdvanced
              ? t('modelGroup.helpers.collapseAdvanced')
              : t('modelGroup.helpers.expandAdvanced')}
          </Button>

          {showAdvanced && (
            <Stack spacing={2} className="pl-4 border-l-2 border-gray-200">
              <TextField
                label={t('modelGroup.form.temperature')}
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
                helperText={t('modelGroup.helpers.temperature') || '控制输出的随机性 (0-2)'}
              />
              <TextField
                label={t('modelGroup.form.topP')}
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
                helperText={t('modelGroup.helpers.topP') || '控制输出的多样性 (0-1)'}
              />
              <TextField
                label={t('modelGroup.form.presencePenalty')}
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
                helperText={
                  t('modelGroup.helpers.presencePenalty') ||
                  '基于生成文本中已出现的内容对新内容的惩罚 (-2 到 2)'
                }
              />
              <TextField
                label={t('modelGroup.form.frequencyPenalty')}
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
                helperText={
                  t('modelGroup.helpers.frequencyPenalty') ||
                  '基于生成文本中出现的内容频率对新内容的惩罚 (-2 到 2)'
                }
              />
              <TextField
                label={t('modelGroup.form.extraBody')}
                value={config.EXTRA_BODY ?? ''}
                onChange={e => setConfig({ ...config, EXTRA_BODY: e.target.value || null })}
                fullWidth
                size={isSmall ? 'small' : 'medium'}
                multiline
                rows={3}
                helperText={t('modelGroup.helpers.extraBody') || '额外的请求参数 (JSON 格式)'}
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
          {t('actions.cancel', { ns: 'common' })}
        </Button>
        <Button
          onClick={handleSubmit}
          color="primary"
          disabled={!!groupNameError || !groupName}
          sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
        >
          {isCopy ? t('modelGroup.actions.createCopy') : t('actions.save', { ns: 'common' })}
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
  const [dialogKey, setDialogKey] = useState(0) // 用于控制对话框重建
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingGroupName, setDeletingGroupName] = useState('')
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const { t } = useTranslation('settings')

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
    setDialogKey(prev => prev + 1)
    setEditDialogOpen(true)
  }

  const handleEdit = (name: string) => {
    // 确保每次打开都基于当前 name 和最新配置，避免状态复用
    setEditingGroup({ name: '', config: undefined, isCopy: false })
    setDialogKey(prev => prev + 1)
    // 使用微任务队列确保状态重置后再设置新值，强制 EditDialog 触发 useEffect
    Promise.resolve().then(() => {
      setEditingGroup({ name, config: modelGroups[name] })
      setEditDialogOpen(true)
    })
  }

  // 添加复制模型组功能
  const handleCopy = (name: string) => {
    setEditingGroup({ name: '', config: undefined, isCopy: false })
    setDialogKey(prev => prev + 1)
    Promise.resolve().then(() => {
      setEditingGroup({
        name: name,
        config: { ...modelGroups[name] },
        isCopy: true,
      })
      setEditDialogOpen(true)
    })
  }

  const handleDelete = async (name: string) => {
    try {
      await unifiedConfigApi.deleteModelGroup(name)
      notification.success(t('modelGroup.notifications.deleteSuccess', { name }))
      queryClient.invalidateQueries({ queryKey: ['model-groups'] })
      setDeleteDialogOpen(false)
    } catch (error) {
      if (error instanceof Error) {
        notification.error(error.message)
      } else {
        notification.error(t('modelGroup.notifications.deleteFailed'))
      }
    }
  }

  // 确认删除
  const confirmDelete = (name: string) => {
    setDeletingGroupName(name)
    setDeleteDialogOpen(true)
  }

  const handleSubmit = async (groupName: string, config: ModelGroupConfig) => {
    // 统一裁剪，防止误输入空白
    const trimmedName = groupName.trim()
    const sanitizedConfig: ModelGroupConfig = {
      ...config,
      CHAT_MODEL: (config.CHAT_MODEL || '').trim(),
      CHAT_PROXY: (config.CHAT_PROXY || '').trim(),
      BASE_URL: (config.BASE_URL || '').trim(),
      API_KEY: (config.API_KEY || '').trim(),
      MODEL_TYPE: (config.MODEL_TYPE || 'chat').trim(),
      EXTRA_BODY: config.EXTRA_BODY ? config.EXTRA_BODY.trim() || null : null,
    }
    // 检查新模型组名称是否已存在
    if (modelGroups[trimmedName] && !editingGroup.isCopy && editingGroup.name === trimmedName) {
      // 如果是编辑已有模型组，允许相同名称
      await unifiedConfigApi.updateModelGroup(trimmedName, sanitizedConfig)
      notification.success(t('modelGroup.notifications.saveSuccess'))
    } else if (!modelGroups[trimmedName]) {
      // 如果是新建或复制模型组，名称必须不存在
      await unifiedConfigApi.updateModelGroup(trimmedName, sanitizedConfig)
      notification.success(
        editingGroup.isCopy
          ? t('modelGroup.notifications.copySuccess', { name: trimmedName })
          : t('modelGroup.notifications.saveSuccess')
      )
    } else {
      // 如果是已有名称
      notification.error(t('modelGroup.notifications.nameExists', { name: trimmedName }))
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
          <Trans
            i18nKey="modelGroup.alert.providerSupport"
            t={t}
            components={{
              link: (
                <Link
                  href="https://api.nekro.ai"
                  target="_blank"
                  rel="noopener"
                  style={{ cursor: 'pointer' }}
                />
              ),
            }}
          />
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
          {t('modelGroup.dialog.createTitle')}
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
                  {t('modelGroup.table.groupName')}
                </TableCell>
                <TableCell
                  width={isMobile ? '18%' : '15%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.modelName')}
                </TableCell>
                <TableCell
                  width={isMobile ? '15%' : '10%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.modelType')}
                </TableCell>
                {!isSmall && (
                  <TableCell
                    width="18%"
                    sx={{
                      py: isSmall ? 1 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                    }}
                  >
                    {t('modelGroup.table.apiAddress')}
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
                    {t('modelGroup.table.proxyAddress')}
                  </TableCell>
                )}
                <TableCell
                  width={isMobile ? '23%' : '15%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.features')}
                </TableCell>
                <TableCell
                  width={isMobile ? '30%' : '15%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.actions')}
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
                      <Tooltip
                        title={
                          config.ENABLE_VISION
                            ? t('modelGroup.chips.visionSupported')
                            : t('modelGroup.chips.visionUnsupported')
                        }
                      >
                        <Chip
                          icon={<ImageIcon fontSize="small" />}
                          label={t('modelGroup.chips.vision')}
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
                      <Tooltip
                        title={
                          config.ENABLE_COT
                            ? t('modelGroup.chips.cotEnabled')
                            : t('modelGroup.chips.cotDisabled')
                        }
                      >
                        <Chip
                          icon={<PsychologyIcon fontSize="small" />}
                          label={t('modelGroup.chips.cot')}
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
                      <Tooltip title={t('modelGroup.tooltips.visitProvider')} arrow>
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
                      <Tooltip title={t('modelGroup.tooltips.edit')} arrow>
                        <IconButton
                          onClick={() => handleEdit(name)}
                          size="small"
                          color="warning"
                          sx={{ p: isSmall ? 0.5 : 1 }}
                        >
                          <EditIcon fontSize={isSmall ? 'small' : 'medium'} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={t('modelGroup.tooltips.copy')} arrow>
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
                        title={
                          name === 'default'
                            ? t('modelGroup.tooltips.defaultDelete')
                            : t('modelGroup.tooltips.delete')
                        }
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

      {/* EditDialog 使用稳定的 key，避免输入时重置 */}
      <EditDialog
        key={dialogKey}
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
        <DialogTitle>{t('modelGroup.deleteDialog.title')}</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: isSmall ? '0.9rem' : 'inherit' }}>
            {t('modelGroup.deleteDialog.content', { name: deletingGroupName })}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setDeleteDialogOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('actions.cancel', { ns: 'common' })}
          </Button>
          <Button
            onClick={() => handleDelete(deletingGroupName)}
            color="error"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('modelGroup.deleteDialog.confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
