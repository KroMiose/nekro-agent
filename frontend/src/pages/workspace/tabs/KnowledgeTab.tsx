import { ChangeEvent, MouseEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Card,
  Chip,
  Checkbox,
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
  Menu,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import {
  Add as AddIcon,
  ArrowDropDown as ArrowDropDownIcon,
  Close as CloseIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Edit as EditIcon,
  Link as LinkIcon,
  Refresh as RefreshIcon,
  RestartAlt as ReindexIcon,
  Search as SearchIcon,
  Visibility as VisibilityIcon,
  LibraryBooks as LibraryIcon,
  FolderOpen as FolderOpenIcon,
  DriveFileMove as ImportFolderIcon,
  Clear as ClearIcon,
  CheckCircleOutline as CheckCircleIcon,
  ErrorOutline as ErrorOutlineIcon,
  ViewList as ViewListIcon,
  AccountTree as GroupedViewIcon,
  Hub as GraphViewIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material'
import { alpha, type SxProps, type Theme } from '@mui/material/styles'
import { useTheme } from '@mui/material/styles'
import { useMutation, useQuery, useQueries, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  KBAssetDetailResponse,
  KBAssetListItem,
  KBCreateTextDocumentBody,
  KBDocumentDetailResponse,
  KBDocumentReferences,
  KBReferenceItem,
  KBSearchResponse,
  KBUploadFilePayload,
  kbLibraryApi,
  knowledgeBaseApi,
  WorkspaceDetail,
} from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { KbIndexProgressInfo, useSystemEventsContext } from '../../../contexts/SystemEventsContext'
import { CARD_VARIANTS, CHIP_VARIANTS, UNIFIED_TABLE_STYLES } from '../../../theme/variants'
import ActionButton from '../../../components/common/ActionButton'
import IconActionButton from '../../../components/common/IconActionButton'
import SearchField from '../../../components/common/SearchField'
import StatCard from '../../../components/common/StatCard'
import ReferenceGraph from '../components/ReferenceGraph'
import KBGraphDialog from '../components/KBGraphDialog'
import KBBatchActionsButton from '../components/KBBatchActionsButton'
import {
  findCategoryLengthOverflow,
  getFolderImportMetadata,
  KB_CATEGORY_MAX_LENGTH,
} from '../kbFolderImport'
import { buildCategoryTree, type KBCategoryTreeNode } from '../kbCategoryTree'

type KnowledgeSelection =
  | { kind: 'document'; id: number }
  | { kind: 'asset'; id: number }
  | null
type KnowledgePreviewDetail = Pick<KBDocumentDetailResponse, 'normalized_content'> | Pick<KBAssetDetailResponse, 'normalized_content'>

const TEXT_FORMAT_OPTIONS: Array<{ value: 'markdown' | 'text'; label: string }> = [
  { value: 'markdown', label: 'Markdown' },
  { value: 'text', label: 'Text' },
]

const EMPTY_DOCUMENTS: KBDocumentDetailResponse['document'][] = []
const EMPTY_GLOBAL_ASSETS: KBAssetListItem[] = []
const EMPTY_SEARCH_DOCUMENTS: KBSearchResponse['documents'] = []
const SUPPORTED_UPLOAD_EXTENSIONS = ['.md', '.txt', '.html', '.htm', '.json', '.yaml', '.yml', '.csv', '.xlsx', '.pdf', '.docx']


function getFileExtension(fileName: string): string {
  const match = fileName.toLowerCase().match(/(\.[^.]+)$/)
  return match?.[1] ?? ''
}


function isSupportedUploadFile(file: File): boolean {
  return SUPPORTED_UPLOAD_EXTENSIONS.includes(getFileExtension(file.name))
}

type BatchItemStatus = 'waiting' | 'uploading' | 'indexing' | 'done' | 'error'

interface BatchQueueItem {
  id: string
  file: File
  status: BatchItemStatus
  uploadProgress: number
  assetId?: number
  documentId?: number
  errorMessage?: string
  title: string
  category: string
  tags: string
  summary: string
  source_path?: string
}

function getKnowledgeEntrySelectionKey(kind: 'document' | 'asset', id: number): string {
  return `${kind}:${id}`
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

function getEffectiveStatus(
  document: Pick<KBDocumentDetailResponse['document'], 'extract_status' | 'sync_status'>
): string {
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

function previewContent(detail: KnowledgePreviewDetail | undefined): string {
  if (!detail) return ''
  return detail.normalized_content ?? ''
}


function kbProgressLabel(phase: string, t: (key: string, options?: Record<string, unknown>) => string): string {
  return t(`knowledge.progress.phase.${phase}`, { defaultValue: phase })
}


export default function KnowledgeTab({ workspace }: { workspace: WorkspaceDetail }) {
  const theme = useTheme()
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const { kbIndexProgresses, kbLibraryIndexProgresses } = useSystemEventsContext()
  const uploadInputRef = useRef<HTMLInputElement | null>(null)
  const batchInputRef = useRef<HTMLInputElement | null>(null)
  const dirInputRef = useRef<HTMLInputElement | null>(null)
  const batchProcessingRef = useRef(false)
  const batchQueueRef = useRef<BatchQueueItem[]>([])
  const batchCancelRequestedRef = useRef(false)
  const batchRunVersionRef = useRef(0)
  const lastProgressTerminalRef = useRef('')
  const lastAssetProgressTerminalRef = useRef('')

  const [selectedItem, setSelectedItem] = useState<KnowledgeSelection>(null)
  const [searchDraft, setSearchDraft] = useState('')
  const [searchResult, setSearchResult] = useState<KBSearchResponse | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [batchUploadOpen, setBatchUploadOpen] = useState(false)
  const [batchQueue, setBatchQueue] = useState<BatchQueueItem[]>([])
  const [batchTarget, setBatchTarget] = useState<'library' | 'workspace'>('library')
  const [batchRunning, setBatchRunning] = useState(false)
  const [batchCancelRequested, setBatchCancelRequested] = useState(false)
  const [batchPanelVisible, setBatchPanelVisible] = useState(false)
  const [expandedBatchItemId, setExpandedBatchItemId] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [bulkDeleteSelectedOpen, setBulkDeleteSelectedOpen] = useState(false)
  const [reuseOpen, setReuseOpen] = useState(false)
  const [listView, setListView] = useState<'flat' | 'grouped' | 'graph'>('graph')
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set())
  const [selectedEntryKeys, setSelectedEntryKeys] = useState<Set<string>>(new Set())
  const [addMenuAnchorEl, setAddMenuAnchorEl] = useState<HTMLElement | null>(null)
  const [reuseSearch, setReuseSearch] = useState('')
  const [reuseAssetIds, setReuseAssetIds] = useState<number[]>([])
  const [reuseCollapsedCategories, setReuseCollapsedCategories] = useState<Set<string>>(new Set())

  const [editMetaOpen, setEditMetaOpen] = useState(false)
  const [editMetaForm, setEditMetaForm] = useState({ title: '', category: '', tagsInput: '', summary: '' })

  const [refDialogOpen, setRefDialogOpen] = useState(false)
  const [refTargetSearch, setRefTargetSearch] = useState('')
  const [refDescription, setRefDescription] = useState('')
  const [editingRef, setEditingRef] = useState<KBReferenceItem | null>(null)

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
  const globalAssetsQuery = useQuery({
    queryKey: ['kb-library-assets'],
    queryFn: () => kbLibraryApi.list(),
  })

  const documents = documentsQuery.data ?? EMPTY_DOCUMENTS
  const globalAssets = globalAssetsQuery.data ?? EMPTY_GLOBAL_ASSETS
  const hasSearchResult = searchResult != null
  const searchDocuments = searchResult?.documents ?? EMPTY_SEARCH_DOCUMENTS
  const suggestedDocumentIds = new Set(searchResult?.suggested_document_ids ?? [])
  const listTitle = hasSearchResult ? t('knowledge.sections.searchResults') : t('knowledge.sections.documents')
  const boundGlobalAssets = useMemo(
    () =>
      globalAssets.filter(asset =>
        asset.bound_workspaces.some(item => item.workspace_id === workspace.id)
      ),
    [globalAssets, workspace.id]
  )
  const defaultListEntries = useMemo(
    () => [
      ...documents.map(item => ({ kind: 'document' as const, id: item.id, item })),
      ...boundGlobalAssets.map(item => ({ kind: 'asset' as const, id: item.id, item })),
    ],
    [documents, boundGlobalAssets]
  )
  const categorizedEntries = useMemo(
    () => buildCategoryTree(defaultListEntries, entry => entry.item.category),
    [defaultListEntries]
  )
  const selectedEntries = useMemo(
    () =>
      defaultListEntries.filter(entry =>
        selectedEntryKeys.has(getKnowledgeEntrySelectionKey(entry.kind, entry.id))
      ),
    [defaultListEntries, selectedEntryKeys]
  )
  const selectedDocumentIds = useMemo(
    () => selectedEntries.filter(entry => entry.kind === 'document').map(entry => entry.id),
    [selectedEntries]
  )
  const selectedAssetIds = useMemo(
    () => selectedEntries.filter(entry => entry.kind === 'asset').map(entry => entry.id),
    [selectedEntries]
  )
  const selectedEnabledDocumentIds = useMemo(
    () =>
      selectedEntries
        .filter(entry => entry.kind === 'document' && entry.item.is_enabled)
        .map(entry => entry.id),
    [selectedEntries]
  )
  const selectedEnabledAssetIds = useMemo(
    () =>
      selectedEntries
        .filter(entry => entry.kind === 'asset' && entry.item.is_enabled)
        .map(entry => entry.id),
    [selectedEntries]
  )
  const selectedEntryCount = selectedEntries.length
  const selectedDocumentId = selectedItem?.kind === 'document' ? selectedItem.id : null
  const selectedAssetId = selectedItem?.kind === 'asset' ? selectedItem.id : null
  const selectedDocument = useMemo(
    () => documents.find(item => item.id === selectedDocumentId) ?? null,
    [documents, selectedDocumentId]
  )
  const selectedAsset = useMemo(
    () => boundGlobalAssets.find(item => item.id === selectedAssetId) ?? null,
    [boundGlobalAssets, selectedAssetId]
  )
  const filteredGlobalAssets = useMemo(() => {
    const keyword = reuseSearch.trim().toLowerCase()
    if (!keyword) return globalAssets
    return globalAssets.filter(asset =>
      [
        asset.title,
        asset.source_path,
        asset.category,
        asset.summary,
        asset.file_name,
        ...asset.tags,
      ]
        .join('\n')
        .toLowerCase()
        .includes(keyword)
    )
  }, [globalAssets, reuseSearch])
  const categorizedReuseAssets = useMemo(
    () => buildCategoryTree(filteredGlobalAssets, asset => asset.category),
    [filteredGlobalAssets]
  )
  const reuseAssetIdSet = useMemo(() => new Set(reuseAssetIds), [reuseAssetIds])

  useEffect(() => {
    batchQueueRef.current = batchQueue
  }, [batchQueue])

  useEffect(() => {
    setSelectedEntryKeys(prev => {
      if (prev.size === 0) return prev
      const existingKeys = new Set(
        defaultListEntries.map(entry => getKnowledgeEntrySelectionKey(entry.kind, entry.id))
      )
      let changed = false
      const next = new Set<string>()
      prev.forEach(key => {
        if (existingKeys.has(key)) {
          next.add(key)
          return
        }
        changed = true
      })
      return changed ? next : prev
    })
  }, [defaultListEntries])

  useEffect(() => {
    if (hasSearchResult) {
      if (
        selectedItem != null &&
        !searchDocuments.some(
          item => item.source_kind === selectedItem.kind && item.document_id === selectedItem.id
        )
      ) {
        setSelectedItem(null)
      }
      return
    }

    if (
      selectedItem != null &&
      !defaultListEntries.some(entry => entry.kind === selectedItem.kind && entry.id === selectedItem.id)
    ) {
      setSelectedItem(null)
    }
  }, [defaultListEntries, hasSearchResult, searchDocuments, selectedItem])

  const detailQuery = useQuery({
    queryKey: ['kb-document', workspace.id, selectedDocumentId],
    queryFn: () => knowledgeBaseApi.getDocument(workspace.id, selectedDocumentId as number),
    enabled: selectedDocumentId != null,
    staleTime: 60_000,
  })
  const assetDetailQuery = useQuery({
    queryKey: ['kb-library-asset', selectedAssetId],
    queryFn: () => kbLibraryApi.getAsset(selectedAssetId as number),
    enabled: selectedAssetId != null,
    staleTime: 60_000,
  })

  const documentReferencesQuery = useQuery({
    queryKey: ['kb-document-references', workspace.id, selectedDocumentId],
    queryFn: () => knowledgeBaseApi.getReferences(workspace.id, selectedDocumentId as number),
    enabled: selectedDocumentId != null,
    staleTime: 30_000,
  })
  const assetReferencesQuery = useQuery({
    queryKey: ['kb-asset-references', selectedAssetId],
    queryFn: () => kbLibraryApi.getReferences(selectedAssetId as number),
    enabled: selectedAssetId != null,
    staleTime: 30_000,
  })
  const activeReferences: KBDocumentReferences = (
    selectedDocumentId != null
      ? documentReferencesQuery.data
      : assetReferencesQuery.data
  ) ?? { references_to: [], referenced_by: [] }

  const refreshAll = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['kb-documents', workspace.id] }),
      queryClient.invalidateQueries({ queryKey: ['kb-document', workspace.id] }),
      queryClient.invalidateQueries({ queryKey: ['kb-library-assets'] }),
      queryClient.invalidateQueries({ queryKey: ['kb-library-asset'] }),
    ])
  }, [queryClient, workspace.id])

  const refreshReferences = useCallback(async () => {
    if (selectedDocumentId != null) {
      await queryClient.invalidateQueries({ queryKey: ['kb-document-references', workspace.id, selectedDocumentId] })
    }
    if (selectedAssetId != null) {
      await queryClient.invalidateQueries({ queryKey: ['kb-asset-references', selectedAssetId] })
    }
  }, [queryClient, workspace.id, selectedDocumentId, selectedAssetId])

  const createMutation = useMutation({
    mutationFn: async (body: KBCreateTextDocumentBody) => {
      const data = await kbLibraryApi.createText(body)
      await kbLibraryApi.bindWorkspace(data.asset.id, workspace.id)
      return data
    },
    onSuccess: async data => {
      await refreshAll()
      setSelectedItem({ kind: 'asset', id: data.asset.id })
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
          ? t('knowledge.notifications.addReusedSuccess')
          : t('knowledge.notifications.addSuccess')
      )
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.createFailed', { message: err.message })),
  })

  const uploadMutation = useMutation({
    mutationFn: async (payload: KBUploadFilePayload) => {
      const data = await kbLibraryApi.uploadFile(payload, percent => setUploadProgress(percent))
      await kbLibraryApi.bindWorkspace(data.asset.id, workspace.id)
      return data
    },
    onSuccess: async data => {
      await refreshAll()
      setSelectedItem({ kind: 'asset', id: data.asset.id })
      setUploadOpen(false)
      setUploadFile(null)
      setUploadTitle('')
      setUploadCategory('')
      setUploadSummary('')
      setUploadTagsInput('')
      setUploadEnabled(true)
      setUploadProgress(0)
      notification.success(
        data.reused_existing
          ? t('knowledge.notifications.addReusedSuccess')
          : t('knowledge.notifications.addSuccess')
      )
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
      if (deletedId != null) {
        setSelectedEntryKeys(prev => {
          const key = getKnowledgeEntrySelectionKey('document', deletedId)
          if (!prev.has(key)) return prev
          const next = new Set(prev)
          next.delete(key)
          return next
        })
      }
      if (selectedItem?.kind === 'document' && deletedId === selectedItem.id) {
        setSelectedItem(null)
      }
      notification.success(t('knowledge.notifications.deleteSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.deleteFailed', { message: err.message })),
  })
  const unbindAssetMutation = useMutation({
    mutationFn: (assetId: number) => kbLibraryApi.unbindWorkspace(assetId, workspace.id),
    onSuccess: async () => {
      const removedId = selectedAssetId
      await refreshAll()
      setDeleteOpen(false)
      if (removedId != null) {
        setSelectedEntryKeys(prev => {
          const key = getKnowledgeEntrySelectionKey('asset', removedId)
          if (!prev.has(key)) return prev
          const next = new Set(prev)
          next.delete(key)
          return next
        })
      }
      if (selectedItem?.kind === 'asset' && removedId === selectedItem.id) {
        setSelectedItem(null)
      }
      notification.success(t('knowledge.notifications.removeSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.removeFailed', { message: err.message })),
  })

  const bulkDeleteSelectedMutation = useMutation({
    mutationFn: async ({ documentIds, assetIds }: { documentIds: number[]; assetIds: number[] }) => {
      const operations = [
        ...documentIds.map(documentId => () => knowledgeBaseApi.deleteDocument(workspace.id, documentId)),
        ...assetIds.map(assetId => () => kbLibraryApi.unbindWorkspace(assetId, workspace.id)),
      ]
      const results = await Promise.allSettled(operations.map(run => run()))
      let deletedCount = 0
      let failedCount = 0
      results.forEach(result => {
        if (result.status === 'fulfilled') deletedCount += 1
        else failedCount += 1
      })
      return { deletedCount, failedCount, documentIds, assetIds }
    },
    onSuccess: async result => {
      setBulkDeleteSelectedOpen(false)
      setSelectedEntryKeys(prev => {
        if (result.documentIds.length === 0 && result.assetIds.length === 0) return prev
        const next = new Set(prev)
        result.documentIds.forEach(id => next.delete(getKnowledgeEntrySelectionKey('document', id)))
        result.assetIds.forEach(id => next.delete(getKnowledgeEntrySelectionKey('asset', id)))
        return next
      })
      if (
        selectedItem != null &&
        ((selectedItem.kind === 'document' && result.documentIds.includes(selectedItem.id)) ||
          (selectedItem.kind === 'asset' && result.assetIds.includes(selectedItem.id)))
      ) {
        setSelectedItem(null)
      }
      await refreshAll()
      if (result.failedCount === 0) {
        notification.success(t('knowledge.notifications.bulkDeleteSelectedSuccess', { count: result.deletedCount }))
      } else {
        notification.warning(
          t('knowledge.notifications.bulkDeleteSelectedPartial', {
            deleted: result.deletedCount,
            failed: result.failedCount,
          })
        )
      }
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.deleteFailed', { message: err.message })),
  })

  const bulkReindexSelectedMutation = useMutation({
    mutationFn: async ({ documentIds, assetIds }: { documentIds: number[]; assetIds: number[] }) => {
      const operations = [
        ...documentIds.map(documentId => () => knowledgeBaseApi.reindexDocument(workspace.id, documentId)),
        ...assetIds.map(assetId => () => kbLibraryApi.reindexAsset(assetId)),
      ]
      const results = await Promise.allSettled(operations.map(run => run()))
      let queuedCount = 0
      let failedCount = 0
      results.forEach(result => {
        if (result.status === 'fulfilled') queuedCount += 1
        else failedCount += 1
      })
      return { queuedCount, failedCount }
    },
    onSuccess: async result => {
      await refreshAll()
      if (result.failedCount === 0) {
        notification.success(t('knowledge.notifications.bulkReindexSelectedSuccess', { count: result.queuedCount }))
      } else {
        notification.warning(
          t('knowledge.notifications.bulkReindexSelectedPartial', {
            queued: result.queuedCount,
            failed: result.failedCount,
          })
        )
      }
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.reindexFailed', { message: err.message })),
  })

  const bulkDisableSelectedMutation = useMutation({
    mutationFn: async ({ documentIds, assetIds }: { documentIds: number[]; assetIds: number[] }) => {
      const operations = [
        ...documentIds.map(documentId => () => knowledgeBaseApi.updateDocument(workspace.id, documentId, { is_enabled: false })),
        ...assetIds.map(assetId => () => kbLibraryApi.updateAsset(assetId, { is_enabled: false })),
      ]
      const results = await Promise.allSettled(operations.map(run => run()))
      let updatedCount = 0
      let failedCount = 0
      results.forEach(result => {
        if (result.status === 'fulfilled') updatedCount += 1
        else failedCount += 1
      })
      return { updatedCount, failedCount }
    },
    onSuccess: async result => {
      await refreshAll()
      if (result.failedCount === 0) {
        notification.success(t('knowledge.notifications.bulkDisableSelectedSuccess', { count: result.updatedCount }))
      } else {
        notification.warning(
          t('knowledge.notifications.bulkDisableSelectedPartial', {
            updated: result.updatedCount,
            failed: result.failedCount,
          })
        )
      }
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.updateFailed', { message: err.message })),
  })

  const reindexMutation = useMutation({
    mutationFn: (documentId: number) => knowledgeBaseApi.reindexDocument(workspace.id, documentId),
    onSuccess: async () => {
      await refreshAll()
      notification.success(t('knowledge.notifications.reindexSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.reindexFailed', { message: err.message })),
  })
  const reindexAssetMutation = useMutation({
    mutationFn: (assetId: number) => kbLibraryApi.reindexAsset(assetId),
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
  const toggleAssetEnabledMutation = useMutation({
    mutationFn: ({ assetId, isEnabled }: { assetId: number; isEnabled: boolean }) =>
      kbLibraryApi.updateAsset(assetId, { is_enabled: isEnabled }),
    onSuccess: async () => {
      await refreshAll()
      notification.success(t('knowledge.notifications.updateSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.updateFailed', { message: err.message })),
  })

  const updateDocMetaMutation = useMutation({
    mutationFn: ({ id, title, category, tags, summary }: { id: number; title: string; category: string; tags: string[]; summary: string }) =>
      knowledgeBaseApi.updateDocument(workspace.id, id, { title, category, tags, summary }),
    onSuccess: async () => {
      await refreshAll()
      setEditMetaOpen(false)
      notification.success(t('knowledge.notifications.updateSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.updateFailed', { message: err.message })),
  })

  const updateAssetMetaMutation = useMutation({
    mutationFn: ({ id, title, category, tags, summary }: { id: number; title: string; category: string; tags: string[]; summary: string }) =>
      kbLibraryApi.updateAsset(id, { title, category, tags, summary }),
    onSuccess: async () => {
      await refreshAll()
      setEditMetaOpen(false)
      notification.success(t('knowledge.notifications.updateSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.notifications.updateFailed', { message: err.message })),
  })

  const addReferenceMutation = useMutation({
    mutationFn: ({ targetId, description }: { targetId: number; description: string }) =>
      selectedDocumentId != null
        ? knowledgeBaseApi.addReference(workspace.id, selectedDocumentId, targetId, description)
        : kbLibraryApi.addReference(selectedAssetId as number, targetId, description),
    onSuccess: async () => {
      await refreshReferences()
      setRefDialogOpen(false)
      setRefTargetSearch('')
      setRefDescription('')
      setEditingRef(null)
      notification.success(t('knowledge.references.addSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.references.addFailed', { message: err.message })),
  })

  const removeReferenceMutation = useMutation({
    mutationFn: (targetId: number) =>
      selectedDocumentId != null
        ? knowledgeBaseApi.removeReference(workspace.id, selectedDocumentId, targetId)
        : kbLibraryApi.removeReference(selectedAssetId as number, targetId),
    onSuccess: async () => {
      await refreshReferences()
      notification.success(t('knowledge.references.removeSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.references.removeFailed', { message: err.message })),
  })

  const updateReferenceMutation = useMutation({
    mutationFn: ({ targetId, description }: { targetId: number; description: string }) =>
      selectedDocumentId != null
        ? knowledgeBaseApi.updateReference(workspace.id, selectedDocumentId, targetId, description)
        : kbLibraryApi.updateReference(selectedAssetId as number, targetId, description),
    onSuccess: async () => {
      await refreshReferences()
      setRefDialogOpen(false)
      setRefTargetSearch('')
      setRefDescription('')
      setEditingRef(null)
      notification.success(t('knowledge.references.updateSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.references.updateFailed', { message: err.message })),
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
  const reuseBindingsMutation = useMutation({
    mutationFn: async (assetIds: number[]) => {
      const selectedAssetSet = new Set(assetIds)
      const changedAssets = globalAssets.filter(asset => {
        const isBound = asset.bound_workspaces.some(item => item.workspace_id === workspace.id)
        return isBound !== selectedAssetSet.has(asset.id)
      })
      await Promise.all(
        changedAssets.map(asset =>
          selectedAssetSet.has(asset.id)
            ? kbLibraryApi.bindWorkspace(asset.id, workspace.id)
            : kbLibraryApi.unbindWorkspace(asset.id, workspace.id)
        )
      )
    },
    onSuccess: async () => {
      await refreshAll()
      setReuseOpen(false)
      setSearchResult(null)
      notification.success(t('knowledge.notifications.reuseBindingsSuccess'))
    },
    onError: (err: Error) =>
      notification.error(t('knowledge.notifications.reuseBindingsFailed', { message: err.message })),
  })

  const handleDownloadRaw = async () => {
    if (selectedDocumentId && selectedDocument) {
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
      return
    }
    if (!selectedAssetId || !selectedAsset) return
    try {
      const { blob, filename } = await kbLibraryApi.downloadRawFile(selectedAssetId)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename ?? selectedAsset.file_name
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

  const handleReuseDialogOpen = () => {
    setAddMenuAnchorEl(null)
    setReuseAssetIds(boundGlobalAssets.map(asset => asset.id))
    setReuseSearch('')
    setReuseOpen(true)
  }

  const handleAddMenuOpen = (event: MouseEvent<HTMLButtonElement>) => {
    setAddMenuAnchorEl(event.currentTarget)
  }

  const handleAddMenuClose = () => {
    setAddMenuAnchorEl(null)
  }

  const handleOpenCreateDialog = () => {
    handleAddMenuClose()
    setCreateOpen(true)
  }

  const handleOpenBatchUploadDialog = () => {
    handleAddMenuClose()
    setBatchQueue([])
    setBatchTarget('library')
    setBatchUploadOpen(true)
  }

  const handleBatchFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (files.length === 0) return
    const unsupported = files.filter(f => !isSupportedUploadFile(f))
    if (unsupported.length > 0) {
      notification.error(
        t('knowledge.notifications.unsupportedFormat', {
          name: unsupported.map(f => f.name).join(', '),
          formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', '),
        })
      )
      return
    }
    setBatchTarget('library')
    setBatchQueue(files.map(f => ({
      id: `${f.name}-${f.size}-${Math.random()}`,
      file: f,
      status: 'waiting',
      uploadProgress: 0,
      title: f.name.replace(/\.[^.]+$/, ''),
      category: uploadCategory,
      tags: uploadTagsInput,
      summary: '',
    })))
  }

  const handleDirFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (files.length === 0) return
    const supported = files.filter(f => isSupportedUploadFile(f))
    const skippedCount = files.length - supported.length
    if (supported.length === 0) {
      notification.error(t('knowledge.notifications.dirImportNoSupported', { formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', ') }))
      return
    }
    if (skippedCount > 0) {
      notification.warning(t('knowledge.notifications.dirImportSkipped', { count: skippedCount }))
    }
    setBatchTarget('workspace')
    const nextQueue = supported.map(f => {
      const { category, sourcePath } = getFolderImportMetadata(f)
      return {
        id: `${sourcePath}-${f.size}-${Math.random()}`,
        file: f,
        status: 'waiting' as BatchItemStatus,
        uploadProgress: 0,
        title: f.name.replace(/\.[^.]+$/, ''),
        category,
        tags: '',
        summary: '',
        source_path: sourcePath,
      }
    })
    const overflow = findCategoryLengthOverflow(nextQueue)
    if (overflow) {
      notification.error(
        t('knowledge.notifications.dirImportCategoryTooLong', {
          category: overflow.item.category,
          length: overflow.length,
          max: KB_CATEGORY_MAX_LENGTH,
        })
      )
      return
    }
    setBatchQueue(nextQueue)
    setBatchUploadOpen(true)
  }

  const removeBatchQueueItem = useCallback((id: string) => {
    setExpandedBatchItemId(prev => (prev === id ? null : prev))
    setBatchQueue(prev => prev.filter(item => item.id !== id))
  }, [])

  const requestBatchCancel = useCallback(() => {
    batchCancelRequestedRef.current = true
    setBatchCancelRequested(true)
  }, [])

  const startBatchUpload = useCallback(async (items: BatchQueueItem[], target: 'library' | 'workspace') => {
    if (batchProcessingRef.current) return
    const overflow = findCategoryLengthOverflow(items)
    if (overflow) {
      notification.error(
        t('knowledge.notifications.dirImportCategoryTooLong', {
          category: overflow.item.category,
          length: overflow.length,
          max: KB_CATEGORY_MAX_LENGTH,
        })
      )
      return
    }
    const runVersion = batchRunVersionRef.current + 1
    batchRunVersionRef.current = runVersion
    batchProcessingRef.current = true
    batchCancelRequestedRef.current = false
    setBatchCancelRequested(false)
    setBatchRunning(true)
    setBatchUploadOpen(false)
    setBatchPanelVisible(true)
    let uploadedAny = false
    try {
      for (const item of items) {
        if (batchRunVersionRef.current !== runVersion || batchCancelRequestedRef.current) break
        if (!batchQueueRef.current.some(queueItem => queueItem.id === item.id && queueItem.status === 'waiting')) continue
        setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, status: 'uploading', uploadProgress: 0 } : i))
        try {
          if (target === 'workspace') {
            const data = await knowledgeBaseApi.uploadFile(
              workspace.id,
              {
                file: item.file,
                title: item.title || item.file.name.replace(/\.[^.]+$/, ''),
                source_path: item.source_path || '',
                category: item.category,
                tags: normalizeTagsInput(item.tags),
                summary: item.summary,
                is_enabled: true,
              },
              pct => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, uploadProgress: pct } : i)),
            )
            if (batchRunVersionRef.current !== runVersion) break
            uploadedAny = true
            setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, status: 'indexing', documentId: data.document.id } : i))
            const deadline = Date.now() + 300_000
            while (Date.now() < deadline) {
              if (batchRunVersionRef.current !== runVersion || batchCancelRequestedRef.current) break
              await new Promise(r => setTimeout(r, 1500))
              if (batchRunVersionRef.current !== runVersion || batchCancelRequestedRef.current) break
              const detail = await knowledgeBaseApi.getDocument(workspace.id, data.document.id)
              if (detail.document.sync_status === 'ready' || detail.document.sync_status === 'failed') break
            }
          } else {
            const data = await kbLibraryApi.uploadFile(
              {
                file: item.file,
                title: item.title || item.file.name.replace(/\.[^.]+$/, ''),
                source_path: item.source_path || '',
                category: item.category,
                tags: normalizeTagsInput(item.tags),
                summary: item.summary,
                is_enabled: true,
              },
              pct => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, uploadProgress: pct } : i)),
            )
            if (batchRunVersionRef.current !== runVersion) break
            uploadedAny = true
            await kbLibraryApi.bindWorkspace(data.asset.id, workspace.id)
            setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, status: 'indexing', assetId: data.asset.id } : i))
            const deadline = Date.now() + 300_000
            while (Date.now() < deadline) {
              if (batchRunVersionRef.current !== runVersion || batchCancelRequestedRef.current) break
              await new Promise(r => setTimeout(r, 1500))
              if (batchRunVersionRef.current !== runVersion || batchCancelRequestedRef.current) break
              const detail = await kbLibraryApi.getAsset(data.asset.id)
              if (detail.asset.sync_status === 'ready' || detail.asset.sync_status === 'failed') break
            }
          }
          if (batchRunVersionRef.current !== runVersion || batchCancelRequestedRef.current) break
          setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, status: 'done' } : i))
        } catch (err) {
          if (batchRunVersionRef.current !== runVersion) break
          setBatchQueue(prev => prev.map(i => i.id === item.id ? {
            ...i,
            status: 'error',
            errorMessage: err instanceof Error ? err.message : String(err),
          } : i))
        }
      }
    } finally {
      const isCurrentRun = batchRunVersionRef.current === runVersion
      const cancelRequested = batchCancelRequestedRef.current
      if (isCurrentRun) {
        batchProcessingRef.current = false
        batchCancelRequestedRef.current = false
        setBatchRunning(false)
        setBatchCancelRequested(false)
        if (cancelRequested) {
          setExpandedBatchItemId(null)
          setBatchQueue(prev => prev.filter(item => item.status !== 'waiting'))
        }
        if (uploadedAny && target === 'workspace') {
          setListView('grouped')
          setCollapsedCategories(new Set())
        }
        await refreshAll()
      }
    }
  }, [notification, refreshAll, t, workspace.id])

  const handleOpenUploadDialog = () => {
    handleAddMenuClose()
    setUploadOpen(true)
  }

  const toggleCategoryCollapse = useCallback((category: string) => {
    setCollapsedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
  }, [])

  const toggleEntrySelection = useCallback((kind: 'document' | 'asset', id: number) => {
    const key = getKnowledgeEntrySelectionKey(kind, id)
    setSelectedEntryKeys(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  const toggleCategorySelection = useCallback((keys: string[]) => {
    if (keys.length === 0) return
    setSelectedEntryKeys(prev => {
      const next = new Set(prev)
      const shouldSelect = keys.some(key => !next.has(key))
      keys.forEach(key => {
        if (shouldSelect) next.add(key)
        else next.delete(key)
      })
      return next
    })
  }, [])

  const toggleReuseAsset = (assetId: number) => {
    setReuseAssetIds(prev =>
      prev.includes(assetId) ? prev.filter(id => id !== assetId) : [...prev, assetId]
    )
  }

  const toggleReuseCategoryCollapse = useCallback((categoryKey: string) => {
    setReuseCollapsedCategories(prev => {
      const next = new Set(prev)
      if (next.has(categoryKey)) next.delete(categoryKey)
      else next.add(categoryKey)
      return next
    })
  }, [])

  const toggleReuseCategory = useCallback((assetIds: number[]) => {
    if (assetIds.length === 0) return
    setReuseAssetIds(prev => {
      const next = new Set(prev)
      const shouldSelect = assetIds.some(id => !next.has(id))
      assetIds.forEach(id => {
        if (shouldSelect) next.add(id)
        else next.delete(id)
      })
      return Array.from(next)
    })
  }, [])

  const detail = detailQuery.data
  const assetDetail = assetDetailQuery.data
  const selectedDocumentMeta = selectedDocument ?? detail?.document ?? null
  const selectedAssetMeta = selectedAsset ?? assetDetail?.asset ?? null
  const preview = previewContent(detail ?? assetDetail ?? undefined)
  const statusLabel = (status: string) => t(`knowledge.status.${status}`, { defaultValue: status })
  const selectedProgress = selectedDocumentId != null ? kbIndexProgresses.get(`${workspace.id}:${selectedDocumentId}`) ?? null : null
  const selectedAssetProgress = selectedAssetId != null ? kbLibraryIndexProgresses.get(selectedAssetId) ?? null : null
  const selectedDerivedStatuses = selectedDocumentMeta
    ? getDerivedStatuses(selectedDocumentMeta, selectedProgress)
    : null
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

  // Batch-fetch all document references when the graph view is active
  const docRefResults = useQueries({
    queries: listView === 'graph' && !hasSearchResult
      ? documents.map(doc => ({
          queryKey: ['kb-document-references', workspace.id, doc.id],
          queryFn: () => knowledgeBaseApi.getReferences(workspace.id, doc.id),
          staleTime: 5 * 60 * 1000,
        }))
      : [],
  })

  const assetRefResults = useQueries({
    queries: listView === 'graph' && !hasSearchResult
      ? boundGlobalAssets.map(asset => ({
          queryKey: ['kb-asset-references', asset.id] as const,
          queryFn: () => kbLibraryApi.getReferences(asset.id),
          staleTime: 5 * 60 * 1000,
        }))
      : [],
  })

  const graphReferenceEdges = useMemo(() => {
    const edges: Array<{ fromId: number; toId: number; fromKind: 'document' | 'asset'; toKind: 'document' | 'asset' }> = []
    docRefResults.forEach((result, i) => {
      if (result.data?.references_to && i < documents.length) {
        for (const ref of result.data.references_to) {
          edges.push({
            fromId: documents[i].id,
            toId: ref.document_id,
            fromKind: 'document',
            toKind: 'document',
          })
        }
      }
    })
    assetRefResults.forEach((result, i) => {
      if (result.data?.references_to && i < boundGlobalAssets.length) {
        for (const ref of result.data.references_to) {
          edges.push({
            fromId: boundGlobalAssets[i].id,
            toId: ref.document_id,
            fromKind: 'asset',
            toKind: 'asset',
          })
        }
      }
    })
    return edges
  }, [assetRefResults, boundGlobalAssets, docRefResults, documents])

  const boundAssetIds = useMemo(() => new Set(boundGlobalAssets.map(a => a.id)), [boundGlobalAssets])

  const alreadyReferencedToIds = useMemo(
    () => new Set(activeReferences.references_to.map(r => r.document_id)),
    [activeReferences.references_to]
  )
  const refCandidates = useMemo(() => {
    const keyword = refTargetSearch.trim().toLowerCase()
    if (selectedDocumentId != null) {
      return documents
        .filter(doc => doc.id !== selectedDocumentId && !alreadyReferencedToIds.has(doc.id))
        .filter(doc =>
          !keyword ||
          [doc.title, doc.category, doc.summary, doc.file_name, ...doc.tags].join('\n').toLowerCase().includes(keyword)
        )
    }
    if (selectedAssetId != null) {
      return boundGlobalAssets
        .filter(a => a.id !== selectedAssetId && !alreadyReferencedToIds.has(a.id))
        .filter(a =>
          !keyword ||
          [a.title, a.category, a.summary, a.file_name, ...a.tags].join('\n').toLowerCase().includes(keyword)
        )
    }
    return []
  }, [selectedDocumentId, selectedAssetId, documents, boundGlobalAssets, alreadyReferencedToIds, refTargetSearch])
  const workspaceTerminalSignature = useMemo(
    () =>
      workspaceProgresses
        .filter(item => item.phase === 'ready' || item.phase === 'failed')
        .map(item => `${item.document_id}:${item.phase}:${item.updated_at}`)
        .sort()
        .join('|'),
    [workspaceProgresses]
  )
  const assetTerminalSignature = useMemo(
    () =>
      Array.from(kbLibraryIndexProgresses.values())
        .filter(item => boundAssetIds.has(item.asset_id) && (item.phase === 'ready' || item.phase === 'failed'))
        .map(item => `${item.asset_id}:${item.phase}:${item.updated_at}`)
        .sort()
        .join('|'),
    [kbLibraryIndexProgresses, boundAssetIds]
  )

  useEffect(() => {
    if (!workspaceTerminalSignature) return
    const signature = workspaceTerminalSignature
    if (lastProgressTerminalRef.current === signature) return
    lastProgressTerminalRef.current = signature
    void refreshAll()
  }, [refreshAll, workspaceTerminalSignature])

  useEffect(() => {
    if (!assetTerminalSignature) return
    const signature = assetTerminalSignature
    if (lastAssetProgressTerminalRef.current === signature) return
    lastAssetProgressTerminalRef.current = signature
    void refreshAll()
  }, [refreshAll, assetTerminalSignature])

  const compactActionSx = {
    minHeight: 32,
    px: 1.25,
    fontSize: '0.82rem',
  }

  const readyCount = defaultListEntries.filter(entry => getEffectiveStatus(entry.item) === 'ready').length
  const failedCount = defaultListEntries.filter(entry => getEffectiveStatus(entry.item) === 'failed').length
  const addMenuOpen = Boolean(addMenuAnchorEl)
  const deleteDialogContent = selectedItem?.kind === 'asset'
    ? t('knowledge.dialogs.removeContent', { title: selectedAssetMeta?.title ?? selectedAsset?.title ?? '-' })
    : t('knowledge.dialogs.deleteContent', { title: selectedDocumentMeta?.title ?? selectedDocument?.title ?? '-' })
  const listSummaryLabel = searchResult
    ? t('knowledge.search.resultCount', { count: searchResult.document_total })
    : t('knowledge.list.total', { count: defaultListEntries.length })
  const neutralChipSx = CHIP_VARIANTS.base(true)
  const infoChipSx = CHIP_VARIANTS.getCustomColorChip(theme.palette.info.main, true)
  const primaryChipSx = CHIP_VARIANTS.getCustomColorChip(theme.palette.primary.main, true)
  const enabledChipSx = CHIP_VARIANTS.getCustomColorChip(theme.palette.success.main, true)
  const disabledChipSx = CHIP_VARIANTS.getCustomColorChip(theme.palette.text.secondary, true)
  const statusChipSx = (status: string) => CHIP_VARIANTS.getCustomColorChip(
    status === 'ready'
      ? theme.palette.success.main
      : status === 'failed'
        ? theme.palette.error.main
        : theme.palette.warning.main,
    true
  )
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
    maxHeight: 520,
    overflow: 'auto',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    fontSize: '0.92rem',
    lineHeight: 1.8,
    backgroundColor: alpha(theme.palette.background.default, 0.42),
  }

  const renderKBEntry = (entry: typeof defaultListEntries[0]) => {
    const item = entry.item
    const isSelected = selectedItem?.kind === entry.kind && selectedItem.id === entry.id
    const checked = selectedEntryKeys.has(getKnowledgeEntrySelectionKey(entry.kind, entry.id))
    const status =
      entry.kind === 'document'
        ? getDerivedStatuses(entry.item, progressByDocumentId.get(entry.id)).overallStatus
        : getEffectiveStatus(item)
    return (
      <ListItemButton
        key={`${entry.kind}-${entry.id}`}
        selected={isSelected}
        onClick={() => setSelectedItem({ kind: entry.kind, id: entry.id })}
        sx={{ alignItems: 'flex-start', py: 1.25 }}
      >
        <Checkbox
          checked={checked}
          size="small"
          tabIndex={-1}
          disableRipple
          onClick={event => event.stopPropagation()}
          onChange={() => toggleEntrySelection(entry.kind, entry.id)}
          sx={{
            pt: 0.25,
            pr: 1,
            alignSelf: 'flex-start',
            '& .MuiSvgIcon-root': { fontSize: 20 },
          }}
        />
        <ListItemText
          primary={
            <Stack spacing={0.75}>
              <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.35, minWidth: 0 }}>
                {item.title}
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                <Chip size="small" label={item.format.toUpperCase()} variant="outlined" sx={neutralChipSx} />
                {entry.kind === 'asset' && (
                  <Chip size="small" label={t('knowledge.list.globalBound')} variant="outlined" sx={infoChipSx} />
                )}
                <Chip
                  size="small"
                  label={item.is_enabled ? t('knowledge.actions.enabled') : t('knowledge.actions.disabled')}
                  sx={item.is_enabled ? enabledChipSx : disabledChipSx}
                />
                <Chip
                  size="small"
                  label={statusLabel(status)}
                  sx={statusChipSx(status)}
                />
              </Stack>
            </Stack>
          }
          secondary={
            <Stack spacing={0.5} sx={{ mt: 0.75 }}>
              <Typography variant="caption" color="text.secondary">
                {item.source_path}
              </Typography>
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
            </Stack>
          }
        />
      </ListItemButton>
    )
  }

  const renderCategoryNode = (node: KBCategoryTreeNode<(typeof defaultListEntries)[number]>) => {
    const isCollapsed = collapsedCategories.has(node.key)
    const categoryEntryKeys = node.allItems.map(entry => getKnowledgeEntrySelectionKey(entry.kind, entry.id))
    const selectedCount = categoryEntryKeys.filter(key => selectedEntryKeys.has(key)).length
    const categoryChecked = selectedCount > 0 && selectedCount === categoryEntryKeys.length
    const categoryIndeterminate = selectedCount > 0 && selectedCount < categoryEntryKeys.length
    const rows: JSX.Element[] = [
      <Box
        key={`cat-header-${node.key}`}
        onClick={() => toggleCategoryCollapse(node.key)}
        sx={{
          px: 2,
          py: 0.75,
          pl: 2 + node.depth * 3,
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          cursor: 'pointer',
          backgroundColor: alpha(theme.palette.primary.main, 0.03 + node.depth * 0.015),
          borderBottom: '1px solid',
          borderColor: 'divider',
          transition: 'background-color 0.15s',
          '&:hover': { backgroundColor: alpha(theme.palette.primary.main, 0.07 + node.depth * 0.01) },
        }}
      >
        <Checkbox
          checked={categoryChecked}
          indeterminate={categoryIndeterminate}
          onClick={event => event.stopPropagation()}
          onChange={() => toggleCategorySelection(categoryEntryKeys)}
          sx={{
            p: 0,
            mr: 0.5,
            color: 'primary.main',
            '&.Mui-checked, &.MuiCheckbox-indeterminate': {
              color: 'primary.main',
            },
            '& .MuiSvgIcon-root': {
              fontSize: 24,
            },
          }}
        />
        <ExpandMoreIcon
          sx={{
            fontSize: 16,
            color: 'text.secondary',
            flexShrink: 0,
            transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s',
          }}
        />
        <Typography
          variant="caption"
          noWrap
          sx={{
            fontWeight: node.depth === 0 ? 700 : 600,
            color: 'text.primary',
            flex: 1,
            minWidth: 0,
            fontSize: '0.74rem',
            letterSpacing: node.depth === 0 ? '0.04em' : 'normal',
          }}
        >
          {node.label || t('knowledge.list.uncategorized')}
        </Typography>
        <Chip
          size="small"
          label={selectedCount > 0 ? `${selectedCount}/${node.itemCount}` : node.itemCount}
          sx={{ height: 18, fontSize: '0.68rem', bgcolor: alpha(theme.palette.primary.main, 0.12), color: 'primary.main' }}
        />
      </Box>,
    ]

    if (isCollapsed) return rows

    node.children.forEach(child => {
      rows.push(...renderCategoryNode(child))
    })
    node.items.forEach(entry => {
      rows.push(renderKBEntry(entry))
    })
    return rows
  }

  const renderReuseAssetRow = (asset: KBAssetListItem) => {
    const checked = reuseAssetIdSet.has(asset.id)
    const isBound = asset.bound_workspaces.some(item => item.workspace_id === workspace.id)
    const status = getEffectiveStatus(asset)
    return (
      <ListItemButton
        key={asset.id}
        onClick={() => toggleReuseAsset(asset.id)}
        sx={{ alignItems: 'flex-start', py: 1.25 }}
      >
        <Checkbox
          checked={checked}
          tabIndex={-1}
          disableRipple
          onClick={event => event.stopPropagation()}
          sx={{ pt: 0.25, pr: 1 }}
        />
        <ListItemText
          primary={
            <Stack spacing={0.75}>
              <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.35 }}>
                {asset.title}
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                <Chip size="small" label={asset.format.toUpperCase()} variant="outlined" sx={neutralChipSx} />
                <Chip size="small" label={statusLabel(status)} sx={statusChipSx(status)} />
                {isBound && (
                  <Chip size="small" label={t('knowledge.list.globalBound')} variant="outlined" sx={infoChipSx} />
                )}
              </Stack>
            </Stack>
          }
          secondary={
            <Stack spacing={0.5} sx={{ mt: 0.75 }}>
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
                {asset.summary || t('knowledge.list.noPreview')}
              </Typography>
            </Stack>
          }
        />
      </ListItemButton>
    )
  }

  const renderReuseCategoryNode = (node: KBCategoryTreeNode<KBAssetListItem>) => {
    const isCollapsed = reuseCollapsedCategories.has(node.key)
    const categoryAssetIds = node.allItems.map(asset => asset.id)
    const selectedCount = categoryAssetIds.filter(id => reuseAssetIdSet.has(id)).length
    const categoryChecked = selectedCount > 0 && selectedCount === categoryAssetIds.length
    const categoryIndeterminate = selectedCount > 0 && selectedCount < categoryAssetIds.length
    const rows: JSX.Element[] = [
      <Box
        key={`reuse-cat-header-${node.key}`}
        onClick={() => toggleReuseCategoryCollapse(node.key)}
        sx={{
          px: 1.5,
          py: 0.75,
          pl: 1.5 + node.depth * 3,
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          cursor: 'pointer',
          backgroundColor: alpha(theme.palette.primary.main, 0.03 + node.depth * 0.015),
          borderBottom: '1px solid',
          borderColor: 'divider',
          transition: 'background-color 0.15s',
          '&:hover': { backgroundColor: alpha(theme.palette.primary.main, 0.07 + node.depth * 0.01) },
        }}
      >
        <Checkbox
          checked={categoryChecked}
          indeterminate={categoryIndeterminate}
          onClick={event => event.stopPropagation()}
          onChange={() => toggleReuseCategory(categoryAssetIds)}
          sx={{
            p: 0,
            mr: 0.5,
            color: 'primary.main',
            '&.Mui-checked, &.MuiCheckbox-indeterminate': {
              color: 'primary.main',
            },
            '& .MuiSvgIcon-root': {
              fontSize: 22,
            },
          }}
        />
        <ExpandMoreIcon
          sx={{
            fontSize: 16,
            color: 'text.secondary',
            flexShrink: 0,
            transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s',
          }}
        />
        <Typography
          variant="caption"
          noWrap
          sx={{
            fontWeight: node.depth === 0 ? 700 : 600,
            color: 'text.primary',
            flex: 1,
            minWidth: 0,
            fontSize: '0.74rem',
            letterSpacing: node.depth === 0 ? '0.04em' : 'normal',
          }}
        >
          {node.label || t('knowledge.list.uncategorized')}
        </Typography>
        <Chip
          size="small"
          label={selectedCount > 0 ? `${selectedCount}/${node.itemCount}` : node.itemCount}
          sx={{ height: 18, fontSize: '0.68rem', bgcolor: alpha(theme.palette.primary.main, 0.12), color: 'primary.main' }}
        />
      </Box>,
    ]

    if (isCollapsed) return rows

    node.children.forEach(child => {
      rows.push(...renderReuseCategoryNode(child))
    })
    node.items.forEach(asset => {
      rows.push(renderReuseAssetRow(asset))
    })
    return rows
  }

  return (
    <Box
      sx={{
        ...UNIFIED_TABLE_STYLES.tableLayoutContainer,
        flex: 1,
        minHeight: 0,
      }}
    >
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', flexShrink: 0 }}>
        <StatCard
          label={t('knowledge.stats.documents', { count: defaultListEntries.length })}
          value={defaultListEntries.length}
          icon={<FolderOpenIcon sx={{ fontSize: 20 }} />}
          color={theme.palette.primary.main}
        />
        <StatCard
          label={t('knowledge.stats.ready', { count: readyCount })}
          value={readyCount}
          icon={<CheckCircleIcon sx={{ fontSize: 20 }} />}
          color={theme.palette.success.main}
        />
        <StatCard
          label={t('knowledge.stats.failed', { count: failedCount })}
          value={failedCount}
          icon={<ErrorOutlineIcon sx={{ fontSize: 20 }} />}
          color={theme.palette.error.main}
        />
        <StatCard
          label={t('knowledge.stats.reusedGlobal', { count: boundGlobalAssets.length })}
          value={boundGlobalAssets.length}
          icon={<LibraryIcon sx={{ fontSize: 20 }} />}
          color={theme.palette.info.main}
        />
      </Box>

      <Card sx={{ ...CARD_VARIANTS.default.styles, mb: 2, flexShrink: 0 }}>
        <Box sx={{ px: 2, py: 1.25, display: 'flex', alignItems: 'center', gap: 1.25, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, flexWrap: 'wrap', flex: '1 1 460px', minWidth: 0 }}>
            <SearchField
              placeholder={t('knowledge.search.placeholder')}
              value={searchDraft}
              onChange={setSearchDraft}
              onClear={() => setSearchDraft('')}
              clearAriaLabel={t('knowledge.actions.clearSearch')}
              onKeyDown={event => {
                if (event.key === 'Enter' && searchDraft.trim()) {
                  searchMutation.mutate(searchDraft.trim())
                }
              }}
              sx={{ width: { xs: '100%', sm: 280, md: 340 }, maxWidth: '100%', flexShrink: 0 }}
            />
            <ActionButton
              size="small"
              tone="primary"
              sx={compactActionSx}
              onClick={() => searchMutation.mutate(searchDraft.trim())}
              disabled={!searchDraft.trim() || searchMutation.isPending}
            >
              {t('knowledge.actions.search')}
            </ActionButton>
            {searchResult && (
              <Tooltip title={t('knowledge.actions.clearSearch')}>
                <IconActionButton size="small" onClick={() => setSearchResult(null)}>
                  <ClearIcon fontSize="small" />
                </IconActionButton>
              </Tooltip>
            )}
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', marginLeft: 'auto' }}>
            <Typography variant="caption" color="text.secondary">
              {listSummaryLabel}
            </Typography>
            <Tooltip title={t('knowledge.actions.refresh')}>
              <IconActionButton size="small" onClick={() => void refreshAll()} disabled={documentsQuery.isLoading}>
                <RefreshIcon fontSize="small" />
              </IconActionButton>
            </Tooltip>
            <ActionButton
              size="small"
              tone="secondary"
              startIcon={<ReindexIcon />}
              onClick={() => reindexAllMutation.mutate()}
              disabled={reindexAllMutation.isPending}
            >
              {t('knowledge.actions.reindexAll')}
            </ActionButton>
            <KBBatchActionsButton
              label={t('knowledge.actions.batchActions', { count: selectedEntryCount })}
              disabled={
                selectedEntryCount === 0 ||
                bulkDeleteSelectedMutation.isPending ||
                bulkReindexSelectedMutation.isPending ||
                bulkDisableSelectedMutation.isPending
              }
              actions={[
                {
                  key: 'delete',
                  label: t('knowledge.actions.bulkDeleteSelected', { count: selectedEntryCount }),
                  onClick: () => setBulkDeleteSelectedOpen(true),
                  disabled:
                    selectedEntryCount === 0 ||
                    bulkDeleteSelectedMutation.isPending ||
                    bulkReindexSelectedMutation.isPending ||
                    bulkDisableSelectedMutation.isPending,
                },
                {
                  key: 'reindex',
                  label: t('knowledge.actions.bulkReindexSelected', { count: selectedEntryCount }),
                  onClick: () =>
                    bulkReindexSelectedMutation.mutate({
                      documentIds: selectedDocumentIds,
                      assetIds: selectedAssetIds,
                    }),
                  disabled:
                    selectedEntryCount === 0 ||
                    bulkDeleteSelectedMutation.isPending ||
                    bulkReindexSelectedMutation.isPending ||
                    bulkDisableSelectedMutation.isPending,
                },
                {
                  key: 'disable-index',
                  label: t('knowledge.actions.bulkDisableSelected', {
                    count: selectedEnabledDocumentIds.length + selectedEnabledAssetIds.length,
                  }),
                  onClick: () =>
                    bulkDisableSelectedMutation.mutate({
                      documentIds: selectedEnabledDocumentIds,
                      assetIds: selectedEnabledAssetIds,
                    }),
                  disabled:
                    selectedEnabledDocumentIds.length + selectedEnabledAssetIds.length === 0 ||
                    bulkDeleteSelectedMutation.isPending ||
                    bulkReindexSelectedMutation.isPending ||
                    bulkDisableSelectedMutation.isPending,
                },
              ]}
            />
            <ActionButton
              size="small"
              tone="primary"
              startIcon={<AddIcon />}
              endIcon={<ArrowDropDownIcon />}
              onClick={handleAddMenuOpen}
              disabled={globalAssetsQuery.isLoading}
            >
              {t('knowledge.actions.addFile')}
            </ActionButton>
            <Menu
              anchorEl={addMenuAnchorEl}
              open={addMenuOpen}
              onClose={handleAddMenuClose}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            >
              <MenuItem onClick={handleOpenUploadDialog}>{t('knowledge.actions.uploadFile')}</MenuItem>
              <MenuItem onClick={handleOpenBatchUploadDialog}>{t('knowledge.actions.batchUpload')}</MenuItem>
              <MenuItem onClick={handleOpenCreateDialog}>{t('knowledge.actions.createText')}</MenuItem>
              <MenuItem onClick={handleReuseDialogOpen}>{t('knowledge.actions.reuseGlobal')}</MenuItem>
            </Menu>
          </Box>
        </Box>
      </Card>

      {searchResult?.next_action_hint && (
        <Alert severity="info" sx={{ mb: 2, flexShrink: 0 }}>
          {searchResult.next_action_hint}
        </Alert>
      )}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: '1fr',
          gap: 2,
          flex: 1,
          minHeight: 0,
          pb: 0.5,
        }}
      >
        <Paper
          sx={{
            ...UNIFIED_TABLE_STYLES.tableContentContainer,
            minWidth: 0,
          }}
        >
          <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {listTitle}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {listSummaryLabel}
              </Typography>
            </Box>
            {!hasSearchResult && (
              <Stack direction="row" spacing={0.25}>
                <Tooltip title={t('knowledge.list.viewFlat')}>
                  <span>
                    <IconActionButton
                      size="small"
                      onClick={() => setListView('flat')}
                      sx={{ color: listView === 'flat' ? 'primary.main' : 'text.secondary' }}
                    >
                      <ViewListIcon sx={{ fontSize: 18 }} />
                    </IconActionButton>
                  </span>
                </Tooltip>
                <Tooltip title={t('knowledge.list.viewGrouped')}>
                  <span>
                    <IconActionButton
                      size="small"
                      onClick={() => setListView('grouped')}
                      sx={{ color: listView === 'grouped' ? 'primary.main' : 'text.secondary' }}
                    >
                      <GroupedViewIcon sx={{ fontSize: 18 }} />
                    </IconActionButton>
                  </span>
                </Tooltip>
                <Tooltip title={t('knowledge.list.viewGraph')}>
                  <span>
                    <IconActionButton
                      size="small"
                      onClick={() => setListView('graph')}
                      sx={{ color: listView === 'graph' ? 'primary.main' : 'text.secondary' }}
                    >
                      <GraphViewIcon sx={{ fontSize: 18 }} />
                    </IconActionButton>
                  </span>
                </Tooltip>
              </Stack>
            )}
          </Box>
          <Divider />
          {documentsQuery.isLoading || (!hasSearchResult && globalAssetsQuery.isLoading) ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
              <CircularProgress size={28} />
            </Box>
          ) : listView === 'graph' && !hasSearchResult ? (
            <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden', height: '100%' }}>
              <KBGraphDialog
                documents={documents}
                boundGlobalAssets={boundGlobalAssets}
                progressByDocumentId={progressByDocumentId}
                references={graphReferenceEdges}
                onOpenDocument={(kind, id) => {
                  setSelectedItem({ kind, id })
                }}
              />
            </Box>
          ) : (hasSearchResult ? searchDocuments.length > 0 : defaultListEntries.length > 0) ? (
            <Box sx={UNIFIED_TABLE_STYLES.tableViewport}>
              <List sx={{ py: 0 }}>
                {hasSearchResult
                  ? searchDocuments.map(item => {
                      const documentId = item.document_id
                      const isSelected =
                        selectedItem?.kind === item.source_kind && selectedItem.id === documentId
                      return (
                        <ListItemButton
                          key={`${item.source_kind}-${documentId}-search-doc`}
                          selected={isSelected}
                          onClick={() => setSelectedItem({ kind: item.source_kind, id: documentId })}
                          sx={{ alignItems: 'flex-start', py: 1.25 }}
                        >
                          <ListItemText
                            primary={
                              <Stack spacing={0.75}>
                                <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.35, minWidth: 0 }}>
                                  {item.title}
                                </Typography>
                                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                                  <Chip size="small" label={item.format.toUpperCase()} variant="outlined" sx={neutralChipSx} />
                                  {item.source_kind === 'asset' && (
                                    <Chip size="small" label={t('knowledge.list.globalBound')} variant="outlined" sx={infoChipSx} />
                                  )}
                                  {item.source_kind === 'document' && suggestedDocumentIds.has(documentId) && (
                                    <Chip size="small" label="Suggested" variant="outlined" sx={primaryChipSx} />
                                  )}
                                  <Chip size="small" label={statusLabel('ready')} sx={statusChipSx('ready')} />
                                </Stack>
                              </Stack>
                            }
                            secondary={
                              <Stack spacing={0.5} sx={{ mt: 0.75 }}>
                                <Typography variant="caption" color="text.secondary">
                                  {item.source_path}
                                </Typography>
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
                                  {item.best_match_excerpt || t('knowledge.list.noPreview')}
                                </Typography>
                              </Stack>
                            }
                          />
                        </ListItemButton>
                      )
                    })
                  : listView === 'grouped'
                    ? categorizedEntries.flatMap(renderCategoryNode)
                    : defaultListEntries.map(renderKBEntry)}
              </List>
            </Box>
          ) : (
            <Box sx={{ px: 2, py: 4 }}>
              <Alert severity="info">
                {searchResult ? t('knowledge.search.empty') : t('knowledge.empty')}
              </Alert>
            </Box>
          )}
        </Paper>

      </Box>

      {/* 文档/资产详情弹窗 */}
      <Dialog
        open={selectedItem !== null}
        onClose={() => setSelectedItem(null)}
        fullWidth
        maxWidth="lg"
        scroll="paper"
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, pr: 1 }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.35, wordBreak: 'break-word' }} noWrap>
              {selectedItem?.kind === 'document' && selectedDocumentMeta
                ? selectedDocumentMeta.title
                : selectedAssetMeta?.title ?? ''}
            </Typography>
          </Box>
          <IconButton size="small" onClick={() => setSelectedItem(null)} sx={{ flexShrink: 0 }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>

        <DialogContent dividers>
          {selectedItem?.kind === 'document' && selectedDocumentMeta ? (
            <Stack spacing={2}>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
                <Chip size="small" label={selectedDocumentMeta.format.toUpperCase()} variant="outlined" sx={neutralChipSx} />
                {selectedDerivedStatuses != null && selectedDerivedStatuses.extractStatus === selectedDerivedStatuses.syncStatus ? (
                  <Chip size="small" label={statusLabel(selectedDerivedStatuses.syncStatus)} sx={statusChipSx(selectedDerivedStatuses.syncStatus)} />
                ) : (
                  <>
                    <Chip
                      size="small"
                      label={t('knowledge.badges.extract', { status: statusLabel(selectedDerivedStatuses?.extractStatus ?? selectedDocumentMeta.extract_status) })}
                      variant="outlined"
                      sx={statusChipSx(selectedDerivedStatuses?.extractStatus ?? selectedDocumentMeta.extract_status)}
                    />
                    <Chip
                      size="small"
                      label={t('knowledge.badges.sync', { status: statusLabel(selectedDerivedStatuses?.syncStatus ?? selectedDocumentMeta.sync_status) })}
                      sx={statusChipSx(selectedDerivedStatuses?.syncStatus ?? selectedDocumentMeta.sync_status)}
                    />
                  </>
                )}
              </Stack>
              <Typography variant="body2" color="text.secondary">
                {selectedDocumentMeta.summary || t('knowledge.detail.noSummary')}
              </Typography>

              {selectedProgress && (
                <Paper sx={detailSectionSx}>
                  <Stack spacing={1} sx={{ p: 2 }}>
                    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1}>
                      <Typography variant="subtitle2">{t('knowledge.progress.title')}</Typography>
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
                        ? t('knowledge.progress.detail', { processed: selectedProgress.processed_chunks, total: selectedProgress.total_chunks })
                        : t('knowledge.progress.pending')}
                    </Typography>
                    {selectedProgress.error_summary && (
                      <Alert severity="error">{selectedProgress.error_summary}</Alert>
                    )}
                  </Stack>
                </Paper>
              )}

              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {selectedDocumentMeta.tags.map(tag => (
                  <Chip key={tag} size="small" label={tag} variant="outlined" sx={neutralChipSx} />
                ))}
                {!selectedDocumentMeta.tags.length && (
                  <Chip size="small" label={t('knowledge.detail.noTags')} variant="outlined" sx={neutralChipSx} />
                )}
              </Stack>

              <Paper sx={detailSectionSx}>
                <Stack spacing={1.25} sx={{ p: 2 }}>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <LinkIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                    <Typography variant="subtitle2">{t('knowledge.references.title')}</Typography>
                  </Stack>
                  <ReferenceGraph
                    currentTitle={selectedDocumentMeta.title}
                    referencesTo={activeReferences.references_to}
                    referencedBy={activeReferences.referenced_by}
                    onNavigate={id => setSelectedItem({ kind: 'document', id })}
                    onAdd={() => { setEditingRef(null); setRefTargetSearch(''); setRefDescription(''); setRefDialogOpen(true) }}
                    onEdit={ref => { setEditingRef(ref); setRefDescription(ref.description); setRefTargetSearch(''); setRefDialogOpen(true) }}
                    onRemove={id => removeReferenceMutation.mutate(id)}
                    disabled={removeReferenceMutation.isPending}
                  />
                </Stack>
              </Paper>

              <Paper sx={detailSectionSx}>
                <Stack spacing={1.25} sx={{ p: 2 }}>
                  <Typography variant="subtitle2">{t('knowledge.detail.metadata')}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
                    {selectedDocumentMeta.source_path}
                  </Typography>
                  <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                    {selectedDocumentMeta.category && (
                      <Chip size="small" label={`${t('knowledge.detail.category')} · ${selectedDocumentMeta.category}`} variant="outlined" sx={neutralChipSx} />
                    )}
                    <Chip size="small" label={`${t('knowledge.detail.fileName')} · ${selectedDocumentMeta.file_name}`} variant="outlined" sx={neutralChipSx} />
                    <Chip size="small" label={`${t('knowledge.detail.fileSize')} · ${formatFileSize(selectedDocumentMeta.file_size)}`} variant="outlined" sx={neutralChipSx} />
                    <Chip size="small" label={`${t('knowledge.detail.chunkCount')} · ${selectedDocumentMeta.chunk_count}`} variant="outlined" sx={neutralChipSx} />
                    <Chip size="small" label={`${t('knowledge.detail.updatedAt')} · ${formatDateTime(selectedDocumentMeta.update_time)}`} variant="outlined" sx={neutralChipSx} />
                    <Chip size="small" label={`${t('knowledge.detail.indexedAt')} · ${formatDateTime(selectedDocumentMeta.last_indexed_at)}`} variant="outlined" sx={neutralChipSx} />
                  </Stack>
                  {selectedDocumentMeta.last_error && <Alert severity="error">{selectedDocumentMeta.last_error}</Alert>}
                </Stack>
              </Paper>

              <Paper sx={detailSectionSx}>
                <Box sx={{ px: 2, pt: 1.5 }}>
                  <Typography variant="subtitle2">{t('knowledge.detail.preview')}</Typography>
                </Box>
                <Divider />
                <Box sx={previewBodySx}>
                  {detailQuery.isLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
                      <CircularProgress size={28} />
                    </Box>
                  ) : preview ? (
                    <Typography component="pre" variant="body2" sx={{ m: 0, fontFamily: 'inherit', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.8 }}>
                      {preview}
                    </Typography>
                  ) : (
                    t('knowledge.preview.empty')
                  )}
                </Box>
              </Paper>
            </Stack>
          ) : selectedAssetMeta ? (
            <Stack spacing={2}>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
                <Chip size="small" label={selectedAssetMeta.format.toUpperCase()} variant="outlined" sx={neutralChipSx} />
                <Chip size="small" label={t('knowledge.list.globalBound')} variant="outlined" sx={infoChipSx} />
                <Chip size="small" label={statusLabel(getEffectiveStatus(selectedAssetMeta))} sx={statusChipSx(getEffectiveStatus(selectedAssetMeta))} />
              </Stack>
              <Typography variant="body2" color="text.secondary">
                {selectedAssetMeta.summary || t('knowledge.detail.noSummary')}
              </Typography>

              {selectedAssetProgress && (
                <Paper sx={detailSectionSx}>
                  <Stack spacing={1} sx={{ p: 2 }}>
                    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1}>
                      <Typography variant="subtitle2">{t('knowledge.progress.title')}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {`${kbProgressLabel(selectedAssetProgress.phase, t)} · ${selectedAssetProgress.progress_percent}%`}
                      </Typography>
                    </Stack>
                    <LinearProgress
                      variant="determinate"
                      value={selectedAssetProgress.progress_percent}
                      color={selectedAssetProgress.phase === 'failed' ? 'error' : selectedAssetProgress.phase === 'ready' ? 'success' : 'primary'}
                      sx={{ height: 8, borderRadius: 999 }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {selectedAssetProgress.total_chunks > 0
                        ? t('knowledge.progress.detail', { processed: selectedAssetProgress.processed_chunks, total: selectedAssetProgress.total_chunks })
                        : t('knowledge.progress.pending')}
                    </Typography>
                    {selectedAssetProgress.error_summary && (
                      <Alert severity="error">{selectedAssetProgress.error_summary}</Alert>
                    )}
                  </Stack>
                </Paper>
              )}

              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {selectedAssetMeta.tags.map(tag => (
                  <Chip key={tag} size="small" label={tag} variant="outlined" sx={neutralChipSx} />
                ))}
                {!selectedAssetMeta.tags.length && (
                  <Chip size="small" label={t('knowledge.detail.noTags')} variant="outlined" sx={neutralChipSx} />
                )}
              </Stack>

              <Paper sx={detailSectionSx}>
                <Stack spacing={1.25} sx={{ p: 2 }}>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <LinkIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                    <Typography variant="subtitle2">{t('knowledge.references.title')}</Typography>
                  </Stack>
                  <ReferenceGraph
                    currentTitle={selectedAssetMeta.title}
                    referencesTo={activeReferences.references_to}
                    referencedBy={activeReferences.referenced_by}
                    onNavigate={id => setSelectedItem({ kind: 'asset', id })}
                    onAdd={() => { setEditingRef(null); setRefTargetSearch(''); setRefDescription(''); setRefDialogOpen(true) }}
                    onEdit={ref => { setEditingRef(ref); setRefDescription(ref.description); setRefTargetSearch(''); setRefDialogOpen(true) }}
                    onRemove={id => removeReferenceMutation.mutate(id)}
                    disabled={removeReferenceMutation.isPending}
                  />
                </Stack>
              </Paper>

              <Paper sx={detailSectionSx}>
                <Stack spacing={1.25} sx={{ p: 2 }}>
                  <Typography variant="subtitle2">{t('knowledge.detail.metadata')}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
                    {selectedAssetMeta.source_path}
                  </Typography>
                  <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                    {selectedAssetMeta.category && (
                      <Chip size="small" label={`${t('knowledge.detail.category')} · ${selectedAssetMeta.category}`} variant="outlined" sx={neutralChipSx} />
                    )}
                    <Chip size="small" label={`${t('knowledge.detail.fileName')} · ${selectedAssetMeta.file_name}`} variant="outlined" sx={neutralChipSx} />
                    <Chip size="small" label={`${t('knowledge.detail.fileSize')} · ${formatFileSize(selectedAssetMeta.file_size)}`} variant="outlined" sx={neutralChipSx} />
                    <Chip size="small" label={`${t('knowledge.detail.chunkCount')} · ${selectedAssetMeta.chunk_count}`} variant="outlined" sx={neutralChipSx} />
                    <Chip size="small" label={`${t('knowledge.detail.updatedAt')} · ${formatDateTime(selectedAssetMeta.update_time)}`} variant="outlined" sx={neutralChipSx} />
                    <Chip size="small" label={`${t('knowledge.detail.indexedAt')} · ${formatDateTime(selectedAssetMeta.last_indexed_at)}`} variant="outlined" sx={neutralChipSx} />
                  </Stack>
                  {selectedAssetMeta.last_error && <Alert severity="error">{selectedAssetMeta.last_error}</Alert>}
                </Stack>
              </Paper>

              <Paper sx={detailSectionSx}>
                <Box sx={{ px: 2, pt: 1.5 }}>
                  <Typography variant="subtitle2">{t('knowledge.detail.preview')}</Typography>
                </Box>
                <Divider />
                <Box sx={previewBodySx}>
                  {assetDetailQuery.isLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
                      <CircularProgress size={28} />
                    </Box>
                  ) : preview ? (
                    <Typography component="pre" variant="body2" sx={{ m: 0, fontFamily: 'inherit', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.8 }}>
                      {preview}
                    </Typography>
                  ) : (
                    t('knowledge.preview.empty')
                  )}
                </Box>
              </Paper>
            </Stack>
          ) : (
            <Alert severity="warning">{t('knowledge.detail.loadFailed')}</Alert>
          )}
        </DialogContent>

        <DialogActions sx={{ px: 2, py: 1.5, gap: 1, flexWrap: 'wrap' }}>
          {selectedItem?.kind === 'document' && selectedDocumentMeta ? (
            <>
              <ActionButton
                tone={selectedDocumentMeta.is_enabled ? 'secondary' : 'primary'}
                onClick={() => toggleEnabledMutation.mutate({ documentId: selectedDocumentMeta.id, isEnabled: !selectedDocumentMeta.is_enabled })}
                disabled={toggleEnabledMutation.isPending}
                sx={compactActionSx}
              >
                {selectedDocumentMeta.is_enabled ? t('knowledge.actions.disable') : t('knowledge.actions.enable')}
              </ActionButton>
              <ActionButton
                tone="secondary"
                startIcon={<ReindexIcon />}
                onClick={() => reindexMutation.mutate(selectedDocumentMeta.id)}
                disabled={reindexMutation.isPending}
                sx={compactActionSx}
              >
                {t('knowledge.actions.reindex')}
              </ActionButton>
              <ActionButton
                tone="secondary"
                startIcon={<EditIcon />}
                sx={compactActionSx}
                onClick={() => {
                  setEditMetaForm({
                    title: selectedDocumentMeta.title,
                    category: selectedDocumentMeta.category ?? '',
                    tagsInput: (selectedDocumentMeta.tags ?? []).join(', '),
                    summary: selectedDocumentMeta.summary ?? '',
                  })
                  setEditMetaOpen(true)
                }}
              >
                {t('knowledge.actions.edit')}
              </ActionButton>
              <ActionButton tone="secondary" startIcon={<DownloadIcon />} onClick={handleDownloadRaw} sx={compactActionSx}>
                {t('knowledge.actions.downloadRaw')}
              </ActionButton>
              <ActionButton tone="danger" startIcon={<DeleteIcon />} onClick={() => setDeleteOpen(true)} sx={compactActionSx}>
                {t('knowledge.actions.delete')}
              </ActionButton>
            </>
          ) : selectedAssetMeta ? (
            <>
              <ActionButton
                tone={selectedAssetMeta.is_enabled ? 'secondary' : 'primary'}
                onClick={() => toggleAssetEnabledMutation.mutate({ assetId: selectedAssetMeta.id, isEnabled: !selectedAssetMeta.is_enabled })}
                disabled={toggleAssetEnabledMutation.isPending}
                sx={compactActionSx}
              >
                {selectedAssetMeta.is_enabled ? t('knowledge.actions.disable') : t('knowledge.actions.enable')}
              </ActionButton>
              <ActionButton
                tone="secondary"
                startIcon={<ReindexIcon />}
                onClick={() => reindexAssetMutation.mutate(selectedAssetMeta.id)}
                disabled={reindexAssetMutation.isPending}
                sx={compactActionSx}
              >
                {t('knowledge.actions.reindex')}
              </ActionButton>
              <ActionButton
                tone="secondary"
                startIcon={<EditIcon />}
                sx={compactActionSx}
                onClick={() => {
                  setEditMetaForm({
                    title: selectedAssetMeta.title,
                    category: selectedAssetMeta.category ?? '',
                    tagsInput: (selectedAssetMeta.tags ?? []).join(', '),
                    summary: selectedAssetMeta.summary ?? '',
                  })
                  setEditMetaOpen(true)
                }}
              >
                {t('knowledge.actions.edit')}
              </ActionButton>
              <ActionButton tone="secondary" startIcon={<DownloadIcon />} onClick={handleDownloadRaw} sx={compactActionSx}>
                {t('knowledge.actions.downloadRaw')}
              </ActionButton>
              <ActionButton tone="danger" startIcon={<DeleteIcon />} onClick={() => setDeleteOpen(true)} sx={compactActionSx}>
                {t('knowledge.actions.delete')}
              </ActionButton>
            </>
          ) : null}
          <Box sx={{ flex: 1 }} />
          <ActionButton onClick={() => setSelectedItem(null)} sx={compactActionSx}>
            {t('knowledge.actions.close')}
          </ActionButton>
        </DialogActions>
      </Dialog>

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
          <ActionButton onClick={() => setCreateOpen(false)} disabled={createMutation.isPending}>
            {t('knowledge.actions.cancel')}
          </ActionButton>
          <ActionButton tone="primary" onClick={handleCreateSubmit} disabled={createMutation.isPending || !createForm.title.trim() || !createForm.content.trim()}>
            {createMutation.isPending ? t('knowledge.actions.creating') : t('knowledge.actions.create')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      {/* 批量上传队列对话框 */}
      <Dialog
        open={batchUploadOpen}
        onClose={() => { setBatchUploadOpen(false); setBatchQueue([]) }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {batchTarget === 'workspace'
            ? t('knowledge.dialogs.dirImportTitle')
            : t('knowledge.dialogs.batchUploadTitle')}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {batchQueue.length === 0 ? (
              <Stack spacing={1.5}>
                <ActionButton
                  tone="secondary"
                  startIcon={<FolderOpenIcon />}
                  onClick={() => batchInputRef.current?.click()}
                >
                  {t('knowledge.actions.chooseFiles')}
                </ActionButton>
                <Divider>{t('knowledge.actions.or')}</Divider>
                <ActionButton
                  tone="secondary"
                  startIcon={<ImportFolderIcon />}
                  onClick={() => dirInputRef.current?.click()}
                >
                  {t('knowledge.actions.importFolder')}
                </ActionButton>
                <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
                  {t('knowledge.form.dirImportHint')}
                </Typography>
              </Stack>
            ) : (
              <>
                {batchTarget === 'workspace' && (
                  <Alert severity="info" icon={<ImportFolderIcon fontSize="inherit" />}>
                    {t('knowledge.form.dirImportModeHint')}
                  </Alert>
                )}
                <Stack spacing={0.5}>
                  {batchQueue.map(item => (
                    <Box key={item.id} sx={{ borderRadius: 1, bgcolor: 'action.hover', overflow: 'hidden' }}>
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ py: 0.75, px: 1 }}>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography variant="body2" noWrap title={item.file.name} sx={{ fontWeight: item.title !== item.file.name.replace(/\.[^.]+$/, '') ? 500 : undefined }}>
                            {item.title || item.file.name}
                          </Typography>
                          {item.source_path ? (
                            <Typography variant="caption" color="text.secondary" noWrap title={item.source_path}>
                              {item.source_path}
                            </Typography>
                          ) : (item.category || item.tags) ? (
                            <Typography variant="caption" color="text.secondary" noWrap>
                              {[item.category, item.tags].filter(Boolean).join(' · ')}
                            </Typography>
                          ) : null}
                          {item.status === 'uploading' && (
                            <LinearProgress variant="determinate" value={item.uploadProgress} sx={{ mt: 0.5, height: 3, borderRadius: 999 }} />
                          )}
                          {item.status === 'error' && item.errorMessage && (
                            <Typography variant="caption" color="error">{item.errorMessage}</Typography>
                          )}
                        </Box>
                        <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
                          {formatFileSize(item.file.size)}
                        </Typography>
                        {item.status === 'waiting' && (
                          <>
                            <Tooltip title={t('knowledge.batchStatus.edit')}>
                              <span>
                                <IconActionButton
                                  size="small"
                                  onClick={() => setExpandedBatchItemId(prev => prev === item.id ? null : item.id)}
                                >
                                  <SearchIcon sx={{ fontSize: 14 }} />
                                </IconActionButton>
                              </span>
                            </Tooltip>
                            <Tooltip title={t('knowledge.actions.removeFromQueue')}>
                              <span>
                                <IconActionButton
                                  size="small"
                                  onClick={() => removeBatchQueueItem(item.id)}
                                >
                                  <DeleteIcon sx={{ fontSize: 14 }} />
                                </IconActionButton>
                              </span>
                            </Tooltip>
                          </>
                        )}
                        {item.status === 'uploading' && <CircularProgress size={14} />}
                        {item.status === 'indexing' && <CircularProgress size={14} color="warning" />}
                        {item.status === 'done' && <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />}
                        {item.status === 'error' && <ErrorOutlineIcon sx={{ fontSize: 16, color: 'error.main' }} />}
                      </Stack>
                      {expandedBatchItemId === item.id && item.status === 'waiting' && (
                        <Box sx={{ px: 1, pb: 1 }}>
                          <Stack spacing={1}>
                            <TextField
                              size="small"
                              label={t('knowledge.form.title')}
                              value={item.title}
                              onChange={e => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, title: e.target.value } : i))}
                              fullWidth
                            />
                            <TextField
                              size="small"
                              label={t('knowledge.form.category')}
                              value={item.category}
                              onChange={e => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, category: e.target.value } : i))}
                              fullWidth
                            />
                            <TextField
                              size="small"
                              label={t('knowledge.form.tags')}
                              value={item.tags}
                              onChange={e => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, tags: e.target.value } : i))}
                              placeholder={t('knowledge.form.tagsPlaceholder')}
                              fullWidth
                            />
                            <TextField
                              size="small"
                              label={t('knowledge.form.summary')}
                              value={item.summary}
                              onChange={e => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, summary: e.target.value } : i))}
                              fullWidth
                            />
                          </Stack>
                        </Box>
                      )}
                    </Box>
                  ))}
                </Stack>
                {batchQueue.every(i => i.status === 'waiting') && (
                  batchTarget === 'workspace' ? (
                    <ActionButton
                      tone="secondary"
                      startIcon={<ImportFolderIcon />}
                      onClick={() => dirInputRef.current?.click()}
                    >
                      {t('knowledge.actions.reChooseFolder')}
                    </ActionButton>
                  ) : (
                    <ActionButton
                      tone="secondary"
                      startIcon={<FolderOpenIcon />}
                      onClick={() => batchInputRef.current?.click()}
                    >
                      {t('knowledge.actions.reChooseFiles')}
                    </ActionButton>
                  )
                )}
              </>
            )}
            <Alert severity="info">
              {t('knowledge.form.supportedFormats', { formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', ') })}
            </Alert>
            <input
              ref={batchInputRef}
              type="file"
              hidden
              multiple
              onChange={handleBatchFileChange}
              accept=".md,.txt,.html,.htm,.json,.yaml,.yml,.csv,.xlsx,.pdf,.docx"
            />
            <input
              ref={dirInputRef}
              type="file"
              hidden
              // @ts-expect-error webkitdirectory is non-standard but widely supported
              webkitdirectory=""
              onChange={handleDirFileChange}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => { setBatchUploadOpen(false); setBatchQueue([]) }}>
            {t('knowledge.actions.cancel')}
          </ActionButton>
          {batchQueue.length > 0 && batchQueue.some(i => i.status === 'waiting') && (
            <ActionButton
              tone="primary"
              onClick={() => startBatchUpload(batchQueue.filter(i => i.status === 'waiting'), batchTarget)}
            >
              {t('knowledge.actions.startUpload', { count: batchQueue.filter(i => i.status === 'waiting').length })}
            </ActionButton>
          )}
        </DialogActions>
      </Dialog>

      {/* 批量上传悬浮进度面板 */}
      {batchPanelVisible && (
        <Box
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: 340,
            zIndex: 1400,
            boxShadow: 6,
            borderRadius: 2,
            overflow: 'hidden',
            bgcolor: 'background.paper',
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            sx={{ px: 2, py: 1.25, bgcolor: 'primary.main' }}
          >
            <Typography variant="subtitle2" sx={{ flex: 1, color: 'primary.contrastText' }}>
              {batchRunning
                ? t('knowledge.batchPanel.inProgress', { done: batchQueue.filter(i => i.status === 'done' || i.status === 'error').length, total: batchQueue.length })
                : t('knowledge.batchPanel.done', { total: batchQueue.length, failed: batchQueue.filter(i => i.status === 'error').length })}
            </Typography>
            {batchRunning ? (
              <Stack direction="row" spacing={0.75}>
                <ActionButton
                  size="small"
                  tone="secondary"
                  onClick={requestBatchCancel}
                  disabled={batchCancelRequested}
                  sx={{
                    minHeight: 28,
                    px: 1,
                    color: 'primary.contrastText',
                    borderColor: 'rgba(255,255,255,0.35)',
                    backgroundColor: 'rgba(255,255,255,0.08)',
                    '&:hover': { backgroundColor: 'rgba(255,255,255,0.16)' },
                  }}
                >
                  {batchCancelRequested ? t('knowledge.actions.canceling') : t('knowledge.actions.cancelUpload')}
                </ActionButton>
              </Stack>
            ) : (
              <Tooltip title={t('knowledge.actions.close')}>
                <span>
                  <IconActionButton size="small" sx={{ color: 'primary.contrastText', '&:hover': { bgcolor: 'rgba(255,255,255,0.15)' } }} onClick={() => setBatchPanelVisible(false)}>
                    <ClearIcon sx={{ fontSize: 16 }} />
                  </IconActionButton>
                </span>
              </Tooltip>
            )}
          </Stack>
          <Box sx={{ maxHeight: 320, overflowY: 'auto' }}>
            {batchQueue.map(item => (
              <Stack key={item.id} spacing={0.25} sx={{ px: 2, py: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="body2" noWrap title={item.title || item.file.name}>
                      {item.title || item.file.name}
                    </Typography>
                    {item.category && (
                      <Typography variant="caption" color="text.secondary" noWrap>{item.category}</Typography>
                    )}
                  </Box>
                  {item.status === 'waiting' && (
                    <>
                      <Typography variant="caption" color="text.disabled">{t('knowledge.batchStatus.waiting')}</Typography>
                      <Tooltip title={t('knowledge.actions.removeFromQueue')}>
                        <span>
                          <IconActionButton size="small" onClick={() => removeBatchQueueItem(item.id)}>
                            <DeleteIcon sx={{ fontSize: 14 }} />
                          </IconActionButton>
                        </span>
                      </Tooltip>
                    </>
                  )}
                  {item.status === 'uploading' && <CircularProgress size={14} />}
                  {item.status === 'indexing' && <CircularProgress size={14} color="warning" />}
                  {item.status === 'done' && <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />}
                  {item.status === 'error' && <ErrorOutlineIcon sx={{ fontSize: 16, color: 'error.main' }} />}
                </Stack>
                {item.status === 'uploading' && (
                  <LinearProgress variant="determinate" value={item.uploadProgress} sx={{ height: 3, borderRadius: 999 }} />
                )}
                {item.status === 'indexing' && (
                  <LinearProgress color="warning" sx={{ height: 3, borderRadius: 999 }} />
                )}
                {item.status === 'error' && item.errorMessage && (
                  <Typography variant="caption" color="error" noWrap title={item.errorMessage}>{item.errorMessage}</Typography>
                )}
              </Stack>
            ))}
          </Box>
        </Box>
      )}

      <Dialog
        open={bulkDeleteSelectedOpen}
        onClose={() => !bulkDeleteSelectedMutation.isPending && setBulkDeleteSelectedOpen(false)}
      >
        <DialogTitle>{t('knowledge.dialogs.bulkDeleteSelectedTitle')}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {t('knowledge.dialogs.bulkDeleteSelectedContent', {
              count: selectedEntryCount,
              documentCount: selectedDocumentIds.length,
              assetCount: selectedAssetIds.length,
            })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setBulkDeleteSelectedOpen(false)} disabled={bulkDeleteSelectedMutation.isPending}>
            {t('knowledge.actions.cancel')}
          </ActionButton>
          <ActionButton
            tone="danger"
            startIcon={<DeleteIcon />}
            onClick={() => bulkDeleteSelectedMutation.mutate({ documentIds: selectedDocumentIds, assetIds: selectedAssetIds })}
            disabled={selectedEntryCount === 0 || bulkDeleteSelectedMutation.isPending}
          >
            {t('knowledge.actions.bulkDeleteSelected', { count: selectedEntryCount })}
          </ActionButton>
        </DialogActions>
      </Dialog>

      <Dialog
        open={uploadOpen}
        onClose={() => {
          if (uploadMutation.isPending) return
          setUploadFile(null)
          setUploadTitle('')
          setUploadCategory('')
          setUploadSummary('')
          setUploadTagsInput('')
          setUploadEnabled(true)
          setUploadProgress(0)
          setUploadOpen(false)
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>{t('knowledge.dialogs.uploadTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <ActionButton tone="secondary" startIcon={<FolderOpenIcon />} onClick={() => uploadInputRef.current?.click()}>
              {uploadFile ? uploadFile.name : t('knowledge.actions.chooseFile')}
            </ActionButton>
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
            <ActionButton
              tone={uploadEnabled ? 'primary' : 'secondary'}
              onClick={() => setUploadEnabled(prev => !prev)}
              startIcon={<VisibilityIcon />}
            >
              {uploadEnabled ? t('knowledge.actions.enabled') : t('knowledge.actions.disabled')}
            </ActionButton>
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
          <ActionButton
            onClick={() => {
              setUploadFile(null)
              setUploadTitle('')
              setUploadCategory('')
              setUploadSummary('')
              setUploadTagsInput('')
              setUploadEnabled(true)
              setUploadProgress(0)
              setUploadOpen(false)
            }}
            disabled={uploadMutation.isPending}
          >
            {t('knowledge.actions.cancel')}
          </ActionButton>
          <ActionButton tone="primary" onClick={handleUploadSubmit} disabled={uploadMutation.isPending || !uploadFile}>
            {uploadMutation.isPending ? t('knowledge.actions.uploading') : t('knowledge.actions.upload')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteOpen}
        onClose={() => !(deleteMutation.isPending || unbindAssetMutation.isPending) && setDeleteOpen(false)}
      >
        <DialogTitle>
          {selectedItem?.kind === 'asset'
            ? t('knowledge.dialogs.removeTitle')
            : t('knowledge.dialogs.deleteTitle')}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {deleteDialogContent}
          </Typography>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setDeleteOpen(false)} disabled={deleteMutation.isPending || unbindAssetMutation.isPending}>
            {t('knowledge.actions.cancel')}
          </ActionButton>
          <ActionButton
            tone="danger"
            onClick={() => {
              if (selectedItem?.kind === 'asset' && selectedAssetId != null) {
                unbindAssetMutation.mutate(selectedAssetId)
                return
              }
              if (selectedDocumentId != null) {
                deleteMutation.mutate(selectedDocumentId)
              }
            }}
            disabled={
              selectedItem?.kind === 'asset'
                ? unbindAssetMutation.isPending || selectedAssetId == null
                : deleteMutation.isPending || selectedDocumentId == null
            }
          >
            {selectedItem?.kind === 'asset'
              ? t('knowledge.actions.remove')
              : t('knowledge.actions.delete')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      {/* 编辑元数据对话框 */}
      <Dialog
        open={editMetaOpen}
        onClose={() => !(updateDocMetaMutation.isPending || updateAssetMetaMutation.isPending) && setEditMetaOpen(false)}
        fullWidth
        maxWidth="sm"
        disableRestoreFocus
      >
        <DialogTitle>{t('knowledge.dialogs.editMetaTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField
              label={t('knowledge.form.title')}
              fullWidth
              value={editMetaForm.title}
              onChange={e => setEditMetaForm(prev => ({ ...prev, title: e.target.value }))}
              autoFocus
            />
            <TextField
              label={t('knowledge.form.category')}
              fullWidth
              value={editMetaForm.category}
              onChange={e => setEditMetaForm(prev => ({ ...prev, category: e.target.value }))}
            />
            <TextField
              label={t('knowledge.form.tags')}
              fullWidth
              value={editMetaForm.tagsInput}
              onChange={e => setEditMetaForm(prev => ({ ...prev, tagsInput: e.target.value }))}
              placeholder={t('knowledge.form.tagsPlaceholder')}
              helperText={t('knowledge.form.tagsHelper')}
            />
            <TextField
              label={t('knowledge.form.summary')}
              fullWidth
              multiline
              minRows={3}
              value={editMetaForm.summary}
              onChange={e => setEditMetaForm(prev => ({ ...prev, summary: e.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <ActionButton
            onClick={() => setEditMetaOpen(false)}
            disabled={updateDocMetaMutation.isPending || updateAssetMetaMutation.isPending}
          >
            {t('knowledge.actions.cancel')}
          </ActionButton>
          <ActionButton
            tone="primary"
            disabled={!editMetaForm.title.trim() || updateDocMetaMutation.isPending || updateAssetMetaMutation.isPending}
            onClick={() => {
              const tags = editMetaForm.tagsInput.split(',').map(s => s.trim()).filter(Boolean)
              if (selectedItem?.kind === 'asset' && selectedAssetId != null) {
                updateAssetMetaMutation.mutate({ id: selectedAssetId, title: editMetaForm.title.trim(), category: editMetaForm.category.trim(), tags, summary: editMetaForm.summary.trim() })
              } else if (selectedDocumentId != null) {
                updateDocMetaMutation.mutate({ id: selectedDocumentId, title: editMetaForm.title.trim(), category: editMetaForm.category.trim(), tags, summary: editMetaForm.summary.trim() })
              }
            }}
          >
            {t('knowledge.actions.save')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      <Dialog
        open={reuseOpen}
        onClose={() => !reuseBindingsMutation.isPending && setReuseOpen(false)}
        fullWidth
        maxWidth="md"
        disableRestoreFocus
      >
        <DialogTitle>{t('knowledge.dialogs.reuseTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {t('knowledge.dialogs.reuseHint')}
            </Typography>
            <TextField
              size="small"
              fullWidth
              value={reuseSearch}
              onChange={event => setReuseSearch(event.target.value)}
              placeholder={t('knowledge.form.reuseSearch')}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
            {globalAssetsQuery.isLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
                <CircularProgress size={28} />
              </Box>
            ) : filteredGlobalAssets.length ? (
              <List sx={{ maxHeight: 420, overflowY: 'auto', py: 0 }}>
                {categorizedReuseAssets.flatMap(renderReuseCategoryNode)}
              </List>
            ) : (
              <Alert severity="info">{t('knowledge.dialogs.reuseEmpty')}</Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setReuseOpen(false)} disabled={reuseBindingsMutation.isPending}>
            {t('knowledge.actions.cancel')}
          </ActionButton>
          <ActionButton
            tone="primary"
            onClick={() => reuseBindingsMutation.mutate(reuseAssetIds)}
            disabled={reuseBindingsMutation.isPending || globalAssetsQuery.isLoading}
          >
            {t('knowledge.actions.saveReuse')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      <Dialog
        open={refDialogOpen}
        onClose={() => {
          if (addReferenceMutation.isPending || updateReferenceMutation.isPending) return
          setRefDialogOpen(false)
          setRefTargetSearch('')
          setRefDescription('')
          setEditingRef(null)
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {editingRef != null ? t('knowledge.references.editDialogTitle') : t('knowledge.references.addDialogTitle')}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {editingRef != null ? (
              <Typography variant="body2" color="text.secondary">
                {t('knowledge.references.editingTarget', { title: editingRef.title })}
              </Typography>
            ) : (
              <>
                <SearchField
                  value={refTargetSearch}
                  onChange={setRefTargetSearch}
                  placeholder={t('knowledge.references.searchPlaceholder')}
                  fullWidth
                />
                {refCandidates.length === 0 ? (
                  <Alert severity="info">{t('knowledge.references.noCandidates')}</Alert>
                ) : (
                  <List sx={{ maxHeight: 320, overflowY: 'auto', py: 0 }}>
                    {refCandidates.map(doc => (
                      <ListItemButton
                        key={doc.id}
                        onClick={() => {
                          addReferenceMutation.mutate({ targetId: doc.id, description: refDescription })
                        }}
                        disabled={addReferenceMutation.isPending}
                        sx={{ py: 1 }}
                      >
                        <ListItemText
                          primary={
                            <Stack spacing={0.5}>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>{doc.title}</Typography>
                              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                                <Chip size="small" label={doc.format.toUpperCase()} variant="outlined" sx={neutralChipSx} />
                                {doc.category && (
                                  <Chip size="small" label={doc.category} variant="outlined" sx={neutralChipSx} />
                                )}
                              </Stack>
                            </Stack>
                          }
                          secondary={doc.summary || undefined}
                        />
                      </ListItemButton>
                    ))}
                  </List>
                )}
              </>
            )}
            <TextField
              label={t('knowledge.references.descriptionLabel')}
              fullWidth
              multiline
              minRows={2}
              value={refDescription}
              onChange={event => setRefDescription(event.target.value)}
              placeholder={t('knowledge.references.descriptionPlaceholder')}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <ActionButton
            onClick={() => {
              setRefDialogOpen(false)
              setRefTargetSearch('')
              setRefDescription('')
              setEditingRef(null)
            }}
            disabled={addReferenceMutation.isPending || updateReferenceMutation.isPending}
          >
            {t('knowledge.actions.cancel')}
          </ActionButton>
          {editingRef != null && (
            <ActionButton
              tone="primary"
              onClick={() => updateReferenceMutation.mutate({ targetId: editingRef.document_id, description: refDescription })}
              disabled={updateReferenceMutation.isPending}
            >
              {t('knowledge.actions.save')}
            </ActionButton>
          )}
        </DialogActions>
      </Dialog>

    </Box>
  )
}
