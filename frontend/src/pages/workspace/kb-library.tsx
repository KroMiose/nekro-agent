import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Card,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Drawer,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  OutlinedInput,
  Paper,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useTheme,
} from '@mui/material'
import {
  Add as AddIcon,
  AutoAwesome as LibraryIcon,
  Close as CloseIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  FileUpload as FileUploadIcon,
  Link as BindIcon,
  Refresh as RefreshIcon,
  RestartAlt as ReindexIcon,
  FilterAltOff as FilterAltOffIcon,
  Description as AssetIcon,
  Hub as BindingsIcon,
  ViewModule as GridViewIcon,
  FormatListBulleted as ListViewIcon,
} from '@mui/icons-material'
import { alpha, type SxProps, type Theme } from '@mui/material/styles'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  KbLibraryIndexProgressInfo,
  useSystemEventsContext,
} from '../../contexts/SystemEventsContext'
import {
  KBAssetDetailResponse,
  KBAssetListItem,
  KBCreateTextDocumentBody,
  KBUploadFilePayload,
  kbLibraryApi,
  workspaceApi,
} from '../../services/api/workspace'
import { useNotification } from '../../hooks/useNotification'
import { CARD_VARIANTS, CHIP_VARIANTS, UNIFIED_TABLE_STYLES } from '../../theme/variants'
import SearchField from '../../components/common/SearchField'
import SegmentedControl from '../../components/common/SegmentedControl'
import IconActionButton from '../../components/common/IconActionButton'
import ActionButton from '../../components/common/ActionButton'
import StatCard from '../../components/common/StatCard'

type FilterStatus = 'all' | 'ready' | 'indexing' | 'failed'
type ViewMode = 'card' | 'list'

const SUPPORTED_UPLOAD_EXTENSIONS = ['.md', '.txt', '.html', '.htm', '.json', '.yaml', '.yml', '.csv', '.xlsx', '.pdf', '.docx']
const EMPTY_ASSETS: KBAssetListItem[] = []
const EMPTY_WORKSPACES: Awaited<ReturnType<typeof workspaceApi.getList>> = []
const TEXT_FORMAT_OPTIONS: Array<{ value: 'markdown' | 'text'; label: string }> = [
  { value: 'markdown', label: 'Markdown' },
  { value: 'text', label: 'Text' },
]

function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatFileSize(size: number): string {
  if (size < 1024) return `${size}B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)}KB`
  return `${(size / 1024 / 1024).toFixed(1)}MB`
}

function getEffectiveStatus(asset: KBAssetListItem): FilterStatus {
  if (asset.extract_status === 'failed' || asset.sync_status === 'failed') return 'failed'
  if (asset.extract_status !== 'ready') return 'indexing'
  if (asset.sync_status !== 'ready') return 'indexing'
  return 'ready'
}

function getProgressStatus(progress: KbLibraryIndexProgressInfo | null | undefined): FilterStatus | null {
  if (!progress) return null
  if (progress.phase === 'failed') return 'failed'
  if (progress.phase === 'ready') return 'ready'
  return 'indexing'
}

function getFileExtension(fileName: string): string {
  const match = fileName.toLowerCase().match(/(\.[^.]+)$/)
  return match?.[1] ?? ''
}

function isSupportedUploadFile(file: File): boolean {
  return SUPPORTED_UPLOAD_EXTENSIONS.includes(getFileExtension(file.name))
}

function normalizeTagsInput(raw: string): string[] {
  return raw
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

function previewContent(detail: KBAssetDetailResponse | undefined): string {
  if (!detail) return ''
  return detail.normalized_content ?? ''
}

function clearInteractiveFocus() {
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur()
  }
}

export default function KbLibraryPage() {
  const theme = useTheme()
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const { kbLibraryIndexProgresses } = useSystemEventsContext()
  const lastProgressTerminalRef = useRef('')

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all')
  const [viewMode, setViewMode] = useState<ViewMode>('card')
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [bindOpen, setBindOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [createForm, setCreateForm] = useState<KBCreateTextDocumentBody>({
    title: '',
    content: '',
    source_path: '',
    file_name: '',
    format: 'markdown',
    category: '',
    tags: [],
    summary: '',
    is_enabled: true,
  })
  const [createTagsInput, setCreateTagsInput] = useState('')
  const [uploadPayload, setUploadPayload] = useState<KBUploadFilePayload | null>(null)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadCategory, setUploadCategory] = useState('')
  const [uploadSummary, setUploadSummary] = useState('')
  const [uploadTagsInput, setUploadTagsInput] = useState('')
  const [bindWorkspaceIds, setBindWorkspaceIds] = useState<number[]>([])
  const [uploadProgress, setUploadProgress] = useState<number>(0)

  const assetsQuery = useQuery({
    queryKey: ['kb-library-assets'],
    queryFn: () => kbLibraryApi.list(),
  })

  const workspacesQuery = useQuery({
    queryKey: ['workspaces-list'],
    queryFn: () => workspaceApi.getList(),
  })

  const assets = assetsQuery.data ?? EMPTY_ASSETS
  const workspaces = workspacesQuery.data ?? EMPTY_WORKSPACES

  const filteredAssets = useMemo(() => {
    const loweredSearch = search.trim().toLowerCase()
    return assets.filter(asset => {
      if (statusFilter !== 'all' && getEffectiveStatus(asset) !== statusFilter) return false
      if (!loweredSearch) return true
      return [
        asset.title,
        asset.source_path,
        asset.category,
        asset.summary,
        asset.tags.join(' '),
      ]
        .join(' ')
        .toLowerCase()
        .includes(loweredSearch)
    })
  }, [assets, search, statusFilter])

  const stats = useMemo(
    () => ({
      total: assets.length,
      ready: assets.filter(asset => getEffectiveStatus(asset) === 'ready').length,
      indexing: assets.filter(asset => getEffectiveStatus(asset) === 'indexing').length,
      bindings: assets.reduce((sum, asset) => sum + asset.binding_count, 0),
    }),
    [assets]
  )

  const selectedAsset = useMemo(
    () => filteredAssets.find(item => item.id === selectedAssetId) ?? assets.find(item => item.id === selectedAssetId) ?? null,
    [assets, filteredAssets, selectedAssetId]
  )

  const assetDetailQuery = useQuery({
    queryKey: ['kb-library-asset', selectedAssetId],
    queryFn: () => kbLibraryApi.getAsset(selectedAssetId as number),
    enabled: selectedAssetId != null,
  })

  const refreshAll = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['kb-library-assets'] }),
      queryClient.invalidateQueries({ queryKey: ['kb-library-asset'] }),
    ])
  }, [queryClient])

  const createMutation = useMutation({
    mutationFn: (body: KBCreateTextDocumentBody) => kbLibraryApi.createText(body),
    onSuccess: async data => {
      await refreshAll()
      setSelectedAssetId(data.asset.id)
      setCreateOpen(false)
      setCreateForm({
        title: '',
        content: '',
        source_path: '',
        file_name: '',
        format: 'markdown',
        category: '',
        tags: [],
        summary: '',
        is_enabled: true,
      })
      setCreateTagsInput('')
      notification.success(
        data.reused_existing
          ? t('kbLibrary.notifications.createReused')
          : t('kbLibrary.notifications.createSuccess')
      )
    },
    onError: (err: Error) => notification.error(t('kbLibrary.notifications.createFailed', { message: err.message })),
  })

  const uploadMutation = useMutation({
    mutationFn: (payload: KBUploadFilePayload) =>
      kbLibraryApi.uploadFile(payload, percent => setUploadProgress(percent)),
    onSuccess: async data => {
      await refreshAll()
      setSelectedAssetId(data.asset.id)
      setUploadOpen(false)
      setUploadPayload(null)
      setUploadTitle('')
      setUploadCategory('')
      setUploadSummary('')
      setUploadTagsInput('')
      setUploadProgress(0)
      notification.success(
        data.reused_existing
          ? t('kbLibrary.notifications.uploadReused')
          : t('kbLibrary.notifications.uploadSuccess')
      )
    },
    onError: (err: Error) => {
      setUploadProgress(0)
      notification.error(t('kbLibrary.notifications.uploadFailed', { message: err.message }))
    },
  })

  const reindexMutation = useMutation({
    mutationFn: (assetId: number) => kbLibraryApi.reindexAsset(assetId),
    onSuccess: async () => {
      await refreshAll()
      notification.success(t('kbLibrary.notifications.reindexSuccess'))
    },
    onError: (err: Error) => notification.error(t('kbLibrary.notifications.reindexFailed', { message: err.message })),
  })

  const deleteMutation = useMutation({
    mutationFn: (assetId: number) => kbLibraryApi.deleteAsset(assetId),
    onSuccess: async () => {
      await refreshAll()
      setDeleteOpen(false)
      setSelectedAssetId(null)
      clearInteractiveFocus()
      notification.success(t('kbLibrary.notifications.deleteSuccess'))
    },
    onError: (err: Error) => notification.error(t('kbLibrary.notifications.deleteFailed', { message: err.message })),
  })

  const bindingsMutation = useMutation({
    mutationFn: ({ assetId, workspaceIds }: { assetId: number; workspaceIds: number[] }) =>
      kbLibraryApi.updateBindings(assetId, workspaceIds),
    onSuccess: async () => {
      await refreshAll()
      setBindOpen(false)
      notification.success(t('kbLibrary.notifications.bindSuccess'))
    },
    onError: (err: Error) => notification.error(t('kbLibrary.notifications.bindFailed', { message: err.message })),
  })

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    if (!file) {
      setUploadPayload(null)
      return
    }
    if (!isSupportedUploadFile(file)) {
      notification.error(
        t('kbLibrary.notifications.unsupportedFormat', {
          name: file.name,
          formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', '),
        })
      )
      event.target.value = ''
      return
    }
    setUploadPayload({ file, is_enabled: true })
    if (!uploadTitle.trim()) {
      setUploadTitle(file.name.replace(/\.[^.]+$/, ''))
    }
  }

  const handleUploadSubmit = () => {
    if (!uploadPayload?.file) return
    uploadMutation.mutate({
      ...uploadPayload,
      title: uploadTitle,
      category: uploadCategory,
      summary: uploadSummary,
      tags: normalizeTagsInput(uploadTagsInput),
      is_enabled: true,
    })
  }

  const handleCreateSubmit = () => {
    if (!createForm.title.trim() || !createForm.content.trim()) return
    createMutation.mutate({
      ...createForm,
      tags: normalizeTagsInput(createTagsInput),
    })
  }

  const handleDownloadRaw = async (asset: KBAssetListItem) => {
    try {
      const { blob, filename } = await kbLibraryApi.downloadRawFile(asset.id)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename ?? asset.file_name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      notification.error(t('kbLibrary.notifications.downloadFailed', { message: (err as Error).message }))
    }
  }

  const detail = assetDetailQuery.data
  const selectedProgress = selectedAssetId != null ? kbLibraryIndexProgresses.get(selectedAssetId) ?? null : null
  const selectedProgressStatus = getProgressStatus(selectedProgress)
  const progressByAssetId = useMemo(() => new Map<number, KbLibraryIndexProgressInfo>(kbLibraryIndexProgresses), [kbLibraryIndexProgresses])
  const terminalSignature = useMemo(
    () =>
      Array.from(kbLibraryIndexProgresses.values())
        .filter(item => item.phase === 'ready' || item.phase === 'failed')
        .map(item => `${item.asset_id}:${item.phase}:${item.updated_at}`)
        .sort()
        .join('|'),
    [kbLibraryIndexProgresses]
  )
  const preview = previewContent(detail)
  const neutralChipSx = CHIP_VARIANTS.base(true)
  const statusChipSx = (status: FilterStatus) => CHIP_VARIANTS.getCustomColorChip({
    ready: theme.palette.success.main,
    indexing: theme.palette.warning.main,
    failed: theme.palette.error.main,
    all: theme.palette.text.secondary,
  }[status], true)

  useEffect(() => {
    if (!terminalSignature) return
    if (lastProgressTerminalRef.current === terminalSignature) return
    lastProgressTerminalRef.current = terminalSignature
    void refreshAll()
  }, [refreshAll, terminalSignature])

  const closeDrawer = () => {
    if (bindingsMutation.isPending || deleteMutation.isPending) return
    setBindOpen(false)
    setDeleteOpen(false)
    setSelectedAssetId(null)
    clearInteractiveFocus()
  }

  const handleRefresh = () => {
    void refreshAll()
  }

  const handleClearFilters = () => {
    setSearch('')
    setStatusFilter('all')
  }

  const compactActionSx = {
    minHeight: 32,
    px: 1.25,
    fontSize: '0.82rem',
  }
  const detailSectionSx: SxProps<Theme> = {
    ...(UNIFIED_TABLE_STYLES.paper as object),
    boxShadow: 'none',
    borderColor: alpha(theme.palette.primary.main, 0.08),
    backgroundColor: alpha(theme.palette.background.paper, 0.82),
    '&:hover': {
      boxShadow: 'none',
    },
  }
  const previewBodySx = {
    px: 2,
    py: 2.25,
    maxHeight: { xs: 420, lg: 620 },
    overflow: 'auto',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    fontSize: '0.92rem',
    lineHeight: 1.8,
    backgroundColor: alpha(theme.palette.background.default, 0.42),
  }

  return (
    <Box
      sx={{
        ...UNIFIED_TABLE_STYLES.tableLayoutContainer,
        p: 3,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <Stack spacing={3} sx={{ flex: 1, minHeight: 0 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <StatCard label={t('kbLibrary.stats.total')} value={stats.total} icon={<LibraryIcon sx={{ fontSize: 20 }} />} color={theme.palette.primary.main} />
          <StatCard label={t('kbLibrary.stats.ready')} value={stats.ready} icon={<AssetIcon sx={{ fontSize: 20 }} />} color={theme.palette.success.main} />
          <StatCard label={t('kbLibrary.stats.indexing')} value={stats.indexing} icon={<ReindexIcon sx={{ fontSize: 20 }} />} color={theme.palette.warning.main} />
          <StatCard label={t('kbLibrary.stats.bindings')} value={stats.bindings} icon={<BindingsIcon sx={{ fontSize: 20 }} />} color={theme.palette.secondary.main} />
        </Box>

        <Card sx={CARD_VARIANTS.default.styles}>
          <Box sx={{ px: 2, py: 1.25, display: 'flex', alignItems: 'center', gap: 1.25, flexWrap: 'wrap' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, flexWrap: 'wrap', flex: '1 1 520px', minWidth: 0 }}>
              <SearchField
                placeholder={t('kbLibrary.search.placeholder')}
                value={search}
                onChange={setSearch}
                onClear={() => setSearch('')}
                clearAriaLabel={t('kbLibrary.actions.clearFilters')}
                sx={{ width: { xs: '100%', sm: 280, md: 320 }, maxWidth: '100%', flexShrink: 0 }}
              />
              <SegmentedControl
                value={statusFilter}
                options={[
                  { value: 'all', label: t('kbLibrary.filter.all') },
                  { value: 'ready', label: t('kbLibrary.filter.ready') },
                  { value: 'indexing', label: t('kbLibrary.filter.indexing') },
                  { value: 'failed', label: t('kbLibrary.filter.failed') },
                ]}
                onChange={value => setStatusFilter(value)}
              />
              <SegmentedControl
                value={viewMode}
                options={[
                  {
                    value: 'card',
                    icon: <GridViewIcon fontSize="small" />,
                    tooltip: t('kbLibrary.toolbar.cardView'),
                    ariaLabel: t('kbLibrary.toolbar.cardView'),
                    iconOnly: true,
                  },
                  {
                    value: 'list',
                    icon: <ListViewIcon fontSize="small" />,
                    tooltip: t('kbLibrary.toolbar.listView'),
                    ariaLabel: t('kbLibrary.toolbar.listView'),
                    iconOnly: true,
                  },
                ]}
                onChange={value => setViewMode(value)}
              />
              {(search.trim() || statusFilter !== 'all') && (
                <Tooltip title={t('kbLibrary.actions.clearFilters')}>
                  <IconActionButton size="small" onClick={handleClearFilters}>
                    <FilterAltOffIcon fontSize="small" />
                  </IconActionButton>
                </Tooltip>
              )}
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', marginLeft: 'auto' }}>
              <Typography variant="caption" color="text.secondary">
                {t('kbLibrary.list.total', { count: filteredAssets.length })}
              </Typography>
              <Tooltip title={t('kbLibrary.actions.refresh')}>
                <IconActionButton size="small" onClick={handleRefresh} disabled={assetsQuery.isLoading}>
                  <RefreshIcon fontSize="small" />
                </IconActionButton>
              </Tooltip>
              <ActionButton size="small" tone="secondary" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
                {t('kbLibrary.actions.createText')}
              </ActionButton>
              <ActionButton size="small" tone="primary" startIcon={<FileUploadIcon />} onClick={() => setUploadOpen(true)}>
                {t('kbLibrary.actions.upload')}
              </ActionButton>
            </Box>
          </Box>
        </Card>

        {assetsQuery.isLoading ? (
          <Box sx={{ flex: 1, minHeight: 0, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <CircularProgress size={30} />
          </Box>
        ) : filteredAssets.length === 0 ? (
          <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
            <LibraryIcon sx={{ fontSize: 64, opacity: 0.2 }} />
            <Typography variant="h6" color="text.secondary">
              {search.trim() || statusFilter !== 'all' ? t('kbLibrary.empty.noMatch') : t('kbLibrary.empty.title')}
            </Typography>
          </Box>
        ) : viewMode === 'card' ? (
          <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', pr: 0.5 }}>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 2 }}>
              {filteredAssets.map(asset => {
                const progress = progressByAssetId.get(asset.id)
                const status = getProgressStatus(progress) ?? getEffectiveStatus(asset)
                return (
                  <Card
                    key={asset.id}
                    sx={{
                      ...CARD_VARIANTS.default.styles,
                      display: 'flex',
                      flexDirection: 'column',
                      cursor: 'pointer',
                      transition: 'border-color 0.2s, box-shadow 0.2s',
                      '&:hover': {
                        borderColor: 'primary.main',
                        boxShadow: 2,
                      },
                    }}
                    onClick={() => setSelectedAssetId(asset.id)}
                  >
                    <Box sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
                        <Chip size="small" label={asset.format.toUpperCase()} variant="outlined" sx={neutralChipSx} />
                        <Chip size="small" label={t(`kbLibrary.status.${status}`)} sx={statusChipSx(status)} />
                        <Chip size="small" label={t('kbLibrary.list.bindingCount', { count: asset.binding_count })} variant="outlined" sx={neutralChipSx} />
                      </Box>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
                        {asset.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
                        {asset.source_path}
                      </Typography>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                          lineHeight: 1.5,
                        }}
                      >
                        {asset.summary || t('kbLibrary.list.noSummary')}
                      </Typography>
                      <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap" sx={{ mt: 'auto' }}>
                        {asset.tags.slice(0, 4).map(tag => (
                          <Chip key={`${asset.id}-${tag}`} size="small" label={tag} variant="outlined" sx={neutralChipSx} />
                        ))}
                      </Stack>
                      {progress && progress.phase !== 'ready' && progress.phase !== 'failed' && (
                        <Stack spacing={0.5} sx={{ pt: 0.25 }}>
                          <LinearProgress
                            variant="determinate"
                            value={progress.progress_percent}
                            sx={{ height: 5, borderRadius: 999 }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {`${t(`kbLibrary.progress.phase.${progress.phase}`)} · ${progress.progress_percent}%`}
                          </Typography>
                        </Stack>
                      )}
                    </Box>
                  </Card>
                )
              })}
            </Box>
          </Box>
        ) : (
          <Paper sx={{ ...UNIFIED_TABLE_STYLES.tableContentContainer, minHeight: 0 }}>
            <Box sx={UNIFIED_TABLE_STYLES.tableViewport}>
              {filteredAssets.map((asset, index) => {
                const progress = progressByAssetId.get(asset.id)
                const status = getProgressStatus(progress) ?? getEffectiveStatus(asset)
                return (
                  <Box key={asset.id}>
                    {index > 0 && <Divider />}
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        px: 2,
                        py: 1.25,
                        gap: 1.5,
                        cursor: 'pointer',
                        ...UNIFIED_TABLE_STYLES.row,
                      }}
                      onClick={() => setSelectedAssetId(asset.id)}
                    >
                      <Chip
                        size="small"
                        label={asset.format.toUpperCase()}
                        variant="outlined"
                        sx={{ ...neutralChipSx, width: 58, flexShrink: 0 }}
                      />
                      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {asset.title}
                          </Typography>
                          <Chip size="small" label={t(`kbLibrary.status.${status}`)} sx={statusChipSx(status)} />
                          <Chip size="small" label={t('kbLibrary.list.bindingCount', { count: asset.binding_count })} variant="outlined" sx={neutralChipSx} />
                        </Box>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                          {asset.source_path}
                        </Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{
                            display: '-webkit-box',
                            WebkitLineClamp: 1,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                            mt: 0.25,
                          }}
                        >
                          {asset.summary || t('kbLibrary.list.noSummary')}
                        </Typography>
                      </Box>
                      {progress && progress.phase !== 'ready' && progress.phase !== 'failed' && (
                        <Box sx={{ width: 96, flexShrink: 0 }}>
                          <LinearProgress
                            variant="determinate"
                            value={progress.progress_percent}
                            sx={{ height: 5, borderRadius: 999, mb: 0.5 }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {`${progress.progress_percent}%`}
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  </Box>
                )
              })}
            </Box>
          </Paper>
        )}
      </Stack>

      <Drawer
        anchor="right"
        open={selectedAssetId != null}
        onClose={closeDrawer}
        PaperProps={{
          sx: {
            width: { xs: '100%', sm: 720, md: 820 },
            maxWidth: '100vw',
            mt: { xs: '56px', sm: '64px' },
            height: { xs: 'calc(100% - 56px)', sm: 'calc(100% - 64px)' },
          },
        }}
      >
        {selectedAssetId != null && (
          <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.3 }} noWrap>
                  {detail?.asset.title ?? selectedAsset?.title ?? t('kbLibrary.detail.noSelection')}
                </Typography>
                <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap" sx={{ mt: 0.75 }}>
                  {(detail?.asset ?? selectedAsset)?.format && (
                    <Chip
                      size="small"
                      label={(detail?.asset ?? selectedAsset)?.format.toUpperCase()}
                      variant="outlined"
                      sx={neutralChipSx}
                    />
                  )}
                  {detail && (
                    <Chip
                      size="small"
                      label={t(`kbLibrary.status.${selectedProgressStatus ?? getEffectiveStatus(detail.asset)}`)}
                      sx={statusChipSx(selectedProgressStatus ?? getEffectiveStatus(detail.asset))}
                    />
                  )}
                  {(detail?.asset ?? selectedAsset) && (
                    <Chip
                      size="small"
                      label={t('kbLibrary.list.bindingCount', { count: (detail?.asset ?? selectedAsset)?.binding_count ?? 0 })}
                      variant="outlined"
                      sx={neutralChipSx}
                    />
                  )}
                </Stack>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.75, wordBreak: 'break-all' }}>
                  {detail?.asset.source_path ?? selectedAsset?.source_path ?? ''}
                </Typography>
              </Box>
              <IconActionButton size="small" onClick={closeDrawer}>
                <CloseIcon fontSize="small" />
              </IconActionButton>
            </Box>
            <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', p: 2 }}>
              {!selectedAssetId ? (
                <Alert severity="info">{t('kbLibrary.detail.noSelection')}</Alert>
              ) : assetDetailQuery.isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
                  <CircularProgress size={30} />
                </Box>
              ) : detail ? (
                <Stack spacing={2}>
                  <Stack
                    direction={{ xs: 'column', lg: 'row' }}
                    spacing={1.5}
                    justifyContent="space-between"
                    alignItems={{ xs: 'flex-start', lg: 'center' }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="body1" sx={{ fontWeight: 700, lineHeight: 1.6 }}>
                        {detail.asset.summary || t('kbLibrary.list.noSummary')}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ flexShrink: 0 }}>
                      <ActionButton
                        size="small"
                        tone="secondary"
                        startIcon={<BindIcon />}
                        sx={compactActionSx}
                        onClick={() => {
                          setBindWorkspaceIds(detail.asset.bound_workspaces.map(item => item.workspace_id))
                          setBindOpen(true)
                        }}
                      >
                        {t('kbLibrary.actions.bind')}
                      </ActionButton>
                      <ActionButton
                        size="small"
                        tone="secondary"
                        startIcon={<ReindexIcon />}
                        sx={compactActionSx}
                        onClick={() => reindexMutation.mutate(detail.asset.id)}
                      >
                        {t('kbLibrary.actions.reindex')}
                      </ActionButton>
                      <ActionButton
                        size="small"
                        tone="secondary"
                        startIcon={<DownloadIcon />}
                        sx={compactActionSx}
                        onClick={() => void handleDownloadRaw(detail.asset)}
                      >
                        {t('kbLibrary.actions.downloadRaw')}
                      </ActionButton>
                      <ActionButton
                        size="small"
                        tone="danger"
                        startIcon={<DeleteIcon />}
                        sx={compactActionSx}
                        onClick={() => setDeleteOpen(true)}
                      >
                        {t('kbLibrary.actions.delete')}
                      </ActionButton>
                    </Stack>
                  </Stack>

                  {selectedProgress && (
                    <Paper sx={detailSectionSx}>
                      <Stack spacing={0.9} sx={{ p: 2 }}>
                        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1}>
                          <Typography variant="subtitle2">{t('kbLibrary.progress.title')}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {`${t(`kbLibrary.progress.phase.${selectedProgress.phase}`)} · ${selectedProgress.progress_percent}%`}
                          </Typography>
                        </Stack>
                        <LinearProgress
                          variant="determinate"
                          value={selectedProgress.progress_percent}
                          color={selectedProgress.phase === 'failed' ? 'error' : selectedProgress.phase === 'ready' ? 'success' : 'primary'}
                          sx={{ height: 8, borderRadius: 999 }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {selectedProgress.total_chunks > 0
                            ? t('kbLibrary.progress.detail', {
                                processed: selectedProgress.processed_chunks,
                                total: selectedProgress.total_chunks,
                              })
                            : t('kbLibrary.progress.pending')}
                        </Typography>
                        {selectedProgress.error_summary && <Alert severity="error">{selectedProgress.error_summary}</Alert>}
                      </Stack>
                    </Paper>
                  )}

                  <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                    {detail.asset.tags.length ? (
                      detail.asset.tags.map(tag => (
                        <Chip key={`${detail.asset.id}-${tag}`} size="small" label={tag} variant="outlined" sx={neutralChipSx} />
                      ))
                    ) : (
                      <Chip size="small" label={t('kbLibrary.detail.noTags')} variant="outlined" sx={neutralChipSx} />
                    )}
                  </Stack>

                  <Paper sx={detailSectionSx}>
                    <Stack spacing={1.25} sx={{ p: 2 }}>
                      <Typography variant="subtitle2">{t('kbLibrary.detail.meta')}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
                        {detail.asset.source_path}
                      </Typography>
                      <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                        {detail.asset.category && (
                          <Chip size="small" label={`${t('kbLibrary.form.category')} · ${detail.asset.category}`} variant="outlined" sx={neutralChipSx} />
                        )}
                        <Chip size="small" label={`${t('kbLibrary.form.fileName')} · ${detail.asset.file_name}`} variant="outlined" sx={neutralChipSx} />
                        <Chip size="small" label={t('kbLibrary.detail.chunkCount', { count: detail.asset.chunk_count })} variant="outlined" sx={neutralChipSx} />
                        <Chip size="small" label={t('kbLibrary.detail.fileSize', { value: formatFileSize(detail.asset.file_size) })} variant="outlined" sx={neutralChipSx} />
                        <Chip size="small" label={t('kbLibrary.detail.updatedAt', { value: formatDateTime(detail.asset.update_time) })} variant="outlined" sx={neutralChipSx} />
                        <Chip size="small" label={`${t('knowledge.detail.indexedAt')} · ${formatDateTime(detail.asset.last_indexed_at)}`} variant="outlined" sx={neutralChipSx} />
                      </Stack>
                      <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                        {detail.asset.bound_workspaces.length ? (
                          detail.asset.bound_workspaces.map(item => (
                            <Chip
                              key={`${detail.asset.id}-${item.workspace_id}`}
                              size="small"
                              label={`${item.workspace_name} · ${item.workspace_status}`}
                              variant="outlined"
                              sx={neutralChipSx}
                            />
                          ))
                        ) : (
                          <Chip size="small" label={t('kbLibrary.detail.noBindings')} variant="outlined" sx={neutralChipSx} />
                        )}
                      </Stack>
                      {detail.asset.last_error && <Alert severity="error">{detail.asset.last_error}</Alert>}
                    </Stack>
                  </Paper>

                  <Paper sx={detailSectionSx}>
                    <Box sx={{ px: 2, pt: 1.5 }}>
                      <Typography variant="subtitle2">{t('kbLibrary.detail.preview')}</Typography>
                    </Box>
                    <Box sx={previewBodySx}>
                      {preview ? (
                        <Typography component="pre" variant="body2" sx={{ m: 0, fontFamily: 'inherit', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.8 }}>
                          {preview}
                        </Typography>
                      ) : (
                        t('kbLibrary.preview.empty')
                      )}
                    </Box>
                  </Paper>
                </Stack>
              ) : (
                <Alert severity="warning">{t('kbLibrary.detail.loadFailed')}</Alert>
              )}
            </Box>
          </Box>
        )}
      </Drawer>

      <Dialog
        open={createOpen}
        onClose={() => !createMutation.isPending && setCreateOpen(false)}
        fullWidth
        maxWidth="md"
        disableRestoreFocus
      >
        <DialogTitle>{t('kbLibrary.dialogs.createTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                label={t('kbLibrary.form.title')}
                fullWidth
                value={createForm.title}
                onChange={event => setCreateForm(prev => ({ ...prev, title: event.target.value }))}
              />
              <TextField
                select
                label={t('kbLibrary.form.format')}
                fullWidth
                value={createForm.format}
                onChange={event => setCreateForm(prev => ({ ...prev, format: event.target.value as 'markdown' | 'text' }))}
              >
                {TEXT_FORMAT_OPTIONS.map(option => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                label={t('kbLibrary.form.sourcePath')}
                fullWidth
                value={createForm.source_path}
                onChange={event => setCreateForm(prev => ({ ...prev, source_path: event.target.value }))}
                placeholder={t('kbLibrary.form.sourcePathPlaceholder')}
              />
              <TextField
                label={t('kbLibrary.form.fileName')}
                fullWidth
                value={createForm.file_name}
                onChange={event => setCreateForm(prev => ({ ...prev, file_name: event.target.value }))}
              />
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                label={t('kbLibrary.form.category')}
                fullWidth
                value={createForm.category}
                onChange={event => setCreateForm(prev => ({ ...prev, category: event.target.value }))}
              />
              <TextField
                label={t('kbLibrary.form.tags')}
                fullWidth
                value={createTagsInput}
                onChange={event => setCreateTagsInput(event.target.value)}
                placeholder={t('kbLibrary.form.tagsPlaceholder')}
              />
            </Stack>
            <TextField
              label={t('kbLibrary.form.summary')}
              fullWidth
              value={createForm.summary}
              onChange={event => setCreateForm(prev => ({ ...prev, summary: event.target.value }))}
            />
            <TextField
              label={t('kbLibrary.form.content')}
              fullWidth
              multiline
              minRows={14}
              value={createForm.content}
              onChange={event => setCreateForm(prev => ({ ...prev, content: event.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setCreateOpen(false)} disabled={createMutation.isPending}>
            {t('kbLibrary.actions.cancel')}
          </ActionButton>
          <ActionButton
            tone="primary"
            onClick={handleCreateSubmit}
            disabled={createMutation.isPending || !createForm.title.trim() || !createForm.content.trim()}
          >
            {createMutation.isPending ? t('kbLibrary.actions.creating') : t('kbLibrary.actions.create')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      <Dialog
        open={uploadOpen}
        onClose={() => {
          if (uploadMutation.isPending) return
          setUploadProgress(0)
          setUploadOpen(false)
        }}
        fullWidth
        maxWidth="sm"
        disableRestoreFocus
      >
        <DialogTitle>{t('kbLibrary.dialogs.uploadTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <ActionButton component="label" tone="secondary" startIcon={<FileUploadIcon />}>
              {uploadPayload?.file?.name ?? t('kbLibrary.actions.chooseFile')}
              <input hidden type="file" accept={SUPPORTED_UPLOAD_EXTENSIONS.join(',')} onChange={handleFileChange} />
            </ActionButton>
            <Alert severity="info">{t('kbLibrary.form.supportedFormats', { formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', ') })}</Alert>
            <TextField label={t('kbLibrary.form.title')} value={uploadTitle} onChange={event => setUploadTitle(event.target.value)} fullWidth />
            <TextField label={t('kbLibrary.form.category')} value={uploadCategory} onChange={event => setUploadCategory(event.target.value)} fullWidth />
            <TextField label={t('kbLibrary.form.tags')} value={uploadTagsInput} onChange={event => setUploadTagsInput(event.target.value)} fullWidth />
            <TextField label={t('kbLibrary.form.summary')} value={uploadSummary} onChange={event => setUploadSummary(event.target.value)} fullWidth multiline minRows={3} />
            {uploadMutation.isPending && (
              <Stack spacing={0.75}>
                <LinearProgress variant="determinate" value={uploadProgress} sx={{ height: 8, borderRadius: 999 }} />
                <Typography variant="caption" color="text.secondary">
                  {`${t('kbLibrary.actions.upload')} · ${uploadProgress}%`}
                </Typography>
              </Stack>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setUploadOpen(false)}>{t('kbLibrary.actions.cancel')}</ActionButton>
          <ActionButton tone="primary" onClick={handleUploadSubmit} disabled={!uploadPayload?.file || uploadMutation.isPending}>
            {t('kbLibrary.actions.upload')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      <Dialog
        open={bindOpen}
        onClose={() => !bindingsMutation.isPending && setBindOpen(false)}
        fullWidth
        maxWidth="sm"
        disableRestoreFocus
      >
        <DialogTitle>{t('kbLibrary.dialogs.bindTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {t('kbLibrary.dialogs.bindHint')}
            </Typography>
            <FormControl fullWidth>
              <InputLabel>{t('kbLibrary.form.bindWorkspaces')}</InputLabel>
              <Select
                multiple
                value={bindWorkspaceIds}
                onChange={event => setBindWorkspaceIds(event.target.value as number[])}
                input={<OutlinedInput label={t('kbLibrary.form.bindWorkspaces')} />}
                renderValue={selected => workspaces.filter(item => selected.includes(item.id)).map(item => item.name).join(', ')}
              >
                {workspaces.map(workspace => (
                  <MenuItem key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setBindOpen(false)}>{t('kbLibrary.actions.cancel')}</ActionButton>
          <ActionButton
            tone="primary"
            onClick={() => selectedAsset && bindingsMutation.mutate({ assetId: selectedAsset.id, workspaceIds: bindWorkspaceIds })}
            disabled={!selectedAsset || bindingsMutation.isPending}
          >
            {t('kbLibrary.actions.saveBindings')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteOpen}
        onClose={() => !deleteMutation.isPending && setDeleteOpen(false)}
        fullWidth
        maxWidth="xs"
        disableRestoreFocus
      >
        <DialogTitle>{t('kbLibrary.dialogs.deleteTitle')}</DialogTitle>
        <DialogContent>
          <Alert severity="warning">
            {t('kbLibrary.dialogs.deleteContent', { title: selectedAsset?.title ?? '-' })}
          </Alert>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setDeleteOpen(false)}>{t('kbLibrary.actions.cancel')}</ActionButton>
          <ActionButton
            tone="danger"
            startIcon={<DeleteIcon />}
            onClick={() => selectedAsset && deleteMutation.mutate(selectedAsset.id)}
            disabled={!selectedAsset || deleteMutation.isPending}
          >
            {t('kbLibrary.actions.delete')}
          </ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
