import { useState, useEffect } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  TextField,
  CircularProgress,
  Stack,
  MenuItem,
  Autocomplete,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  IconButton,
  InputAdornment,
  Tooltip,
} from '@mui/material'
import {
  Delete as DeleteIcon,
  Save as SaveIcon,
  Add as AddIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  workspaceApi,
  WorkspaceDetail,
  UpdateWorkspaceBody,
  WorkspaceEnvVar,
} from '../../../services/api/workspace'
import { ccModelPresetApi, CCModelPresetInfo } from '../../../services/api/cc-model-preset'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS } from '../../../theme/variants'
import { useTranslation } from 'react-i18next'

export default function ConfigTab({
  workspace,
  onDeleted,
}: {
  workspace: WorkspaceDetail
  onDeleted: () => void
}) {
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')

  const [form, setForm] = useState<UpdateWorkspaceBody>({
    name: workspace.name,
    description: workspace.description,
    sandbox_image: workspace.sandbox_image,
    runtime_policy: workspace.runtime_policy,
  })

  const saveMutation = useMutation({
    mutationFn: () => workspaceApi.update(workspace.id, form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      notification.success(t('detail.config.notifications.saveSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.config.notifications.saveFailed', { message: err.message })),
  })

  const [deleteOpen, setDeleteOpen] = useState(false)
  const deleteMutation = useMutation({
    mutationFn: () => workspaceApi.delete(workspace.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      notification.success(t('detail.config.notifications.deleteSuccess'))
      onDeleted()
    },
    onError: (err: Error) => notification.error(t('detail.config.notifications.deleteFailed', { message: err.message })),
  })

  // CC 模型预设
  const { data: allPresets = [] } = useQuery({
    queryKey: ['cc-model-presets'],
    queryFn: () => ccModelPresetApi.getList(),
  })

  const [selectedPreset, setSelectedPreset] = useState<CCModelPresetInfo | null>(null)

  // 用 WorkspaceDetail 自带的 cc_model_preset_id 初始化选中项，避免独立查询的竞态问题
  useEffect(() => {
    if (!allPresets.length) return
    const presetId = workspace.cc_model_preset_id
    if (presetId != null) {
      const found = allPresets.find(p => p.id === presetId)
      setSelectedPreset(found ?? allPresets.find(p => p.is_default) ?? allPresets[0])
    } else {
      setSelectedPreset(allPresets.find(p => p.is_default) ?? allPresets[0])
    }
  }, [workspace.cc_model_preset_id, allPresets])

  const setCCPresetMutation = useMutation({
    mutationFn: (presetId: number | null) => workspaceApi.setCCModelPreset(workspace.id, presetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      notification.success(t('detail.config.notifications.ccPresetSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.config.notifications.ccPresetFailed', { message: err.message })),
  })

  // 环境变量
  const { data: serverEnvVars = [] } = useQuery({
    queryKey: ['workspace-env-vars', workspace.id],
    queryFn: () => workspaceApi.getEnvVars(workspace.id),
  })

  const [envVars, setEnvVars] = useState<WorkspaceEnvVar[]>([])
  const [visibleValues, setVisibleValues] = useState<Set<number>>(new Set())

  useEffect(() => {
    setEnvVars(serverEnvVars)
  }, [serverEnvVars])

  const saveEnvVarsMutation = useMutation({
    mutationFn: () => workspaceApi.updateEnvVars(workspace.id, envVars),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-env-vars', workspace.id] })
      queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
      notification.success(t('detail.config.notifications.envVarsSaveSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.config.notifications.envVarsSaveFailed', { message: err.message })),
  })

  const addEnvVar = () => {
    setEnvVars(prev => [...prev, { key: '', value: '', description: '' }])
  }

  const removeEnvVar = (idx: number) => {
    setEnvVars(prev => prev.filter((_, i) => i !== idx))
    setVisibleValues(prev => {
      const next = new Set(prev)
      next.delete(idx)
      return new Set([...next].map(i => (i > idx ? i - 1 : i)))
    })
  }

  const updateEnvVar = (idx: number, field: keyof WorkspaceEnvVar, val: string) => {
    setEnvVars(prev => prev.map((item, i) => i === idx ? { ...item, [field]: val } : item))
  }

  const toggleValueVisible = (idx: number) => {
    setVisibleValues(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  return (
    <Stack spacing={2}>
      {/* 基本设置 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1 }}>
              {t('detail.config.sections.basic')}
            </Typography>
            <Button
              size="small"
              variant="contained"
              startIcon={
                saveMutation.isPending ? (
                  <CircularProgress size={14} color="inherit" />
                ) : (
                  <SaveIcon />
                )
              }
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || !form.name?.trim()}
            >
              {t('detail.config.buttons.save')}
            </Button>
          </Box>
          <Stack spacing={2}>
            <TextField
              label={t('detail.config.fields.name')}
              fullWidth
              required
              size="small"
              autoComplete="off"
              value={form.name ?? ''}
              onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
              disabled={saveMutation.isPending}
            />
            <TextField
              label={t('detail.config.fields.desc')}
              fullWidth
              multiline
              rows={2}
              size="small"
              autoComplete="off"
              value={form.description ?? ''}
              onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))}
              disabled={saveMutation.isPending}
            />
            <TextField
              label={t('detail.config.fields.image')}
              fullWidth
              size="small"
              autoComplete="off"
              placeholder={t('detail.config.fields.imageHint')}
              helperText={t('detail.config.fields.imageHelperText')}
              value={form.sandbox_image ?? ''}
              onChange={e => setForm(prev => ({ ...prev, sandbox_image: e.target.value }))}
              disabled={saveMutation.isPending}
            />
            <TextField
              label={t('detail.config.fields.policy')}
              select
              fullWidth
              size="small"
              value={form.runtime_policy ?? 'agent'}
              onChange={e =>
                setForm(prev => ({
                  ...prev,
                  runtime_policy: e.target.value as UpdateWorkspaceBody['runtime_policy'],
                }))
              }
              disabled={saveMutation.isPending}
            >
              <MenuItem value="agent">{t('detail.config.policyOptions.agent')}</MenuItem>
              <MenuItem value="relaxed">{t('detail.config.policyOptions.relaxed')}</MenuItem>
              <MenuItem value="strict">{t('detail.config.policyOptions.strict')}</MenuItem>
            </TextField>
          </Stack>
        </CardContent>
      </Card>

      {/* CC 模型配置 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>
            {t('detail.config.sections.ccModel')}
          </Typography>
          <Autocomplete
            options={allPresets}
            value={selectedPreset}
            disableClearable
            onChange={(_, val: CCModelPresetInfo | null) => {
              if (!val) return
              setSelectedPreset(val)
              setCCPresetMutation.mutate(val.id)
            }}
            getOptionLabel={opt => opt.name}
            isOptionEqualToValue={(opt, val) => opt.id === val.id}
            renderInput={params => (
              <TextField
                {...params}
                size="small"
                label={t('detail.config.fields.ccModel')}
                helperText={t('detail.config.fields.modelHelperText')}
              />
            )}
            renderOption={(props, opt) => (
              <Box component="li" {...props} key={opt.id}>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {opt.name}
                    {opt.is_default && (
                      <Typography
                        component="span"
                        variant="caption"
                        color="primary"
                        sx={{ ml: 0.5 }}
                      >
                        {t('detail.config.ccModelDefault')}
                      </Typography>
                    )}
                  </Typography>
                  {opt.description && (
                    <Typography variant="caption" color="text.secondary">
                      {opt.description}
                    </Typography>
                  )}
                </Box>
              </Box>
            )}
            loading={setCCPresetMutation.isPending}
          />
          {selectedPreset && (
            <TextField
              fullWidth
              multiline
              rows={8}
              size="small"
              value={JSON.stringify(selectedPreset.config_json, null, 2)}
              InputProps={{ readOnly: true }}
              inputProps={{
                style: {
                  fontFamily: '"SFMono-Regular", Consolas, monospace',
                  fontSize: '0.78rem',
                },
              }}
              sx={{ mt: 1.5 }}
              label={t('detail.config.fields.generatedConfig')}
            />
          )}
        </CardContent>
      </Card>

      {/* 环境变量 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1 }}>
              {t('detail.config.sections.envVars')}
            </Typography>
            <Button
              size="small"
              variant="contained"
              startIcon={saveEnvVarsMutation.isPending ? <CircularProgress size={14} color="inherit" /> : <SaveIcon />}
              onClick={() => saveEnvVarsMutation.mutate()}
              disabled={saveEnvVarsMutation.isPending}
            >
              {t('detail.config.buttons.save')}
            </Button>
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
            {t('detail.config.envVars.hint')}
          </Typography>

          <Stack spacing={1}>
            {envVars.map((ev, idx) => (
              <Box key={idx} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                <TextField
                  size="small"
                  label={t('detail.config.envVars.key')}
                  value={ev.key}
                  onChange={e => updateEnvVar(idx, 'key', e.target.value)}
                  sx={{ width: 180, flexShrink: 0 }}
                  inputProps={{ style: { fontFamily: 'monospace', fontSize: '0.82rem' } }}
                  autoComplete="off"
                />
                <TextField
                  size="small"
                  label={t('detail.config.envVars.value')}
                  type={visibleValues.has(idx) ? 'text' : 'password'}
                  value={ev.value}
                  onChange={e => updateEnvVar(idx, 'value', e.target.value)}
                  sx={{ width: 200, flexShrink: 0 }}
                  autoComplete="new-password"
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton size="small" onClick={() => toggleValueVisible(idx)} edge="end" tabIndex={-1}>
                          {visibleValues.has(idx) ? <VisibilityOffIcon sx={{ fontSize: 16 }} /> : <VisibilityIcon sx={{ fontSize: 16 }} />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
                <TextField
                  size="small"
                  label={t('detail.config.envVars.description')}
                  value={ev.description}
                  onChange={e => updateEnvVar(idx, 'description', e.target.value)}
                  sx={{ flex: 1 }}
                  autoComplete="off"
                />
                <Tooltip title={t('detail.config.envVars.remove')}>
                  <IconButton size="small" color="error" onClick={() => removeEnvVar(idx)} sx={{ mt: 0.5 }}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            ))}
          </Stack>

          <Button
            size="small"
            startIcon={<AddIcon />}
            onClick={addEnvVar}
            sx={{ mt: envVars.length > 0 ? 1.5 : 0.5 }}
          >
            {t('detail.config.envVars.add')}
          </Button>
        </CardContent>
      </Card>

      {/* 危险区 */}
      <Card
        sx={{ ...CARD_VARIANTS.default.styles, border: '1px solid', borderColor: 'error.main' }}
      >
        <CardContent>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'error.main', mb: 0.5 }}>
            {t('detail.config.sections.danger')}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('detail.config.dangerDesc')}
          </Typography>
          <Button
            variant="outlined"
            color="error"
            size="small"
            startIcon={<DeleteIcon />}
            onClick={() => setDeleteOpen(true)}
          >
            {t('detail.config.deleteBtn')}
          </Button>
        </CardContent>
      </Card>

      <Dialog open={deleteOpen} onClose={() => !deleteMutation.isPending && setDeleteOpen(false)}>
        <DialogTitle>{t('detail.config.deleteDialog.title')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t('detail.config.deleteDialog.content', { name: workspace.name })}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteOpen(false)} disabled={deleteMutation.isPending}>
            {t('detail.config.deleteDialog.cancel')}
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? <CircularProgress size={20} /> : t('detail.config.deleteDialog.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
