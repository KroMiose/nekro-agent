import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Stack,
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
  Chip,
  MenuItem,
  CircularProgress,
  Tooltip,
  Alert,
  SxProps,
  Theme,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  RemoveCircleOutline as RemoveIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ccModelPresetApi, CCModelPresetInfo, CCModelPresetCreate } from '../../services/api/cc-model-preset'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'

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
  extra_env: [
    { key: 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC', value: '1' },
    { key: 'CLAUDE_CODE_ATTRIBUTION_HEADER', value: '0' },
  ],
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
  onSuccess: () => void
}

function EditDialog({ open, onClose, initial, onSuccess }: EditDialogProps) {
  const [form, setForm] = useState<PresetFormState>(DEFAULT_FORM)
  const [showToken, setShowToken] = useState(false)
  const notification = useNotification()

  const createMutation = useMutation({
    mutationFn: (body: CCModelPresetCreate) => ccModelPresetApi.create(body),
    onSuccess: () => {
      notification.success('预设已创建')
      onSuccess()
      onClose()
    },
    onError: (err: Error) => notification.error(`创建失败：${err.message}`),
  })

  const updateMutation = useMutation({
    mutationFn: (body: CCModelPresetCreate) => ccModelPresetApi.update(initial!.id, body),
    onSuccess: () => {
      notification.success('预设已保存')
      onSuccess()
      onClose()
    },
    onError: (err: Error) => notification.error(`保存失败：${err.message}`),
  })

  useEffect(() => {
    if (open) {
      if (initial) {
        setForm({
          name: initial.name,
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
      setShowToken(false)
    }
  }, [open, initial])

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
    if (initial) {
      updateMutation.mutate(body)
    } else {
      createMutation.mutate(body)
    }
  }

  const addEnvPair = () => setForm(prev => ({ ...prev, extra_env: [...prev.extra_env, { key: '', value: '' }] }))
  const removeEnvPair = (idx: number) =>
    setForm(prev => ({ ...prev, extra_env: prev.extra_env.filter((_, i) => i !== idx) }))
  const updateEnvPair = (idx: number, field: 'key' | 'value', val: string) =>
    setForm(prev => {
      const pairs = [...prev.extra_env]
      pairs[idx] = { ...pairs[idx], [field]: val }
      return { ...prev, extra_env: pairs }
    })

  const configPreview = JSON.stringify(computeConfigJson(form), null, 2)

  return (
    <Dialog open={open} onClose={() => !isPending && onClose()} maxWidth="md" fullWidth>
      <DialogTitle>{initial ? '编辑 CC 模型预设' : '新建 CC 模型预设'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {/* 基本信息 */}
          <TextField
            label="预设名称"
            value={form.name}
            onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
            fullWidth
            required
            size="small"
            autoComplete="off"
            disabled={!!initial}
            helperText={initial ? '名称创建后不可修改' : ''}
          />
          <TextField
            label="描述"
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
            API 配置
          </Typography>
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
                    '-webkit-text-security': 'disc',
                    'text-security': 'disc',
                  } as React.CSSProperties)
                : undefined,
            }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowToken(v => !v)} edge="end" size="small">
                    {showToken ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          <TextField
            label="超时 (ms)"
            value={form.api_timeout_ms}
            onChange={e => setForm(prev => ({ ...prev, api_timeout_ms: e.target.value }))}
            size="small"
            autoComplete="off"
            helperText="API_TIMEOUT_MS"
            fullWidth
          />

          {/* 模型类型 */}
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mt: 1 }}>
            模型配置
          </Typography>
          <TextField
            label="模型类型"
            select
            value={form.model_type}
            onChange={e => setForm(prev => ({ ...prev, model_type: e.target.value as 'preset' | 'manual' }))}
            size="small"
            fullWidth
          >
            <MenuItem value="preset">预设模式（使用预设名称）</MenuItem>
            <MenuItem value="manual">手动模式（分别指定各角色模型）</MenuItem>
          </TextField>

          {form.model_type === 'preset' ? (
            <TextField
              label="预设模型"
              select
              value={form.preset_model}
              onChange={e => setForm(prev => ({ ...prev, preset_model: e.target.value }))}
              size="small"
              fullWidth
              helperText="model 字段值"
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
                placeholder="留空则不设置"
              />
              <TextField
                label="ANTHROPIC_SMALL_FAST_MODEL"
                value={form.small_fast_model}
                onChange={e => setForm(prev => ({ ...prev, small_fast_model: e.target.value }))}
                size="small"
                fullWidth
                autoComplete="off"
                placeholder="留空则不设置"
              />
              <TextField
                label="ANTHROPIC_DEFAULT_SONNET_MODEL"
                value={form.default_sonnet}
                onChange={e => setForm(prev => ({ ...prev, default_sonnet: e.target.value }))}
                size="small"
                fullWidth
                autoComplete="off"
                placeholder="留空则不设置"
              />
              <TextField
                label="ANTHROPIC_DEFAULT_OPUS_MODEL"
                value={form.default_opus}
                onChange={e => setForm(prev => ({ ...prev, default_opus: e.target.value }))}
                size="small"
                fullWidth
                autoComplete="off"
                placeholder="留空则不设置"
              />
              <TextField
                label="ANTHROPIC_DEFAULT_HAIKU_MODEL"
                value={form.default_haiku}
                onChange={e => setForm(prev => ({ ...prev, default_haiku: e.target.value }))}
                size="small"
                fullWidth
                autoComplete="off"
                placeholder="留空则不设置"
              />
            </Stack>
          )}

          {/* 自定义附加变量 */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              自定义附加变量
            </Typography>
            <Button size="small" startIcon={<AddIcon />} onClick={addEnvPair} sx={{ minWidth: 0 }}>
              添加
            </Button>
          </Box>
          {form.extra_env.length === 0 ? (
            <Typography variant="caption" color="text.disabled" sx={{ pl: 0.5 }}>
              暂无自定义变量，点击"添加"新增键值对
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
                  <IconButton size="small" color="error" onClick={() => removeEnvPair(idx)}>
                    <RemoveIcon fontSize="small" />
                  </IconButton>
                </Stack>
              ))}
            </Stack>
          )}

          {/* 配置预览 */}
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mt: 1 }}>
            生成的配置 JSON 预览
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
        <Button onClick={onClose} disabled={isPending}>
          取消
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isPending || !form.name.trim()}
        >
          {isPending ? <CircularProgress size={18} /> : initial ? '保存' : '创建'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default function CCModelsPage() {
  const queryClient = useQueryClient()
  const notification = useNotification()

  const [editOpen, setEditOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<CCModelPresetInfo | undefined>(undefined)
  const [deleteTarget, setDeleteTarget] = useState<CCModelPresetInfo | null>(null)

  const { data: presets = [], isLoading } = useQuery({
    queryKey: ['cc-model-presets'],
    queryFn: () => ccModelPresetApi.getList(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => ccModelPresetApi.delete(id),
    onSuccess: () => {
      notification.success('预设已删除')
      queryClient.invalidateQueries({ queryKey: ['cc-model-presets'] })
      setDeleteTarget(null)
    },
    onError: (err: Error) => notification.error(`删除失败：${err.message}`),
  })

  const handleAdd = () => {
    setEditTarget(undefined)
    setEditOpen(true)
  }

  const handleEdit = (preset: CCModelPresetInfo) => {
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
        <Alert severity="info" sx={{ flex: 1 }}>
          管理 Claude Code (CC) 沙盒使用的模型预设配置，在工作区配置页中选择预设以生成注入配置。
        </Alert>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAdd}
          sx={{ minWidth: 140, minHeight: 40, flexShrink: 0 }}
        >
          新建预设
        </Button>
      </Box>

      {/* 表格 */}
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
          <Table stickyHeader size="medium" sx={{ minWidth: 700 }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  预设名称
                </TableCell>
                <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  描述
                </TableCell>
                <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  类型
                </TableCell>
                <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  模型
                </TableCell>
                <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  Base URL
                </TableCell>
                <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>) }}>
                  操作
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : presets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                    暂无预设，点击"新建预设"添加
                  </TableCell>
                </TableRow>
              ) : (
                presets.map(preset => (
                  <TableRow key={preset.id} sx={UNIFIED_TABLE_STYLES.row as SxProps<Theme>}>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>) }}>
                      <Stack direction="row" alignItems="center" spacing={0.5}>
                        <Typography variant="subtitle2">{preset.name}</Typography>
                        {preset.is_default && (
                          <Chip label="默认" size="small" color="primary" sx={{ height: 18, fontSize: '0.68rem' }} />
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>), maxWidth: 200 }}>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                      >
                        {preset.description || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>) }}>
                      <Chip
                        label={preset.model_type === 'preset' ? '预设' : '手动'}
                        size="small"
                        color={preset.model_type === 'preset' ? 'primary' : 'secondary'}
                        variant="outlined"
                        sx={{ height: 22, fontSize: '0.72rem' }}
                      />
                    </TableCell>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>) }}>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {preset.model_type === 'preset'
                          ? preset.preset_model
                          : preset.anthropic_model || '(多模型)'}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>), maxWidth: 200 }}>
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
                      <Stack direction="row" spacing={0.5}>
                        <Tooltip title="编辑" arrow>
                          <IconButton
                            size="small"
                            color="warning"
                            onClick={() => handleEdit(preset)}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={preset.is_default ? '默认预设不可删除' : '删除'} arrow>
                          <span>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => setDeleteTarget(preset)}
                              disabled={preset.is_default}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
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

      {/* 编辑/新建 Dialog */}
      <EditDialog
        open={editOpen}
        onClose={() => setEditOpen(false)}
        initial={editTarget}
        onSuccess={handleSuccess}
      />

      {/* 删除确认 Dialog */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => !deleteMutation.isPending && setDeleteTarget(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>确认删除预设</DialogTitle>
        <DialogContent>
          <Typography>
            确定要删除预设 <strong>{deleteTarget?.name}</strong> 吗？此操作不可撤销。
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleteMutation.isPending}>
            取消
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? <CircularProgress size={18} /> : '删除'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
