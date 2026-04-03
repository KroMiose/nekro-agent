import { useEffect, useMemo, useState } from 'react'
import { Editor as MonacoEditor } from '@monaco-editor/react'
import {
  Box,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  IconButton,
  Skeleton,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import {
  AutoAwesome as AutoAwesomeIcon,
  ChevronRight as ChevronRightIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  InfoOutlined as InfoOutlinedIcon,
  Save as SaveIcon,
} from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import MarkdownRenderer from '../../../components/common/MarkdownRenderer'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS, CHIP_VARIANTS } from '../../../theme/variants'
import { PromptLayerItem, workspaceApi, WorkspaceDetail } from '../../../services/api/workspace'

type MainSectionKey = 'na_context' | 'shared_manual_rules' | 'execution_rules'
type ExecutionSubSection = 'cc_rules' | 'na_rules'
type SystemPromptView = 'preview' | 'source'

function targetLabel(target: PromptLayerItem['target']) {
  return {
    cc: '仅 CC',
    na: '仅 NA',
    shared: 'NA / CC',
  }[target]
}

function maintainerLabel(maintainer: PromptLayerItem['maintainer']) {
  return {
    manual: '手动维护',
    cc: 'CC 维护',
    na: 'NA 维护',
    'manual+cc': '手动 / CC',
    'manual+na': '手动 / NA',
  }[maintainer]
}

function compactPreview(content: string, fallback: string): string {
  const text = content.trim().replace(/\s+/g, ' ')
  if (!text) return fallback
  return text.length > 88 ? `${text.slice(0, 88)}…` : text
}

function SectionCard({
  title,
  subtitle,
  tooltip,
  preview,
  tone,
  active,
  onClick,
  metaLabels,
}: {
  title: string
  subtitle: string
  tooltip: string
  preview: string
  tone: string
  active: boolean
  onClick: () => void
  metaLabels: string[]
}) {
  const theme = useTheme()
  const isLight = theme.palette.mode === 'light'
  const accentColor = isLight ? tone : theme.palette.text.primary
  const subtitleColor = isLight ? alpha(theme.palette.text.primary, 0.72) : theme.palette.text.secondary
  const previewColor = isLight ? alpha(theme.palette.text.primary, active ? 0.82 : 0.72) : theme.palette.text.secondary
  const lightShadow = active
    ? '0 18px 40px rgba(15, 23, 42, 0.12), 0 6px 16px rgba(15, 23, 42, 0.08)'
    : '0 10px 28px rgba(15, 23, 42, 0.08), 0 3px 10px rgba(15, 23, 42, 0.05)'

  return (
    <Card
      onClick={onClick}
      sx={{
        ...CARD_VARIANTS.default.styles,
        cursor: 'pointer',
        position: 'relative',
        overflow: 'hidden',
        background: theme.palette.mode === 'light'
          ? theme.palette.background.paper
          : `linear-gradient(145deg, ${alpha(tone, active ? 0.16 : 0.1)} 0%, ${alpha(tone, 0.03)} 72%)`,
        boxShadow: theme.palette.mode === 'light'
          ? lightShadow
          : active
            ? `0 10px 24px ${alpha(tone, 0.16)}`
            : `0 4px 18px ${alpha(tone, 0.08)}`,
        transform: active ? 'translateY(-2px)' : 'translateY(0)',
        transition: 'all 0.22s ease',
        '&:hover': {
          transform: 'translateY(-3px)',
          boxShadow: theme.palette.mode === 'light'
            ? '0 20px 44px rgba(15, 23, 42, 0.14), 0 8px 18px rgba(15, 23, 42, 0.08)'
            : `0 14px 30px ${alpha(tone, 0.14)}`,
        },
      }}
    >
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          background: theme.palette.mode === 'light'
            ? 'transparent'
            : `radial-gradient(circle at top right, ${alpha(tone, 0.18)} 0%, transparent 48%)`,
          pointerEvents: 'none',
        }}
      />
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 4,
          bgcolor: alpha(tone, active ? 0.92 : 0.72),
        }}
      />
      <CardContent sx={{ p: 2.25, '&:last-child': { pb: 2.25 }, position: 'relative' }}>
        <Stack spacing={1.25}>
          <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={1.5}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle1" fontWeight={700} sx={{ color: isLight ? alpha(theme.palette.text.primary, 0.94) : 'text.primary' }}>
                {title}
              </Typography>
              <Stack direction="row" spacing={0.5} alignItems="center">
                <Typography variant="caption" sx={{ color: subtitleColor }}>
                  {subtitle}
                </Typography>
                <Tooltip title={tooltip} placement="top">
                  <InfoOutlinedIcon sx={{ fontSize: 14, color: isLight ? alpha(accentColor, 0.72) : 'text.disabled' }} />
                </Tooltip>
              </Stack>
            </Box>
            <Box
              sx={{
                width: 30,
                height: 30,
                borderRadius: '10px',
                bgcolor: alpha(tone, isLight ? (active ? 0.16 : 0.1) : (active ? 0.2 : 0.14)),
                color: accentColor,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <ChevronRightIcon fontSize="small" />
            </Box>
          </Stack>

          <Typography
            variant="body2"
            sx={{
              minHeight: 42,
              color: previewColor,
              lineHeight: 1.6,
              fontWeight: isLight ? 500 : 400,
            }}
          >
            {preview}
          </Typography>

          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
            {metaLabels.map(label => (
              <Chip
                key={label}
                label={label}
                size="small"
                sx={isLight ? {
                  color: alpha(accentColor, 0.92),
                  bgcolor: alpha(tone, 0.08),
                  fontWeight: 600,
                  '& .MuiChip-label': { px: 1.1 },
                } : CHIP_VARIANTS.getCustomColorChip(tone, true)}
              />
            ))}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}

function EditorPanel({
  title,
  subtitle,
  tooltip,
  tone,
  draft,
  placeholder,
  isDirty,
  isSaving,
  onSave,
  onChange,
  metaLabels,
  extraActions,
  footerNote,
}: {
  title: string
  subtitle: string
  tooltip: string
  tone: string
  draft: string
  placeholder: string
  isDirty: boolean
  isSaving: boolean
  onSave: () => void
  onChange: (value: string) => void
  metaLabels: string[]
  extraActions?: React.ReactNode
  footerNote?: React.ReactNode
}) {
  const theme = useTheme()

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        overflow: 'hidden',
        boxShadow: theme.palette.mode === 'light'
          ? `0 10px 28px ${alpha(theme.palette.common.black, 0.05)}`
          : undefined,
        background: theme.palette.mode === 'light'
          ? theme.palette.background.paper
          : undefined,
      }}
    >
      <Box
        sx={{
          height: 4,
          background: `linear-gradient(90deg, ${alpha(tone, 0.92)} 0%, ${alpha(tone, 0.35)} 100%)`,
        }}
      />
      <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
        <Stack spacing={1.5}>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            justifyContent="space-between"
            alignItems={{ xs: 'flex-start', md: 'flex-start' }}
            spacing={1.5}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle1" fontWeight={700}>
                {title}
              </Typography>
              <Stack direction="row" spacing={0.5} alignItems="center">
                <Typography variant="caption" color="text.secondary">
                  {subtitle}
                </Typography>
                <Tooltip title={tooltip} placement="top">
                  <InfoOutlinedIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
                </Tooltip>
              </Stack>
            </Box>
            <Stack direction="row" spacing={1} alignItems="center">
              {extraActions}
              <Button
                variant="contained"
                size="small"
                startIcon={isSaving ? <CircularProgress size={14} color="inherit" /> : <SaveIcon />}
                onClick={onSave}
                disabled={!isDirty || isSaving}
              >
                保存
              </Button>
            </Stack>
          </Stack>

          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
            {metaLabels.map(label => (
              <Chip key={label} label={label} size="small" sx={CHIP_VARIANTS.getCustomColorChip(tone, true)} />
            ))}
          </Stack>

          <Box
            sx={{
              borderRadius: 2,
              overflow: 'hidden',
              bgcolor: theme.palette.mode === 'dark' ? 'rgba(10, 18, 32, 0.42)' : alpha(theme.palette.common.black, 0.018),
            }}
          >
            {!draft.trim() ? (
              <Box
                sx={{
                  px: 1.5,
                  py: 1,
                  bgcolor: theme.palette.mode === 'dark' ? alpha(tone, 0.04) : alpha(theme.palette.common.black, 0.02),
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {placeholder}
                </Typography>
              </Box>
            ) : null}
            <MonacoEditor
              height="320px"
              language="markdown"
              value={draft}
              onChange={value => onChange(value ?? '')}
              theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'vs'}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: 'on',
                wordWrap: 'on',
                scrollBeyondLastLine: false,
                renderLineHighlight: 'none',
                automaticLayout: true,
                padding: { top: 12, bottom: 12 },
              }}
            />
          </Box>

          {footerNote}
        </Stack>
      </CardContent>
    </Card>
  )
}

function LoadingSectionCard() {
  const theme = useTheme()

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        overflow: 'hidden',
        background: theme.palette.background.paper,
        boxShadow: theme.palette.mode === 'light'
          ? '0 10px 28px rgba(15, 23, 42, 0.08), 0 3px 10px rgba(15, 23, 42, 0.05)'
          : undefined,
      }}
    >
      <Box sx={{ height: 4, bgcolor: alpha(theme.palette.text.primary, 0.08) }} />
      <CardContent sx={{ p: 2.25, '&:last-child': { pb: 2.25 } }}>
        <Stack spacing={1.25}>
          <Stack direction="row" justifyContent="space-between" spacing={1.5}>
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="44%" height={30} />
              <Skeleton variant="text" width="58%" height={20} />
            </Box>
            <Skeleton variant="rounded" width={30} height={30} />
          </Stack>
          <Box>
            <Skeleton variant="text" width="96%" />
            <Skeleton variant="text" width="74%" />
          </Box>
          <Stack direction="row" spacing={0.75}>
            <Skeleton variant="rounded" width={76} height={24} />
            <Skeleton variant="rounded" width={92} height={24} />
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}

function LoadingEditorPanel() {
  const theme = useTheme()

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        overflow: 'hidden',
        background: theme.palette.background.paper,
        boxShadow: theme.palette.mode === 'light'
          ? `0 10px 28px ${alpha(theme.palette.common.black, 0.05)}`
          : undefined,
      }}
    >
      <Box sx={{ height: 4, bgcolor: alpha(theme.palette.text.primary, 0.08) }} />
      <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
        <Stack spacing={1.5}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={1.5}>
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="28%" height={32} />
              <Skeleton variant="text" width="36%" height={20} />
            </Box>
            <Stack direction="row" spacing={1}>
              <Skeleton variant="rounded" width={72} height={32} />
              <Skeleton variant="rounded" width={88} height={32} />
            </Stack>
          </Stack>
          <Stack direction="row" spacing={0.75}>
            <Skeleton variant="rounded" width={84} height={24} />
            <Skeleton variant="rounded" width={96} height={24} />
            <Skeleton variant="rounded" width={108} height={24} />
          </Stack>
          <Skeleton variant="rounded" width="100%" height={320} />
        </Stack>
      </CardContent>
    </Card>
  )
}

export default function PromptTab({ workspace }: { workspace: WorkspaceDetail }) {
  const theme = useTheme()
  const { t } = useTranslation('workspace')
  const notification = useNotification()
  const queryClient = useQueryClient()

  const [previewExpanded, setPreviewExpanded] = useState(false)
  const [systemPromptView, setSystemPromptView] = useState<SystemPromptView>('preview')
  const [activeSection, setActiveSection] = useState<MainSectionKey>('na_context')
  const [executionSubSection, setExecutionSubSection] = useState<ExecutionSubSection>('cc_rules')
  const [ccRulesDraft, setCcRulesDraft] = useState('')
  const [naContextDraft, setNaContextDraft] = useState('')
  const [sharedRulesDraft, setSharedRulesDraft] = useState('')
  const [naRulesDraft, setNaRulesDraft] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['prompt-composer', workspace.id],
    queryFn: () => workspaceApi.getPromptComposer(workspace.id),
  })

  useEffect(() => {
    if (!data) return
    setCcRulesDraft(data.claude_md_extra)
    setNaContextDraft(data.na_context.content)
    setSharedRulesDraft(data.shared_manual_rules.content)
    setNaRulesDraft(data.na_manual_rules.content)
  }, [data])

  const invalidatePromptComposer = () => {
    queryClient.invalidateQueries({ queryKey: ['prompt-composer', workspace.id] })
    queryClient.invalidateQueries({ queryKey: ['claude-md', workspace.id] })
  }

  const saveCcRulesMutation = useMutation({
    mutationFn: () => workspaceApi.updateClaudeMdExtra(workspace.id, ccRulesDraft),
    onSuccess: () => {
      invalidatePromptComposer()
      notification.success(t('detail.prompt.notifications.saveSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.prompt.notifications.saveFailed', { message: err.message })),
  })

  const saveNaContextMutation = useMutation({
    mutationFn: () => workspaceApi.updatePromptComposerNaContext(workspace.id, naContextDraft),
    onSuccess: () => {
      invalidatePromptComposer()
      notification.success(t('detail.prompt.notifications.naContextSaveSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.prompt.notifications.saveFailed', { message: err.message })),
  })

  const saveSharedRulesMutation = useMutation({
    mutationFn: () => workspaceApi.updatePromptComposerSharedRules(workspace.id, sharedRulesDraft),
    onSuccess: () => {
      invalidatePromptComposer()
      notification.success(t('detail.prompt.notifications.sharedRulesSaveSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.prompt.notifications.saveFailed', { message: err.message })),
  })

  const saveNaRulesMutation = useMutation({
    mutationFn: () => workspaceApi.updatePromptComposerNaRules(workspace.id, naRulesDraft),
    onSuccess: () => {
      invalidatePromptComposer()
      notification.success(t('detail.prompt.notifications.naRulesSaveSuccess'))
    },
    onError: (err: Error) => notification.error(t('detail.prompt.notifications.saveFailed', { message: err.message })),
  })

  const dirtyState = useMemo(() => ({
    ccRules: data ? ccRulesDraft !== data.claude_md_extra : false,
    naContext: data ? naContextDraft !== data.na_context.content : false,
    sharedRules: data ? sharedRulesDraft !== data.shared_manual_rules.content : false,
    naRules: data ? naRulesDraft !== data.na_manual_rules.content : false,
  }), [ccRulesDraft, data, naContextDraft, naRulesDraft, sharedRulesDraft])

  const executionTone = theme.palette.primary.main
  const executionLayer: PromptLayerItem = executionSubSection === 'cc_rules'
    ? {
        key: 'cc_manual_rules',
        title: t('detail.prompt.extraTitle'),
        target: 'cc',
        maintainer: 'manual',
        content: ccRulesDraft,
        description: '',
        editable_by_cc: false,
        auto_inject: true,
        updated_at: null,
        updated_by: 'manual',
      }
    : data?.na_manual_rules ?? {
        key: 'na_manual_rules',
        title: t('detail.prompt.naRulesTitle'),
        target: 'na',
        maintainer: 'manual',
        content: naRulesDraft,
        description: '',
        editable_by_cc: false,
        auto_inject: true,
        updated_at: null,
        updated_by: 'manual',
      }

  return (
    <Stack spacing={1.5} sx={{ flex: 1 }}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: 'repeat(3, minmax(0, 1fr))' },
          gap: 2,
        }}
      >
        {data ? (
          <>
            <SectionCard
              title={t('detail.prompt.summaryCards.naContext.title')}
              subtitle={t('detail.prompt.naContextHint')}
              tooltip={t('detail.prompt.naContextDesc')}
              preview={compactPreview(naContextDraft, '记录当前状态、临时说明和最新进展')}
              tone={theme.palette.info.main}
              active={activeSection === 'na_context'}
              onClick={() => setActiveSection('na_context')}
              metaLabels={['当前状态', '可由 CC 自动更新']}
            />
            <SectionCard
              title={t('detail.prompt.summaryCards.sharedFacts.title')}
              subtitle={t('detail.prompt.sharedFactsHint')}
              tooltip={t('detail.prompt.sharedFactsDesc')}
              preview={compactPreview(sharedRulesDraft, '适合放长期有效的事实与约束')}
              tone={theme.palette.success.main}
              active={activeSection === 'shared_manual_rules'}
              onClick={() => setActiveSection('shared_manual_rules')}
              metaLabels={['NA / CC', '保持稳定']}
            />
            <SectionCard
              title={t('detail.prompt.summaryCards.ccRules.title')}
              subtitle={t('detail.prompt.summaryCards.ccRules.subtitle')}
              tooltip={t('detail.prompt.summaryCards.ccRules.tooltip')}
              preview={`CC：${compactPreview(ccRulesDraft, '执行规则、代码风格、输出要求')} / NA：${compactPreview(naRulesDraft, '表达方式、沟通边界、回复偏好')}`}
              tone={executionTone}
              active={activeSection === 'execution_rules'}
              onClick={() => setActiveSection('execution_rules')}
              metaLabels={['CC / NA', '分别配置']}
            />
          </>
        ) : (
          <>
            <LoadingSectionCard />
            <LoadingSectionCard />
            <LoadingSectionCard />
          </>
        )}
      </Box>

      {!data && isLoading && <LoadingEditorPanel />}

      {data && activeSection === 'na_context' && (
        <EditorPanel
          title={t('detail.prompt.naContextTitle')}
          subtitle={t('detail.prompt.naContextHint')}
          tooltip={t('detail.prompt.naContextDesc')}
          tone={theme.palette.info.main}
          draft={naContextDraft}
          placeholder={t('detail.prompt.naContextPlaceholder')}
          isDirty={dirtyState.naContext}
          isSaving={saveNaContextMutation.isPending}
          onSave={() => saveNaContextMutation.mutate()}
          onChange={setNaContextDraft}
          metaLabels={[
            targetLabel(data.na_context.target),
            maintainerLabel(data.na_context.maintainer),
            data.na_context.editable_by_cc ? '可由 CC 自动更新' : '仅手动维护',
          ]}
          footerNote={(
            <Box
              sx={{
                px: 1.25,
                py: 1,
                borderRadius: 1.5,
                bgcolor: alpha(theme.palette.info.main, 0.05),
              }}
            >
              <Stack direction="row" spacing={0.75} alignItems="flex-start">
                <AutoAwesomeIcon sx={{ fontSize: 16, color: theme.palette.info.main, mt: '2px', flexShrink: 0 }} />
                <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.65 }}>
                  {t('detail.prompt.naContextWarning')}
                </Typography>
              </Stack>
            </Box>
          )}
        />
      )}

      {data && activeSection === 'shared_manual_rules' && (
        <EditorPanel
          title={t('detail.prompt.sharedFactsTitle')}
          subtitle={t('detail.prompt.sharedFactsHint')}
          tooltip={t('detail.prompt.sharedFactsDesc')}
          tone={theme.palette.success.main}
          draft={sharedRulesDraft}
          placeholder={t('detail.prompt.sharedFactsPlaceholder')}
          isDirty={dirtyState.sharedRules}
          isSaving={saveSharedRulesMutation.isPending}
          onSave={() => saveSharedRulesMutation.mutate()}
          onChange={setSharedRulesDraft}
          metaLabels={[
            targetLabel(data.shared_manual_rules.target),
            maintainerLabel(data.shared_manual_rules.maintainer),
            '建议长期保留',
          ]}
        />
      )}

      {data && activeSection === 'execution_rules' && (
        <EditorPanel
          title={executionSubSection === 'cc_rules' ? t('detail.prompt.extraTitle') : t('detail.prompt.naRulesTitle')}
          subtitle={executionSubSection === 'cc_rules' ? t('detail.prompt.extraHint') : t('detail.prompt.naRulesHint')}
          tooltip={executionSubSection === 'cc_rules' ? t('detail.prompt.ccRulesDesc') : t('detail.prompt.naRulesDesc')}
          tone={executionTone}
          draft={executionSubSection === 'cc_rules' ? ccRulesDraft : naRulesDraft}
          placeholder={executionSubSection === 'cc_rules' ? t('detail.prompt.extraPlaceholder') : t('detail.prompt.naRulesPlaceholder')}
          isDirty={executionSubSection === 'cc_rules' ? dirtyState.ccRules : dirtyState.naRules}
          isSaving={executionSubSection === 'cc_rules' ? saveCcRulesMutation.isPending : saveNaRulesMutation.isPending}
          onSave={() => {
            if (executionSubSection === 'cc_rules') {
              saveCcRulesMutation.mutate()
              return
            }
            saveNaRulesMutation.mutate()
          }}
          onChange={value => {
            if (executionSubSection === 'cc_rules') {
              setCcRulesDraft(value)
              return
            }
            setNaRulesDraft(value)
          }}
          metaLabels={[
            targetLabel(executionLayer.target),
            maintainerLabel(executionLayer.maintainer),
            executionSubSection === 'cc_rules' ? '执行约束' : '表达策略',
          ]}
          extraActions={(
            <ButtonGroup size="small" variant="outlined" sx={{ flexShrink: 0 }}>
              <Button
                variant={executionSubSection === 'cc_rules' ? 'contained' : 'outlined'}
                onClick={() => setExecutionSubSection('cc_rules')}
              >
                CC
              </Button>
              <Button
                variant={executionSubSection === 'na_rules' ? 'contained' : 'outlined'}
                onClick={() => setExecutionSubSection('na_rules')}
              >
                NA
              </Button>
            </ButtonGroup>
          )}
        />
      )}

      <Card
        onClick={() => setPreviewExpanded(v => !v)}
        sx={{
          ...CARD_VARIANTS.default.styles,
          cursor: 'pointer',
        background: theme.palette.mode === 'light'
          ? theme.palette.background.paper
          : undefined,
        boxShadow: theme.palette.mode === 'light'
          ? `0 8px 24px ${alpha(theme.palette.common.black, 0.05)}`
            : undefined,
          transition: 'all 0.18s ease',
          '&:hover': {
            boxShadow: theme.shadows[6],
          },
        }}
      >
        <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
            <Box>
              <Typography variant="subtitle2" fontWeight={700}>
                {t('detail.prompt.systemPromptTitle')}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t('detail.prompt.systemPromptHint')}
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} alignItems="center">
              {previewExpanded ? (
                <ButtonGroup size="small" variant="outlined" sx={{ flexShrink: 0 }}>
                  <Button
                    variant={systemPromptView === 'preview' ? 'contained' : 'outlined'}
                    onClick={event => {
                      event.stopPropagation()
                      setSystemPromptView('preview')
                    }}
                  >
                    预览
                  </Button>
                  <Button
                    variant={systemPromptView === 'source' ? 'contained' : 'outlined'}
                    onClick={event => {
                      event.stopPropagation()
                      setSystemPromptView('source')
                    }}
                  >
                    源文
                  </Button>
                </ButtonGroup>
              ) : null}
              <Tooltip title={previewExpanded ? t('detail.prompt.collapseTooltip') : t('detail.prompt.expandTooltip')}>
                <IconButton
                  size="small"
                  onClick={event => {
                    event.stopPropagation()
                    setPreviewExpanded(v => !v)
                  }}
                >
                  {previewExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
            </Stack>
          </Stack>

          <Collapse in={previewExpanded || (!data && isLoading)}>
            <Divider sx={{ my: 1.5 }} />
            {isLoading ? (
              <Stack spacing={1.5}>
                <Stack direction="row" spacing={1}>
                  <Skeleton variant="rounded" width={68} height={32} />
                  <Skeleton variant="rounded" width={68} height={32} />
                </Stack>
                <Skeleton variant="rounded" width="100%" height={220} />
              </Stack>
            ) : (
              <Stack spacing={1.5}>
                {systemPromptView === 'preview' ? (
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: 1.5,
                      bgcolor: 'background.default',
                      boxShadow: 'none',
                      maxHeight: 520,
                      overflowY: 'auto',
                    }}
                  >
                    <MarkdownRenderer enableHtml={false}>
                      {data?.claude_md_content ?? ''}
                    </MarkdownRenderer>
                  </Box>
                ) : (
                  <Box
                    sx={{
                      borderRadius: 1.5,
                      overflow: 'hidden',
                      boxShadow: 'none',
                    }}
                  >
                    <MonacoEditor
                      height="520px"
                      language="markdown"
                      value={data?.claude_md_content ?? ''}
                      theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'vs'}
                      options={{
                        readOnly: true,
                        minimap: { enabled: false },
                        fontSize: 13,
                        lineNumbers: 'on',
                        wordWrap: 'on',
                        scrollBeyondLastLine: false,
                        renderLineHighlight: 'none',
                        automaticLayout: true,
                        padding: { top: 12, bottom: 12 },
                      }}
                    />
                  </Box>
                )}
              </Stack>
            )}
          </Collapse>
        </CardContent>
      </Card>
    </Stack>
  )
}
