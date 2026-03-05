import { useState, useMemo, useRef, useCallback } from 'react'
import {
  Box,
  Button,
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
  IconButton,
  Tooltip,
  TextField,
  ToggleButtonGroup,
  ToggleButton,
  InputAdornment,
  Divider,
  Paper,
  Switch,
  Drawer,
} from '@mui/material'
import {
  Extension as ExtensionIcon,
  Delete as DeleteIcon,
  GitHub as GitHubIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Search as SearchIcon,
  ViewModule as GridViewIcon,
  Upload as UploadIcon,
  Close as CloseIcon,
  AutoAwesome as AutoInjectIcon,
  Visibility as ViewIcon,
  FormatListBulleted as ListViewIcon,
  Inventory2 as BuiltinIcon,
  FolderCopy as UserIcon,
  HelpOutline as HelpIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { skillsLibraryApi, builtinSkillApi, AllSkillItem, SkillItem } from '../../services/api/workspace'
import { useNotification } from '../../hooks/useNotification'
import { CARD_VARIANTS } from '../../theme/variants'
import MarkdownRenderer from '../../components/common/MarkdownRenderer'

// ─── Types ───────────────────────────────────────────────────

interface UnifiedSkill {
  name: string
  displayName: string
  description: string
  source: 'builtin' | 'user'
  hasGit: boolean
  repoUrl?: string
  treePath?: string
}

interface SkillMdData {
  frontmatter: Record<string, string>
  body: string
}

type SourceFilter = 'all' | 'builtin' | 'user'
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

// ─── Stat Card ──────────────────────────────────────────────

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
        minWidth: 140,
        flex: '1 1 0',
      }}
    >
      <Box
        sx={{
          width: 36,
          height: 36,
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

// ─── Main Page ──────────────────────────────────────────────

export default function SkillsLibraryPage() {
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('card')
  const [searchQuery, setSearchQuery] = useState('')
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')

  // Drawer state
  const [drawerSkill, setDrawerSkill] = useState<UnifiedSkill | null>(null)
  const [drawerContent, setDrawerContent] = useState<string | null>(null)
  const [drawerLoading, setDrawerLoading] = useState(false)

  // Dialog state
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [cloneDialogOpen, setCloneDialogOpen] = useState(false)
  const [cloneUrl, setCloneUrl] = useState('')
  const [cloneTargetDir, setCloneTargetDir] = useState('')
  const [cloneUrlTouched, setCloneUrlTouched] = useState(false)

  // Pull state
  const [pullingName, setPullingName] = useState<string | null>(null)

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
    autoInject: autoInjectList.length,
  }), [unifiedSkills, autoInjectList])

  const isLoading = loadingAll || loadingBuiltin

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

  const openDrawer = useCallback(
    async (skill: UnifiedSkill) => {
      setDrawerSkill(skill)
      setDrawerContent(null)
      setDrawerLoading(true)
      try {
        let content: string
        if (skill.source === 'builtin') {
          content = await builtinSkillApi.getContent(skill.name)
        } else if (skill.treePath) {
          content = await skillsLibraryApi.getContent(skill.treePath)
        } else {
          content = await skillsLibraryApi.getReadme(skill.name)
        }
        setDrawerContent(content)
      } catch {
        setDrawerContent('')
      } finally {
        setDrawerLoading(false)
      }
    },
    [],
  )

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

  const handleRefresh = () => {
    refetchAll()
    refetchBuiltin()
    refetchTree()
    refetchAutoInject()
  }

  // ── Render ────────────────────────────────────────────────

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* Stat cards */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <StatCard label={t('skills.statBuiltin')} value={stats.builtin} icon={<BuiltinIcon sx={{ fontSize: 20 }} />} color="#5c6bc0" />
        <StatCard label={t('skills.statUser')} value={stats.user} icon={<UserIcon sx={{ fontSize: 20 }} />} color="#26a69a" />
        <StatCard label={t('skills.statAutoInject')} value={stats.autoInject} icon={<AutoInjectIcon sx={{ fontSize: 20 }} />} color="#ef6c00" />
      </Box>

      {/* Toolbar */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2.5, flexWrap: 'wrap' }}>
        {/* Search */}
        <TextField
          size="small"
          placeholder={t('skills.search.placeholder')}
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          sx={{ width: 240 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: searchQuery ? (
              <InputAdornment position="end">
                <IconButton size="small" onClick={() => setSearchQuery('')}>
                  <CloseIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </InputAdornment>
            ) : undefined,
          }}
        />

        {/* Source filter */}
        <ToggleButtonGroup
          value={sourceFilter}
          exclusive
          onChange={(_, v: SourceFilter | null) => { if (v !== null) setSourceFilter(v) }}
          size="small"
        >
          <ToggleButton value="all" sx={{ px: 1.5, py: 0.5, fontSize: '0.8rem' }}>{t('skills.filter.all')}</ToggleButton>
          <ToggleButton value="builtin" sx={{ px: 1.5, py: 0.5, fontSize: '0.8rem' }}>{t('skills.filter.builtin')}</ToggleButton>
          <ToggleButton value="user" sx={{ px: 1.5, py: 0.5, fontSize: '0.8rem' }}>{t('skills.filter.user')}</ToggleButton>
        </ToggleButtonGroup>

        {/* View mode */}
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={(_, v: ViewMode | null) => { if (v !== null) setViewMode(v) }}
          size="small"
        >
          <ToggleButton value="card">
            <Tooltip title={t('skills.toolbar.cardView')}>
              <GridViewIcon fontSize="small" />
            </Tooltip>
          </ToggleButton>
          <ToggleButton value="list">
            <Tooltip title={t('skills.toolbar.listView')}>
              <ListViewIcon fontSize="small" />
            </Tooltip>
          </ToggleButton>
        </ToggleButtonGroup>

        <Box sx={{ flexGrow: 1 }} />

        {/* Actions */}
        <Tooltip title={t('skills.toolbar.refresh')}>
          <IconButton onClick={handleRefresh} disabled={isLoading} size="small">
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>

        <input type="file" accept=".zip" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileChange} />
        <Tooltip title={t('skills.toolbar.uploadTooltip')}>
          <Button
            variant="outlined"
            startIcon={uploadMutation.isPending ? <CircularProgress size={16} color="inherit" /> : <UploadIcon />}
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadMutation.isPending}
            size="small"
          >
            {t('skills.toolbar.uploadBtn')}
          </Button>
        </Tooltip>

        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCloneDialogOpen(true)} size="small">
          {t('skills.toolbar.addBtn')}
        </Button>

        <Tooltip title={t('skills.pageDesc')} arrow>
          <IconButton size="small" sx={{ color: 'text.disabled' }}>
            <HelpIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Error */}
      {errorAll && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {t('skills.error.loadFailed', { message: (errorAll as Error).message })}
        </Alert>
      )}

      {/* Loading */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}>
          <CircularProgress />
        </Box>
      ) : filteredSkills.length === 0 ? (
        /* Empty state */
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', pt: 8, gap: 2 }}>
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
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 2 }}>
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
                    label={skill.source === 'builtin' ? t('skills.card.sourceBuiltin') : t('skills.card.sourceUser')}
                    size="small"
                    color={skill.source === 'builtin' ? 'primary' : 'success'}
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
                      <IconButton size="small" color="primary" onClick={() => handlePull(skill)} disabled={pullingName === skill.name}>
                        {pullingName === skill.name ? <CircularProgress size={14} /> : <RefreshIcon sx={{ fontSize: 16 }} />}
                      </IconButton>
                    </span>
                  </Tooltip>
                )}
                {skill.source === 'user' && (
                  <Tooltip title={t('skills.card.deleteTooltip')}>
                    <IconButton size="small" color="error" onClick={() => setDeleteTarget(skill.name)}>
                      <DeleteIcon sx={{ fontSize: 16 }} />
                    </IconButton>
                  </Tooltip>
                )}
                <Tooltip title={t('skills.card.viewTooltip')}>
                  <IconButton size="small" onClick={() => openDrawer(skill)}>
                    <ViewIcon sx={{ fontSize: 16 }} />
                  </IconButton>
                </Tooltip>
              </Box>
            </Card>
          ))}
        </Box>
      ) : (
        /* ── List View ── */
        <Paper variant="outlined" sx={{ borderRadius: 2, overflow: 'hidden' }}>
          {filteredSkills.map((skill, index) => (
            <Box key={skill.name}>
              {index > 0 && <Divider />}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  px: 2,
                  py: 1.25,
                  gap: 1.5,
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'action.hover' },
                  transition: 'background-color 0.15s',
                }}
                onClick={() => openDrawer(skill)}
              >
                {/* Source chip */}
                <Chip
                  label={skill.source === 'builtin' ? t('skills.card.sourceBuiltin') : t('skills.card.sourceUser')}
                  size="small"
                  color={skill.source === 'builtin' ? 'primary' : 'success'}
                  variant="outlined"
                  sx={{ fontSize: '0.7rem', height: 22, width: 52, flexShrink: 0 }}
                />

                {/* Name + desc */}
                <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, flexShrink: 0 }}>
                      {skill.displayName}
                    </Typography>
                    {skill.displayName !== skill.name && (
                      <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
                        ({skill.name})
                      </Typography>
                    )}
                    {skill.description && (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
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
                <Box onClick={e => e.stopPropagation()} sx={{ flexShrink: 0 }}>
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
                <Box sx={{ display: 'flex', gap: 0.25, flexShrink: 0 }} onClick={e => e.stopPropagation()}>
                  {skill.source === 'user' && skill.hasGit && (
                    <Tooltip title={t('skills.card.pullTooltip')}>
                      <span>
                        <IconButton size="small" color="primary" onClick={() => handlePull(skill)} disabled={pullingName === skill.name}>
                          {pullingName === skill.name ? <CircularProgress size={14} /> : <RefreshIcon sx={{ fontSize: 14 }} />}
                        </IconButton>
                      </span>
                    </Tooltip>
                  )}
                  {skill.source === 'user' && (
                    <Tooltip title={t('skills.card.deleteTooltip')}>
                      <IconButton size="small" color="error" onClick={() => setDeleteTarget(skill.name)}>
                        <DeleteIcon sx={{ fontSize: 14 }} />
                      </IconButton>
                    </Tooltip>
                  )}
                </Box>
              </Box>
            </Box>
          ))}
        </Paper>
      )}

      {/* ── Detail Drawer ── */}
      <Drawer
        anchor="right"
        open={!!drawerSkill}
        onClose={() => setDrawerSkill(null)}
        PaperProps={{
          sx: {
            width: { xs: '100%', sm: 500 },
            maxWidth: '100vw',
            mt: { xs: '56px', sm: '64px' },
            height: { xs: 'calc(100% - 56px)', sm: 'calc(100% - 64px)' },
          },
        }}
      >
        {drawerSkill && (
          <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Drawer header */}
            <Box sx={{ px: 2.5, py: 2, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.3 }}>
                  {drawerSkill.displayName}
                </Typography>
                {drawerSkill.displayName !== drawerSkill.name && (
                  <Typography variant="caption" color="text.disabled">
                    {drawerSkill.name}
                  </Typography>
                )}
                <Stack direction="row" spacing={0.75} sx={{ mt: 1 }}>
                  <Chip
                    label={drawerSkill.source === 'builtin' ? t('skills.card.sourceBuiltin') : t('skills.card.sourceUser')}
                    size="small"
                    color={drawerSkill.source === 'builtin' ? 'primary' : 'success'}
                    variant="outlined"
                    sx={{ fontSize: '0.7rem', height: 22 }}
                  />
                  {autoInjectSet.has(drawerSkill.name) && (
                    <Chip
                      label={t('skills.autoInject.badge')}
                      size="small"
                      sx={{ fontSize: '0.65rem', height: 20, bgcolor: 'warning.main', color: 'warning.contrastText', fontWeight: 600 }}
                    />
                  )}
                  {drawerSkill.hasGit && (
                    <Chip
                      icon={<GitHubIcon sx={{ fontSize: '14px !important' }} />}
                      label="git"
                      size="small"
                      sx={{ height: 22, fontSize: '0.7rem' }}
                    />
                  )}
                </Stack>
              </Box>
              <IconButton size="small" onClick={() => setDrawerSkill(null)}>
                <CloseIcon />
              </IconButton>
            </Box>

            {/* Drawer: auto-inject control */}
            <Box sx={{ px: 2.5, py: 1.5, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1 }}>
              <AutoInjectIcon sx={{ fontSize: 18, color: 'warning.main' }} />
              <Typography variant="body2" sx={{ fontWeight: 500, flex: 1 }}>
                {t('skills.drawer.autoInject')}
              </Typography>
              <Switch
                size="small"
                checked={autoInjectSet.has(drawerSkill.name)}
                onChange={(_, checked) => toggleAutoInject(drawerSkill.name, checked)}
                color="warning"
              />
            </Box>

            {/* Drawer body (SKILL.md content) */}
            <Box sx={{ flex: 1, overflow: 'auto' }}>
              {drawerLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : drawerContent !== null ? (
                drawerContent ? (
                  <SkillContentPanel raw={drawerContent} />
                ) : (
                  <Box sx={{ px: 2.5, py: 3 }}>
                    <Typography variant="body2" color="text.disabled">
                      {t('skills.drawer.noContent')}
                    </Typography>
                  </Box>
                )
              ) : null}
            </Box>
          </Box>
        )}
      </Drawer>

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
          <Button
            onClick={() => {
              setCloneDialogOpen(false)
              setCloneUrl('')
              setCloneTargetDir('')
              setCloneUrlTouched(false)
            }}
            disabled={cloneMutation.isPending}
          >
            {t('skills.cloneDialog.cancel')}
          </Button>
          <Button
            variant="contained"
            onClick={() => cloneMutation.mutate()}
            disabled={cloneMutation.isPending || !cloneUrl.trim() || !cloneTargetDir.trim()}
            startIcon={cloneMutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            {cloneMutation.isPending ? t('skills.cloneDialog.cloning') : t('skills.cloneDialog.cloneBtn')}
          </Button>
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
          <Button onClick={() => setDeleteTarget(null)} disabled={deleteMutation.isPending}>
            {t('skills.deleteDialog.cancel')}
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget)}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? <CircularProgress size={20} /> : t('skills.deleteDialog.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
