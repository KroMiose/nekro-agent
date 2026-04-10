import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  LinearProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  InputAdornment,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  FileUpload as FileUploadIcon,
  Refresh as RefreshIcon,
  RestartAlt as ReindexIcon,
  Search as SearchIcon,
  Visibility as VisibilityIcon,
  FolderOpen as FolderOpenIcon,
  Clear as ClearIcon,
} from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  KBCreateTextDocumentBody,
  KBDocumentDetailResponse,
  KBSearchResponse,
  KBUploadFilePayload,
  knowledgeBaseApi,
  WorkspaceDetail,
} from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { KbIndexProgressInfo, useSystemEventsContext } from '../../../contexts/SystemEventsContext'
import { CARD_VARIANTS } from '../../../theme/variants'

type PreviewTab = 'normalized' | 'source'

const TEXT_FORMAT_OPTIONS: Array<{ value: 'markdown' | 'text'; label: string }> = [
  { value: 'markdown', label: 'Markdown' },
  { value: 'text', label: 'Text' },
]

const EMPTY_DOCUMENTS: KBDocumentDetailResponse['document'][] = []
const SUPPORTED_UPLOAD_EXTENSIONS = ['.md', '.txt', '.html', '.htm', '.json', '.yaml', '.yml', '.csv', '.xlsx', '.pdf', '.docx']


function getFileExtension(fileName: string): string {
  const match = fileName.toLowerCase().match(/(\.[^.]+)$/)
  return match?.[1] ?? ''
}


function isSupportedUploadFile(file: File): boolean {
  return SUPPORTED_UPLOAD_EXTENSIONS.includes(getFileExtension(file.name))
}

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

function statusColor(status: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
  if (status === 'ready') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'extracting' || status === 'indexing') return 'warning'
  return 'default'
}

function getEffectiveStatus(document: KBDocumentDetailResponse['document']): string {
  if (document.extract_status === 'failed' || document.sync_status === 'failed') return 'failed'
  if (document.extract_status !== 'ready') return document.extract_status
  return document.sync_status
}

function getDerivedStatuses(
  document: KBDocumentDetailResponse['document'],
  progress: KbIndexProgressInfo | null | undefined
): { extractStatus: string; syncStatus: string; overallStatus: string } {
  if (!progress) {
    return {
      extractStatus: document.extract_status,
      syncStatus: document.sync_status,
      overallStatus: getEffectiveStatus(document),
    }
  }

  if (progress.phase === 'failed') {
    return {
      extractStatus: 'failed',
      syncStatus: 'failed',
      overallStatus: 'failed',
    }
  }

  if (progress.phase === 'queued') {
    return {
      extractStatus: document.extract_status === 'ready' ? 'ready' : 'pending',
      syncStatus: 'pending',
      overallStatus: 'pending',
    }
  }

  if (progress.phase === 'extracting') {
    return {
      extractStatus: 'extracting',
      syncStatus: 'pending',
      overallStatus: 'extracting',
    }
  }

  if (progress.phase === 'ready') {
    return {
      extractStatus: 'ready',
      syncStatus: 'ready',
      overallStatus: 'ready',
    }
  }

  return {
    extractStatus: 'ready',
    syncStatus: 'indexing',
    overallStatus: 'indexing',
  }
}

function normalizeTagsInput(raw: string): string[] {
  return raw
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

function previewContent(detail: KBDocumentDetailResponse | undefined, tab: PreviewTab): string {
  if (!detail) return ''
  if (tab === 'source') return detail.source_content ?? ''
  return detail.normalized_content ?? ''
}


function kbProgressLabel(phase: string, t: (key: string, options?: Record<string, unknown>) => string): string {
  return t(`knowledge.progress.phase.${phase}`, { defaultValue: phase })
}

export default function KnowledgeTab({ workspace }: { workspace: WorkspaceDetail }) {
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const { kbIndexProgresses } = useSystemEventsContext()
  const uploadInputRef = useRef<HTMLInputElement | null>(null)
  const lastProgressTerminalRef = useRef('')

  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null)
  const [previewTab, setPreviewTab] = useState<PreviewTab>('normalized')
  const [searchDraft, setSearchDraft] = useState('')
  const [searchResult, setSearchResult] = useState<KBSearchResponse | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
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

  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadCategory, setUploadCategory] = useState('')
  const [uploadSummary, setUploadSummary] = useState('')
  const [uploadTagsInput, setUploadTagsInput] = useState('')
  const [uploadEnabled, setUploadEnabled] = useState(true)
  const [uploadProgress, setUploadProgress] = useState<number>(0)

  const documentsQuery = useQuery({
    queryKey: ['kb-documents', workspace.id],
    queryFn: () => knowledgeBaseApi.list(workspace.id),
  })

  const documents = documentsQuery.data ?? EMPTY_DOCUMENTS
  const selectedDocument = useMemo(
    () => documents.find(item => item.id === selectedDocumentId) ?? null,
    [documents, selectedDocumentId]
  )

  useEffect(() => {
    if (!documents.length) {
      setSelectedDocumentId(null)
      return
    }
    if (selectedDocumentId == null || !documents.some(item => item.id === selectedDocumentId)) {
      setSelectedDocumentId(documents[0].id)
    }
  }, [documents, selectedDocumentId])

  const detailQuery = useQuery({
    queryKey: ['kb-document', workspace.id, selectedDocumentId],
    queryFn: () => knowledgeBaseApi.getDocument(workspace.id, selectedDocumentId as number),
    enabled: selectedDocumentId != null,
  })

  const refreshAll = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['kb-documents', workspace.id] }),
      queryClient.invalidateQueries({ queryKey: ['kb-document', workspace.id] }),
    ])
  }, [queryClient, workspace.id])

  const createMutation = useMutation({
    mutationFn: (body: KBCreateTextDocumentBody) => knowledgeBaseApi.createText(workspace.id, body),
    onSuccess: async data => {
      await refreshAll()
      setSelectedDocumentId(data.document.id)
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
      notification.success(t('knowledge.notifications.createSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.createFailed', { message: err.message })),
  })

  const uploadMutation = useMutation({
    mutationFn: (payload: KBUploadFilePayload) =>
      knowledgeBaseApi.uploadFile(workspace.id, payload, percent => setUploadProgress(percent)),
    onSuccess: async data => {
      await refreshAll()
      setSelectedDocumentId(data.document.id)
      setUploadOpen(false)
      setUploadFile(null)
      setUploadTitle('')
      setUploadCategory('')
      setUploadSummary('')
      setUploadTagsInput('')
      setUploadEnabled(true)
      setUploadProgress(0)
      notification.success(t('knowledge.notifications.uploadSuccess'))
    },
    onError: (err: Error) => {
      setUploadProgress(0)
      notification.error(t('knowledge.notifications.uploadFailed', { message: err.message }))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (documentId: number) => knowledgeBaseApi.deleteDocument(workspace.id, documentId),
    onSuccess: async () => {
      const deletedId = selectedDocumentId
      await refreshAll()
      setDeleteOpen(false)
      if (deletedId === selectedDocumentId) {
        setSelectedDocumentId(null)
      }
      notification.success(t('knowledge.notifications.deleteSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.deleteFailed', { message: err.message })),
  })

  const reindexMutation = useMutation({
    mutationFn: (documentId: number) => knowledgeBaseApi.reindexDocument(workspace.id, documentId),
    onSuccess: async () => {
      await refreshAll()
      notification.success(t('knowledge.notifications.reindexSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.reindexFailed', { message: err.message })),
  })

  const reindexAllMutation = useMutation({
    mutationFn: () => knowledgeBaseApi.reindexAll(workspace.id),
    onSuccess: async data => {
      await refreshAll()
      notification.success(
        t('knowledge.notifications.reindexAllSuccess', {
          success: data.success,
          failed: data.failed,
        })
      )
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.reindexAllFailed', { message: err.message })),
  })

  const toggleEnabledMutation = useMutation({
    mutationFn: ({ documentId, isEnabled }: { documentId: number; isEnabled: boolean }) =>
      knowledgeBaseApi.updateDocument(workspace.id, documentId, { is_enabled: isEnabled }),
    onSuccess: async () => {
      await refreshAll()
      notification.success(t('knowledge.notifications.updateSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.updateFailed', { message: err.message })),
  })

  const searchMutation = useMutation({
    mutationFn: (query: string) =>
      knowledgeBaseApi.search(workspace.id, {
        query,
        limit: 8,
        max_chunks_per_document: 2,
      }),
    onSuccess: data => setSearchResult(data),
    onError: (err: Error) => notification.error(t('knowledge.notifications.searchFailed', { message: err.message })),
  })

  const handleDownloadRaw = async () => {
    if (!selectedDocumentId || !selectedDocument) return
    try {
      const { blob, filename } = await knowledgeBaseApi.downloadRawFile(workspace.id, selectedDocumentId)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename ?? selectedDocument.file_name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      notification.error(t('knowledge.notifications.downloadFailed', { message: (err as Error).message }))
    }
  }

  const handleCreateSubmit = () => {
    if (!createForm.title.trim() || !createForm.content.trim()) return
    createMutation.mutate({
      ...createForm,
      tags: normalizeTagsInput(createTagsInput),
    })
  }

  const handleUploadSubmit = () => {
    if (!uploadFile) return
    if (!isSupportedUploadFile(uploadFile)) {
      notification.error(
        t('knowledge.notifications.unsupportedFormat', {
          name: uploadFile.name,
          formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', '),
        })
      )
      return
    }
    uploadMutation.mutate({
      file: uploadFile,
      title: uploadTitle,
      category: uploadCategory,
      summary: uploadSummary,
      tags: normalizeTagsInput(uploadTagsInput),
      is_enabled: uploadEnabled,
    })
  }

  const handleFileInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    if (file && !isSupportedUploadFile(file)) {
      setUploadFile(null)
      event.target.value = ''
      notification.error(
        t('knowledge.notifications.unsupportedFormat', {
          name: file.name,
          formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', '),
        })
      )
      return
    }
    setUploadFile(file)
    if (file && !uploadTitle.trim()) {
      setUploadTitle(file.name.replace(/\.[^.]+$/, ''))
    }
  }

  const hasSearchResult = searchResult != null
  const searchDocuments = searchResult?.documents ?? []
  const suggestedDocumentIds = new Set(searchResult?.suggested_document_ids ?? [])
  const activeList = hasSearchResult ? searchDocuments.map(item => item.document_id) : documents.map(item => item.id)
  const listItems = hasSearchResult ? searchDocuments : documents
  const listTitle = hasSearchResult ? t('knowledge.sections.searchResults') : t('knowledge.sections.documents')
  const detail = detailQuery.data
  const preview = previewContent(detail, previewTab)
  const statusLabel = (status: string) => t(`knowledge.status.${status}`, { defaultValue: status })
  const selectedProgress = selectedDocumentId != null ? kbIndexProgresses.get(`${workspace.id}:${selectedDocumentId}`) ?? null : null
  const selectedDerivedStatuses = detail ? getDerivedStatuses(detail.document, selectedProgress) : null
  const workspaceProgresses = useMemo(
    () => Array.from(kbIndexProgresses.values()).filter(item => item.workspace_id === workspace.id),
    [kbIndexProgresses, workspace.id]
  )
  const progressByDocumentId = useMemo(() => {
    const next = new Map<number, KbIndexProgressInfo>()
    for (const item of workspaceProgresses) {
      const current = next.get(item.document_id)
      if (!current || current.updated_at < item.updated_at) {
        next.set(item.document_id, item)
      }
    }
    return next
  }, [workspaceProgresses])
  const workspaceTerminalSignature = useMemo(
    () =>
      workspaceProgresses
        .filter(item => item.phase === 'ready' || item.phase === 'failed')
        .map(item => `${item.document_id}:${item.phase}:${item.updated_at}`)
        .sort()
        .join('|'),
    [workspaceProgresses]
  )

  useEffect(() => {
    if (!workspaceTerminalSignature) return
    const signature = workspaceTerminalSignature
    if (lastProgressTerminalRef.current === signature) return
    lastProgressTerminalRef.current = signature
    void refreshAll()
  }, [refreshAll, workspaceTerminalSignature])

  return (
    <Stack spacing={2}>
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent>
          <Stack spacing={2}>
            <Stack
              direction={{ xs: 'column', md: 'row' }}
              alignItems={{ xs: 'stretch', md: 'center' }}
              justifyContent="space-between"
              spacing={1.5}
            >
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {t('knowledge.title')}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('knowledge.description')}
                </Typography>
              </Box>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => refreshAll()} disabled={documentsQuery.isLoading}>
                  {t('knowledge.actions.refresh')}
                </Button>
                <Button variant="outlined" startIcon={<ReindexIcon />} onClick={() => reindexAllMutation.mutate()} disabled={reindexAllMutation.isPending}>
                  {t('knowledge.actions.reindexAll')}
                </Button>
                <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
                  {t('knowledge.actions.createText')}
                </Button>
                <Button variant="contained" color="secondary" startIcon={<FileUploadIcon />} onClick={() => setUploadOpen(true)}>
                  {t('knowledge.actions.uploadFile')}
                </Button>
              </Stack>
            </Stack>

            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip label={t('knowledge.stats.documents', { count: documents.length })} />
              <Chip label={t('knowledge.stats.ready', { count: documents.filter(item => item.sync_status === 'ready').length })} color="success" />
              <Chip label={t('knowledge.stats.failed', { count: documents.filter(item => item.sync_status === 'failed' || item.extract_status === 'failed').length })} color="error" />
            </Stack>

            <TextField
              fullWidth
              size="small"
              value={searchDraft}
              onChange={event => setSearchDraft(event.target.value)}
              placeholder={t('knowledge.search.placeholder')}
              onKeyDown={event => {
                if (event.key === 'Enter' && searchDraft.trim()) {
                  searchMutation.mutate(searchDraft.trim())
                }
              }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <Stack direction="row" spacing={0.5}>
                      {searchResult && (
                        <Tooltip title={t('knowledge.actions.clearSearch')}>
                          <IconButton size="small" onClick={() => setSearchResult(null)}>
                            <ClearIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Button
                        size="small"
                        variant="contained"
                        onClick={() => searchMutation.mutate(searchDraft.trim())}
                        disabled={!searchDraft.trim() || searchMutation.isPending}
                      >
                        {t('knowledge.actions.search')}
                      </Button>
                    </Stack>
                  </InputAdornment>
                ),
              }}
            />
            {searchResult && <Alert severity="info">{searchResult.next_action_hint}</Alert>}
          </Stack>
        </CardContent>
      </Card>

      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', lg: 'row' },
          gap: 2,
          minHeight: 0,
          pb: 1.5,
        }}
      >
        <Card sx={{ ...CARD_VARIANTS.default.styles, width: { xs: '100%', lg: 360 }, flexShrink: 0 }}>
          <CardContent sx={{ p: 0 }}>
            <Box sx={{ px: 2, py: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {listTitle}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {searchResult
                  ? t('knowledge.search.resultCount', { count: searchResult.document_total })
                  : t('knowledge.list.total', { count: documents.length })}
              </Typography>
            </Box>
            <Divider />
            {documentsQuery.isLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
                <CircularProgress size={28} />
              </Box>
            ) : activeList.length ? (
              <List sx={{ maxHeight: 720, overflowY: 'auto', py: 0 }}>
                {listItems.map(item => {
                  const documentId = 'document_id' in item ? item.document_id : item.id
                  const isSearchDocument = 'document_score' in item
                  const subtitle = isSearchDocument ? item.best_match_excerpt : item.summary || item.source_path
                  const isSelected = selectedDocumentId === documentId
                  const status = 'sync_status' in item ? getDerivedStatuses(item, progressByDocumentId.get(documentId)).overallStatus : 'ready'
                  return (
                    <ListItemButton
                      key={`${documentId}-${isSearchDocument ? 'search-doc' : 'doc'}`}
                      selected={isSelected}
                      onClick={() => setSelectedDocumentId(documentId)}
                      sx={{ alignItems: 'flex-start', py: 1.25 }}
                    >
                      <ListItemText
                        primary={
                          <Stack spacing={0.75}>
                            <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.35, minWidth: 0 }}>
                              {item.title}
                            </Typography>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                              {'format' in item && <Chip size="small" label={item.format.toUpperCase()} variant="outlined" />}
                              {isSearchDocument && suggestedDocumentIds.has(documentId) && (
                                <Chip size="small" label="Suggested" color="primary" variant="outlined" />
                              )}
                              <Chip size="small" label={statusLabel(status)} color={statusColor(status)} />
                            </Stack>
                          </Stack>
                        }
                        secondary={
                          <Stack spacing={0.5} sx={{ mt: 0.75 }}>
                            <Typography variant="caption" color="text.secondary">
                              {'source_path' in item ? item.source_path : ''}
                            </Typography>
                            {isSearchDocument && (
                              <>
                                {!!item.headings.length && (
                                  <Typography variant="caption" color="text.secondary">
                                    {item.headings.join(' / ')}
                                  </Typography>
                                )}
                                <Typography variant="caption" color="text.secondary">
                                  {`Score ${item.document_score.toFixed(3)} · ${item.matched_chunk_count} chunks`}
                                </Typography>
                                <Typography
                                  variant="body2"
                                  color="text.secondary"
                                  sx={{
                                    display: '-webkit-box',
                                    WebkitLineClamp: 3,
                                    WebkitBoxOrient: 'vertical',
                                    overflow: 'hidden',
                                  }}
                                >
                                  {subtitle || t('knowledge.list.noPreview')}
                                </Typography>
                              </>
                            )}
                            {!isSearchDocument && (
                              <>
                                {!!item.summary && (
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
                                    {item.summary}
                                  </Typography>
                                )}
                                <Typography variant="caption" color="text.secondary">
                                  {`${item.chunk_count} chunks`}
                                </Typography>
                              </>
                            )}
                          </Stack>
                        }
                      />
                    </ListItemButton>
                  )
                })}
              </List>
            ) : (
              <Box sx={{ px: 2, py: 4 }}>
                <Alert severity="info">
                  {searchResult ? t('knowledge.search.empty') : t('knowledge.empty')}
                </Alert>
              </Box>
            )}
          </CardContent>
        </Card>

        <Box sx={{ flex: 1, minWidth: 0, overflow: 'auto', pb: 1 }}>
          <Card sx={{ ...CARD_VARIANTS.default.styles }}>
            <CardContent sx={{ minHeight: 540 }}>
              {!selectedDocumentId ? (
                <Alert severity="info">{t('knowledge.detail.noSelection')}</Alert>
              ) : detailQuery.isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
                  <CircularProgress size={32} />
                </Box>
              ) : detail ? (
                <Stack spacing={2}>
                <Stack
                  direction={{ xs: 'column', md: 'row' }}
                  justifyContent="space-between"
                  alignItems={{ xs: 'flex-start', md: 'flex-start' }}
                  spacing={1.5}
                >
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.35, wordBreak: 'break-word' }}>
                      {detail.document.title}
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center" sx={{ mt: 1 }}>
                      <Chip label={detail.document.format.toUpperCase()} />
                      {selectedDerivedStatuses != null && selectedDerivedStatuses.extractStatus === selectedDerivedStatuses.syncStatus ? (
                        <Chip label={statusLabel(selectedDerivedStatuses.syncStatus)} color={statusColor(selectedDerivedStatuses.syncStatus)} />
                      ) : (
                        <>
                          <Chip
                            label={t('knowledge.badges.extract', { status: statusLabel(selectedDerivedStatuses?.extractStatus ?? detail.document.extract_status) })}
                            color={statusColor(selectedDerivedStatuses?.extractStatus ?? detail.document.extract_status)}
                            variant="outlined"
                          />
                          <Chip
                            label={t('knowledge.badges.sync', { status: statusLabel(selectedDerivedStatuses?.syncStatus ?? detail.document.sync_status) })}
                            color={statusColor(selectedDerivedStatuses?.syncStatus ?? detail.document.sync_status)}
                          />
                        </>
                      )}
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
                      {detail.document.summary || t('knowledge.detail.noSummary')}
                    </Typography>
                  </Box>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                    <Button
                      variant={detail.document.is_enabled ? 'outlined' : 'contained'}
                      onClick={() =>
                        toggleEnabledMutation.mutate({
                          documentId: detail.document.id,
                          isEnabled: !detail.document.is_enabled,
                        })
                      }
                      disabled={toggleEnabledMutation.isPending}
                    >
                      {detail.document.is_enabled ? t('knowledge.actions.disable') : t('knowledge.actions.enable')}
                    </Button>
                    <Button variant="outlined" startIcon={<ReindexIcon />} onClick={() => reindexMutation.mutate(detail.document.id)} disabled={reindexMutation.isPending}>
                      {t('knowledge.actions.reindex')}
                    </Button>
                    <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleDownloadRaw}>
                      {t('knowledge.actions.downloadRaw')}
                    </Button>
                    <Button variant="outlined" color="error" startIcon={<DeleteIcon />} onClick={() => setDeleteOpen(true)}>
                      {t('knowledge.actions.delete')}
                    </Button>
                  </Stack>
                </Stack>

                {selectedProgress && (
                  <Card variant="outlined">
                    <CardContent>
                      <Stack spacing={1}>
                        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1}>
                          <Typography variant="subtitle2">
                            {t('knowledge.progress.title')}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {`${kbProgressLabel(selectedProgress.phase, t)} · ${selectedProgress.progress_percent}%`}
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
                            ? t('knowledge.progress.detail', {
                                processed: selectedProgress.processed_chunks,
                                total: selectedProgress.total_chunks,
                              })
                            : t('knowledge.progress.pending')}
                        </Typography>
                        {selectedProgress.error_summary && (
                          <Alert severity="error">{selectedProgress.error_summary}</Alert>
                        )}
                      </Stack>
                    </CardContent>
                  </Card>
                )}

                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {detail.document.tags.map(tag => (
                    <Chip key={tag} size="small" label={tag} variant="outlined" />
                  ))}
                  {!detail.document.tags.length && (
                    <Chip size="small" label={t('knowledge.detail.noTags')} variant="outlined" />
                  )}
                </Stack>

                <Card variant="outlined">
                  <CardContent>
                    <Stack spacing={1}>
                      <Typography variant="subtitle2">{t('knowledge.detail.metadata')}</Typography>
                      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                        <TextField label={t('knowledge.detail.category')} size="small" fullWidth value={detail.document.category || '-'} InputProps={{ readOnly: true }} />
                        <TextField label={t('knowledge.detail.fileName')} size="small" fullWidth value={detail.document.file_name} InputProps={{ readOnly: true }} />
                        <TextField label={t('knowledge.detail.fileSize')} size="small" fullWidth value={formatFileSize(detail.document.file_size)} InputProps={{ readOnly: true }} />
                      </Stack>
                      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                        <TextField label={t('knowledge.detail.chunkCount')} size="small" fullWidth value={String(detail.document.chunk_count)} InputProps={{ readOnly: true }} />
                        <TextField label={t('knowledge.detail.updatedAt')} size="small" fullWidth value={formatDateTime(detail.document.update_time)} InputProps={{ readOnly: true }} />
                        <TextField label={t('knowledge.detail.indexedAt')} size="small" fullWidth value={formatDateTime(detail.document.last_indexed_at)} InputProps={{ readOnly: true }} />
                      </Stack>
                      {detail.document.last_error && <Alert severity="error">{detail.document.last_error}</Alert>}
                    </Stack>
                  </CardContent>
                </Card>

                <Card variant="outlined">
                  <CardContent sx={{ p: 0 }}>
                    <Box sx={{ px: 2, pt: 1.5 }}>
                      <Typography variant="subtitle2">{t('knowledge.detail.preview')}</Typography>
                    </Box>
                    <Tabs
                      value={previewTab}
                      onChange={(_, value: PreviewTab) => setPreviewTab(value)}
                      sx={{ px: 1.5 }}
                    >
                      <Tab value="normalized" label={t('knowledge.preview.normalized')} />
                      <Tab value="source" label={t('knowledge.preview.source')} />
                    </Tabs>
                    <Divider />
                    <Box
                      sx={{
                        p: 2,
                        maxHeight: 520,
                        overflow: 'auto',
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        fontSize: 13,
                        lineHeight: 1.7,
                      }}
                    >
                      {preview ? preview : t('knowledge.preview.empty')}
                    </Box>
                  </CardContent>
                </Card>
                </Stack>
              ) : (
                <Alert severity="warning">{t('knowledge.detail.loadFailed')}</Alert>
              )}
            </CardContent>
          </Card>
        </Box>
      </Box>

      <Dialog open={createOpen} onClose={() => !createMutation.isPending && setCreateOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{t('knowledge.dialogs.createTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                label={t('knowledge.form.title')}
                fullWidth
                value={createForm.title}
                onChange={event => setCreateForm(prev => ({ ...prev, title: event.target.value }))}
              />
              <TextField
                select
                label={t('knowledge.form.format')}
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
                label={t('knowledge.form.sourcePath')}
                fullWidth
                value={createForm.source_path}
                onChange={event => setCreateForm(prev => ({ ...prev, source_path: event.target.value }))}
                placeholder={t('knowledge.form.sourcePathPlaceholder')}
              />
              <TextField
                label={t('knowledge.form.fileName')}
                fullWidth
                value={createForm.file_name}
                onChange={event => setCreateForm(prev => ({ ...prev, file_name: event.target.value }))}
              />
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                label={t('knowledge.form.category')}
                fullWidth
                value={createForm.category}
                onChange={event => setCreateForm(prev => ({ ...prev, category: event.target.value }))}
              />
              <TextField
                label={t('knowledge.form.tags')}
                fullWidth
                value={createTagsInput}
                onChange={event => setCreateTagsInput(event.target.value)}
                placeholder={t('knowledge.form.tagsPlaceholder')}
              />
            </Stack>
            <TextField
              label={t('knowledge.form.summary')}
              fullWidth
              value={createForm.summary}
              onChange={event => setCreateForm(prev => ({ ...prev, summary: event.target.value }))}
            />
            <TextField
              label={t('knowledge.form.content')}
              fullWidth
              multiline
              minRows={14}
              value={createForm.content}
              onChange={event => setCreateForm(prev => ({ ...prev, content: event.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)} disabled={createMutation.isPending}>
            {t('knowledge.actions.cancel')}
          </Button>
          <Button onClick={handleCreateSubmit} variant="contained" disabled={createMutation.isPending || !createForm.title.trim() || !createForm.content.trim()}>
            {createMutation.isPending ? t('knowledge.actions.creating') : t('knowledge.actions.create')}
          </Button>
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
      >
        <DialogTitle>{t('knowledge.dialogs.uploadTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Button variant="outlined" startIcon={<FolderOpenIcon />} onClick={() => uploadInputRef.current?.click()}>
              {uploadFile ? uploadFile.name : t('knowledge.actions.chooseFile')}
            </Button>
            <Alert severity="info">
              {t('knowledge.form.supportedFormats', { formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', ') })}
            </Alert>
            <input
              ref={uploadInputRef}
              type="file"
              hidden
              onChange={handleFileInputChange}
              accept=".md,.txt,.html,.htm,.json,.yaml,.yml,.csv,.xlsx,.pdf,.docx"
            />
            <TextField label={t('knowledge.form.title')} fullWidth value={uploadTitle} onChange={event => setUploadTitle(event.target.value)} />
            <TextField label={t('knowledge.form.category')} fullWidth value={uploadCategory} onChange={event => setUploadCategory(event.target.value)} />
            <TextField
              label={t('knowledge.form.tags')}
              fullWidth
              value={uploadTagsInput}
              onChange={event => setUploadTagsInput(event.target.value)}
              placeholder={t('knowledge.form.tagsPlaceholder')}
            />
            <TextField label={t('knowledge.form.summary')} fullWidth value={uploadSummary} onChange={event => setUploadSummary(event.target.value)} />
            <Button
              variant={uploadEnabled ? 'contained' : 'outlined'}
              onClick={() => setUploadEnabled(prev => !prev)}
              startIcon={<VisibilityIcon />}
            >
              {uploadEnabled ? t('knowledge.actions.enabled') : t('knowledge.actions.disabled')}
            </Button>
            {uploadMutation.isPending && (
              <Stack spacing={0.75}>
                <LinearProgress variant="determinate" value={uploadProgress} sx={{ height: 8, borderRadius: 999 }} />
                <Typography variant="caption" color="text.secondary">
                  {`${t('knowledge.actions.uploading')} · ${uploadProgress}%`}
                </Typography>
              </Stack>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadOpen(false)} disabled={uploadMutation.isPending}>
            {t('knowledge.actions.cancel')}
          </Button>
          <Button onClick={handleUploadSubmit} variant="contained" disabled={uploadMutation.isPending || !uploadFile}>
            {uploadMutation.isPending ? t('knowledge.actions.uploading') : t('knowledge.actions.upload')}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteOpen} onClose={() => !deleteMutation.isPending && setDeleteOpen(false)}>
        <DialogTitle>{t('knowledge.dialogs.deleteTitle')}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {t('knowledge.dialogs.deleteContent', { title: selectedDocument?.title ?? '-' })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteOpen(false)} disabled={deleteMutation.isPending}>
            {t('knowledge.actions.cancel')}
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => selectedDocumentId != null && deleteMutation.mutate(selectedDocumentId)}
            disabled={deleteMutation.isPending || selectedDocumentId == null}
          >
            {t('knowledge.actions.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
