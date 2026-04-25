import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  DialogContentText,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import type { InputBaseComponentProps } from '@mui/material/InputBase'
import Grid from '@mui/material/Grid2'
import {
  Add as AddIcon,
  CheckCircleOutline as CheckCircleOutlineIcon,
  Delete as DeleteIcon,
  DragIndicator as DragIcon,
  Edit as EditIcon,
  FolderOpen as FolderOpenIcon,
  HelpOutline as HelpOutlineIcon,
  Link as LinkIcon,
  LinkOff as LinkOffIcon,
  Refresh as RefreshIcon,
  Route as RouteIcon,
  Storage as StorageIcon,
  Tag as TagIcon,
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import ActionButton from '../../../components/common/ActionButton'
import IconActionButton from '../../../components/common/IconActionButton'
import SearchField from '../../../components/common/SearchField'
import StatCard from '../../../components/common/StatCard'
import { useNotification } from '../../../hooks/useNotification'
import {
  type WorkspaceDetail,
  type WorkspaceResourceBinding,
  type WorkspaceResourceField,
  type WorkspaceResourceTemplate,
  type WorkspaceResourceUpsertBody,
  workspaceApi,
} from '../../../services/api/workspace'
import { CARD_VARIANTS, CHIP_VARIANTS, UNIFIED_TABLE_STYLES } from '../../../theme/variants'
import { workspaceDetailPath } from '../../../router/routes'

type EditorMode = 'create' | 'edit'

/* cspell:ignore lpignore */
const NO_AUTOFILL_INPUT_PROPS: InputBaseComponentProps = {
  autoCorrect: 'off',
  autoCapitalize: 'none',
  spellCheck: false,
  'data-lpignore': 'true',
  'data-1p-ignore': 'true',
}

function moveItem<T>(items: T[], fromIndex: number, toIndex: number) {
  const next = [...items]
  const [moved] = next.splice(fromIndex, 1)
  next.splice(toIndex, 0, moved)
  return next
}

function normalizeFieldOrders(fields: WorkspaceResourceField[]) {
  return fields.map((field, index) => ({ ...field, order: index * 10 + 10 }))
}

function createEmptyField(index: number): WorkspaceResourceField {
  return {
    field_key: '',
    label: '',
    description: '',
    secret: false,
    value_kind: 'text',
    order: index * 10 + 10,
    export_mode: 'env',
    fixed_aliases: [],
    value: '',
  }
}

function createEmptyResourceValue(): WorkspaceResourceUpsertBody {
  return {
    name: '',
    resource_note: '',
    resource_tags: [],
    resource_prompt: '',
    fields: [createEmptyField(0)],
    enabled: true,
  }
}

function blurActiveElement() {
  if (typeof document === 'undefined') return
  const activeElement = document.activeElement
  if (activeElement instanceof HTMLElement) {
    activeElement.blur()
  }
}

function ResourceFieldEditor({
  fields,
  onChange,
  t,
}: {
  fields: WorkspaceResourceField[]
  onChange: (fields: WorkspaceResourceField[]) => void
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  const [dragIndex, setDragIndex] = useState<number | null>(null)

  const updateField = (index: number, updater: (field: WorkspaceResourceField) => WorkspaceResourceField) => {
    onChange(normalizeFieldOrders(fields.map((field, current) => (current === index ? updater(field) : field))))
  }

  const addField = () => {
    onChange(normalizeFieldOrders([...fields, createEmptyField(fields.length)]))
  }

  const removeField = (index: number) => {
    onChange(normalizeFieldOrders(fields.filter((_, current) => current !== index)))
  }

  const handleDrop = (targetIndex: number) => {
    if (dragIndex === null || dragIndex === targetIndex) return
    onChange(normalizeFieldOrders(moveItem(fields, dragIndex, targetIndex)))
    setDragIndex(null)
  }

  return (
    <Stack spacing={1.25}>
      {fields.map((field, index) => (
        <Card
          key={`${field.field_key || 'field'}-${index}`}
          variant="outlined"
          data-resource-field-card="true"
          onDragOver={event => event.preventDefault()}
          onDrop={() => handleDrop(index)}
          onDragEnd={() => setDragIndex(null)}
          sx={{
            borderColor: dragIndex === index ? 'primary.main' : 'divider',
            backgroundColor: dragIndex === index ? alpha('#1976d2', 0.04) : 'background.paper',
          }}
        >
          <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Stack spacing={1.25}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box
                  draggable
                  onDragStart={event => {
                    event.stopPropagation()
                    event.dataTransfer.effectAllowed = 'move'
                    const card = event.currentTarget.closest('[data-resource-field-card="true"]')
                    if (card instanceof HTMLElement) {
                      const rect = card.getBoundingClientRect()
                      event.dataTransfer.setDragImage(card, event.clientX - rect.left, event.clientY - rect.top)
                    }
                    setDragIndex(index)
                  }}
                  onDragEnd={() => setDragIndex(null)}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    color: 'text.secondary',
                    cursor: 'grab',
                    '&:active': { cursor: 'grabbing' },
                  }}
                >
                  <DragIcon fontSize="small" />
                </Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1 }}>
                  {field.label || t('detail.resources.editor.unnamedField', { index: index + 1 })}
                </Typography>
                <Tooltip title={t('detail.resources.editor.removeField')}>
                  <Box component="span">
                    <IconActionButton
                      size="small"
                      tone="danger"
                      onClick={() => removeField(index)}
                      disabled={fields.length <= 1}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconActionButton>
                  </Box>
                </Tooltip>
              </Box>

              <Grid container spacing={1.25}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label={t('detail.resources.editor.fieldLabel')}
                    value={field.label}
                    autoComplete="off"
                    inputProps={NO_AUTOFILL_INPUT_PROPS}
                    onChange={event => updateField(index, current => ({ ...current, label: event.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    fullWidth
                    size="small"
                    select
                    label={t('detail.resources.editor.valueKind')}
                    value={field.value_kind}
                    onChange={event =>
                      updateField(index, current => ({
                        ...current,
                        value_kind: event.target.value as WorkspaceResourceField['value_kind'],
                      }))
                    }
                  >
                    {['text', 'password', 'host', 'port', 'private_key', 'username', 'database', 'json'].map(kind => (
                      <MenuItem key={kind} value={kind}>
                        {t(`detail.resources.valueKinds.${kind}`)}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label={t('detail.resources.editor.compatEnvNames')}
                    placeholder={t('detail.resources.editor.compatEnvNamesPlaceholder')}
                    value={field.fixed_aliases.join(', ')}
                    autoComplete="off"
                    inputProps={NO_AUTOFILL_INPUT_PROPS}
                    onChange={event =>
                      updateField(index, current => ({
                        ...current,
                        fixed_aliases: event.target.value
                          .split(',')
                          .map(item => item.trim())
                          .filter(Boolean),
                      }))
                    }
                  />
                </Grid>
                <Grid size={12}>
                  <TextField
                    fullWidth
                    size="small"
                    label={t('detail.resources.editor.fieldDescription')}
                    value={field.description}
                    autoComplete="off"
                    inputProps={NO_AUTOFILL_INPUT_PROPS}
                    onChange={event => updateField(index, current => ({ ...current, description: event.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 8 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label={field.secret ? t('detail.resources.editor.secretValue') : t('detail.resources.editor.value')}
                    value={field.value}
                    type={field.secret ? 'password' : 'text'}
                    autoComplete={field.secret ? 'new-password' : 'off'}
                    inputProps={NO_AUTOFILL_INPUT_PROPS}
                    onChange={event => updateField(index, current => ({ ...current, value: event.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Box
                    sx={{
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    <Box
                      sx={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 2,
                        px: 0.5,
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, minWidth: 0 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                          {t('detail.resources.editor.sensitive')}
                        </Typography>
                        <Tooltip title={t('detail.resources.editor.sensitiveHint')} arrow>
                          <Box component="span" sx={{ display: 'inline-flex', color: 'text.secondary', cursor: 'help' }}>
                            <HelpOutlineIcon sx={{ fontSize: 16 }} />
                          </Box>
                        </Tooltip>
                      </Box>
                      <Switch
                        checked={field.secret}
                        onChange={(_, checked) => updateField(index, current => ({ ...current, secret: checked }))}
                        color="warning"
                      />
                    </Box>
                  </Box>
                </Grid>
              </Grid>
            </Stack>
          </CardContent>
        </Card>
      ))}
      <ActionButton tone="secondary" startIcon={<AddIcon />} onClick={addField}>
        {t('detail.resources.editor.addField')}
      </ActionButton>
    </Stack>
  )
}

function ResourceEditorDialog({
  open,
  mode,
  templates,
  initialValue,
  onClose,
  onSubmit,
  t,
}: {
  open: boolean
  mode: EditorMode
  templates: WorkspaceResourceTemplate[]
  initialValue: WorkspaceResourceUpsertBody
  onClose: () => void
  onSubmit: (value: WorkspaceResourceUpsertBody) => void
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  const [form, setForm] = useState<WorkspaceResourceUpsertBody>(initialValue)
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false)
  const [pendingTemplateKey, setPendingTemplateKey] = useState('')

  useEffect(() => {
    setForm(initialValue)
    setTemplateDialogOpen(false)
    setPendingTemplateKey('')
  }, [initialValue])

  const applyTemplate = (templateKey: string) => {
    const template = templates.find(item => item.key === templateKey)
    if (!template) return
    setForm({
      name: template.name,
      template_key: template.key,
      resource_note: template.resource_note,
      resource_tags: [...template.resource_tags],
      resource_prompt: template.resource_prompt,
      fields: template.fields.map(field => ({ ...field })),
      enabled: true,
    })
  }

  const handleTemplateConfirm = () => {
    if (!pendingTemplateKey) return
    applyTemplate(pendingTemplateKey)
    setTemplateDialogOpen(false)
    setPendingTemplateKey('')
  }

  const canSubmit = form.name.trim() && form.fields.length > 0 && form.fields.every(field => field.label.trim())

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth disableRestoreFocus>
        <DialogTitle>
          {mode === 'create' ? t('detail.resources.editor.createTitle') : t('detail.resources.editor.editTitle')}
        </DialogTitle>
        <DialogContent dividers>
          <Box autoComplete="off" component="form" data-form-type="other">
            <Stack spacing={2}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: { xs: 'stretch', sm: 'center' },
                  flexDirection: { xs: 'column', sm: 'row' },
                  gap: 1.25,
                }}
              >
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    {t('detail.resources.editor.templateSectionTitle')}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t('detail.resources.editor.templateSectionHint')}
                  </Typography>
                </Box>
                <ActionButton
                  variant="outlined"
                  onClick={() => {
                    blurActiveElement()
                    setTemplateDialogOpen(true)
                  }}
                >
                  {t('detail.resources.editor.templateAction')}
                </ActionButton>
              </Box>

              <Grid container spacing={1.5}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label={t('detail.resources.editor.name')}
                    value={form.name}
                    autoComplete="off"
                    inputProps={NO_AUTOFILL_INPUT_PROPS}
                    onChange={event => setForm(current => ({ ...current, name: event.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label={t('detail.resources.editor.resourceTags')}
                    value={form.resource_tags.join(', ')}
                    autoComplete="off"
                    inputProps={NO_AUTOFILL_INPUT_PROPS}
                    onChange={event =>
                      setForm(current => ({
                        ...current,
                        resource_tags: event.target.value.split(',').map(item => item.trim()).filter(Boolean),
                      }))
                    }
                    helperText={t('detail.resources.editor.resourceTagsHint')}
                  />
                </Grid>
                <Grid size={12}>
                  <TextField
                    fullWidth
                    size="small"
                    multiline
                    minRows={2}
                    label={t('detail.resources.editor.resourceNote')}
                    value={form.resource_note}
                    autoComplete="off"
                    inputProps={NO_AUTOFILL_INPUT_PROPS}
                    onChange={event => setForm(current => ({ ...current, resource_note: event.target.value }))}
                  />
                </Grid>
                <Grid size={12}>
                  <TextField
                    fullWidth
                    size="small"
                    multiline
                    minRows={3}
                    label={t('detail.resources.editor.resourcePrompt')}
                    value={form.resource_prompt}
                    autoComplete="off"
                    inputProps={NO_AUTOFILL_INPUT_PROPS}
                    onChange={event => setForm(current => ({ ...current, resource_prompt: event.target.value }))}
                    helperText={t('detail.resources.editor.resourcePromptHelper')}
                  />
                </Grid>
              </Grid>

              <Divider />

              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                  {t('detail.resources.editor.fields')}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  {t('detail.resources.editor.fieldsHint')}
                </Typography>
                <ResourceFieldEditor
                  fields={normalizeFieldOrders(form.fields)}
                  onChange={fields => setForm(current => ({ ...current, fields }))}
                  t={t}
                />
              </Box>
            </Stack>
          </Box>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={onClose}>{t('actions.cancel', { ns: 'common' })}</ActionButton>
          <ActionButton variant="contained" onClick={() => onSubmit(form)} disabled={!canSubmit}>
            {mode === 'create' ? t('detail.resources.editor.createAction') : t('detail.resources.editor.saveAction')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      <Dialog
        open={templateDialogOpen}
        onClose={() => setTemplateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        disableRestoreFocus
      >
        <DialogTitle>{t('detail.resources.editor.templateDialogTitle')}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              {t('detail.resources.editor.templateDialogHint')}
            </Typography>
            <TextField
              select
              size="small"
              fullWidth
              label={t('detail.resources.editor.template')}
              value={pendingTemplateKey}
              onChange={event => setPendingTemplateKey(event.target.value)}
            >
              {templates.map(template => (
                <MenuItem key={template.key} value={template.key}>
                  {template.name}
                </MenuItem>
              ))}
            </TextField>
            <Alert severity="warning">{t('detail.resources.editor.templateOverwriteWarning')}</Alert>
          </Stack>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setTemplateDialogOpen(false)}>
            {t('actions.cancel', { ns: 'common' })}
          </ActionButton>
          <ActionButton variant="contained" onClick={handleTemplateConfirm} disabled={!pendingTemplateKey}>
            {t('detail.resources.editor.templateApply')}
          </ActionButton>
        </DialogActions>
      </Dialog>
    </>
  )
}

function ResourceSummaryLine({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ minWidth: 0, wordBreak: 'break-word' }}>
        {value}
      </Typography>
    </Box>
  )
}

function CompactChipList({
  label,
  items,
  visibleCount,
  tone = 'primary',
}: {
  label: string
  items: string[]
  visibleCount: number
  tone?: 'primary' | 'secondary'
}) {
  const theme = useTheme()

  if (!items.length) {
    return <ResourceSummaryLine label={label} value="—" />
  }

  const visibleItems = items.slice(0, visibleCount)
  const hiddenItems = items.slice(visibleCount)
  const chipColor = tone === 'secondary' ? theme.palette.secondary.main : theme.palette.primary.main

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{
          flexShrink: 0,
          lineHeight: 1.2,
        }}
      >
        {label}
      </Typography>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          minWidth: 0,
          flexWrap: 'nowrap',
          overflow: 'hidden',
        }}
      >
        {visibleItems.map(item => (
          <Tooltip key={item} title={item} arrow>
            <Chip
              label={item}
              size="small"
              sx={[
                CHIP_VARIANTS.getCustomColorChip(chipColor, true) as object,
                {
                  maxWidth: 160,
                  flexShrink: 0,
                  borderRadius: 999,
                  '& .MuiChip-label': {
                    px: 0.9,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  },
                },
              ]}
            />
          </Tooltip>
        ))}
        {hiddenItems.length > 0 && (
          <Tooltip title={hiddenItems.join(', ')} arrow>
            <Chip
              label={`+${hiddenItems.length}`}
              size="small"
              sx={[
                CHIP_VARIANTS.getCustomColorChip(theme.palette.text.secondary, true) as object,
                {
                  flexShrink: 0,
                  borderRadius: 999,
                  '& .MuiChip-label': {
                    px: 0.8,
                  },
                },
              ]}
            />
          </Tooltip>
        )}
      </Box>
    </Box>
  )
}

function ResourceUsageLine({
  label,
  workspaces,
  onOpenWorkspace,
  emptyText,
  t,
}: {
  label: string
  workspaces: Array<{ id: number; name: string }>
  onOpenWorkspace: (workspaceId: number) => void
  emptyText: string
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  const theme = useTheme()

  if (!workspaces.length) {
    return <ResourceSummaryLine label={label} value={emptyText} />
  }

  const [primaryWorkspace, ...overflowWorkspaces] = workspaces

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0, lineHeight: 1.2 }}>
        {label}
      </Typography>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          minWidth: 0,
          flexWrap: 'nowrap',
          overflow: 'hidden',
        }}
      >
        <Tooltip title={primaryWorkspace.name} arrow>
          <Chip
            clickable
            label={primaryWorkspace.name}
            size="small"
            onClick={() => onOpenWorkspace(primaryWorkspace.id)}
            icon={<RouteIcon sx={{ fontSize: 14 }} />}
            sx={[
              CHIP_VARIANTS.getCustomColorChip(theme.palette.info.main, true) as object,
              {
                maxWidth: 180,
                flexShrink: 0,
                borderRadius: 999,
                cursor: 'pointer',
                transition: 'transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease',
                '&:hover': {
                  transform: 'translateY(-1px)',
                  boxShadow: `0 6px 16px ${alpha(theme.palette.info.main, 0.18)}`,
                },
                '& .MuiChip-label': {
                  px: 0.8,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                },
                '& .MuiChip-icon': {
                  color: 'inherit',
                  ml: 0.35,
                },
              },
            ]}
          />
        </Tooltip>

        {overflowWorkspaces.length > 0 && (
          <Tooltip
            arrow
            placement="top-start"
            title={
              <Stack spacing={0.9} sx={{ minWidth: 220, py: 0.25 }}>
                <Typography variant="caption" sx={{ display: 'block', fontWeight: 700, opacity: 0.98, px: 0.25 }}>
                  {t('detail.resources.tooltips.workspaceRefsTitle', { count: workspaces.length })}
                </Typography>
                {overflowWorkspaces.map(workspace => (
                  <Box
                    key={workspace.id}
                    component="button"
                    type="button"
                    onClick={() => onOpenWorkspace(workspace.id)}
                    sx={theme => ({
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: 1,
                      px: 1,
                      py: 0.85,
                      border: 'none',
                      borderRadius: 1.5,
                      backgroundColor: alpha(theme.palette.common.white, 0.08),
                      color: 'inherit',
                      cursor: 'pointer',
                      transition: 'background-color 0.18s ease, transform 0.18s ease',
                      '&:hover': {
                        backgroundColor: alpha(theme.palette.common.white, 0.16),
                        transform: 'translateX(2px)',
                      },
                    })}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {workspace.name}
                    </Typography>
                    <RouteIcon sx={{ fontSize: 16, opacity: 0.78, flexShrink: 0 }} />
                  </Box>
                ))}
              </Stack>
            }
          >
            <Chip
              label={`+${overflowWorkspaces.length}`}
              size="small"
              sx={[
                CHIP_VARIANTS.getCustomColorChip(theme.palette.text.secondary, true) as object,
                {
                  flexShrink: 0,
                  borderRadius: 999,
                  cursor: 'default',
                  '& .MuiChip-label': {
                    px: 0.8,
                  },
                },
              ]}
            />
          </Tooltip>
        )}
      </Box>
    </Box>
  )
}

function ResourceCard({
  resource,
  inWorkspace,
  mounted,
  actionWidth,
  onMount,
  onEdit,
  onDelete,
  onOpenWorkspace,
  t,
}: {
  resource: WorkspaceResourceBinding['resource']
  inWorkspace: boolean
  mounted: boolean
  actionWidth: number
  onMount: () => void
  onEdit: () => void
  onDelete: () => void
  onOpenWorkspace: (workspaceId: number) => void
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  return (
    <Card variant="outlined">
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Stack spacing={1.5}>
          <Box
            sx={{
              display: 'flex',
              alignItems: { xs: 'flex-start', md: 'center' },
              justifyContent: 'space-between',
              gap: 1.5,
              flexDirection: { xs: 'column', md: 'row' },
            }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                {resource.name}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {resource.resource_note || t('detail.resources.noDescription')}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
              {inWorkspace ? (
                mounted ? (
                  <ActionButton
                    size="small"
                    variant="outlined"
                    startIcon={<CheckCircleOutlineIcon />}
                    disabled
                    sx={{
                      width: actionWidth,
                      minWidth: actionWidth,
                      flexShrink: 0,
                      whiteSpace: 'nowrap',
                      '& .MuiButton-startIcon': { mr: 0.75, ml: 0 },
                    }}
                  >
                    {t('detail.resources.actions.mounted')}
                  </ActionButton>
                ) : (
                  <ActionButton
                    size="small"
                    variant="contained"
                    startIcon={<LinkIcon />}
                    onClick={onMount}
                    sx={{
                      width: actionWidth,
                      minWidth: actionWidth,
                      flexShrink: 0,
                      whiteSpace: 'nowrap',
                      '& .MuiButton-startIcon': { mr: 0.75, ml: 0 },
                    }}
                  >
                    {t('detail.resources.actions.mount')}
                  </ActionButton>
                )
              ) : (
                <>
                  <IconActionButton size="small" onClick={onEdit}>
                    <EditIcon fontSize="small" />
                  </IconActionButton>
                  <IconActionButton size="small" tone="danger" onClick={onDelete}>
                    <DeleteIcon fontSize="small" />
                  </IconActionButton>
                </>
              )}
            </Box>
          </Box>

          <Grid container spacing={1.5}>
            <Grid size={{ xs: 12, lg: 6 }}>
              <Stack spacing={1}>
                <ResourceSummaryLine
                  label={t('detail.resources.meta.fields')}
                  value={t('detail.resources.fieldCount', { count: resource.field_count })}
                />
                <CompactChipList
                  label={t('detail.resources.meta.tags')}
                  items={resource.resource_tags}
                  visibleCount={3}
                  tone="secondary"
                />
              </Stack>
            </Grid>
            <Grid size={{ xs: 12, lg: 6 }}>
              <Stack spacing={1}>
                <CompactChipList
                  label={t('detail.resources.meta.compatEnvNames')}
                  items={resource.fixed_aliases}
                  visibleCount={1}
                />
                <ResourceUsageLine
                  label={t('detail.resources.meta.usage')}
                  workspaces={resource.bound_workspaces}
                  onOpenWorkspace={onOpenWorkspace}
                  emptyText={t('detail.resources.tooltips.noWorkspaceRef')}
                  t={t}
                />
              </Stack>
            </Grid>
          </Grid>
        </Stack>
      </CardContent>
    </Card>
  )
}

function MountedResourceCard({
  binding,
  dragging,
  actionWidth,
  onDragStart,
  onDrop,
  onUnmount,
  t,
}: {
  binding: WorkspaceResourceBinding
  dragging: boolean
  actionWidth: number
  onDragStart: () => void
  onDrop: () => void
  onUnmount: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  const resource = binding.resource
  return (
    <Card
      variant="outlined"
      draggable
      onDragStart={onDragStart}
      onDragOver={event => event.preventDefault()}
      onDrop={onDrop}
      sx={{
        borderColor: dragging ? 'primary.main' : 'divider',
        backgroundColor: dragging ? theme => alpha(theme.palette.primary.main, 0.05) : 'background.paper',
      }}
    >
      <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
        <Stack spacing={1.25}>
          <Box
            sx={{
              display: 'flex',
              alignItems: { xs: 'flex-start', md: 'center' },
              justifyContent: 'space-between',
              gap: 1.25,
              flexDirection: { xs: 'column', md: 'row' },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', color: 'text.secondary', cursor: 'grab' }}>
                <DragIcon fontSize="small" />
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  {resource.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                  {resource.resource_note || t('detail.resources.noDescription')}
                </Typography>
              </Box>
            </Box>
            <ActionButton
              size="small"
              variant="outlined"
              startIcon={<LinkOffIcon />}
              onClick={onUnmount}
              sx={{
                width: actionWidth,
                minWidth: actionWidth,
                flexShrink: 0,
                whiteSpace: 'nowrap',
                '& .MuiButton-startIcon': { mr: 0.75, ml: 0 },
              }}
            >
              {t('detail.resources.actions.unmount')}
            </ActionButton>
          </Box>

          <Grid container spacing={1.25}>
            <Grid size={{ xs: 12, md: 6 }}>
              <CompactChipList
                label={t('detail.resources.meta.tags')}
                items={resource.resource_tags}
                visibleCount={3}
                tone="secondary"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <CompactChipList
                label={t('detail.resources.meta.compatEnvNames')}
                items={resource.fixed_aliases}
                visibleCount={1}
              />
            </Grid>
          </Grid>
        </Stack>
      </CardContent>
    </Card>
  )
}

export default function ResourcesTab({ workspace }: { workspace?: WorkspaceDetail }) {
  const theme = useTheme()
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t, i18n } = useTranslation('workspace')
  const navigate = useNavigate()
  const inWorkspace = workspace !== undefined
  const resourceActionWidth = i18n.resolvedLanguage?.startsWith('zh') ? 88 : 104

  const [search, setSearch] = useState('')
  const [editorOpen, setEditorOpen] = useState(false)
  const [editorMode, setEditorMode] = useState<EditorMode>('create')
  const [editingResourceId, setEditingResourceId] = useState<number | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<WorkspaceResourceBinding['resource'] | null>(null)
  const [dragBindingId, setDragBindingId] = useState<number | null>(null)

  const { data: templates = [] } = useQuery({
    queryKey: ['resource-templates'],
    queryFn: () => workspaceApi.getResourceTemplates(),
  })
  const { data: resources = [] } = useQuery({
    queryKey: ['resources'],
    queryFn: () => workspaceApi.getResources(),
  })
  const { data: bindings = [] } = useQuery({
    queryKey: ['workspace-resources', workspace?.id],
    queryFn: () => workspaceApi.getWorkspaceResources(workspace?.id as number),
    enabled: inWorkspace,
  })
  const { data: editingResource } = useQuery({
    queryKey: ['resource-detail', editingResourceId],
    queryFn: () => workspaceApi.getResourceDetail(editingResourceId as number),
    enabled: editingResourceId !== null,
  })

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['resources'] })
    if (workspace) {
      queryClient.invalidateQueries({ queryKey: ['workspace-resources', workspace.id] })
      queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
    }
    if (editingResourceId !== null) {
      queryClient.invalidateQueries({ queryKey: ['resource-detail', editingResourceId] })
    }
  }

  const createMutation = useMutation({
    mutationFn: (body: WorkspaceResourceUpsertBody) => workspaceApi.createResource(body),
    onSuccess: () => {
      notification.success(t('detail.resources.notifications.created'))
      invalidateAll()
      setEditorOpen(false)
    },
    onError: (error: Error) => notification.error(t('detail.resources.notifications.createFailed', { message: error.message })),
  })

  const updateMutation = useMutation({
    mutationFn: (body: WorkspaceResourceUpsertBody) => workspaceApi.updateResourceDetail(editingResourceId as number, body),
    onSuccess: () => {
      notification.success(t('detail.resources.notifications.updated'))
      invalidateAll()
      setEditorOpen(false)
    },
    onError: (error: Error) => notification.error(t('detail.resources.notifications.updateFailed', { message: error.message })),
  })

  const deleteMutation = useMutation({
    mutationFn: ({ resourceId, removeBindings }: { resourceId: number; removeBindings: boolean }) =>
      workspaceApi.deleteResourceDetail(resourceId, removeBindings),
    onSuccess: () => {
      notification.success(t('detail.resources.notifications.deleted'))
      invalidateAll()
      setDeleteTarget(null)
    },
    onError: (error: Error) => notification.error(t('detail.resources.notifications.deleteFailed', { message: error.message })),
  })

  const mountMutation = useMutation({
    mutationFn: async (resourceId: number) => {
      if (!workspace) throw new Error(t('detail.resources.notifications.workspaceRequired'))
      const conflicts = await workspaceApi.checkWorkspaceResourceBind(workspace.id, resourceId)
      if (conflicts.length) {
        throw new Error(
          t('detail.resources.notifications.mountConflict', {
            env: conflicts[0].env_name,
            name: conflicts[0].existing_resource_name,
          }),
        )
      }
      await workspaceApi.bindWorkspaceResource(workspace.id, resourceId)
    },
    onSuccess: () => {
      notification.success(t('detail.resources.notifications.mounted'))
      invalidateAll()
    },
    onError: (error: Error) => notification.error(t('detail.resources.notifications.mountFailed', { message: error.message })),
  })

  const unmountMutation = useMutation({
    mutationFn: (resourceId: number) => {
      if (!workspace) throw new Error(t('detail.resources.notifications.workspaceRequired'))
      return workspaceApi.unbindWorkspaceResource(workspace.id, resourceId)
    },
    onSuccess: () => {
      notification.success(t('detail.resources.notifications.unmounted'))
      invalidateAll()
    },
    onError: (error: Error) => notification.error(t('detail.resources.notifications.unmountFailed', { message: error.message })),
  })

  const reorderMutation = useMutation({
    mutationFn: (bindingIds: number[]) => {
      if (!workspace) throw new Error(t('detail.resources.notifications.workspaceRequired'))
      return workspaceApi.reorderWorkspaceResources(workspace.id, bindingIds)
    },
    onError: (error: Error) => notification.error(t('detail.resources.notifications.reorderFailed', { message: error.message })),
    onSuccess: () => invalidateAll(),
  })

  const mountedResourceIds = useMemo(() => new Set(bindings.map(item => item.resource_id)), [bindings])

  const filteredResources = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    if (!keyword) return resources
    return resources.filter(item =>
      item.name.toLowerCase().includes(keyword)
      || item.resource_note.toLowerCase().includes(keyword)
      || item.resource_tags.some(tag => tag.toLowerCase().includes(keyword)),
    )
  }, [resources, search])

  const mountedCount = bindings.length
  const availableCount = resources.length
  const aliasResourceCount = resources.filter(item => item.fixed_aliases.length > 0).length
  const sharedCount = resources.filter(item => item.bound_workspace_count > 1).length

  const initialCreateValue: WorkspaceResourceUpsertBody = useMemo(() => createEmptyResourceValue(), [])

  const initialEditValue: WorkspaceResourceUpsertBody = useMemo(
    () => (
      editingResource
        ? {
            name: editingResource.name,
            template_key: editingResource.template_key ?? undefined,
            resource_note: editingResource.resource_note,
            resource_tags: [...editingResource.resource_tags],
            resource_prompt: editingResource.resource_prompt,
            fields: editingResource.fields.map(field => ({ ...field })),
            enabled: editingResource.enabled,
          }
        : initialCreateValue
    ),
    [editingResource, initialCreateValue],
  )

  const openCreate = () => {
    blurActiveElement()
    setEditorMode('create')
    setEditingResourceId(null)
    setEditorOpen(true)
  }

  const openEdit = (resourceId: number) => {
    blurActiveElement()
    setEditorMode('edit')
    setEditingResourceId(resourceId)
    setEditorOpen(true)
  }

  const openDeleteDialog = (resource: WorkspaceResourceBinding['resource']) => {
    blurActiveElement()
    setDeleteTarget(resource)
  }

  const handleBindingDrop = (targetBinding: WorkspaceResourceBinding) => {
    if (dragBindingId === null || dragBindingId === targetBinding.binding_id) return
    const fromIndex = bindings.findIndex(item => item.binding_id === dragBindingId)
    const toIndex = bindings.findIndex(item => item.binding_id === targetBinding.binding_id)
    if (fromIndex < 0 || toIndex < 0) return
    const reordered = moveItem(bindings, fromIndex, toIndex).map(item => item.binding_id)
    reorderMutation.mutate(reordered)
    setDragBindingId(null)
  }

  const handleOpenWorkspaceMounts = (workspaceId: number) => {
    navigate(workspaceDetailPath(workspaceId, 'resources'))
  }

  if (!inWorkspace) {
    return (
      <>
        <Box sx={{ ...UNIFIED_TABLE_STYLES.tableLayoutContainer, gap: 2.5 }}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', flexShrink: 0 }}>
            <StatCard
              label={t('detail.resources.stats.total')}
              value={availableCount}
              icon={<StorageIcon sx={{ fontSize: 20 }} />}
              color={theme.palette.primary.main}
            />
            <StatCard
              label={t('detail.resources.stats.shared')}
              value={sharedCount}
              icon={<RouteIcon sx={{ fontSize: 20 }} />}
              color={theme.palette.success.main}
            />
            <StatCard
              label={t('detail.resources.stats.compat')}
              value={aliasResourceCount}
              icon={<TagIcon sx={{ fontSize: 20 }} />}
              color={theme.palette.warning.main}
            />
          </Box>

          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ p: 2.25 }}>
              <Stack spacing={2}>
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: { xs: 'column', lg: 'row' },
                    alignItems: { lg: 'center' },
                    justifyContent: 'space-between',
                    gap: 1.5,
                  }}
                >
                  <SearchField
                    placeholder={t('detail.resources.searchPlaceholder')}
                    value={search}
                    onChange={setSearch}
                    onClear={() => setSearch('')}
                    sx={{ width: { xs: '100%', sm: 320, md: 360 }, maxWidth: '100%' }}
                  />
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <ActionButton startIcon={<RefreshIcon />} onClick={() => invalidateAll()}>
                      {t('detail.resources.actions.refresh')}
                    </ActionButton>
                    <ActionButton variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
                      {t('detail.resources.actions.create')}
                    </ActionButton>
                  </Box>
                </Box>

                {filteredResources.length === 0 ? (
                  <Box
                    sx={{
                      py: 6,
                      textAlign: 'center',
                      color: 'text.secondary',
                    }}
                  >
                    <Typography variant="body1">{t('detail.resources.emptyLibrary')}</Typography>
                  </Box>
                ) : (
                  <Stack spacing={1.5}>
                    {filteredResources.map(resource => (
                      <ResourceCard
                        key={resource.id}
                        resource={resource}
                        inWorkspace={false}
                        mounted={false}
                        actionWidth={resourceActionWidth}
                        onMount={() => {}}
                        onEdit={() => openEdit(resource.id)}
                        onDelete={() => openDeleteDialog(resource)}
                        onOpenWorkspace={handleOpenWorkspaceMounts}
                        t={t}
                      />
                    ))}
                  </Stack>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Box>

      <ResourceEditorDialog
          open={editorOpen}
          mode={editorMode}
          templates={templates}
          initialValue={editorMode === 'create' ? initialCreateValue : initialEditValue}
          onClose={() => setEditorOpen(false)}
          onSubmit={value => {
            if (editorMode === 'create') {
              createMutation.mutate(value)
            } else {
              updateMutation.mutate(value)
            }
          }}
          t={t}
        />

        <Dialog
          open={deleteTarget !== null}
          onClose={() => !deleteMutation.isPending && setDeleteTarget(null)}
          maxWidth="sm"
          fullWidth
          disableRestoreFocus
        >
          <DialogTitle>{t('detail.resources.deleteDialog.title')}</DialogTitle>
          <DialogContent>
            {deleteTarget && (
              <Stack spacing={1.5}>
                <DialogContentText>
                  {deleteTarget.bound_workspace_count > 0
                    ? t('detail.resources.deleteDialog.contentWithBindings', {
                        name: deleteTarget.name,
                        count: deleteTarget.bound_workspace_count,
                      })
                    : t('detail.resources.deleteDialog.content', { name: deleteTarget.name })}
                </DialogContentText>
                {deleteTarget.bound_workspaces.length > 0 && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 0.75 }}>
                      {t('detail.resources.deleteDialog.boundListTitle')}
                    </Typography>
                    <Stack spacing={0.5}>
                      {deleteTarget.bound_workspaces.map(workspaceItem => (
                        <Typography key={workspaceItem.id} variant="body2">
                          {workspaceItem.name}
                        </Typography>
                      ))}
                    </Stack>
                  </Box>
                )}
              </Stack>
            )}
          </DialogContent>
          <DialogActions>
            <ActionButton onClick={() => setDeleteTarget(null)} disabled={deleteMutation.isPending}>
              {t('actions.cancel', { ns: 'common' })}
            </ActionButton>
            <ActionButton
              tone="danger"
              variant="contained"
              onClick={() => {
                if (!deleteTarget) return
                deleteMutation.mutate({
                  resourceId: deleteTarget.id,
                  removeBindings: deleteTarget.bound_workspace_count > 0,
                })
              }}
              disabled={deleteMutation.isPending}
            >
              {t('detail.resources.deleteDialog.confirm')}
            </ActionButton>
          </DialogActions>
        </Dialog>
      </>
    )
  }

  return (
    <Stack spacing={2}>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <StatCard
          label={t('detail.resources.stats.mounted')}
          value={mountedCount}
          icon={<LinkIcon sx={{ fontSize: 20 }} />}
          color={theme.palette.primary.main}
        />
        <StatCard
          label={t('detail.resources.stats.available')}
          value={availableCount}
          icon={<StorageIcon sx={{ fontSize: 20 }} />}
          color={theme.palette.info.main}
        />
      </Box>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, xl: 5 }}>
          <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%' }}>
            <CardContent sx={{ p: 2.25 }}>
              <Stack spacing={2}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: { xs: 'flex-start', sm: 'center' },
                    justifyContent: 'space-between',
                    gap: 1.5,
                    flexDirection: { xs: 'column', sm: 'row' },
                  }}
                >
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                      {t('detail.resources.mountsTitle')}
                    </Typography>
                  </Box>
                  <ActionButton
                    variant="outlined"
                    startIcon={<FolderOpenIcon />}
                    onClick={() => navigate('/workspace/resources')}
                  >
                    {t('detail.resources.actions.openCenter')}
                  </ActionButton>
                </Box>

                {bindings.length === 0 ? (
                  <Box
                    sx={{
                      py: 6,
                      borderRadius: 2,
                      border: '1px dashed',
                      borderColor: 'divider',
                      textAlign: 'center',
                    }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      {t('detail.resources.emptyMounted')}
                    </Typography>
                  </Box>
                ) : (
                  <Stack spacing={1.25}>
                    {bindings.map(binding => (
                      <MountedResourceCard
                        key={binding.binding_id}
                        binding={binding}
                        dragging={dragBindingId === binding.binding_id}
                        actionWidth={resourceActionWidth}
                        onDragStart={() => setDragBindingId(binding.binding_id)}
                        onDrop={() => handleBindingDrop(binding)}
                        onUnmount={() => unmountMutation.mutate(binding.resource_id)}
                        t={t}
                      />
                    ))}
                  </Stack>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, xl: 7 }}>
          <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%' }}>
            <CardContent sx={{ p: 2.25 }}>
              <Stack spacing={2}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: { xs: 'stretch', lg: 'center' },
                    justifyContent: 'space-between',
                    flexDirection: { xs: 'column', lg: 'row' },
                    gap: 1.5,
                  }}
                >
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                      {t('detail.resources.libraryTitle')}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <SearchField
                      placeholder={t('detail.resources.searchPlaceholder')}
                      value={search}
                      onChange={setSearch}
                      onClear={() => setSearch('')}
                      sx={{ width: { xs: '100%', sm: 320 } }}
                    />
                    <ActionButton startIcon={<RefreshIcon />} onClick={() => invalidateAll()}>
                      {t('detail.resources.actions.refresh')}
                    </ActionButton>
                  </Box>
                </Box>

                {filteredResources.length === 0 ? (
                  <Box
                    sx={{
                      py: 6,
                      textAlign: 'center',
                      color: 'text.secondary',
                    }}
                  >
                    <Typography variant="body2">{t('detail.resources.emptyLibrary')}</Typography>
                  </Box>
                ) : (
                  <Stack spacing={1.5}>
                    {filteredResources.map(resource => (
                      <ResourceCard
                        key={resource.id}
                        resource={resource}
                        inWorkspace
                        mounted={mountedResourceIds.has(resource.id)}
                        actionWidth={resourceActionWidth}
                        onMount={() => mountMutation.mutate(resource.id)}
                        onEdit={() => {}}
                        onDelete={() => {}}
                        onOpenWorkspace={handleOpenWorkspaceMounts}
                        t={t}
                      />
                    ))}
                  </Stack>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Stack>
  )
}
