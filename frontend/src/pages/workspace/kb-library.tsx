import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  LinearProgress,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  MenuItem,
  OutlinedInput,
  Paper,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useTheme,
  useMediaQuery,
} from '@mui/material'
import {
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
} from '@mui/icons-material'
import { alpha } from '@mui/material/styles'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  KbLibraryIndexProgressInfo,
  useSystemEventsContext,
} from '../../contexts/SystemEventsContext'
import {
  KBAssetListItem,
  KBUploadFilePayload,
  kbLibraryApi,
  workspaceApi,
} from '../../services/api/workspace'
import { useNotification } from '../../hooks/useNotification'
import { CARD_VARIANTS, UNIFIED_TABLE_STYLES } from '../../theme/variants'
import SearchField from '../../components/common/SearchField'
import SegmentedControl from '../../components/common/SegmentedControl'
import IconActionButton from '../../components/common/IconActionButton'
import ActionButton from '../../components/common/ActionButton'

type FilterStatus = 'all' | 'ready' | 'indexing' | 'failed'

const SUPPORTED_UPLOAD_EXTENSIONS = ['.md', '.txt', '.html', '.htm', '.json', '.yaml', '.yml', '.csv', '.xlsx', '.pdf', '.docx']
const EMPTY_ASSETS: KBAssetListItem[] = []
const EMPTY_WORKSPACES: Awaited<ReturnType<typeof workspaceApi.getList>> = []

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

function statusColor(status: FilterStatus): 'default' | 'success' | 'warning' | 'error' {
  if (status === 'ready') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'indexing') return 'warning'
  return 'default'
}

function getFileExtension(fileName: string): string {
  const match = fileName.toLowerCase().match(/(\.[^.]+)$/)
  return match?.[1] ?? ''
}

function isSupportedUploadFile(file: File): boolean {
  return SUPPORTED_UPLOAD_EXTENSIONS.includes(getFileExtension(file.name))
}

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string
  value: number
  icon: React.ReactNode
  color: string
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        px: 2,
        py: 1.5,
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        borderRadius: 2,
        minWidth: 160,
        flex: '1 1 0',
      }}
    >
      <Box
        sx={{
          width: 38,
          height: 38,
          borderRadius: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: color,
          color: '#fff',
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>
      <Box>
        <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
      </Box>
    </Paper>
  )
}

function clearInteractiveFocus() {
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur()
  }
}

export default function KbLibraryPage() {
  const theme = useTheme()
  const isCompactDialog = useMediaQuery(theme.breakpoints.down('md'))
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const { kbLibraryIndexProgresses } = useSystemEventsContext()
  const lastProgressTerminalRef = useRef('')

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all')
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [bindOpen, setBindOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
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
      tags: uploadTagsInput.split(',').map(item => item.trim()).filter(Boolean),
      is_enabled: true,
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
  const detailOpen = selectedAssetId != null
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
  const preview = detail?.normalized_content ?? ''

  useEffect(() => {
    if (!terminalSignature) return
    if (lastProgressTerminalRef.current === terminalSignature) return
    lastProgressTerminalRef.current = terminalSignature
    void refreshAll()
  }, [refreshAll, terminalSignature])

  const closeDetailDialog = () => {
    if (bindingsMutation.isPending || deleteMutation.isPending) return
    setBindOpen(false)
    setDeleteOpen(false)
    setSelectedAssetId(null)
    clearInteractiveFocus()
  }

  const compactActionSx = {
    minHeight: 32,
    px: 1.25,
    fontSize: '0.82rem',
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
          <CardContent>
            <Stack direction={{ xs: 'column', lg: 'row' }} spacing={1.5} justifyContent="space-between">
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.25} sx={{ flex: 1 }}>
                <SearchField
                  placeholder={t('kbLibrary.search.placeholder')}
                  value={search}
                  onChange={setSearch}
                  onClear={() => setSearch('')}
                  sx={{ width: { xs: '100%', md: 360 }, maxWidth: '100%' }}
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
                {(search.trim() || statusFilter !== 'all') && (
                  <Tooltip title={t('kbLibrary.actions.clearFilters')}>
                    <IconActionButton onClick={() => { setSearch(''); setStatusFilter('all') }}>
                      <FilterAltOffIcon fontSize="small" />
                    </IconActionButton>
                  </Tooltip>
                )}
              </Stack>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ alignSelf: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  {t('kbLibrary.list.total', { count: filteredAssets.length })}
                </Typography>
                <Tooltip title={t('kbLibrary.actions.refresh')}>
                  <IconActionButton tone="primary" onClick={() => void refreshAll()} disabled={assetsQuery.isLoading}>
                    <RefreshIcon fontSize="small" />
                  </IconActionButton>
                </Tooltip>
                <ActionButton tone="primary" startIcon={<FileUploadIcon />} onClick={() => setUploadOpen(true)}>
                  {t('kbLibrary.actions.upload')}
                </ActionButton>
              </Stack>
            </Stack>
          </CardContent>
        </Card>

        <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <CardContent sx={{ p: 0, flex: 1, minHeight: 0 }}>
            {assetsQuery.isLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
                <CircularProgress size={30} />
              </Box>
            ) : filteredAssets.length ? (
              <List sx={{ py: 0, height: '100%', overflow: 'auto' }}>
                {filteredAssets.map(asset => {
                  const progress = progressByAssetId.get(asset.id)
                  const status = getProgressStatus(progress) ?? getEffectiveStatus(asset)
                  return (
                    <ListItem
                      key={asset.id}
                      disablePadding
                      divider
                    >
                      <ListItemButton
                        onClick={() => setSelectedAssetId(asset.id)}
                        sx={{
                          alignItems: 'flex-start',
                          py: 1.5,
                          px: 2,
                        }}
                      >
                        <ListItemText
                          primary={
                            <Stack spacing={0.75}>
                              <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                                <Typography variant="body1" sx={{ fontWeight: 700 }}>
                                  {asset.title}
                                </Typography>
                                <Chip size="small" label={asset.format.toUpperCase()} variant="outlined" />
                                <Chip size="small" label={t(`kbLibrary.status.${status}`)} color={statusColor(status)} />
                                <Chip size="small" label={t('kbLibrary.list.bindingCount', { count: asset.binding_count })} variant="outlined" />
                              </Stack>
                              <Typography variant="caption" color="text.secondary">
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
                                }}
                              >
                                {asset.summary || t('kbLibrary.list.noSummary')}
                              </Typography>
                              <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                                {asset.tags.slice(0, 4).map(tag => (
                                  <Chip key={`${asset.id}-${tag}`} size="small" label={tag} variant="outlined" />
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
                            </Stack>
                          }
                        />
                      </ListItemButton>
                    </ListItem>
                  )
                })}
              </List>
            ) : (
              <Box sx={{ p: 4 }}>
                <Alert severity="info">
                  {search.trim() || statusFilter !== 'all' ? t('kbLibrary.empty.noMatch') : t('kbLibrary.empty.title')}
                </Alert>
              </Box>
            )}
          </CardContent>
        </Card>
      </Stack>

      <Dialog
        open={detailOpen}
        onClose={closeDetailDialog}
        fullWidth
        maxWidth="lg"
        fullScreen={isCompactDialog}
        scroll="paper"
        disableRestoreFocus
      >
        <DialogTitle sx={{ px: 3, py: 2 }}>
          <Stack direction="row" spacing={1.5} justifyContent="space-between" alignItems="flex-start">
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.35 }}>
                {detail?.asset.title ?? t('kbLibrary.detail.noSelection')}
              </Typography>
              {detail?.asset.source_path && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
                  {detail.asset.source_path}
                </Typography>
              )}
            </Box>
            <Tooltip title={t('kbLibrary.actions.cancel')}>
              <IconActionButton onClick={closeDetailDialog}>
                <CloseIcon fontSize="small" />
              </IconActionButton>
            </Tooltip>
          </Stack>
        </DialogTitle>
        <DialogContent sx={{ px: 3, py: 2.5 }}>
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
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.25 }}>
                    <Chip label={detail.asset.format.toUpperCase()} />
                    <Chip
                      label={t(`kbLibrary.status.${selectedProgressStatus ?? getEffectiveStatus(detail.asset)}`)}
                      color={statusColor(selectedProgressStatus ?? getEffectiveStatus(detail.asset))}
                    />
                    <Chip label={t('kbLibrary.list.bindingCount', { count: detail.asset.binding_count })} variant="outlined" />
                  </Stack>
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
                <Card variant="outlined">
                  <CardContent>
                    <Stack spacing={0.9}>
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
                  </CardContent>
                </Card>
              )}

              <Card variant="outlined">
                <CardContent>
                  <Stack spacing={1.25}>
                    <Typography variant="subtitle2">{t('kbLibrary.detail.meta')}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {detail.asset.source_path}
                    </Typography>
                    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                      <Chip size="small" label={t('kbLibrary.detail.chunkCount', { count: detail.asset.chunk_count })} variant="outlined" />
                      <Chip size="small" label={t('kbLibrary.detail.fileSize', { value: formatFileSize(detail.asset.file_size) })} variant="outlined" />
                      <Chip size="small" label={t('kbLibrary.detail.updatedAt', { value: formatDateTime(detail.asset.update_time) })} variant="outlined" />
                    </Stack>
                    <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                      {detail.asset.bound_workspaces.length ? (
                        detail.asset.bound_workspaces.map(item => (
                          <Chip
                            key={`${detail.asset.id}-${item.workspace_id}`}
                            size="small"
                            label={`${item.workspace_name} · ${item.workspace_status}`}
                            variant="outlined"
                          />
                        ))
                      ) : (
                        <Chip size="small" label={t('kbLibrary.detail.noBindings')} variant="outlined" />
                      )}
                    </Stack>
                    {detail.asset.last_error && <Alert severity="error">{detail.asset.last_error}</Alert>}
                  </Stack>
                </CardContent>
              </Card>

              <Card variant="outlined">
                <CardContent sx={{ p: 0 }}>
                  <Box sx={{ px: 2, py: 1.5 }}>
                    <Typography variant="subtitle2">{t('kbLibrary.detail.preview')}</Typography>
                  </Box>
                  <Box
                    sx={{
                      p: 2,
                      maxHeight: { xs: 420, lg: 620 },
                      overflow: 'auto',
                      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      fontSize: 13,
                      lineHeight: 1.7,
                      bgcolor: alpha(theme.palette.background.default, 0.4),
                    }}
                  >
                    {preview || t('kbLibrary.preview.empty')}
                  </Box>
                </CardContent>
              </Card>
            </Stack>
          ) : (
            <Alert severity="warning">{t('kbLibrary.detail.loadFailed')}</Alert>
          )}
        </DialogContent>
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
