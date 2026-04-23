import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Card,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  ToggleButton,
  ToggleButtonGroup,
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
  AccountTree as GroupedViewIcon,
  AutoAwesome as LibraryIcon,
  CheckCircleOutline as CheckCircleIcon,
  Close as CloseIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  ErrorOutline as ErrorOutlineIcon,
  ExpandMore as ExpandMoreIcon,
  FileUpload as FileUploadIcon,
  FolderOpen as FolderOpenIcon,
  DriveFileMove as ImportFolderIcon,
  Hub as GraphViewIcon,
  InsertLink as RefLinkIcon,
  Link as BindIcon,
  Refresh as RefreshIcon,
  RestartAlt as ReindexIcon,
  FilterAltOff as FilterAltOffIcon,
  Tune as EditMetaIcon,
  Description as AssetIcon,
  ShareOutlined as BindingsIcon,
  ViewList as ViewListIcon,
} from '@mui/icons-material'
import { alpha, type SxProps, type Theme } from '@mui/material/styles'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  type KbIndexProgressInfo,
  KbLibraryIndexProgressInfo,
  useSystemEventsContext,
} from '../../contexts/SystemEventsContext'
import {
  type KBDocumentReferences,
  KBAssetDetailResponse,
  KBAssetListItem,
  KBCreateTextDocumentBody,
  type KBReferenceItem,
  KBUploadFilePayload,
  kbLibraryApi,
  workspaceApi,
} from '../../services/api/workspace'
import { useNotification } from '../../hooks/useNotification'
import { CARD_VARIANTS, CHIP_VARIANTS, UNIFIED_TABLE_STYLES } from '../../theme/variants'
import SearchField from '../../components/common/SearchField'
import IconActionButton from '../../components/common/IconActionButton'
import ActionButton from '../../components/common/ActionButton'
import StatCard from '../../components/common/StatCard'
import KBGraphDialog from './components/KBGraphDialog'
import ReferenceGraph from './components/ReferenceGraph'
import KBBatchActionsButton from './components/KBBatchActionsButton'
import {
  findCategoryLengthOverflow,
  getFolderImportMetadata,
  KB_CATEGORY_MAX_LENGTH,
} from './kbFolderImport'
import { buildCategoryTree, type KBCategoryTreeNode } from './kbCategoryTree'

type FilterStatus = 'all' | 'ready' | 'indexing' | 'failed'
type BatchItemStatus = 'waiting' | 'uploading' | 'indexing' | 'done' | 'error'

interface BatchQueueItem {
  id: string
  file: File
  status: BatchItemStatus
  uploadProgress: number
  assetId?: number
  errorMessage?: string
  title: string
  category: string
  tags: string
  summary: string
  source_path?: string
}

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
  const batchInputRef = useRef<HTMLInputElement | null>(null)
  const dirInputRef = useRef<HTMLInputElement | null>(null)
  const batchProcessingRef = useRef(false)
  const batchQueueRef = useRef<BatchQueueItem[]>([])
  const batchCancelRequestedRef = useRef(false)
  const batchRunVersionRef = useRef(0)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all')
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [bindOpen, setBindOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)
  const [assetToDelete, setAssetToDelete] = useState<{ id: number; title: string } | null>(null)
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
  const [uploadPayload, setUploadPayload] = useState<KBUploadFilePayload | null>(null)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadCategory, setUploadCategory] = useState('')
  const [uploadSummary, setUploadSummary] = useState('')
  const [uploadTagsInput, setUploadTagsInput] = useState('')
  const [bindWorkspaceIds, setBindWorkspaceIds] = useState<number[]>([])
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [batchUploadOpen, setBatchUploadOpen] = useState(false)
  const [batchQueue, setBatchQueue] = useState<BatchQueueItem[]>([])
  const [batchRunning, setBatchRunning] = useState(false)
  const [batchCancelRequested, setBatchCancelRequested] = useState(false)
  const [batchPanelVisible, setBatchPanelVisible] = useState(false)
  const [expandedBatchItemId, setExpandedBatchItemId] = useState<string | null>(null)
  const [batchFromFolder, setBatchFromFolder] = useState(false)
  const [listView, setListView] = useState<'flat' | 'grouped' | 'graph'>('grouped')
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set())
  const [selectedAssetIds, setSelectedAssetIds] = useState<Set<number>>(new Set())

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

  useEffect(() => {
    batchQueueRef.current = batchQueue
  }, [batchQueue])

  useEffect(() => {
    setSelectedAssetIds(prev => {
      if (prev.size === 0) return prev
      const existingIds = new Set(assets.map(asset => asset.id))
      let changed = false
      const next = new Set<number>()
      prev.forEach(id => {
        if (existingIds.has(id)) {
          next.add(id)
          return
        }
        changed = true
      })
      return changed ? next : prev
    })
  }, [assets])

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

  const categorizedAssets = useMemo(
    () => buildCategoryTree(filteredAssets, asset => asset.category),
    [filteredAssets]
  )

  const toggleCategoryCollapse = useCallback((category: string) => {
    setCollapsedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
  }, [])

  const toggleAssetSelection = useCallback((assetId: number) => {
    setSelectedAssetIds(prev => {
      const next = new Set(prev)
      if (next.has(assetId)) next.delete(assetId)
      else next.add(assetId)
      return next
    })
  }, [])

  const toggleCategorySelection = useCallback((assetIds: number[]) => {
    if (assetIds.length === 0) return
    setSelectedAssetIds(prev => {
      const next = new Set(prev)
      const shouldSelect = assetIds.some(id => !next.has(id))
      assetIds.forEach(id => {
        if (shouldSelect) next.add(id)
        else next.delete(id)
      })
      return next
    })
  }, [])

  const emptyDocumentProgressMap = useMemo(() => new Map<number, KbIndexProgressInfo>(), [])

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

  const assetReferencesQuery = useQuery({
    queryKey: ['kb-asset-references', selectedAssetId],
    queryFn: () => kbLibraryApi.getReferences(selectedAssetId as number),
    enabled: selectedAssetId != null,
    staleTime: 30_000,
  })

  const activeReferences: KBDocumentReferences = assetReferencesQuery.data ?? {
    references_to: [],
    referenced_by: [],
  }

  const alreadyReferencedToIds = useMemo(
    () => new Set(activeReferences.references_to.map(r => r.document_id)),
    [activeReferences.references_to]
  )

  const refCandidates = useMemo(() => {
    const keyword = refTargetSearch.trim().toLowerCase()
    if (selectedAssetId == null) return []
    return assets
      .filter(a => a.id !== selectedAssetId && !alreadyReferencedToIds.has(a.id))
      .filter(
        a =>
          !keyword ||
          [a.title, a.category ?? '', a.summary ?? '', a.file_name, ...a.tags].join('\n').toLowerCase().includes(keyword)
      )
  }, [selectedAssetId, assets, alreadyReferencedToIds, refTargetSearch])

  const refreshAll = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['kb-library-assets'] }),
      queryClient.invalidateQueries({ queryKey: ['kb-library-asset'] }),
    ])
  }, [queryClient])

  const refreshReferences = useCallback(async () => {
    if (selectedAssetId != null) {
      await queryClient.invalidateQueries({ queryKey: ['kb-asset-references', selectedAssetId] })
    }
  }, [queryClient, selectedAssetId])

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
      if (data.reused_existing) {
        notification.warning(t('kbLibrary.notifications.createReused'), { duration: 6000 })
      } else {
        notification.success(t('kbLibrary.notifications.createSuccess'))
      }
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
      if (data.reused_existing) {
        notification.warning(t('kbLibrary.notifications.uploadReused'), { duration: 6000 })
      } else {
        notification.success(t('kbLibrary.notifications.uploadSuccess'))
      }
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
    onSuccess: async (_, assetId) => {
      setDeleteOpen(false)
      setAssetToDelete(null)
      setSelectedAssetId(null)
      setSelectedAssetIds(prev => {
        if (!prev.has(assetId)) return prev
        const next = new Set(prev)
        next.delete(assetId)
        return next
      })
      clearInteractiveFocus()
      await refreshAll()
      notification.success(t('kbLibrary.notifications.deleteSuccess'))
    },
    onError: (err: Error) => notification.error(t('kbLibrary.notifications.deleteFailed', { message: err.message })),
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: async (assetIds: number[]) => {
      const results = await Promise.allSettled(assetIds.map(assetId => kbLibraryApi.deleteAsset(assetId)))
      const deletedIds: number[] = []
      let failedCount = 0
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          deletedIds.push(assetIds[index])
          return
        }
        failedCount += 1
      })
      return { deletedCount: deletedIds.length, failedCount, deletedIds }
    },
    onSuccess: async result => {
      setBulkDeleteOpen(false)
      if (selectedAssetId != null && result.deletedIds.includes(selectedAssetId)) {
        setSelectedAssetId(null)
      }
      setSelectedAssetIds(prev => {
        if (result.deletedIds.length === 0) return prev
        const next = new Set(prev)
        result.deletedIds.forEach(id => next.delete(id))
        return next
      })
      clearInteractiveFocus()
      await refreshAll()
      if (result.failedCount === 0) {
        notification.success(t('kbLibrary.notifications.bulkDeleteSelectedSuccess', { count: result.deletedCount }))
      } else {
        notification.warning(
          t('kbLibrary.notifications.bulkDeleteSelectedPartial', {
            deleted: result.deletedCount,
            failed: result.failedCount,
          })
        )
      }
    },
    onError: (err: Error) => notification.error(t('kbLibrary.notifications.deleteFailed', { message: err.message })),
  })

  const bulkReindexMutation = useMutation({
    mutationFn: async (assetIds: number[]) => {
      const results = await Promise.allSettled(assetIds.map(assetId => kbLibraryApi.reindexAsset(assetId)))
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
        notification.success(t('kbLibrary.notifications.bulkReindexSelectedSuccess', { count: result.queuedCount }))
      } else {
        notification.warning(
          t('kbLibrary.notifications.bulkReindexSelectedPartial', {
            queued: result.queuedCount,
            failed: result.failedCount,
          })
        )
      }
    },
    onError: (err: Error) => notification.error(t('kbLibrary.notifications.reindexFailed', { message: err.message })),
  })

  const updateMetaMutation = useMutation({
    mutationFn: ({ id, title, category, tags, summary }: { id: number; title: string; category: string; tags: string[]; summary: string }) =>
      kbLibraryApi.updateAsset(id, { title, category, tags, summary }),
    onSuccess: async () => {
      await refreshAll()
      setEditMetaOpen(false)
      notification.success(t('kbLibrary.notifications.updateSuccess'))
    },
    onError: (err: Error) => notification.error(t('kbLibrary.notifications.updateFailed', { message: err.message })),
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

  const addReferenceMutation = useMutation({
    mutationFn: ({ targetId, description }: { targetId: number; description: string }) =>
      kbLibraryApi.addReference(selectedAssetId as number, targetId, description),
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
    mutationFn: (targetId: number) => kbLibraryApi.removeReference(selectedAssetId as number, targetId),
    onSuccess: async () => {
      await refreshReferences()
      notification.success(t('knowledge.references.removeSuccess'))
    },
    onError: (err: Error) => notification.error(t('knowledge.references.removeFailed', { message: err.message })),
  })

  const updateReferenceMutation = useMutation({
    mutationFn: ({ targetId, description }: { targetId: number; description: string }) =>
      kbLibraryApi.updateReference(selectedAssetId as number, targetId, description),
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

  const handleBatchFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (files.length === 0) return
    const unsupported = files.filter(f => !isSupportedUploadFile(f))
    if (unsupported.length > 0) {
      notification.error(
        t('kbLibrary.notifications.unsupportedFormat', {
          name: unsupported.map(f => f.name).join(', '),
          formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', '),
        })
      )
      return
    }
    setBatchFromFolder(false)
    setBatchQueue(files.map(f => ({
      id: `${f.name}-${f.size}-${Math.random()}`,
      file: f,
      status: 'waiting',
      uploadProgress: 0,
      title: f.name.replace(/\.[^.]+$/, ''),
      category: '',
      tags: '',
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
    setBatchFromFolder(true)
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
  }

  const removeBatchQueueItem = useCallback((id: string) => {
    setExpandedBatchItemId(prev => (prev === id ? null : prev))
    setBatchQueue(prev => prev.filter(item => item.id !== id))
  }, [])

  const requestBatchCancel = useCallback(() => {
    batchCancelRequestedRef.current = true
    setBatchCancelRequested(true)
  }, [])

  const startBatchUpload = useCallback(async (items: BatchQueueItem[]) => {
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
          const data = await kbLibraryApi.uploadFile(
            {
              file: item.file,
              title: item.title || item.file.name.replace(/\.[^.]+$/, ''),
              source_path: item.source_path ?? '',
              category: item.category,
              tags: item.tags ? item.tags.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
              summary: item.summary,
              is_enabled: true,
            },
            pct => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, uploadProgress: pct } : i)),
          )
          if (batchRunVersionRef.current !== runVersion) break
          uploadedAny = true
          setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, status: 'indexing', assetId: data.asset.id } : i))
          const deadline = Date.now() + 300_000
          while (Date.now() < deadline) {
            if (batchRunVersionRef.current !== runVersion || batchCancelRequestedRef.current) break
            await new Promise(r => setTimeout(r, 1500))
            if (batchRunVersionRef.current !== runVersion || batchCancelRequestedRef.current) break
            const detail = await kbLibraryApi.getAsset(data.asset.id)
            if (detail.asset.sync_status === 'ready' || detail.asset.sync_status === 'failed') break
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
        if (uploadedAny && items.some(i => Boolean(i.source_path))) {
          setListView('grouped')
          setCollapsedCategories(new Set())
        }
        await refreshAll()
      }
    }
  }, [notification, refreshAll, t])

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
  const statusChipSx = useCallback(
    (status: FilterStatus) => CHIP_VARIANTS.getCustomColorChip({
      ready: theme.palette.success.main,
      indexing: theme.palette.warning.main,
      failed: theme.palette.error.main,
      all: theme.palette.text.secondary,
    }[status], true),
    [theme.palette.error.main, theme.palette.success.main, theme.palette.text.secondary, theme.palette.warning.main],
  )

  useEffect(() => {
    if (!terminalSignature) return
    if (lastProgressTerminalRef.current === terminalSignature) return
    lastProgressTerminalRef.current = terminalSignature
    void refreshAll()
  }, [refreshAll, terminalSignature])

  const closeDrawer = () => {
    if (
      bindingsMutation.isPending ||
      deleteMutation.isPending ||
      addReferenceMutation.isPending ||
      updateReferenceMutation.isPending ||
      removeReferenceMutation.isPending
    )
      return
    setBindOpen(false)
    setDeleteOpen(false)
    setAssetToDelete(null)
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

  const hasListFilter = search.trim() !== ''
  const listTitle = hasListFilter ? t('knowledge.sections.searchResults') : t('knowledge.sections.documents')
  const listSummaryLabel = hasListFilter
    ? t('knowledge.search.resultCount', { count: filteredAssets.length })
    : t('kbLibrary.list.total', { count: filteredAssets.length })

  const assetRefResults = useQueries({
    queries:
      listView === 'graph' && !hasListFilter
        ? filteredAssets.map(asset => ({
            queryKey: ['kb-asset-references', asset.id] as const,
            queryFn: () => kbLibraryApi.getReferences(asset.id),
            staleTime: 5 * 60 * 1000,
          }))
        : [],
  })

  const graphReferenceEdges = useMemo(() => {
    const edges: Array<{ fromId: number; toId: number; fromKind: 'asset'; toKind: 'asset' }> = []
    assetRefResults.forEach((result, i) => {
      if (result.data?.references_to && i < filteredAssets.length) {
        for (const ref of result.data.references_to) {
          edges.push({
            fromId: filteredAssets[i].id,
            toId: ref.document_id,
            fromKind: 'asset',
            toKind: 'asset',
          })
        }
      }
    })
    return edges
  }, [assetRefResults, filteredAssets])

  const selectedAssetIdList = useMemo(
    () => assets.filter(asset => selectedAssetIds.has(asset.id)).map(asset => asset.id),
    [assets, selectedAssetIds]
  )
  const batchActionPending = bulkDeleteMutation.isPending || bulkReindexMutation.isPending

  const renderAssetRow = useCallback(
    (asset: KBAssetListItem) => {
      const progress = progressByAssetId.get(asset.id)
      const status = getProgressStatus(progress) ?? getEffectiveStatus(asset)
      const checked = selectedAssetIds.has(asset.id)
      return (
        <ListItemButton
          key={asset.id}
          selected={selectedAssetId === asset.id}
          onClick={() => setSelectedAssetId(asset.id)}
          sx={{ alignItems: 'flex-start', py: 1.25 }}
        >
          <Checkbox
            checked={checked}
            size="small"
            tabIndex={-1}
            disableRipple
            onClick={event => event.stopPropagation()}
            onChange={() => toggleAssetSelection(asset.id)}
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
                <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.35 }}>
                  {asset.title}
                </Typography>
                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                  <Chip size="small" label={asset.format.toUpperCase()} variant="outlined" sx={neutralChipSx} />
                  <Chip size="small" label={t(`kbLibrary.status.${status}`)} sx={statusChipSx(status)} />
                  <Chip size="small" label={t('kbLibrary.list.bindingCount', { count: asset.binding_count })} variant="outlined" sx={neutralChipSx} />
                </Stack>
              </Stack>
            }
            secondary={
              <Stack spacing={0.5} sx={{ mt: 0.75 }}>
                <Typography variant="caption" color="text.secondary">
                  {asset.source_path}
                </Typography>
                {asset.summary && (
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
                    {asset.summary}
                  </Typography>
                )}
                {progress && progress.phase !== 'ready' && progress.phase !== 'failed' && (
                  <Stack spacing={0.25} sx={{ pt: 0.25 }}>
                    <LinearProgress
                      variant="determinate"
                      value={progress.progress_percent}
                      sx={{ height: 4, borderRadius: 999 }}
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
      )
    },
    [progressByAssetId, selectedAssetId, selectedAssetIds, t, neutralChipSx, statusChipSx, toggleAssetSelection],
  )

  const renderCategoryNode = (node: KBCategoryTreeNode<KBAssetListItem>) => {
    const isCollapsed = collapsedCategories.has(node.key)
    const categoryAssetIds = node.allItems.map(item => item.id)
    const selectedCount = categoryAssetIds.filter(id => selectedAssetIds.has(id)).length
    const categoryChecked = selectedCount > 0 && selectedCount === categoryAssetIds.length
    const categoryIndeterminate = selectedCount > 0 && selectedCount < categoryAssetIds.length
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
          onChange={() => toggleCategorySelection(categoryAssetIds)}
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
    node.items.forEach(item => {
      rows.push(renderAssetRow(item))
    })
    return rows
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
      <Stack spacing={3} sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
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
              <ToggleButtonGroup
                value={statusFilter}
                exclusive
                size="small"
                onChange={(_, v) => { if (v != null) setStatusFilter(v) }}
              >
                <ToggleButton value="all">{t('kbLibrary.filter.all')}</ToggleButton>
                <ToggleButton value="ready">{t('kbLibrary.filter.ready')}</ToggleButton>
                <ToggleButton value="indexing">{t('kbLibrary.filter.indexing')}</ToggleButton>
                <ToggleButton value="failed">{t('kbLibrary.filter.failed')}</ToggleButton>
              </ToggleButtonGroup>
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
              <ActionButton size="small" tone="secondary" startIcon={<FileUploadIcon />} onClick={() => { setBatchQueue([]); setBatchFromFolder(false); setBatchUploadOpen(true) }}>
                {t('kbLibrary.actions.batchUpload')}
              </ActionButton>
              <KBBatchActionsButton
                label={t('kbLibrary.actions.batchActions', { count: selectedAssetIdList.length })}
                disabled={selectedAssetIdList.length === 0 || batchActionPending}
                actions={[
                  {
                    key: 'delete',
                    label: t('kbLibrary.actions.bulkDeleteSelected', { count: selectedAssetIdList.length }),
                    onClick: () => setBulkDeleteOpen(true),
                    disabled: selectedAssetIdList.length === 0 || batchActionPending,
                  },
                  {
                    key: 'reindex',
                    label: t('kbLibrary.actions.bulkReindexSelected', { count: selectedAssetIdList.length }),
                    onClick: () => bulkReindexMutation.mutate(selectedAssetIdList),
                    disabled: selectedAssetIdList.length === 0 || batchActionPending,
                  },
                ]}
              />
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
        ) : (
          <Paper
            sx={{
              ...UNIFIED_TABLE_STYLES.tableContentContainer,
              minHeight: 0,
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
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
              {!hasListFilter && (
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
            {!hasListFilter && listView === 'graph' ? (
              <Box sx={{ flex: 1, minHeight: 420, overflow: 'hidden', position: 'relative' }}>
                <KBGraphDialog
                  documents={[]}
                  boundGlobalAssets={filteredAssets}
                  progressByDocumentId={emptyDocumentProgressMap}
                  references={graphReferenceEdges}
                  onOpenDocument={(kind, id) => {
                    if (kind === 'asset') setSelectedAssetId(id)
                  }}
                />
              </Box>
            ) : (
              <Box sx={UNIFIED_TABLE_STYLES.tableViewport}>
                <List sx={{ py: 0 }}>
                  {hasListFilter || listView === 'flat'
                    ? filteredAssets.map(renderAssetRow)
                    : categorizedAssets.flatMap(renderCategoryNode)}
                </List>
              </Box>
            )}
          </Paper>
        )}
      </Stack>

      {/* 资产详情弹窗 */}
      <Dialog
        open={selectedAssetId != null}
        onClose={closeDrawer}
        fullWidth
        maxWidth="lg"
        scroll="paper"
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, pr: 1 }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.35, wordBreak: 'break-word' }} noWrap>
              {detail?.asset.title ?? selectedAsset?.title ?? ''}
            </Typography>
          </Box>
          <IconButton size="small" onClick={closeDrawer} sx={{ flexShrink: 0 }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>

        <DialogContent dividers>
          {assetDetailQuery.isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
              <CircularProgress size={30} />
            </Box>
          ) : detail ? (
            <Stack spacing={2}>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
                {(detail.asset ?? selectedAsset)?.format && (
                  <Chip size="small" label={(detail.asset ?? selectedAsset)?.format.toUpperCase()} variant="outlined" sx={neutralChipSx} />
                )}
                <Chip
                  size="small"
                  label={t(`kbLibrary.status.${selectedProgressStatus ?? getEffectiveStatus(detail.asset)}`)}
                  sx={statusChipSx(selectedProgressStatus ?? getEffectiveStatus(detail.asset))}
                />
                <Chip
                  size="small"
                  label={t('kbLibrary.list.bindingCount', { count: detail.asset.binding_count })}
                  variant="outlined"
                  sx={neutralChipSx}
                />
              </Stack>
              <Typography variant="body2" color="text.secondary">
                {detail.asset.summary || t('kbLibrary.list.noSummary')}
              </Typography>

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
                        ? t('kbLibrary.progress.detail', { processed: selectedProgress.processed_chunks, total: selectedProgress.total_chunks })
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
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <RefLinkIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                    <Typography variant="subtitle2">{t('knowledge.references.title')}</Typography>
                  </Stack>
                  <ReferenceGraph
                    currentTitle={detail.asset.title}
                    referencesTo={activeReferences.references_to}
                    referencedBy={activeReferences.referenced_by}
                    onNavigate={id => setSelectedAssetId(id)}
                    onAdd={() => {
                      setEditingRef(null)
                      setRefTargetSearch('')
                      setRefDescription('')
                      setRefDialogOpen(true)
                    }}
                    onEdit={ref => {
                      setEditingRef(ref)
                      setRefDescription(ref.description)
                      setRefTargetSearch('')
                      setRefDialogOpen(true)
                    }}
                    onRemove={id => removeReferenceMutation.mutate(id)}
                    disabled={removeReferenceMutation.isPending}
                  />
                </Stack>
              </Paper>

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
                <Divider />
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
        </DialogContent>

        <DialogActions sx={{ px: 2, py: 1.5, gap: 1, flexWrap: 'wrap' }}>
          {detail && (
            <>
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
                startIcon={<EditMetaIcon />}
                sx={compactActionSx}
                onClick={() => {
                  setEditMetaForm({
                    title: detail.asset.title,
                    category: detail.asset.category ?? '',
                    tagsInput: (detail.asset.tags ?? []).join(', '),
                    summary: detail.asset.summary ?? '',
                  })
                  setEditMetaOpen(true)
                }}
              >
                {t('kbLibrary.actions.edit')}
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
                onClick={() => { setAssetToDelete({ id: detail.asset.id, title: detail.asset.title }); setDeleteOpen(true) }}
              >
                {t('kbLibrary.actions.delete')}
              </ActionButton>
            </>
          )}
          <Box sx={{ flex: 1 }} />
          <ActionButton onClick={closeDrawer} sx={compactActionSx}>
            {t('kbLibrary.actions.close')}
          </ActionButton>
        </DialogActions>
      </Dialog>

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

      {/* 编辑元数据对话框 */}
      <Dialog
        open={editMetaOpen}
        onClose={() => !updateMetaMutation.isPending && setEditMetaOpen(false)}
        fullWidth
        maxWidth="sm"
        disableRestoreFocus
      >
        <DialogTitle>{t('kbLibrary.dialogs.editMetaTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField
              label={t('kbLibrary.form.title')}
              fullWidth
              value={editMetaForm.title}
              onChange={e => setEditMetaForm(prev => ({ ...prev, title: e.target.value }))}
              autoFocus
            />
            <TextField
              label={t('kbLibrary.form.category')}
              fullWidth
              value={editMetaForm.category}
              onChange={e => setEditMetaForm(prev => ({ ...prev, category: e.target.value }))}
            />
            <TextField
              label={t('kbLibrary.form.tags')}
              fullWidth
              value={editMetaForm.tagsInput}
              onChange={e => setEditMetaForm(prev => ({ ...prev, tagsInput: e.target.value }))}
              placeholder={t('kbLibrary.form.tagsPlaceholder')}
              helperText={t('kbLibrary.form.tagsHelper')}
            />
            <TextField
              label={t('kbLibrary.form.summary')}
              fullWidth
              multiline
              minRows={3}
              value={editMetaForm.summary}
              onChange={e => setEditMetaForm(prev => ({ ...prev, summary: e.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setEditMetaOpen(false)} disabled={updateMetaMutation.isPending}>
            {t('kbLibrary.actions.cancel')}
          </ActionButton>
          <ActionButton
            tone="primary"
            disabled={!editMetaForm.title.trim() || updateMetaMutation.isPending}
            onClick={() => {
              if (!selectedAssetId) return
              const tags = editMetaForm.tagsInput.split(',').map(s => s.trim()).filter(Boolean)
              updateMetaMutation.mutate({ id: selectedAssetId, title: editMetaForm.title.trim(), category: editMetaForm.category.trim(), tags, summary: editMetaForm.summary.trim() })
            }}
          >
            {t('kbLibrary.actions.save')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      {/* 批量上传队列对话框 */}
      <Dialog
        open={batchUploadOpen}
        onClose={() => { setBatchUploadOpen(false); setBatchQueue([]); setBatchFromFolder(false) }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {batchFromFolder && batchQueue.length > 0
            ? t('knowledge.dialogs.dirImportTitle')
            : t('kbLibrary.dialogs.batchUploadTitle')}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {batchQueue.length === 0 ? (
              <Stack spacing={1.5}>
                <ActionButton tone="secondary" startIcon={<FolderOpenIcon />} onClick={() => batchInputRef.current?.click()}>
                  {t('kbLibrary.actions.chooseFiles')}
                </ActionButton>
                <Divider>{t('knowledge.actions.or')}</Divider>
                <ActionButton tone="secondary" startIcon={<ImportFolderIcon />} onClick={() => dirInputRef.current?.click()}>
                  {t('knowledge.actions.importFolder')}
                </ActionButton>
                <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
                  {t('knowledge.form.dirImportHint')}
                </Typography>
              </Stack>
            ) : (
              <>
                {batchFromFolder && (
                  <Alert severity="info" icon={<ImportFolderIcon fontSize="inherit" />}>
                    {t('knowledge.form.dirImportModeHint')}
                  </Alert>
                )}
                <Stack spacing={0.5}>
                  {batchQueue.map(item => (
                    <Box key={item.id} sx={{ borderRadius: 1, bgcolor: 'action.hover', overflow: 'hidden' }}>
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ py: 0.75, px: 1 }}>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography variant="body2" noWrap title={item.file.name}>
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
                            <Tooltip title={t('kbLibrary.batchStatus.edit')}>
                              <span>
                                <IconActionButton
                                  size="small"
                                  onClick={() => setExpandedBatchItemId(prev => prev === item.id ? null : item.id)}
                                >
                                  <EditMetaIcon sx={{ fontSize: 14 }} />
                                </IconActionButton>
                              </span>
                            </Tooltip>
                            <Tooltip title={t('kbLibrary.actions.removeFromQueue')}>
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
                              label={t('kbLibrary.form.title')}
                              value={item.title}
                              onChange={e => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, title: e.target.value } : i))}
                              fullWidth
                            />
                            <TextField
                              size="small"
                              label={t('kbLibrary.form.category')}
                              value={item.category}
                              onChange={e => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, category: e.target.value } : i))}
                              fullWidth
                            />
                            <TextField
                              size="small"
                              label={t('kbLibrary.form.tags')}
                              value={item.tags}
                              onChange={e => setBatchQueue(prev => prev.map(i => i.id === item.id ? { ...i, tags: e.target.value } : i))}
                              fullWidth
                            />
                            <TextField
                              size="small"
                              label={t('kbLibrary.form.summary')}
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
                  batchFromFolder ? (
                    <ActionButton tone="secondary" startIcon={<ImportFolderIcon />} onClick={() => dirInputRef.current?.click()}>
                      {t('knowledge.actions.reChooseFolder')}
                    </ActionButton>
                  ) : (
                    <ActionButton tone="secondary" startIcon={<FolderOpenIcon />} onClick={() => batchInputRef.current?.click()}>
                      {t('kbLibrary.actions.reChooseFiles')}
                    </ActionButton>
                  )
                )}
              </>
            )}
            <Alert severity="info">
              {t('kbLibrary.form.supportedFormats', { formats: SUPPORTED_UPLOAD_EXTENSIONS.join(', ') })}
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
          <ActionButton onClick={() => { setBatchUploadOpen(false); setBatchQueue([]); setBatchFromFolder(false) }}>
            {t('kbLibrary.actions.cancel')}
          </ActionButton>
          {batchQueue.length > 0 && batchQueue.some(i => i.status === 'waiting') && (
            <ActionButton
              tone="primary"
              onClick={() => startBatchUpload(batchQueue.filter(i => i.status === 'waiting'))}
            >
              {t('kbLibrary.actions.startUpload', { count: batchQueue.filter(i => i.status === 'waiting').length })}
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
          <Stack direction="row" alignItems="center" sx={{ px: 2, py: 1.25, bgcolor: 'primary.main' }}>
            <Typography variant="subtitle2" sx={{ flex: 1, color: 'primary.contrastText' }}>
              {batchRunning
                ? t('kbLibrary.batchPanel.inProgress', { done: batchQueue.filter(i => i.status === 'done' || i.status === 'error').length, total: batchQueue.length })
                : t('kbLibrary.batchPanel.done', { total: batchQueue.length, failed: batchQueue.filter(i => i.status === 'error').length })}
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
                  {batchCancelRequested ? t('kbLibrary.actions.canceling') : t('kbLibrary.actions.cancelUpload')}
                </ActionButton>
              </Stack>
            ) : (
              <Tooltip title={t('kbLibrary.actions.close')}>
                <span>
                  <IconActionButton size="small" sx={{ color: 'primary.contrastText', '&:hover': { bgcolor: 'rgba(255,255,255,0.15)' } }} onClick={() => setBatchPanelVisible(false)}>
                    <CloseIcon sx={{ fontSize: 16 }} />
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
                      <Typography variant="caption" color="text.disabled">{t('kbLibrary.batchStatus.waiting')}</Typography>
                      <Tooltip title={t('kbLibrary.actions.removeFromQueue')}>
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
        open={bulkDeleteOpen}
        onClose={() => !bulkDeleteMutation.isPending && setBulkDeleteOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>{t('kbLibrary.dialogs.bulkDeleteSelectedTitle')}</DialogTitle>
        <DialogContent>
          <Alert severity="warning">
            {t('kbLibrary.dialogs.bulkDeleteSelectedContent', { count: selectedAssetIdList.length })}
          </Alert>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setBulkDeleteOpen(false)} disabled={bulkDeleteMutation.isPending}>
            {t('kbLibrary.actions.cancel')}
          </ActionButton>
          <ActionButton
            tone="danger"
            startIcon={<DeleteIcon />}
            onClick={() => bulkDeleteMutation.mutate(selectedAssetIdList)}
            disabled={selectedAssetIdList.length === 0 || bulkDeleteMutation.isPending}
          >
            {t('kbLibrary.actions.bulkDeleteSelected', { count: selectedAssetIdList.length })}
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
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {doc.title}
                              </Typography>
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
              onClick={() =>
                updateReferenceMutation.mutate({ targetId: editingRef.document_id, description: refDescription })
              }
              disabled={updateReferenceMutation.isPending}
            >
              {t('knowledge.actions.save')}
            </ActionButton>
          )}
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
            {t('kbLibrary.dialogs.deleteContent', { title: assetToDelete?.title ?? '-' })}
          </Alert>
        </DialogContent>
        <DialogActions>
          <ActionButton onClick={() => setDeleteOpen(false)}>{t('kbLibrary.actions.cancel')}</ActionButton>
          <ActionButton
            tone="danger"
            startIcon={<DeleteIcon />}
            onClick={() => assetToDelete && deleteMutation.mutate(assetToDelete.id)}
            disabled={!assetToDelete || deleteMutation.isPending}
          >
            {t('kbLibrary.actions.delete')}
          </ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
