import { useState, useMemo, useRef, useCallback } from 'react'
import { useTheme } from '@mui/material/styles'
import { Editor } from '@monaco-editor/react'
import {
  Box,
  Card,
  Typography,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  CircularProgress,
  Alert,
  Stack,
  Tooltip,
  TextField,
  Divider,
  Paper,
  Switch,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  alpha,
  useMediaQuery,
} from '@mui/material'
import {
  Extension as ExtensionIcon,
  Delete as DeleteIcon,
  GitHub as GitHubIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  ViewModule as GridViewIcon,
  Upload as UploadIcon,
  Close as CloseIcon,
  AutoAwesome as AutoInjectIcon,
  Visibility as ViewIcon,
  FormatListBulleted as ListViewIcon,
  Inventory2 as BuiltinIcon,
  FolderCopy as UserIcon,
  HelpOutline as HelpIcon,
  InsertDriveFileOutlined as FileIcon,
  FolderOutlined as FolderIcon,
  Description as SkillMdIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Code as CodeIcon,
  PreviewOutlined as PreviewIcon,
  SyncOutlined as SyncIcon,
  Inventory as RepoIcon,
  FilterAltOff as FilterAltOffIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  skillsLibraryApi,
  builtinSkillApi,
  AllSkillItem,
  SkillItem,
  SkillDirEntry,
} from '../../services/api/workspace'
import { useNotification } from '../../hooks/useNotification'
import { CARD_VARIANTS, UNIFIED_TABLE_STYLES } from '../../theme/variants'
import MarkdownRenderer from '../../components/common/MarkdownRenderer'
import SegmentedControl from '../../components/common/SegmentedControl'
import SearchField from '../../components/common/SearchField'
import ActionButton from '../../components/common/ActionButton'
import IconActionButton from '../../components/common/IconActionButton'
import StatCard from '../../components/common/StatCard'

// ─── Types ───────────────────────────────────────────────────

interface UnifiedSkill {
  name: string
  displayName: string
  description: string
  source: 'builtin' | 'user' | 'repo'
  hasGit: boolean
  repoUrl?: string
  treePath?: string
  repoName?: string
}

interface SkillMdData {
  frontmatter: Record<string, string>
  body: string
}

type SourceFilter = 'all' | 'builtin' | 'user' | 'repo'
type ViewMode = 'card' | 'list'

// ─── Helpers ─────────────────────────────────────────────────

function parseSkillMd(raw: string): SkillMdData {
  const lines = raw.split('\n')
  const frontmatter: Record<string, string> = {}
  let body = raw

  if (lines[0]?.trim() === '---') {
    let endLine = -1
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim() === '---') {
        endLine = i
        break
      }
      const colonIdx = lines[i].indexOf(':')
      if (colonIdx > 0) {
        const key = lines[i].slice(0, colonIdx).trim()
        const value = lines[i].slice(colonIdx + 1).trim().replace(/^["']|["']$/g, '')
        frontmatter[key] = value
      }
    }
    if (endLine > 0) {
      body = lines.slice(endLine + 1).join('\n').trimStart()
    }
  }

  return { frontmatter, body }
}

const EXT_LANG_MAP: Record<string, string> = {
  '.md': 'markdown', '.txt': 'plaintext', '.yaml': 'yaml', '.yml': 'yaml',
  '.json': 'json', '.toml': 'toml', '.py': 'python', '.js': 'javascript',
  '.ts': 'typescript', '.html': 'html', '.css': 'css', '.xml': 'xml',
  '.sh': 'shell', '.bash': 'shell', '.cfg': 'ini', '.ini': 'ini',
  '.conf': 'ini', '.env': 'shell', '.rst': 'restructuredtext', '.csv': 'plaintext',
  '.log': 'plaintext', '.svg': 'xml',
}

function getMonacoLanguage(filename: string): string {
  const lower = filename.toLowerCase()
  const dotIdx = lower.lastIndexOf('.')
  if (dotIdx >= 0) {
    return EXT_LANG_MAP[lower.slice(dotIdx)] ?? 'plaintext'
  }
  return 'plaintext'
}

function autoDeriveName(url: string): string {
  const segment = url.trim().split('/').pop() ?? ''
  return segment
    .replace(/\.git$/i, '')
    .replace(/[^a-zA-Z0-9_-]/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase()
}

// ─── Skill Content Panel (Drawer body) ──────────────────────

function SkillContentPanel({ raw }: { raw: string }) {
  const { t } = useTranslation('workspace')
  const { frontmatter, body } = useMemo(() => parseSkillMd(raw), [raw])
  const allowedTools =
    frontmatter['allowed-tools']
      ?.split(',')
      .map(s => s.trim())
      .filter(Boolean) ?? []
  const fmDesc = frontmatter['description']
  const otherFields = Object.entries(frontmatter).filter(
    ([k]) => !['name', 'description', 'allowed-tools'].includes(k),
  )

  return (
    <Box>
      {/* Frontmatter meta */}
      {Object.keys(frontmatter).length > 0 && (
        <Box sx={{ px: 2.5, py: 1.5, bgcolor: 'action.hover', borderBottom: '1px solid', borderColor: 'divider' }}>
          {allowedTools.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
              <Typography variant="caption" color="text.secondary">
                {t('skills.content.allowedTools')}
              </Typography>
              {allowedTools.map(tool => (
                <Chip
                  key={tool}
                  label={tool}
                  size="small"
                  variant="outlined"
                  sx={{ height: 20, fontSize: 11, borderColor: 'divider', color: 'text.secondary' }}
                />
              ))}
            </Box>
          )}
          {fmDesc && (
            <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
              {fmDesc}
            </Typography>
          )}
          {otherFields.map(([k, v]) => (
            <Typography key={k} variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.25 }}>
              {k}: {v}
            </Typography>
          ))}
        </Box>
      )}
      {/* Markdown body */}
      {body ? (
        <Box sx={{ px: 2.5, py: 2 }}>
          <MarkdownRenderer>{body}</MarkdownRenderer>
        </Box>
      ) : (
        <Box sx={{ px: 2.5, py: 2 }}>
          <Typography variant="body2" color="text.disabled">{t('skills.content.noContent')}</Typography>
        </Box>
      )}
    </Box>
  )
}

// ─── Main Page ──────────────────────────────────────────────

export default function SkillsLibraryPage() {
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const fileInputRef = useRef<HTMLInputElement>(null)

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('card')
  const [searchQuery, setSearchQuery] = useState('')
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')

  // Drawer state
  const [drawerSkill, setDrawerSkill] = useState<UnifiedSkill | null>(null)
  const [drawerFiles, setDrawerFiles] = useState<SkillDirEntry[]>([])
  const [drawerFilesLoading, setDrawerFilesLoading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null) // rel_path
  const [fileContent, setFileContent] = useState<string | null>(null)
  const [fileLoading, setFileLoading] = useState(false)
  const [drawerViewMode, setDrawerViewMode] = useState<'preview' | 'source'>('preview')
  const [editing, setEditing] = useState(false)
  const [editBuffer, setEditBuffer] = useState('')
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [unsavedDialogTarget, setUnsavedDialogTarget] = useState<string | null>(null)

  // Dialog state
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [cloneDialogOpen, setCloneDialogOpen] = useState(false)
  const [cloneUrl, setCloneUrl] = useState('')
  const [cloneTargetDir, setCloneTargetDir] = useState('')
  const [cloneUrlTouched, setCloneUrlTouched] = useState(false)

  // Pull state
  const [pullingName, setPullingName] = useState<string | null>(null)

  // Sync to workspaces state
  const [syncingSkill, setSyncingSkill] = useState<string | null>(null)

  // ── Data fetching ──

  const { data: allSkillsRaw = [], isLoading: loadingAll, error: errorAll, refetch: refetchAll } = useQuery({
    queryKey: ['skills-all'],
    queryFn: () => skillsLibraryApi.getAll(),
  })

  const { data: builtinSkills = [], isLoading: loadingBuiltin, refetch: refetchBuiltin } = useQuery<SkillItem[]>({
    queryKey: ['skills-builtin'],
    queryFn: builtinSkillApi.getList,
  })

  const { data: treeData, refetch: refetchTree } = useQuery({
    queryKey: ['skills-tree'],
    queryFn: skillsLibraryApi.getTree,
  })

  const { data: autoInjectList = [], refetch: refetchAutoInject } = useQuery({
    queryKey: ['skills-auto-inject'],
    queryFn: skillsLibraryApi.getAutoInject,
  })

  const autoInjectSet = useMemo(() => new Set(autoInjectList), [autoInjectList])

  // ── Unified skill list ──

  const unifiedSkills = useMemo<UnifiedSkill[]>(() => {
    const builtinMap = new Map(builtinSkills.map(s => [s.name, s]))
    const treeNodes = treeData ?? []

    const hasGitMap = new Map<string, { hasGit: boolean; repoUrl?: string; treePath?: string }>()
    const collectGit = (nodes: typeof treeNodes) => {
      for (const node of nodes) {
        if (node.type === 'skill') {
          hasGitMap.set(node.name, { hasGit: node.has_git, repoUrl: node.repo_url ?? undefined, treePath: node.path })
        }
        if (node.type === 'repo' && node.children) {
          for (const child of node.children) {
            if (child.type === 'skill') {
              hasGitMap.set(child.name, { hasGit: true, repoUrl: node.repo_url ?? undefined, treePath: child.path })
            }
          }
        }
        if (node.children) collectGit(node.children)
      }
    }
    collectGit(treeNodes)

    return allSkillsRaw.map((s: AllSkillItem) => {
      const gitInfo = hasGitMap.get(s.name)
      const builtin = builtinMap.get(s.name)
      return {
        name: s.name,
        displayName: s.display_name || s.name,
        description: s.description || builtin?.description || '',
        source: s.source,
        hasGit: gitInfo?.hasGit ?? false,
        repoUrl: gitInfo?.repoUrl,
        treePath: gitInfo?.treePath,
        repoName: s.repo_name ?? undefined,
      }
    })
  }, [allSkillsRaw, builtinSkills, treeData])

  // ── Filtered list ──

  const filteredSkills = useMemo(() => {
    let list = unifiedSkills
    if (sourceFilter !== 'all') {
      list = list.filter(s => s.source === sourceFilter)
    }
    const q = searchQuery.trim().toLowerCase()
    if (q) {
      list = list.filter(
        s =>
          s.name.toLowerCase().includes(q) ||
          s.displayName.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q),
      )
    }
    return list
  }, [unifiedSkills, sourceFilter, searchQuery])

  // ── Stats ──

  const stats = useMemo(() => ({
    builtin: unifiedSkills.filter(s => s.source === 'builtin').length,
    user: unifiedSkills.filter(s => s.source === 'user').length,
    repo: unifiedSkills.filter(s => s.source === 'repo').length,
    autoInject: autoInjectList.length,
  }), [unifiedSkills, autoInjectList])

  const isLoading = loadingAll || loadingBuiltin
  const hasActiveFilters = searchQuery.trim() !== '' || sourceFilter !== 'all'

  // ── Auto-inject toggle ──

  const toggleAutoInject = useCallback(
    async (skillName: string, enabled: boolean) => {
      const current = new Set(autoInjectList)
      if (enabled) {
        current.add(skillName)
      } else {
        current.delete(skillName)
      }
      try {
        await skillsLibraryApi.setAutoInject([...current])
        await refetchAutoInject()
        notification.success(t('skills.notifications.autoInjectUpdated'))
      } catch (err) {
        notification.error(t('skills.notifications.autoInjectFailed', { message: (err as Error).message }))
      }
    },
    [autoInjectList, refetchAutoInject, notification, t],
  )

  // ── Drawer ──

  const isTextFile = useCallback((name: string) => {
    const textExts = ['.md', '.txt', '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini', '.sh', '.bash', '.py', '.js', '.ts', '.html', '.css', '.xml', '.csv', '.env', '.conf', '.rst', '.log']
    const lower = name.toLowerCase()
    return textExts.some(ext => lower.endsWith(ext)) || !lower.includes('.')
  }, [])

  const loadFileContent = useCallback(
    async (skill: UnifiedSkill, relPath: string) => {
      setFileLoading(true)
      setFileContent(null)
      try {
        let content: string
        if (skill.source === 'builtin') {
          content = await builtinSkillApi.getFile(skill.name, relPath)
        } else if (skill.source === 'repo') {
          content = await skillsLibraryApi.getFile(`${skill.name}/${relPath}`)
        } else {
          content = await skillsLibraryApi.getFile(`${skill.name}/${relPath}`)
        }
        setFileContent(content)
        setEditBuffer(content)
        setDirty(false)
      } catch {
        setFileContent(null)
      } finally {
        setFileLoading(false)
      }
    },
    [],
  )

  const selectFile = useCallback(
    (skill: UnifiedSkill, relPath: string) => {
      if (dirty) {
        setUnsavedDialogTarget(relPath)
        return
      }
      setSelectedFile(relPath)
      setEditing(false)
      setDrawerViewMode('preview')
      loadFileContent(skill, relPath)
    },
    [dirty, loadFileContent],
  )

  const openDrawer = useCallback(
    async (skill: UnifiedSkill) => {
      setDrawerSkill(skill)
      setDrawerFiles([])
      setSelectedFile(null)
      setFileContent(null)
      setEditing(false)
      setDirty(false)
      setDrawerViewMode('preview')
      setDrawerFilesLoading(true)
      try {
        const entries = await skillsLibraryApi.getDir(skill.name, skill.source === 'repo' ? 'repo' : skill.source)
        setDrawerFiles(entries)
        const skillMd = entries.find(e => e.type === 'file' && e.name === 'SKILL.md')
        if (skillMd) {
          setSelectedFile(skillMd.rel_path)
          loadFileContent(skill, skillMd.rel_path)
        }
      } catch {
        setDrawerFiles([])
      } finally {
        setDrawerFilesLoading(false)
      }
    },
    [loadFileContent],
  )

  const closeDrawer = useCallback(() => {
    if (dirty) {
      setUnsavedDialogTarget('__close__')
      return
    }
    setDrawerSkill(null)
    setSelectedFile(null)
    setFileContent(null)
    setEditing(false)
    setDirty(false)
  }, [dirty])

  const handleSave = useCallback(async () => {
    if (!drawerSkill || !selectedFile) return
    setSaving(true)
    try {
      await skillsLibraryApi.saveFile(`${drawerSkill.name}/${selectedFile}`, editBuffer)
      setFileContent(editBuffer)
      setDirty(false)
      setEditing(false)
      notification.success(t('skills.drawer.saveSuccess'))
      queryClient.invalidateQueries({ queryKey: ['skills-all'] })
    } catch (err) {
      notification.error(t('skills.drawer.saveFailed', { message: (err as Error).message }))
    } finally {
      setSaving(false)
    }
  }, [drawerSkill, selectedFile, editBuffer, notification, t, queryClient])

  const handleDiscardAndSwitch = useCallback(() => {
    const target = unsavedDialogTarget
    setDirty(false)
    setEditing(false)
    setUnsavedDialogTarget(null)
    if (target === '__close__') {
      setDrawerSkill(null)
      setSelectedFile(null)
      setFileContent(null)
    } else if (target && drawerSkill) {
      setSelectedFile(target)
      setDrawerViewMode('preview')
      loadFileContent(drawerSkill, target)
    }
  }, [unsavedDialogTarget, drawerSkill, loadFileContent])

  // ── Mutations ──

  const deleteMutation = useMutation({
    mutationFn: (name: string) => skillsLibraryApi.delete(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills-all'] })
      queryClient.invalidateQueries({ queryKey: ['skills-tree'] })
      notification.success(t('skills.notifications.deleted'))
      setDeleteTarget(null)
    },
    onError: (err: Error) => notification.error(t('skills.notifications.deleteFailed', { message: err.message })),
  })

  const cloneMutation = useMutation({
    mutationFn: () => skillsLibraryApi.clone(cloneUrl.trim(), cloneTargetDir.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills-all'] })
      queryClient.invalidateQueries({ queryKey: ['skills-tree'] })
      notification.success(t('skills.notifications.cloned', { dir: cloneTargetDir }))
      setCloneDialogOpen(false)
      setCloneUrl('')
      setCloneTargetDir('')
      setCloneUrlTouched(false)
    },
    onError: (err: Error) => notification.error(t('skills.notifications.cloneFailed', { message: err.message })),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => skillsLibraryApi.upload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills-all'] })
      queryClient.invalidateQueries({ queryKey: ['skills-tree'] })
      notification.success(t('skills.notifications.uploaded'))
    },
    onError: (err: Error) => notification.error(t('skills.notifications.uploadFailed', { message: err.message })),
  })

  const handlePull = async (skill: UnifiedSkill) => {
    const path = skill.treePath || skill.name
    setPullingName(skill.name)
    try {
      const output = await skillsLibraryApi.pull(path)
      notification.success(
        output
          ? t('skills.notifications.pullSuccess', { output: output.slice(0, 120) })
          : t('skills.notifications.pullUpToDate'),
      )
      queryClient.invalidateQueries({ queryKey: ['skills-all'] })
      queryClient.invalidateQueries({ queryKey: ['skills-tree'] })
    } catch (err) {
      notification.error(t('skills.notifications.pullFailed', { message: (err as Error).message }))
    } finally {
      setPullingName(null)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.zip')) {
      notification.warning(t('skills.notifications.invalidFile'))
      return
    }
    uploadMutation.mutate(file)
    e.target.value = ''
  }

  const handleCloneUrlChange = (url: string) => {
    setCloneUrl(url)
    if (!cloneUrlTouched) {
      setCloneTargetDir(autoDeriveName(url))
    }
  }

  const handleSyncToWorkspaces = async (skillId: string) => {
    setSyncingSkill(skillId)
    try {
      const result = await skillsLibraryApi.syncToWorkspaces(skillId)
      notification.success(t('skills.notifications.syncSuccess', { count: result.synced_count }))
    } catch (err) {
      notification.error(t('skills.notifications.syncFailed', { message: (err as Error).message }))
    } finally {
      setSyncingSkill(null)
    }
  }

  const handleRefresh = () => {
    refetchAll()
    refetchBuiltin()
    refetchTree()
    refetchAutoInject()
  }

  const handleClearFilters = () => {
    setSearchQuery('')
    setSourceFilter('all')
  }

  // ── Render ────────────────────────────────────────────────

  return (
    <Box sx={{ ...UNIFIED_TABLE_STYLES.tableLayoutContainer, p: { xs: 1.5, sm: 2, md: 3 } }}>
      {/* Stat cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', md: 'repeat(4, minmax(0, 1fr))' }, gap: { xs: 1, sm: 2 }, mb: { xs: 1.5, sm: 3 }, flexShrink: 0 }}>
        <StatCard label={t('skills.statBuiltin')} value={stats.builtin} icon={<BuiltinIcon sx={{ fontSize: 20 }} />} color={theme.palette.primary.main} />
        <StatCard label={t('skills.statUser')} value={stats.user} icon={<UserIcon sx={{ fontSize: 20 }} />} color={theme.palette.success.main} />
        <StatCard label={t('skills.statRepo')} value={stats.repo} icon={<RepoIcon sx={{ fontSize: 20 }} />} color={theme.palette.info.main} />
        <StatCard label={t('skills.statAutoInject')} value={stats.autoInject} icon={<AutoInjectIcon sx={{ fontSize: 20 }} />} color={theme.palette.warning.main} />
      </Box>

      {/* Toolbar */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, mb: 2, flexShrink: 0 }}>
        <Box sx={{ px: { xs: 1.25, sm: 2 }, py: 1.25, display: 'flex', alignItems: { xs: 'stretch', md: 'center' }, gap: 1.25, flexWrap: 'wrap', flexDirection: { xs: 'column', md: 'row' } }}>
          <Box sx={{ display: 'flex', alignItems: { xs: 'stretch', sm: 'center' }, gap: 1.25, flexWrap: 'wrap', flex: { xs: '1 1 auto', md: '1 1 520px' }, minWidth: 0 }}>
            <SearchField
              placeholder={t('skills.search.placeholder')}
              value={searchQuery}
              onChange={setSearchQuery}
              onClear={() => setSearchQuery('')}
              sx={{ width: { xs: '100%', sm: 280, md: 320 }, maxWidth: '100%', flexShrink: 0 }}
            />

            <Box sx={{ maxWidth: '100%', overflowX: 'auto' }}>
              <SegmentedControl
                value={sourceFilter}
                options={[
                  { value: 'all', label: t('skills.filter.all') },
                  { value: 'builtin', label: t('skills.filter.builtin') },
                  { value: 'user', label: t('skills.filter.user') },
                  { value: 'repo', label: t('skills.filter.repo') },
                ]}
                onChange={v => setSourceFilter(v)}
              />
            </Box>

            <SegmentedControl
              value={viewMode}
              options={[
                {
                  value: 'card',
                  icon: <GridViewIcon fontSize="small" />,
                  tooltip: t('skills.toolbar.cardView'),
                  ariaLabel: t('skills.toolbar.cardView'),
                  iconOnly: true,
                },
                {
                  value: 'list',
                  icon: <ListViewIcon fontSize="small" />,
                  tooltip: t('skills.toolbar.listView'),
                  ariaLabel: t('skills.toolbar.listView'),
                  iconOnly: true,
                },
              ]}
              onChange={v => setViewMode(v)}
            />

            {hasActiveFilters && (
              <Tooltip title={t('skills.toolbar.clearFilters')}>
                <IconActionButton size="small" onClick={handleClearFilters}>
                  <FilterAltOffIcon fontSize="small" />
                </IconActionButton>
              </Tooltip>
            )}
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', marginLeft: { xs: 0, md: 'auto' }, width: { xs: '100%', md: 'auto' }, justifyContent: { xs: 'space-between', sm: 'flex-start', md: 'flex-end' } }}>
            <Tooltip title={t('skills.toolbar.refresh')}>
              <IconActionButton onClick={handleRefresh} disabled={isLoading} size="small">
                <RefreshIcon fontSize="small" />
              </IconActionButton>
            </Tooltip>

            <input type="file" accept=".zip" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileChange} />
            <Tooltip title={t('skills.toolbar.uploadTooltip')}>
              <ActionButton
                tone="secondary"
                startIcon={uploadMutation.isPending ? <CircularProgress size={16} color="inherit" /> : <UploadIcon />}
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadMutation.isPending}
                size="small"
                sx={{ flex: { xs: '1 1 auto', sm: '0 0 auto' } }}
              >
                {t('skills.toolbar.uploadBtn')}
              </ActionButton>
            </Tooltip>

            <ActionButton tone="primary" startIcon={<AddIcon />} onClick={() => setCloneDialogOpen(true)} size="small" sx={{ flex: { xs: '1 1 auto', sm: '0 0 auto' } }}>
              {t('skills.toolbar.addBtn')}
            </ActionButton>

            <Tooltip title={t('skills.pageDesc')} arrow>
              <IconActionButton size="small">
                <HelpIcon fontSize="small" />
              </IconActionButton>
            </Tooltip>
          </Box>
        </Box>
      </Card>

      {/* Error */}
      {errorAll && (
        <Alert severity="error" sx={{ mb: 2, flexShrink: 0 }}>
          {t('skills.error.loadFailed', { message: (errorAll as Error).message })}
        </Alert>
      )}

      {/* Loading */}
      {isLoading ? (
        <Box sx={{ flex: 1, minHeight: 0, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <CircularProgress />
        </Box>
      ) : filteredSkills.length === 0 ? (
        /* Empty state */
        <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
          <ExtensionIcon sx={{ fontSize: 64, opacity: 0.2 }} />
          <Typography variant="h6" color="text.secondary">
            {searchQuery || sourceFilter !== 'all' ? t('skills.empty.noMatch') : t('skills.empty.title')}
          </Typography>
          {!searchQuery && sourceFilter === 'all' && (
            <Typography variant="body2" color="text.secondary">
              {t('skills.empty.hint')}
            </Typography>
          )}
        </Box>
      ) : viewMode === 'card' ? (
        /* ── Card View ── */
        <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', pr: 0.5 }}>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', sm: 'repeat(auto-fill, minmax(280px, 1fr))', md: 'repeat(auto-fill, minmax(320px, 1fr))' }, gap: { xs: 1.25, sm: 2 } }}>
            {filteredSkills.map(skill => (
              <Card
                key={skill.name}
                sx={{
                  ...CARD_VARIANTS.default.styles,
                  display: 'flex',
                  flexDirection: 'column',
                  cursor: 'pointer',
                  '&:hover': { borderColor: 'primary.main', boxShadow: 2 },
                  transition: 'border-color 0.2s, box-shadow 0.2s',
                }}
                onClick={() => openDrawer(skill)}
              >
              <Box sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                {/* Top row: source chip + git icon */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  <Chip
                    label={
                      skill.source === 'builtin' ? t('skills.card.sourceBuiltin')
                        : skill.source === 'repo' ? t('skills.card.sourceRepo')
                          : t('skills.card.sourceUser')
                    }
                    size="small"
                    color={skill.source === 'builtin' ? 'primary' : skill.source === 'repo' ? 'secondary' : 'success'}
                    variant="outlined"
                    sx={{ fontSize: '0.7rem', height: 22 }}
                  />
                  {autoInjectSet.has(skill.name) && (
                    <Chip
                      label={t('skills.autoInject.badge')}
                      size="small"
                      sx={{
                        fontSize: '0.65rem',
                        height: 20,
                        bgcolor: 'warning.main',
                        color: 'warning.contrastText',
                        fontWeight: 600,
                      }}
                    />
                  )}
                  {skill.repoName && (
                    <Chip label={skill.repoName} size="small" variant="outlined" sx={{ fontSize: '0.6rem', height: 18, opacity: 0.7 }} />
                  )}
                  {skill.hasGit && (
                    <GitHubIcon sx={{ fontSize: 14, color: 'text.disabled', ml: 'auto' }} />
                  )}
                </Box>

                {/* Name */}
                <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
                  {skill.displayName}
                </Typography>
                {skill.displayName !== skill.name && (
                  <Typography variant="caption" color="text.disabled" sx={{ mt: -0.5 }}>
                    {skill.name}
                  </Typography>
                )}

                {/* Description */}
                {skill.description && (
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
                    {skill.description}
                  </Typography>
                )}
              </Box>

              {/* Bottom actions bar */}
              <Box
                sx={{ px: 2, py: 1, borderTop: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 0.5 }}
                onClick={e => e.stopPropagation()}
              >
                <Tooltip title={t('skills.autoInject.tooltip')}>
                  <Switch
                    size="small"
                    checked={autoInjectSet.has(skill.name)}
                    onChange={(_, checked) => toggleAutoInject(skill.name, checked)}
                    color="warning"
                  />
                </Tooltip>
                <Typography variant="caption" color="text.secondary" sx={{ mr: 'auto' }}>
                  {autoInjectSet.has(skill.name) ? t('skills.autoInject.on') : t('skills.autoInject.off')}
                </Typography>

                {skill.source === 'user' && skill.hasGit && (
                  <Tooltip title={t('skills.card.pullTooltip')}>
                    <span>
                      <IconActionButton size="small" color="primary" onClick={() => handlePull(skill)} disabled={pullingName === skill.name}>
                        {pullingName === skill.name ? <CircularProgress size={14} /> : <RefreshIcon sx={{ fontSize: 16 }} />}
                      </IconActionButton>
                    </span>
                  </Tooltip>
                )}
                {skill.source === 'user' && (
                  <Tooltip title={t('skills.card.deleteTooltip')}>
                    <IconActionButton size="small" color="error" onClick={() => setDeleteTarget(skill.name)}>
                      <DeleteIcon sx={{ fontSize: 16 }} />
                    </IconActionButton>
                  </Tooltip>
                )}
                <Tooltip title={t('skills.card.viewTooltip')}>
                  <IconActionButton size="small" onClick={() => openDrawer(skill)}>
                    <ViewIcon sx={{ fontSize: 16 }} />
                  </IconActionButton>
                </Tooltip>
              </Box>
              </Card>
            ))}
          </Box>
        </Box>
      ) : (
        /* ── List View ── */
        <Paper sx={{ ...UNIFIED_TABLE_STYLES.tableContentContainer, position: 'relative', minHeight: 0 }}>
          <Box sx={UNIFIED_TABLE_STYLES.tableViewport}>
            {filteredSkills.map((skill, index) => (
              <Box key={skill.name}>
                {index > 0 && <Divider />}
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: { xs: 'stretch', sm: 'center' },
                    flexDirection: { xs: 'column', sm: 'row' },
                    px: { xs: 1.25, sm: 2 },
                    py: 1.25,
                    gap: { xs: 1, sm: 1.5 },
                    cursor: 'pointer',
                    ...UNIFIED_TABLE_STYLES.row,
                  }}
                  onClick={() => openDrawer(skill)}
                >
                {/* Source chip */}
                <Chip
                  label={
                    skill.source === 'builtin' ? t('skills.card.sourceBuiltin')
                      : skill.source === 'repo' ? t('skills.card.sourceRepo')
                        : t('skills.card.sourceUser')
                  }
                  size="small"
                  color={skill.source === 'builtin' ? 'primary' : skill.source === 'repo' ? 'secondary' : 'success'}
                  variant="outlined"
                  sx={{ fontSize: '0.7rem', height: 22, width: 52, flexShrink: 0 }}
                />

                {/* Name + desc */}
                <Box sx={{ flexGrow: 1, minWidth: 0, width: { xs: '100%', sm: 'auto' } }}>
                  <Box sx={{ display: 'flex', alignItems: { xs: 'flex-start', sm: 'baseline' }, flexDirection: { xs: 'column', sm: 'row' }, gap: { xs: 0.25, sm: 1 } }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, flexShrink: 0, maxWidth: '100%', overflowWrap: 'anywhere' }}>
                      {skill.displayName}
                    </Typography>
                    {skill.displayName !== skill.name && (
                      <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0, maxWidth: '100%', overflowWrap: 'anywhere' }}>
                        ({skill.name})
                      </Typography>
                    )}
                    {skill.description && (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: { xs: 'normal', sm: 'nowrap' }, display: { xs: '-webkit-box', sm: 'block' }, WebkitLineClamp: { xs: 2, sm: 'unset' }, WebkitBoxOrient: 'vertical' }}
                      >
                        {skill.description}
                      </Typography>
                    )}
                  </Box>
                </Box>

                {/* Auto-inject badge */}
                {autoInjectSet.has(skill.name) && (
                  <Chip
                    label={t('skills.autoInject.badge')}
                    size="small"
                    sx={{ fontSize: '0.65rem', height: 20, bgcolor: 'warning.main', color: 'warning.contrastText', fontWeight: 600, flexShrink: 0 }}
                  />
                )}

                {/* Git icon */}
                {skill.hasGit && <GitHubIcon sx={{ fontSize: 14, color: 'text.disabled', flexShrink: 0 }} />}

                {/* Auto-inject toggle */}
                <Box onClick={e => e.stopPropagation()} sx={{ flexShrink: 0, alignSelf: { xs: 'flex-start', sm: 'center' } }}>
                  <Tooltip title={t('skills.autoInject.tooltip')}>
                    <Switch
                      size="small"
                      checked={autoInjectSet.has(skill.name)}
                      onChange={(_, checked) => toggleAutoInject(skill.name, checked)}
                      color="warning"
                    />
                  </Tooltip>
                </Box>

                {/* Actions */}
                <Box sx={{ display: 'flex', gap: 0.25, flexShrink: 0, alignSelf: { xs: 'flex-end', sm: 'center' } }} onClick={e => e.stopPropagation()}>
                  {skill.source === 'user' && skill.hasGit && (
                    <Tooltip title={t('skills.card.pullTooltip')}>
                      <span>
                        <IconActionButton size="small" color="primary" onClick={() => handlePull(skill)} disabled={pullingName === skill.name}>
                          {pullingName === skill.name ? <CircularProgress size={14} /> : <RefreshIcon sx={{ fontSize: 14 }} />}
                        </IconActionButton>
                      </span>
                    </Tooltip>
                  )}
                  {skill.source === 'user' && (
                    <Tooltip title={t('skills.card.deleteTooltip')}>
                      <IconActionButton size="small" color="error" onClick={() => setDeleteTarget(skill.name)}>
                        <DeleteIcon sx={{ fontSize: 14 }} />
                      </IconActionButton>
                    </Tooltip>
                  )}
                </Box>
                </Box>
              </Box>
            ))}
          </Box>
        </Paper>
      )}

      {/* ── Detail Drawer ── */}
      <Drawer
        anchor="right"
        open={!!drawerSkill}
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
        {drawerSkill && (
          <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Drawer header */}
            <Box sx={{ px: { xs: 1.5, sm: 2 }, py: 1.5, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: { xs: 'flex-start', sm: 'center' }, gap: { xs: 1, sm: 1.5 }, flexWrap: 'wrap' }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.3 }} noWrap>
                    {drawerSkill.displayName}
                  </Typography>
                  <Chip
                    label={
                      drawerSkill.source === 'builtin' ? t('skills.card.sourceBuiltin')
                        : drawerSkill.source === 'repo' ? t('skills.card.sourceRepo')
                          : t('skills.card.sourceUser')
                    }
                    size="small"
                    color={drawerSkill.source === 'builtin' ? 'primary' : drawerSkill.source === 'repo' ? 'secondary' : 'success'}
                    variant="outlined"
                    sx={{ fontSize: '0.65rem', height: 20 }}
                  />
                  {autoInjectSet.has(drawerSkill.name) && (
                    <Chip
                      label={t('skills.autoInject.badge')}
                      size="small"
                      sx={{ fontSize: '0.6rem', height: 18, bgcolor: 'warning.main', color: 'warning.contrastText', fontWeight: 600 }}
                    />
                  )}
                  {drawerSkill.hasGit && (
                    <GitHubIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
                  )}
                </Box>
                {drawerSkill.displayName !== drawerSkill.name && (
                  <Typography variant="caption" color="text.disabled">{drawerSkill.name}</Typography>
                )}
              </Box>
              <Tooltip title={t('skills.drawer.syncToWorkspaces')}>
                <span>
                  <IconActionButton
                    size="small"
                    onClick={() => handleSyncToWorkspaces(drawerSkill.name)}
                    disabled={syncingSkill === drawerSkill.name}
                  >
                    {syncingSkill === drawerSkill.name ? <CircularProgress size={16} /> : <SyncIcon fontSize="small" />}
                  </IconActionButton>
                </span>
              </Tooltip>
              <Tooltip title={t('skills.drawer.autoInject')}>
                <Switch
                  size="small"
                  checked={autoInjectSet.has(drawerSkill.name)}
                  onChange={(_, checked) => toggleAutoInject(drawerSkill.name, checked)}
                  color="warning"
                />
              </Tooltip>
              <IconActionButton size="small" onClick={closeDrawer}>
                <CloseIcon fontSize="small" />
              </IconActionButton>
            </Box>

            {/* Drawer body: file tree + content pane */}
            <Box sx={{ flex: 1, display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, overflow: 'hidden' }}>
              {/* ── Left: File tree ── */}
              <Box
                sx={{
                  width: { xs: '100%', sm: 200 },
                  minWidth: { xs: 0, sm: 200 },
                  maxHeight: { xs: 180, sm: 'none' },
                  borderRight: { xs: 0, sm: '1px solid' },
                  borderBottom: { xs: '1px solid', sm: 0 },
                  borderColor: 'divider',
                  overflow: 'auto',
                  bgcolor: theme => alpha(theme.palette.background.default, 0.5),
                }}
              >
                <Box sx={{ px: 1.5, py: 1, display: 'flex', alignItems: 'center', gap: 0.5, position: { xs: 'sticky', sm: 'static' }, top: 0, bgcolor: theme => alpha(theme.palette.background.default, 0.88), zIndex: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    {t('skills.drawer.files')}
                  </Typography>
                  <Typography variant="caption" color="text.disabled">
                    ({t('skills.drawer.fileCount', { count: drawerFiles.filter(e => e.type === 'file').length })})
                  </Typography>
                </Box>
                {drawerFilesLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                    <CircularProgress size={18} />
                  </Box>
                ) : drawerFiles.length === 0 ? (
                  <Typography variant="caption" color="text.disabled" sx={{ px: 1.5 }}>
                    {t('skills.drawer.emptyDir')}
                  </Typography>
                ) : (
                  <List dense disablePadding sx={{ pb: 1 }}>
                    {drawerFiles.map(entry => (
                      <ListItemButton
                        key={entry.rel_path}
                        selected={selectedFile === entry.rel_path}
                        disabled={entry.type === 'dir'}
                        onClick={() => {
                          if (entry.type === 'file') {
                            selectFile(drawerSkill, entry.rel_path)
                          }
                        }}
                        sx={{
                          pl: 1 + (entry.rel_path.split('/').length - 1) * 1.5,
                          py: 0.25,
                          minHeight: 30,
                          '&.Mui-selected': {
                            bgcolor: theme => alpha(theme.palette.primary.main, 0.12),
                          },
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 24 }}>
                          {entry.type === 'dir' ? (
                            <FolderIcon sx={{ fontSize: 16, color: 'text.disabled' }} />
                          ) : entry.name === 'SKILL.md' ? (
                            <SkillMdIcon sx={{ fontSize: 16, color: 'primary.main' }} />
                          ) : (
                            <FileIcon sx={{ fontSize: 16, color: 'text.disabled' }} />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={entry.name}
                          primaryTypographyProps={{
                            variant: 'caption',
                            fontWeight: entry.name === 'SKILL.md' ? 600 : 400,
                            noWrap: true,
                            color: entry.type === 'dir' ? 'text.disabled' : 'text.primary',
                          }}
                        />
                        {entry.type === 'file' && selectedFile === entry.rel_path && dirty && (
                          <Box
                            sx={{
                              width: 6,
                              height: 6,
                              borderRadius: '50%',
                              bgcolor: 'warning.main',
                              flexShrink: 0,
                              ml: 0.5,
                            }}
                          />
                        )}
                      </ListItemButton>
                    ))}
                  </List>
                )}
              </Box>

              {/* ── Right: Content pane ── */}
              <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0, minHeight: { xs: 0, sm: 'auto' } }}>
                {/* Content toolbar */}
                {selectedFile && (
                  <Box
                    sx={{
                      px: { xs: 1, sm: 1.5 },
                      py: 0.75,
                      display: 'flex',
                      alignItems: { xs: 'stretch', sm: 'center' },
                      gap: 0.5,
                      flexWrap: 'wrap',
                      borderBottom: '1px solid',
                      borderColor: 'divider',
                      bgcolor: theme => alpha(theme.palette.background.default, 0.3),
                    }}
                  >
                    <Typography variant="caption" sx={{ fontWeight: 500, flex: { xs: '1 1 100%', sm: 1 }, overflowWrap: 'anywhere' }} noWrap={!isMobile}>
                      {selectedFile}
                    </Typography>

                    {dirty && (
                      <Chip
                        label={t('skills.drawer.modified')}
                        size="small"
                        color="warning"
                        sx={{ height: 18, fontSize: '0.6rem' }}
                      />
                    )}

                    {drawerSkill.source !== 'user' && (
                      <Chip
                        label={t('skills.drawer.readOnly')}
                        size="small"
                        variant="outlined"
                        sx={{ height: 18, fontSize: '0.6rem' }}
                      />
                    )}

                    {/* Source / Preview toggle */}
                    {isTextFile(selectedFile) && (
                      <SegmentedControl
                        density="tight"
                        value={editing ? 'source' : drawerViewMode}
                        options={[
                          {
                            value: 'preview',
                            icon: <PreviewIcon sx={{ fontSize: 16 }} />,
                            tooltip: t('skills.drawer.preview'),
                            ariaLabel: t('skills.drawer.preview'),
                            iconOnly: true,
                          },
                          {
                            value: 'source',
                            icon: <CodeIcon sx={{ fontSize: 16 }} />,
                            tooltip: t('skills.drawer.source_code'),
                            ariaLabel: t('skills.drawer.source_code'),
                            iconOnly: true,
                          },
                        ]}
                        onChange={v => {
                          if (v === 'source' || v === 'preview') {
                            setDrawerViewMode(v)
                            if (v === 'preview') setEditing(false)
                          }
                        }}
                        disabled={editing}
                      />
                    )}

                    {/* Edit / Save for user skills */}
                    {drawerSkill.source === 'user' && isTextFile(selectedFile) && (
                      editing ? (
                        <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap' }}>
                          <ActionButton
                            size="small"
                            variant="contained"
                            startIcon={saving ? <CircularProgress size={12} color="inherit" /> : <SaveIcon sx={{ fontSize: 14 }} />}
                            onClick={handleSave}
                            disabled={saving || !dirty}
                            sx={{ minWidth: 0, px: 1, py: 0.25, fontSize: '0.7rem' }}
                          >
                            {saving ? t('skills.drawer.saving') : t('skills.drawer.save')}
                          </ActionButton>
                          <ActionButton
                            size="small"
                            variant="outlined"
                            onClick={() => {
                              setEditing(false)
                              setEditBuffer(fileContent ?? '')
                              setDirty(false)
                              setDrawerViewMode('source')
                            }}
                            disabled={saving}
                            sx={{ minWidth: 0, px: 1, py: 0.25, fontSize: '0.7rem' }}
                          >
                            {t('skills.drawer.cancel_edit')}
                          </ActionButton>
                        </Stack>
                      ) : (
                        <Tooltip title={t('skills.drawer.edit')}>
                          <IconActionButton
                            size="small"
                            onClick={() => {
                              setEditing(true)
                              setEditBuffer(fileContent ?? '')
                              setDirty(false)
                              setDrawerViewMode('source')
                            }}
                          >
                            <EditIcon sx={{ fontSize: 16 }} />
                          </IconActionButton>
                        </Tooltip>
                      )
                    )}
                  </Box>
                )}

                {/* Content body */}
                <Box sx={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
                  {!selectedFile ? (
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 1 }}>
                      <ExtensionIcon sx={{ fontSize: 48, opacity: 0.15 }} />
                      <Typography variant="body2" color="text.disabled">
                        {t('skills.drawer.noContent')}
                      </Typography>
                    </Box>
                  ) : fileLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                      <CircularProgress size={24} />
                    </Box>
                  ) : !isTextFile(selectedFile) ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                      <Typography variant="body2" color="text.disabled">
                        {t('skills.drawer.binaryFile')}
                      </Typography>
                    </Box>
                  ) : editing ? (
                    /* Edit mode: Monaco Editor */
                    <Editor
                      key={`edit-${selectedFile}`}
                      height="100%"
                      language={getMonacoLanguage(selectedFile)}
                      value={editBuffer}
                      onChange={v => {
                        const val = v ?? ''
                        setEditBuffer(val)
                        setDirty(val !== (fileContent ?? ''))
                      }}
                      theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'vs'}
                      options={{
                        minimap: { enabled: false },
                        fontSize: 13,
                        lineNumbers: 'on',
                        wordWrap: 'on',
                        scrollBeyondLastLine: false,
                        renderLineHighlight: 'none',
                        automaticLayout: true,
                      }}
                    />
                  ) : drawerViewMode === 'source' ? (
                    /* Source view: read-only Monaco */
                    <Editor
                      key={`readonly-${selectedFile}`}
                      height="100%"
                      language={getMonacoLanguage(selectedFile)}
                      value={fileContent ?? ''}
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
                      }}
                    />
                  ) : (
                    /* Preview view */
                    fileContent !== null && selectedFile.toLowerCase().endsWith('.md') ? (
                      <SkillContentPanel raw={fileContent} />
                    ) : (
                      <Editor
                        key={`preview-${selectedFile}`}
                        height="100%"
                        language={getMonacoLanguage(selectedFile)}
                        value={fileContent ?? ''}
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
                        }}
                      />
                    )
                  )}
                </Box>
              </Box>
            </Box>
          </Box>
        )}
      </Drawer>

      {/* ── Unsaved Changes Dialog ── */}
      <Dialog open={!!unsavedDialogTarget} onClose={() => setUnsavedDialogTarget(null)}>
        <DialogTitle>{t('skills.drawer.unsavedTitle')}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t('skills.drawer.unsavedConfirm')}</DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <ActionButton onClick={() => setUnsavedDialogTarget(null)}>
            {t('skills.drawer.keepEditing')}
          </ActionButton>
          <ActionButton variant="contained" color="warning" onClick={handleDiscardAndSwitch}>
            {t('skills.drawer.discard')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      {/* ── Clone Dialog ── */}
      <Dialog
        open={cloneDialogOpen}
        onClose={() => !cloneMutation.isPending && setCloneDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t('skills.cloneDialog.title')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField
              label={t('skills.cloneDialog.urlLabel')}
              placeholder="https://github.com/user/my-skill.git"
              value={cloneUrl}
              onChange={e => handleCloneUrlChange(e.target.value)}
              fullWidth
              autoFocus
              disabled={cloneMutation.isPending}
            />
            <TextField
              label={t('skills.cloneDialog.dirLabel')}
              helperText={
                cloneTargetDir
                  ? t('skills.cloneDialog.dirHintSaving', { dir: cloneTargetDir })
                  : t('skills.cloneDialog.dirHintAuto')
              }
              value={cloneTargetDir}
              onChange={e => {
                setCloneTargetDir(e.target.value)
                setCloneUrlTouched(true)
              }}
              fullWidth
              disabled={cloneMutation.isPending}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <ActionButton
            onClick={() => {
              setCloneDialogOpen(false)
              setCloneUrl('')
              setCloneTargetDir('')
              setCloneUrlTouched(false)
            }}
            disabled={cloneMutation.isPending}
          >
            {t('skills.cloneDialog.cancel')}
          </ActionButton>
          <ActionButton
            variant="contained"
            onClick={() => cloneMutation.mutate()}
            disabled={cloneMutation.isPending || !cloneUrl.trim() || !cloneTargetDir.trim()}
            startIcon={cloneMutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            {cloneMutation.isPending ? t('skills.cloneDialog.cloning') : t('skills.cloneDialog.cloneBtn')}
          </ActionButton>
        </DialogActions>
      </Dialog>

      {/* ── Delete Confirm Dialog ── */}
      <Dialog open={!!deleteTarget} onClose={() => !deleteMutation.isPending && setDeleteTarget(null)}>
        <DialogTitle>{t('skills.deleteDialog.title')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t('skills.deleteDialog.content', { name: deleteTarget })}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <ActionButton onClick={() => setDeleteTarget(null)} disabled={deleteMutation.isPending}>
            {t('skills.deleteDialog.cancel')}
          </ActionButton>
          <ActionButton
            variant="contained"
            color="error"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget)}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? <CircularProgress size={20} /> : t('skills.deleteDialog.delete')}
          </ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
