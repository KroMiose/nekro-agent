import { useState, useEffect, useMemo } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Stack,
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
  Chip,
  MenuItem,
  CircularProgress,
  Tooltip,
  Alert,
  Link,
  SxProps,
  Theme,
  useTheme,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  RemoveCircleOutline as RemoveIcon,
  NetworkCheck as NetworkCheckIcon,
  ContentCopy as ContentCopyIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  CC_MODEL_SOURCE_PRESETS,
  DEFAULT_CC_EXTRA_ENV,
  getLocalizedText,
} from '../../config/model-presets'
import {
  ccModelPresetApi,
  CCModelPresetInfo,
  CCModelPresetCreate,
  CCModelPresetTestItem,
} from '../../services/api/cc-model-preset'
import { workspaceApi } from '../../services/api/workspace'
import { CHIP_VARIANTS, UNIFIED_TABLE_STYLES } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'
import SearchField from '../../components/common/SearchField'
import ActionButton from '../../components/common/ActionButton'
import IconActionButton from '../../components/common/IconActionButton'

interface EnvPair {
  key: string
  value: string
}

interface PresetFormState {
  name: string
  description: string
  base_url: string
  auth_token: string
  api_timeout_ms: string
  model_type: 'preset' | 'manual'
  preset_model: string
  anthropic_model: string
  small_fast_model: string
  default_sonnet: string
  default_opus: string
  default_haiku: string
  extra_env: EnvPair[]
}

function recordToEnvPairs(record: Record<string, string>): EnvPair[] {
  return Object.entries(record).map(([key, value]) => ({ key, value }))
}

function envPairsToRecord(pairs: EnvPair[]): Record<string, string> {
  const result: Record<string, string> = {}
  for (const { key, value } of pairs) {
    if (key.trim()) result[key.trim()] = value
  }
  return result
}

const DEFAULT_FORM: PresetFormState = {
  name: '',
  description: '',
  base_url: 'https://api.nekro.ai/claude',
  auth_token: '',
  api_timeout_ms: '3000000',
  model_type: 'preset',
  preset_model: 'opus',
  anthropic_model: '',
  small_fast_model: '',
  default_sonnet: '',
  default_opus: '',
  default_haiku: '',
  extra_env: DEFAULT_CC_EXTRA_ENV.map(pair => ({ ...pair })),
}

function computeConfigJson(form: PresetFormState): Record<string, unknown> {
  const env: Record<string, string> = {
    ANTHROPIC_BASE_URL: form.base_url,
    ANTHROPIC_AUTH_TOKEN: form.auth_token,
    API_TIMEOUT_MS: form.api_timeout_ms,
  }
  if (form.model_type === 'manual') {
    if (form.anthropic_model) env['ANTHROPIC_MODEL'] = form.anthropic_model
    if (form.small_fast_model) env['ANTHROPIC_SMALL_FAST_MODEL'] = form.small_fast_model
    if (form.default_sonnet) env['ANTHROPIC_DEFAULT_SONNET_MODEL'] = form.default_sonnet
    if (form.default_opus) env['ANTHROPIC_DEFAULT_OPUS_MODEL'] = form.default_opus
    if (form.default_haiku) env['ANTHROPIC_DEFAULT_HAIKU_MODEL'] = form.default_haiku
  }
  for (const { key, value } of form.extra_env) {
    if (key.trim()) env[key.trim()] = value
  }
  if (form.model_type === 'preset') {
    return { env, model: form.preset_model, includeCoAuthoredBy: false }
  }
  return { env, includeCoAuthoredBy: false }
}

interface EditDialogProps {
  open: boolean
  onClose: () => void
  initial?: CCModelPresetInfo
  isCopy?: boolean
  onSuccess: () => void
}

function EditDialog({ open, onClose, initial, isCopy, onSuccess }: EditDialogProps) {
  const [form, setForm] = useState<PresetFormState>(DEFAULT_FORM)
  const [sourcePresetId, setSourcePresetId] = useState('')
  const [showToken, setShowToken] = useState(false)
  const notification = useNotification()
  const { t, i18n } = useTranslation('workspace')
  const selectedSourcePreset = CC_MODEL_SOURCE_PRESETS.find(item => item.id === sourcePresetId)

  const createMutation = useMutation({
    mutationFn: (body: CCModelPresetCreate) => ccModelPresetApi.create(body),
    onSuccess: () => {
      notification.success(t('ccModels.notifications.created'))
      onSuccess()
      onClose()
    },
    onError: (err: Error) =>
      notification.error(t('ccModels.notifications.createFailed', { message: err.message })),
  })

  const updateMutation = useMutation({
    mutationFn: (body: CCModelPresetCreate) => ccModelPresetApi.update(initial!.id, body),
    onSuccess: () => {
      notification.success(t('ccModels.notifications.saved'))
      onSuccess()
      onClose()
    },
    onError: (err: Error) =>
      notification.error(t('ccModels.notifications.saveFailed', { message: err.message })),
  })

  useEffect(() => {
    if (open) {
      if (initial) {
        setForm({
          name: isCopy ? '' : initial.name,
          description: initial.description,
          base_url: initial.base_url,
          auth_token: initial.auth_token,
          api_timeout_ms: initial.api_timeout_ms,
          model_type: initial.model_type as 'preset' | 'manual',
          preset_model: initial.preset_model,
          anthropic_model: initial.anthropic_model,
          small_fast_model: initial.small_fast_model,
          default_sonnet: initial.default_sonnet,
          default_opus: initial.default_opus,
          default_haiku: initial.default_haiku,
          extra_env: recordToEnvPairs(initial.extra_env),
        })
      } else {
        setForm(DEFAULT_FORM)
      }
      setSourcePresetId('')
      setShowToken(false)
    }
  }, [open, initial, isCopy])

  const isPending = createMutation.isPending || updateMutation.isPending

  const handleSubmit = () => {
    if (!form.name.trim()) return
    const body: CCModelPresetCreate = {
      name: form.name.trim(),
      description: form.description,
      base_url: form.base_url,
      auth_token: form.auth_token,
      api_timeout_ms: form.api_timeout_ms,
      model_type: form.model_type,
      preset_model: form.preset_model,
      anthropic_model: form.anthropic_model,
      small_fast_model: form.small_fast_model,
      default_sonnet: form.default_sonnet,
      default_opus: form.default_opus,
      default_haiku: form.default_haiku,
      extra_env: envPairsToRecord(form.extra_env),
    }
    if (initial && !isCopy) {
      updateMutation.mutate(body)
    } else {
      createMutation.mutate(body)
    }
  }

  const addEnvPair = () =>
    setForm(prev => ({ ...prev, extra_env: [...prev.extra_env, { key: '', value: '' }] }))
  const removeEnvPair = (idx: number) =>
    setForm(prev => ({ ...prev, extra_env: prev.extra_env.filter((_, i) => i !== idx) }))
  const updateEnvPair = (idx: number, field: 'key' | 'value', val: string) =>
    setForm(prev => {
      const pairs = [...prev.extra_env]
      pairs[idx] = { ...pairs[idx], [field]: val }
      return { ...prev, extra_env: pairs }
    })

  const applySourcePreset = (presetId: string) => {
    setSourcePresetId(presetId)
    if (!presetId) return

    const preset = CC_MODEL_SOURCE_PRESETS.find(item => item.id === presetId)
    if (!preset) return

    setForm(prev => ({
      ...prev,
      base_url: preset.form.base_url,
      api_timeout_ms: preset.form.api_timeout_ms,
      model_type: preset.form.model_type,
      preset_model: preset.form.preset_model,
      anthropic_model: preset.form.anthropic_model,
      small_fast_model: preset.form.small_fast_model,
      default_sonnet: preset.form.default_sonnet,
      default_opus: preset.form.default_opus,
      default_haiku: preset.form.default_haiku,
      extra_env: preset.form.extra_env.map(pair => ({ ...pair })),
    }))
  }

  const configPreview = JSON.stringify(computeConfigJson(form), null, 2)

  return (
    <Dialog open={open} onClose={() => !isPending && onClose()} maxWidth="md" fullWidth>
      <DialogTitle>
        {isCopy
          ? t('ccModels.dialog.titleCopy')
          : initial
            ? t('ccModels.dialog.titleEdit')
            : t('ccModels.dialog.titleCreate')}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {/* 基本信息 */}
          <TextField
            label={t('ccModels.dialog.name')}
            value={form.name}
            onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
            fullWidth
            required
            size="small"
            autoComplete="off"
            disabled={!!initial && !isCopy}
            helperText={initial && !isCopy ? t('ccModels.dialog.nameReadonly') : ''}
          />
          <TextField
            label={t('ccModels.dialog.desc')}
            value={form.description}
            onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))}
            fullWidth
            size="small"
            multiline
            rows={2}
            autoComplete="off"
          />

          {/* 通用 API 配置 */}
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mt: 1 }}>
            {t('ccModels.dialog.sectionApi')}
          </Typography>
          <TextField
            label={t('ccModels.dialog.sourcePreset')}
            select
            value={sourcePresetId}
            onChange={e => applySourcePreset(e.target.value)}
            fullWidth
            size="small"
            helperText={t('ccModels.dialog.sourcePresetHint')}
          >
            <MenuItem value="">{t('ccModels.dialog.sourcePresetCustom')}</MenuItem>
            {CC_MODEL_SOURCE_PRESETS.map(preset => (
              <MenuItem key={preset.id} value={preset.id}>
                {getLocalizedText(preset.label, i18n.resolvedLanguage)}
              </MenuItem>
            ))}
          </TextField>
          {selectedSourcePreset && (
            <Alert severity="info" variant="outlined">
              {getLocalizedText(selectedSourcePreset.note, i18n.resolvedLanguage)}
            </Alert>
          )}
          <TextField
            label="Base URL"
            value={form.base_url}
            onChange={e => setForm(prev => ({ ...prev, base_url: e.target.value }))}
            fullWidth
            size="small"
            autoComplete="off"
            helperText="ANTHROPIC_BASE_URL"
          />
          <TextField
            label="Auth Token"
            value={form.auth_token}
            onChange={e => setForm(prev => ({ ...prev, auth_token: e.target.value }))}
            fullWidth
            size="small"
            autoComplete="off"
            helperText="ANTHROPIC_AUTH_TOKEN"
            inputProps={{
              autoComplete: 'new-password',
              style: !showToken
                ? ({
                    WebkitTextSecurity: 'disc',
                  } as React.CSSProperties)
                : undefined,
            }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconActionButton onClick={() => setShowToken(v => !v)} edge="end" size="small">
                    {showToken ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconActionButton>
                </InputAdornment>
              ),
            }}
          />
          <TextField
            label={t('ccModels.dialog.timeout')}
            value={form.api_timeout_ms}
            onChange={e => setForm(prev => ({ ...prev, api_timeout_ms: e.target.value }))}
            size="small"
            autoComplete="off"
            helperText="API_TIMEOUT_MS"
            fullWidth
          />

          {/* 模型类型 */}
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mt: 1 }}>
            {t('ccModels.dialog.sectionModel')}
          </Typography>
          <TextField
            label={t('ccModels.dialog.modelType')}
            select
            value={form.model_type}
            onChange={e =>
              setForm(prev => ({ ...prev, model_type: e.target.value as 'preset' | 'manual' }))
            }
            size="small"
            fullWidth
          >
            <MenuItem value="preset">{t('ccModels.dialog.modelTypePreset')}</MenuItem>
            <MenuItem value="manual">{t('ccModels.dialog.modelTypeManual')}</MenuItem>
          </TextField>

          {form.model_type === 'preset' ? (
            <TextField
              label={t('ccModels.dialog.presetModel')}
              select
              value={form.preset_model}
              onChange={e => setForm(prev => ({ ...prev, preset_model: e.target.value }))}
              size="small"
              fullWidth
              helperText={t('ccModels.dialog.presetModelHint')}
            >
              <MenuItem value="opus">opus</MenuItem>
              <MenuItem value="sonnet">sonnet</MenuItem>
              <MenuItem value="haiku">haiku</MenuItem>
            </TextField>
          ) : (
            <Stack spacing={2}>
              <TextField
                label="ANTHROPIC_MODEL"
                value={form.anthropic_model}
                onChange={e => setForm(prev => ({ ...prev, anthropic_model: e.target.value }))}
                size="small"
                fullWidth
                autoComplete="off"
                placeholder={t('ccModels.dialog.emptyMeans')}
              />
              <TextField
                label="ANTHROPIC_SMALL_FAST_MODEL"
                value={form.small_fast_model}
                onChange={e => setForm(prev => ({ ...prev, small_fast_model: e.target.value }))}
                size="small"
                fullWidth
                autoComplete="off"
                placeholder={t('ccModels.dialog.emptyMeans')}
              />
              <TextField
                label="ANTHROPIC_DEFAULT_SONNET_MODEL"
                value={form.default_sonnet}
                onChange={e => setForm(prev => ({ ...prev, default_sonnet: e.target.value }))}
                size="small"
                fullWidth
                autoComplete="off"
                placeholder={t('ccModels.dialog.emptyMeans')}
              />
              <TextField
                label="ANTHROPIC_DEFAULT_OPUS_MODEL"
                value={form.default_opus}
                onChange={e => setForm(prev => ({ ...prev, default_opus: e.target.value }))}
                size="small"
                fullWidth
                autoComplete="off"
                placeholder={t('ccModels.dialog.emptyMeans')}
              />
              <TextField
                label="ANTHROPIC_DEFAULT_HAIKU_MODEL"
                value={form.default_haiku}
                onChange={e => setForm(prev => ({ ...prev, default_haiku: e.target.value }))}
                size="small"
                fullWidth
                autoComplete="off"
                placeholder={t('ccModels.dialog.emptyMeans')}
              />
            </Stack>
          )}

          {/* 自定义附加变量 */}
          <Box
            sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 1 }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              {t('ccModels.dialog.sectionEnv')}
            </Typography>
            <ActionButton size="small" startIcon={<AddIcon />} onClick={addEnvPair} sx={{ minWidth: 0 }}>
              {t('ccModels.dialog.envAdd')}
            </ActionButton>
          </Box>
          {form.extra_env.length === 0 ? (
            <Typography variant="caption" color="text.disabled" sx={{ pl: 0.5 }}>
              {t('ccModels.dialog.envEmpty')}
            </Typography>
          ) : (
            <Stack spacing={1}>
              {form.extra_env.map((pair, idx) => (
                <Stack key={idx} direction="row" spacing={1} alignItems="center">
                  <TextField
                    placeholder="KEY"
                    value={pair.key}
                    onChange={e => updateEnvPair(idx, 'key', e.target.value)}
                    size="small"
                    autoComplete="off"
                    inputProps={{ style: { fontFamily: 'monospace', fontSize: '0.8rem' } }}
                    sx={{ flex: 1 }}
                  />
                  <TextField
                    placeholder="VALUE"
                    value={pair.value}
                    onChange={e => updateEnvPair(idx, 'value', e.target.value)}
                    size="small"
                    autoComplete="off"
                    inputProps={{ style: { fontFamily: 'monospace', fontSize: '0.8rem' } }}
                    sx={{ flex: 2 }}
                  />
                  <IconActionButton size="small" tone="danger" onClick={() => removeEnvPair(idx)}>
                    <RemoveIcon fontSize="small" />
                  </IconActionButton>
                </Stack>
              ))}
            </Stack>
          )}

          {/* 配置预览 */}
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mt: 1 }}>
            {t('ccModels.dialog.sectionPreview')}
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={8}
            size="small"
            value={configPreview}
            InputProps={{ readOnly: true }}
            inputProps={{
              style: {
                fontFamily: '"SFMono-Regular", Consolas, monospace',
                fontSize: '0.78rem',
              },
            }}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <ActionButton tone="secondary" onClick={onClose} disabled={isPending}>
          {t('ccModels.dialog.cancel')}
        </ActionButton>
        <ActionButton
          tone="primary"
          onClick={handleSubmit}
          disabled={isPending || !form.name.trim()}
        >
          {isPending ? (
            <CircularProgress size={18} />
          ) : initial ? (
            t('ccModels.dialog.save')
          ) : (
            t('ccModels.dialog.create')
          )}
        </ActionButton>
      </DialogActions>
    </Dialog>
  )
}

export default function CCModelsPage() {
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const theme = useTheme()

  const [editOpen, setEditOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<CCModelPresetInfo | undefined>(undefined)
  const [isCopyMode, setIsCopyMode] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<CCModelPresetInfo | null>(null)
  const [testingPresetIds, setTestingPresetIds] = useState<Set<number>>(new Set())
  const [testResults, setTestResults] = useState<Record<number, CCModelPresetTestItem>>({})
  const [searchText, setSearchText] = useState('')

  const { data: presets = [], isLoading } = useQuery({
    queryKey: ['cc-model-presets'],
    queryFn: () => ccModelPresetApi.getList(),
  })

  const { data: workspaces = [] } = useQuery({
    queryKey: ['workspaces'],
    queryFn: workspaceApi.getList,
  })

  const usageMap = useMemo(
    () =>
      presets.reduce<Record<number, string[]>>((acc, preset) => {
        acc[preset.id] = workspaces
          .filter(workspace => workspace.cc_model_preset_name === preset.name)
          .map(workspace => workspace.name)
        return acc
      }, {}),
    [presets, workspaces]
  )

  const deleteMutation = useMutation({
    mutationFn: (id: number) => ccModelPresetApi.delete(id),
    onSuccess: () => {
      notification.success(t('ccModels.notifications.deleted'))
      queryClient.invalidateQueries({ queryKey: ['cc-model-presets'] })
      setDeleteTarget(null)
    },
    onError: (err: Error) =>
      notification.error(t('ccModels.notifications.deleteFailed', { message: err.message })),
  })

  const getUsageNames = (preset: CCModelPresetInfo) => usageMap[preset.id] ?? []
  const getTestModel = (preset: CCModelPresetInfo) => {
    const manualCandidates = [
      preset.anthropic_model,
      preset.default_sonnet,
      preset.default_opus,
      preset.default_haiku,
      preset.small_fast_model,
    ]
    const presetCandidates = [...manualCandidates, preset.preset_model]
    const candidates = preset.model_type === 'manual' ? manualCandidates : presetCandidates
    return candidates.find(candidate => candidate.trim())?.trim() || ''
  }
  const canTestPreset = (preset: CCModelPresetInfo) =>
    Boolean(preset.base_url.trim() && preset.auth_token.trim() && getTestModel(preset))

  const filteredPresets = useMemo(() => {
    const keyword = searchText.trim().toLowerCase()
    if (!keyword) return presets
    return presets.filter(preset => {
      return (
        preset.name.toLowerCase().includes(keyword) ||
        preset.description.toLowerCase().includes(keyword) ||
        preset.base_url.toLowerCase().includes(keyword) ||
        (preset.model_type === 'preset'
          ? preset.preset_model
          : preset.anthropic_model || ''
        )
          .toLowerCase()
          .includes(keyword)
      )
    })
  }, [presets, searchText])
  const runConnectivityTest = async (presetIds: number[]) => {
    const targets = presetIds.filter(id => {
      const preset = presets.find(item => item.id === id)
      return preset ? canTestPreset(preset) : false
    })
    if (targets.length === 0) {
      notification.info(t('ccModels.notifications.noTestableGroups'))
      return
    }

    setTestingPresetIds(prev => new Set([...prev, ...targets]))
    try {
      const items = await ccModelPresetApi.test(targets)
      const safeItems = Array.isArray(items) ? items : []
      setTestResults(prev => {
        const next = { ...prev }
        safeItems.forEach(item => {
          next[item.preset_id] = item
        })
        return next
      })
      if (safeItems.length === 0) {
        notification.warning(t('ccModels.notifications.testNoResults'))
        return
      }
      const successCount = safeItems.filter(item => item.success).length
      const failCount = safeItems.length - successCount
      if (failCount === 0) {
        notification.success(t('ccModels.notifications.testAllPassed'))
      } else {
        notification.warning(t('ccModels.notifications.testCompleted'))
      }
    } catch (err) {
      notification.error(
        err instanceof Error ? err.message : t('ccModels.notifications.testFailed')
      )
    } finally {
      setTestingPresetIds(prev => {
        const next = new Set(prev)
        targets.forEach(id => next.delete(id))
        return next
      })
    }
  }

  const renderTestTooltip = (result: CCModelPresetTestItem) => (
    <Box sx={{ maxWidth: 360 }}>
      <Typography variant="caption" sx={{ display: 'block', fontWeight: 700, mb: 0.5 }}>
        {result.success ? t('ccModels.health.tooltipPassed') : t('ccModels.health.tooltipFailed')}
      </Typography>
      <Typography variant="caption" sx={{ display: 'block' }}>
        {t('ccModels.health.tooltipModel', {
          model: result.used_model || result.model_name || '-',
        })}
      </Typography>
      <Typography variant="caption" sx={{ display: 'block' }}>
        {t('ccModels.health.tooltipLatency', { ms: result.latency_ms })}
      </Typography>
      {result.success ? (
        <>
          <Typography variant="caption" sx={{ display: 'block' }}>
            {t('ccModels.health.tooltipTokens', {
              input: result.input_tokens || 0,
              output: result.output_tokens || 0,
            })}
          </Typography>
          <Typography
            variant="caption"
            sx={{ display: 'block', mt: 0.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
          >
            {t('ccModels.health.tooltipReply', {
              text: result.response_text?.trim() || '-',
            })}
          </Typography>
        </>
      ) : (
        <Typography
          variant="caption"
          sx={{ display: 'block', mt: 0.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
        >
          {t('ccModels.health.tooltipError', {
            error: result.error_message || '-',
          })}
        </Typography>
      )}
    </Box>
  )

  const handleAdd = () => {
    setIsCopyMode(false)
    setEditTarget(undefined)
    setEditOpen(true)
  }

  const handleEdit = (preset: CCModelPresetInfo) => {
    setIsCopyMode(false)
    setEditTarget(preset)
    setEditOpen(true)
  }

  const handleCopy = (preset: CCModelPresetInfo) => {
    setIsCopyMode(true)
    setEditTarget(preset)
    setEditOpen(true)
  }

  const handleSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['cc-model-presets'] })
  }

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
        {t('ccModels.alert.providerSupportBefore')}
        <Link href="https://api.nekro.ai" target="_blank" rel="noopener noreferrer">
          {t('ccModels.alert.providerSupportLink')}
        </Link>
        {t('ccModels.alert.providerSupportAfter')}
      </Alert>

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
          placeholder={t('ccModels.actions.searchPlaceholder')}
          sx={{ flex: 1 }}
        />
        <ActionButton
          tone="primary"
          startIcon={<AddIcon />}
          onClick={handleAdd}
          size="small"
          sx={{ height: 40, whiteSpace: 'nowrap', flexShrink: 0 }}
        >
          {t('ccModels.createBtn')}
        </ActionButton>
      </Box>

      {/* 表格 */}
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
          <Table stickyHeader size="medium" sx={{ minWidth: 700 }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ whiteSpace: 'nowrap', minWidth: 80, ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  {t('ccModels.table.headers.name')}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', minWidth: 120, ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  {t('ccModels.table.headers.desc')}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', minWidth: 60, ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  {t('ccModels.table.headers.type')}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', minWidth: 80, ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  {t('ccModels.table.headers.model')}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', minWidth: 120, ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  {t('ccModels.table.headers.baseUrl')}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', minWidth: 60, ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  {t('ccModels.table.headers.usage')}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', minWidth: 60, ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  {t('ccModels.table.headers.health')}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', minWidth: 80, ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  {t('ccModels.table.headers.actions')}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : filteredPresets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                    {t('ccModels.table.empty')}
                  </TableCell>
                </TableRow>
              ) : (
                filteredPresets.map(preset => (
                  <TableRow key={preset.id} sx={UNIFIED_TABLE_STYLES.row as SxProps<Theme>}>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>) }}>
                      <Stack direction="row" alignItems="center" spacing={0.5}>
                        <Typography variant="subtitle2">{preset.name}</Typography>
                        {preset.is_default && (
                          <Chip
                            label={t('ccModels.table.defaultChip')}
                            size="small"
                            sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.primary.main, true)}
                          />
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell
                      sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>), maxWidth: 200 }}
                    >
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                      >
                        {preset.description || '-'}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>) }}>
                      <Chip
                        label={
                          preset.model_type === 'preset'
                            ? t('ccModels.table.typePreset')
                            : t('ccModels.table.typeManual')
                        }
                        size="small"
                        variant="outlined"
                        sx={CHIP_VARIANTS.getCustomColorChip(
                          preset.model_type === 'preset'
                            ? theme.palette.primary.main
                            : theme.palette.secondary.main,
                          false
                        )}
                      />
                    </TableCell>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>) }}>
                      {preset.model_type === 'preset' ? (
                        <Typography
                          variant="body2"
                          sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
                        >
                          {preset.preset_model || '-'}
                        </Typography>
                      ) : (() => {
                        const extraModels = [
                          preset.small_fast_model && `SMALL_FAST: ${preset.small_fast_model}`,
                          preset.default_sonnet && `SONNET: ${preset.default_sonnet}`,
                          preset.default_opus && `OPUS: ${preset.default_opus}`,
                          preset.default_haiku && `HAIKU: ${preset.default_haiku}`,
                        ].filter(Boolean) as string[]
                        const primaryModel = preset.anthropic_model
                        return (
                          <Stack direction="row" alignItems="center" spacing={0.5}>
                            <Typography
                              variant="body2"
                              sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
                            >
                              {primaryModel || t('ccModels.table.multiModel')}
                            </Typography>
                            {extraModels.length > 0 && (
                              <Tooltip
                                title={
                                  <Box>
                                    {extraModels.map(m => (
                                      <Typography
                                        key={m}
                                        variant="caption"
                                        sx={{ display: 'block', fontFamily: 'monospace' }}
                                      >
                                        {m}
                                      </Typography>
                                    ))}
                                  </Box>
                                }
                                arrow
                              >
                                <Typography
                                  variant="caption"
                                  sx={{
                                    color: 'primary.main',
                                    cursor: 'default',
                                    fontWeight: 600,
                                    lineHeight: 1,
                                  }}
                                >
                                  +{extraModels.length}
                                </Typography>
                              </Tooltip>
                            )}
                          </Stack>
                        )
                      })()}
                    </TableCell>
                    <TableCell
                      sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>), maxWidth: 200 }}
                    >
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: 'monospace',
                          fontSize: '0.78rem',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          filter: 'blur(4px)',
                          transition: 'filter 0.2s',
                          '&:hover': { filter: 'blur(0)' },
                        }}
                      >
                        {preset.base_url}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>) }}>
                      {usageMap[preset.id]?.length ? (
                        <Tooltip title={usageMap[preset.id].join('、')} arrow>
                          <Chip
                            size="small"
                            variant="outlined"
                            label={t('ccModels.table.usageBound', { count: usageMap[preset.id].length })}
                            sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.success.main, false)}
                          />
                        </Tooltip>
                      ) : (
                        <Chip
                          size="small"
                          variant="outlined"
                          label={t('ccModels.table.usageIdle')}
                          sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.text.secondary, false)}
                        />
                      )}
                    </TableCell>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>) }}>
                      {testingPresetIds.has(preset.id) ? (
                        <Chip
                          size="small"
                          variant="outlined"
                          icon={<CircularProgress size={12} />}
                          label={t('ccModels.health.testing')}
                          sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.info.main, false)}
                        />
                      ) : testResults[preset.id] ? (
                        <Tooltip title={renderTestTooltip(testResults[preset.id])} arrow>
                          {testResults[preset.id].success ? (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={t('ccModels.health.ok', {
                                ms: testResults[preset.id].latency_ms,
                              })}
                              sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.success.main, false)}
                            />
                          ) : (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={t('ccModels.health.failed')}
                              sx={CHIP_VARIANTS.getCustomColorChip(theme.palette.error.main, false)}
                            />
                          )}
                        </Tooltip>
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          {t('ccModels.health.notTested')}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>) }}>
                      <Stack direction="row" spacing={0.5}>
                        <Tooltip title={t('ccModels.table.tooltips.edit')} arrow>
                          <IconActionButton
                            size="small"
                            sx={{ color: 'warning.main', p: 0.5 }}
                            onClick={() => handleEdit(preset)}
                          >
                            <EditIcon fontSize="small" />
                          </IconActionButton>
                        </Tooltip>
                        <Tooltip title={t('ccModels.table.tooltips.copy')} arrow>
                          <IconActionButton
                            size="small"
                            tone="subtle"
                            onClick={() => handleCopy(preset)}
                            sx={{ p: 0.5 }}
                          >
                            <ContentCopyIcon fontSize="small" />
                          </IconActionButton>
                        </Tooltip>
                        <Tooltip
                          title={
                            canTestPreset(preset)
                              ? t('ccModels.table.tooltips.test')
                              : t('ccModels.table.tooltips.testDisabled')
                          }
                          arrow
                        >
                          <span>
                            <IconActionButton
                              size="small"
                              tone="primary"
                              onClick={() => runConnectivityTest([preset.id])}
                              disabled={!canTestPreset(preset) || testingPresetIds.has(preset.id)}
                            >
                              {testingPresetIds.has(preset.id) ? (
                                <CircularProgress size={18} />
                              ) : (
                                <NetworkCheckIcon fontSize="small" />
                              )}
                            </IconActionButton>
                          </span>
                        </Tooltip>
                        <Tooltip
                          title={
                            preset.is_default
                              ? t('ccModels.table.tooltips.defaultCannotDelete')
                              : getUsageNames(preset).length > 0
                                ? t('ccModels.table.tooltips.boundCannotDelete', {
                                    count: getUsageNames(preset).length,
                                  })
                              : t('ccModels.table.tooltips.delete')
                          }
                          arrow
                        >
                          <span>
                            <IconActionButton
                              size="small"
                              tone="danger"
                              onClick={() => setDeleteTarget(preset)}
                              disabled={preset.is_default || getUsageNames(preset).length > 0}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconActionButton>
                          </span>
                        </Tooltip>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 编辑/新建/复制 Dialog */}
      <EditDialog
        open={editOpen}
        onClose={() => {
          setEditOpen(false)
          setIsCopyMode(false)
        }}
        initial={editTarget}
        isCopy={isCopyMode}
        onSuccess={handleSuccess}
      />

      {/* 删除确认 Dialog */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => !deleteMutation.isPending && setDeleteTarget(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>{t('ccModels.deleteDialog.title')}</DialogTitle>
        <DialogContent>
          <Stack spacing={1.25}>
            <Typography>
              {t('ccModels.deleteDialog.content', { name: deleteTarget?.name })}
            </Typography>
            {deleteTarget && getUsageNames(deleteTarget).length > 0 && (
              <Alert severity="warning">
                {t('ccModels.deleteDialog.boundHint', {
                  count: getUsageNames(deleteTarget).length,
                  names: getUsageNames(deleteTarget).join('、'),
                })}
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <ActionButton onClick={() => setDeleteTarget(null)} disabled={deleteMutation.isPending}>
            {t('ccModels.deleteDialog.cancel')}
          </ActionButton>
          <ActionButton
            tone="danger"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? (
              <CircularProgress size={18} />
            ) : (
              t('ccModels.deleteDialog.delete')
            )}
          </ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
