import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Autocomplete,
  Stack,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
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
  NetworkCheck as NetworkCheckIcon,
} from '@mui/icons-material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ModelGroupConfig } from '../../services/api/config'
import { unifiedConfigApi, ModelGroupTestItem } from '../../services/api/unified-config'
import { getLocalizedText, OPENAI_COMPAT_PROVIDERS } from '../../config/model-presets'
import { CHIP_VARIANTS, UNIFIED_TABLE_STYLES } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'
import ActionButton from '../../components/common/ActionButton'
import IconActionButton from '../../components/common/IconActionButton'
import SearchField from '../../components/common/SearchField'

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
  const { t, i18n } = useTranslation('settings')

  const [modelOptions, setModelOptions] = useState<string[]>([])
  const [fetchingModels, setFetchingModels] = useState(false)
  const [testingModel, setTestingModel] = useState(false)
  const [testResult, setTestResult] = useState<ModelGroupTestItem | null>(null)

  // 统一输入尺寸与高度，确保按钮与输入框一致
  const inputSize: 'small' | 'medium' = isSmall ? 'small' : 'medium'
  const inputHeight = isSmall ? 40 : 56

  const canFetchModels = Boolean(config.BASE_URL && config.API_KEY && !fetchingModels)
  const fetchTooltipTitle = canFetchModels ? '' : t('modelGroup.helpers.fetchPrecondition')

  // 供应商快捷选项 - 使用翻译获取名称
  const providerOptions = OPENAI_COMPAT_PROVIDERS.map(p => p.url)
  const providerMetaByUrl = new Map(
    OPENAI_COMPAT_PROVIDERS.map(p => [p.url, getLocalizedText(p.label, i18n.resolvedLanguage)])
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

  const handleTestModel = async () => {
    if (!config.CHAT_MODEL || !config.BASE_URL || !config.API_KEY) return
    setTestingModel(true)
    setTestResult(null)
    try {
      const item = await unifiedConfigApi.testModelGroupInline({
        group_name: groupName || 'inline-test',
        chat_model: config.CHAT_MODEL,
        base_url: config.BASE_URL,
        api_key: config.API_KEY,
        model_type: config.MODEL_TYPE || 'chat',
        chat_proxy: config.CHAT_PROXY || undefined,
        temperature: config.TEMPERATURE ?? undefined,
        top_p: config.TOP_P ?? undefined,
        top_k: config.TOP_K ?? undefined,
        presence_penalty: config.PRESENCE_PENALTY ?? undefined,
        frequency_penalty: config.FREQUENCY_PENALTY ?? undefined,
        extra_body: config.EXTRA_BODY ?? undefined,
      })
      setTestResult(item)
      if (item.success) {
        notification.success(t('modelGroup.notifications.testPassed'))
      } else {
        notification.warning(t('modelGroup.notifications.testFailed'))
      }
    } catch (err) {
      notification.error(err instanceof Error ? err.message : t('modelGroup.notifications.testError'))
    } finally {
      setTestingModel(false)
    }
  }

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
                    WebkitTextSecurity: 'disc',
                  } as React.CSSProperties)
                : undefined,
            }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconActionButton
                    onClick={() => setShowApiKey(!showApiKey)}
                    edge="end"
                    size={isSmall ? 'small' : 'medium'}
                    title={showApiKey ? t('actions.hide', { ns: 'common', defaultValue: '隐藏' }) : t('actions.show', { ns: 'common', defaultValue: '显示' })}
                  >
                    {showApiKey ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconActionButton>
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
                <ActionButton
                  tone="secondary"
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
                </ActionButton>
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
                      {t(`modelGroup.types.${type.value as 'chat' | 'embedding' | 'draw'}`, {
                        defaultValue: type.label,
                      })}
                    </Typography>
                    {type.description && (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontSize: isSmall ? '0.7rem' : 'inherit' }}
                      >
                        {t(
                          `modelGroup.typeDescriptions.${type.value as 'chat' | 'embedding' | 'draw'}`,
                          {
                            defaultValue: type.description,
                          }
                        )}
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
          <ActionButton
            tone="ghost"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="self-start"
            size={isSmall ? 'small' : 'medium'}
          >
            {showAdvanced
              ? t('modelGroup.helpers.collapseAdvanced')
              : t('modelGroup.helpers.expandAdvanced')}
          </ActionButton>

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

          {testResult && (
            <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mt: 1 }}>
              {testResult.success ? (
                <Stack spacing={0.25}>
                  <Typography variant="caption" component="div">
                    {t('modelGroup.health.tooltipPassed')} · {testResult.latency_ms}ms
                  </Typography>
                  {testResult.used_model && (
                    <Typography variant="caption" component="div" color="text.secondary">
                      {t('modelGroup.health.tooltipModel', { model: testResult.used_model })}
                    </Typography>
                  )}
                  {((testResult.input_tokens ?? 0) > 0 || (testResult.output_tokens ?? 0) > 0) && (
                    <Typography variant="caption" component="div" color="text.secondary">
                      {t('modelGroup.health.tooltipTokens', {
                        input: testResult.input_tokens ?? 0,
                        output: testResult.output_tokens ?? 0,
                      })}
                    </Typography>
                  )}
                  {testResult.response_text && (
                    <Typography variant="caption" component="div" color="text.secondary"
                      sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 60, overflow: 'auto' }}>
                      {t('modelGroup.health.tooltipReply', { text: testResult.response_text.trim() })}
                    </Typography>
                  )}
                </Stack>
              ) : (
                <Typography variant="caption" component="div">
                  {testResult.error_message || t('modelGroup.health.failed')}
                </Typography>
              )}
            </Alert>
          )}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, gap: 1 }}>
        {(config.MODEL_TYPE === 'chat' || config.MODEL_TYPE === 'embedding') && (
          <Tooltip
            title={
              !config.CHAT_MODEL || !config.BASE_URL || !config.API_KEY
                ? t('modelGroup.tooltips.testNeedsConfig')
                : ''
            }
            arrow
          >
            <span>
              <ActionButton
                tone="secondary"
                onClick={handleTestModel}
                size="small"
                startIcon={testingModel ? <CircularProgress size={14} /> : <NetworkCheckIcon />}
                disabled={testingModel || !config.CHAT_MODEL || !config.BASE_URL || !config.API_KEY}
                sx={{ mr: 'auto' }}
              >
                {t('modelGroup.actions.test')}
              </ActionButton>
            </span>
          </Tooltip>
        )}
        <ActionButton
          tone="secondary"
          onClick={onClose}
          sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
        >
          {t('actions.cancel', { ns: 'common' })}
        </ActionButton>
        <ActionButton
          tone="primary"
          onClick={handleSubmit}
          disabled={!!groupNameError || !groupName}
          sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
        >
          {isCopy ? t('modelGroup.actions.createCopy') : t('actions.save', { ns: 'common' })}
        </ActionButton>
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
  const [dialogKey, setDialogKey] = useState(0)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingGroupName, setDeletingGroupName] = useState('')
  const [searchText, setSearchText] = useState('')
  const [testingGroups, setTestingGroups] = useState<Set<string>>(new Set())
  const [testResults, setTestResults] = useState<Record<string, ModelGroupTestItem>>({})
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
    if (!type) return t('modelGroup.types.chat', { ns: 'settings', defaultValue: '聊天' })
    return t(`modelGroup.types.${type as 'chat' | 'embedding' | 'draw'}`, {
      ns: 'settings',
      defaultValue: modelTypes.find(mt => mt.value === type)?.label || type,
    })
  }

  // 将模型类型映射到主题颜色值（用于 CHIP_VARIANTS）
  const getModelTypeThemeColor = (type: string | undefined): string => {
    if (!type) return theme.palette.primary.main
    const found = modelTypes.find(t => t.value === type)
    const color = found?.color as string | undefined
    switch (color) {
      case 'primary':
        return theme.palette.primary.main
      case 'secondary':
        return theme.palette.secondary.main
      case 'error':
        return theme.palette.error.main
      case 'info':
        return theme.palette.info.main
      case 'success':
        return theme.palette.success.main
      case 'warning':
        return theme.palette.warning.main
      default:
        return theme.palette.primary.main
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

  const runTest = async (groupName: string) => {
    if (testingGroups.has(groupName)) return
    setTestingGroups(prev => new Set([...prev, groupName]))
    try {
      const items = await unifiedConfigApi.testModelGroups([groupName])
      const item = items[0]
      if (item) {
        setTestResults(prev => ({ ...prev, [groupName]: item }))
        if (item.success) {
          notification.success(t('modelGroup.notifications.testPassed'))
        } else {
          notification.warning(t('modelGroup.notifications.testFailed'))
        }
      }
    } catch (err) {
      notification.error(err instanceof Error ? err.message : t('modelGroup.notifications.testError'))
    } finally {
      setTestingGroups(prev => {
        const next = new Set(prev)
        next.delete(groupName)
        return next
      })
    }
  }

  const renderTestTooltip = (result: ModelGroupTestItem) => (
    <Box sx={{ maxWidth: 320 }}>
      <Typography variant="caption" sx={{ display: 'block', fontWeight: 700, mb: 0.5 }}>
        {result.success ? t('modelGroup.health.tooltipPassed') : t('modelGroup.health.tooltipFailed')}
      </Typography>
      <Typography variant="caption" sx={{ display: 'block' }}>
        {t('modelGroup.health.tooltipModel', { model: result.used_model || result.model_name || '-' })}
      </Typography>
      <Typography variant="caption" sx={{ display: 'block' }}>
        {t('modelGroup.health.tooltipLatency', { ms: result.latency_ms })}
      </Typography>
      {result.success ? (
        <>
          {((result.input_tokens ?? 0) > 0 || (result.output_tokens ?? 0) > 0) && (
            <Typography variant="caption" sx={{ display: 'block' }}>
              {t('modelGroup.health.tooltipTokens', {
                input: result.input_tokens ?? 0,
                output: result.output_tokens ?? 0,
              })}
            </Typography>
          )}
          <Typography variant="caption" sx={{ display: 'block', mt: 0.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {t('modelGroup.health.tooltipReply', { text: result.response_text?.trim() || '-' })}
          </Typography>
        </>
      ) : (
        <Typography variant="caption" sx={{ display: 'block', mt: 0.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {t('modelGroup.health.tooltipError', { error: result.error_message || '-' })}
        </Typography>
      )}
    </Box>
  )

  const filteredModelGroups = Object.fromEntries(
    Object.entries(modelGroups).filter(([name, config]) => {
      if (!searchText.trim()) return true
      const kw = searchText.trim().toLowerCase()
      return (
        name.toLowerCase().includes(kw) ||
        config.CHAT_MODEL.toLowerCase().includes(kw) ||
        (config.BASE_URL || '').toLowerCase().includes(kw) ||
        (config.MODEL_TYPE || '').toLowerCase().includes(kw)
      )
    })
  )

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 顶部提示 */}
      <Alert severity="info" sx={{ mb: 1.5, flexShrink: 0 }}>
        {t('modelGroup.alert.providerSupportBefore')}
        <Link href="https://api.nekro.ai" target="_blank" rel="noopener noreferrer">
          {t('modelGroup.alert.providerSupportLink')}
        </Link>
        {t('modelGroup.alert.providerSupportAfter')}
      </Alert>

      {/* 顶部工具栏 */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          mb: 1.5,
          flexShrink: 0,
          gap: 1,
        }}
      >
        <SearchField
          size="small"
          value={searchText}
          onChange={setSearchText}
          placeholder={t('modelGroup.actions.searchPlaceholder')}
          sx={{ flex: 1 }}
        />
        <ActionButton
          tone="primary"
          startIcon={<AddIcon />}
          onClick={handleAdd}
          size="small"
          sx={{ height: 40, whiteSpace: 'nowrap', flexShrink: 0 }}
        >
          {t('modelGroup.actions.createBtn')}
        </ActionButton>
      </Box>

      {/* 表格容器 */}
      <Paper
        elevation={0}
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
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    whiteSpace: 'nowrap',
                    minWidth: 80,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.groupName')}
                </TableCell>
                <TableCell
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    whiteSpace: 'nowrap',
                    minWidth: 120,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.modelName')}
                </TableCell>
                <TableCell
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    whiteSpace: 'nowrap',
                    minWidth: 80,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.modelType')}
                </TableCell>
                {!isSmall && (
                  <TableCell
                    sx={{
                      py: isSmall ? 1 : 1.5,
                      whiteSpace: 'nowrap',
                      minWidth: 160,
                      ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                    }}
                  >
                    {t('modelGroup.table.apiAddress')}
                  </TableCell>
                )}
                {!isMobile && (
                  <TableCell
                    sx={{
                      py: isSmall ? 1 : 1.5,
                      whiteSpace: 'nowrap',
                      minWidth: 60,
                      ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                    }}
                  >
                    {t('modelGroup.table.proxyAddress')}
                  </TableCell>
                )}
                <TableCell
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    whiteSpace: 'nowrap',
                    minWidth: 100,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.features')}
                </TableCell>
                <TableCell
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    whiteSpace: 'nowrap',
                    minWidth: 80,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.health')}
                </TableCell>
                <TableCell
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    whiteSpace: 'nowrap',
                    minWidth: 80,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  {t('modelGroup.table.actions')}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(filteredModelGroups).map(([name, config]) => (
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
                      variant="outlined"
                      sx={CHIP_VARIANTS.getCustomColorChip(getModelTypeThemeColor(config.MODEL_TYPE), isSmall)}
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
                          variant="outlined"
                          sx={CHIP_VARIANTS.getCustomColorChip(
                            config.ENABLE_VISION
                              ? theme.palette.primary.main
                              : theme.palette.text.secondary,
                            isSmall
                          )}
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
                          variant="outlined"
                          sx={CHIP_VARIANTS.getCustomColorChip(
                            config.ENABLE_COT
                              ? theme.palette.secondary.main
                              : theme.palette.text.secondary,
                            isSmall
                          )}
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
                    {config.MODEL_TYPE !== 'chat' && config.MODEL_TYPE !== 'embedding' ? (
                      <Typography variant="caption" color="text.secondary">-</Typography>
                    ) : testingGroups.has(name) ? (
                      <Chip
                        size="small"
                        variant="outlined"
                        icon={<CircularProgress size={12} />}
                        label={t('modelGroup.health.testing')}
                        sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.info.main, isSmall)}
                      />
                    ) : testResults[name] ? (
                      <Tooltip title={renderTestTooltip(testResults[name])} arrow>
                        {testResults[name].success ? (
                          <Chip
                            size="small"
                            variant="outlined"
                            label={t('modelGroup.health.ok', { ms: testResults[name].latency_ms })}
                            sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.success.main, isSmall)}
                          />
                        ) : (
                          <Chip
                            size="small"
                            variant="outlined"
                            label={t('modelGroup.health.failed')}
                            sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.error.main, isSmall)}
                          />
                        )}
                      </Tooltip>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        {t('modelGroup.health.notTested')}
                      </Typography>
                    )}
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
                        <IconActionButton
                          tone="primary"
                          onClick={() => window.open(getBaseUrl(config.BASE_URL), '_blank')}
                          size="small"
                          disabled={!config.BASE_URL}
                          sx={{ p: 0.5 }}
                        >
                          <LaunchIcon fontSize="small" />
                        </IconActionButton>
                      </Tooltip>
                      <Tooltip
                        title={config.MODEL_TYPE !== 'chat' && config.MODEL_TYPE !== 'embedding' ? t('modelGroup.tooltips.testOnlyChat') : t('modelGroup.tooltips.test')}
                        arrow
                      >
                        <span>
                          <IconActionButton
                            tone="primary"
                            onClick={() => runTest(name)}
                            size="small"
                            disabled={(config.MODEL_TYPE !== 'chat' && config.MODEL_TYPE !== 'embedding') || testingGroups.has(name)}
                            sx={{ p: 0.5 }}
                          >
                            {testingGroups.has(name)
                              ? <CircularProgress size={16} />
                              : <NetworkCheckIcon fontSize="small" />
                            }
                          </IconActionButton>
                        </span>
                      </Tooltip>
                      <Tooltip title={t('modelGroup.tooltips.edit')} arrow>
                        <IconActionButton
                          onClick={() => handleEdit(name)}
                          size="small"
                          sx={{ p: 0.5 }}
                        >
                          <EditIcon fontSize="small" />
                        </IconActionButton>
                      </Tooltip>
                      <Tooltip title={t('modelGroup.tooltips.copy')} arrow>
                        <IconActionButton
                          onClick={() => handleCopy(name)}
                          size="small"
                          sx={{ p: 0.5 }}
                        >
                          <ContentCopyIcon fontSize="small" />
                        </IconActionButton>
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
                          <IconActionButton
                            tone="danger"
                            onClick={() => name !== 'default' && confirmDelete(name)}
                            size="small"
                            disabled={name === 'default'}
                            sx={{ p: 0.5 }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconActionButton>
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
          <ActionButton
            tone="secondary"
            onClick={() => setDeleteDialogOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('actions.cancel', { ns: 'common' })}
          </ActionButton>
          <ActionButton
            tone="danger"
            onClick={() => handleDelete(deletingGroupName)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('modelGroup.deleteDialog.confirm')}
          </ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
