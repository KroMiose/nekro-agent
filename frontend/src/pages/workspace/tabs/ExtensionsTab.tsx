import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Chip,
  TextField,
  CircularProgress,
  Alert,
  Stack,
  Divider,
  IconButton,
  Tooltip,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  InputAdornment,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  ToggleButtonGroup,
  ToggleButton,
  Drawer,
  alpha,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import {
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Delete as DeleteIcon,
  ArrowForward as ArrowForwardIcon,
  Extension as ExtensionIcon,
  Add as AddIcon,
  Search as SearchIcon,
  Edit as EditIcon,
  Sync as SyncIcon,
  Close as CloseIcon,
  Visibility as ViewIcon,
  InsertDriveFileOutlined as FileIcon,
  FolderOutlined as FolderIcon,
  Description as SkillMdIcon,
  Code as CodeIcon,
  PreviewOutlined as PreviewIcon,
  SystemUpdateAlt as UpdateIcon,
} from '@mui/icons-material'
import { Editor } from '@monaco-editor/react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  workspaceApi,
  skillsLibraryApi,
  dynamicSkillApi,
  WorkspaceDetail,
  AllSkillItem,
  DynamicSkillItem,
  DynamicSkillDirEntry,
} from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS } from '../../../theme/variants'
import { useTranslation } from 'react-i18next'
import MarkdownRenderer from '../../../components/common/MarkdownRenderer'

type SourceFilter = 'all' | 'builtin' | 'user' | 'repo'

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
  if (dotIdx >= 0) return EXT_LANG_MAP[lower.slice(dotIdx)] ?? 'plaintext'
  return 'plaintext'
}

const TEXT_EXTS = ['.md', '.txt', '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini', '.sh', '.bash', '.py', '.js', '.ts', '.html', '.css', '.xml', '.csv', '.env', '.conf', '.rst', '.log']

function isTextFile(name: string): boolean {
  const lower = name.toLowerCase()
  return TEXT_EXTS.some(ext => lower.endsWith(ext)) || !lower.includes('.')
}

function parseSkillMd(raw: string): { frontmatter: Record<string, string>; body: string } {
  const lines = raw.split('\n')
  const frontmatter: Record<string, string> = {}
  let body = raw
  if (lines[0]?.trim() === '---') {
    let endLine = -1
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim() === '---') { endLine = i; break }
      const colonIdx = lines[i].indexOf(':')
      if (colonIdx > 0) {
        const key = lines[i].slice(0, colonIdx).trim()
        const value = lines[i].slice(colonIdx + 1).trim().replace(/^["']|["']$/g, '')
        frontmatter[key] = value
      }
    }
    if (endLine > 0) body = lines.slice(endLine + 1).join('\n').trimStart()
  }
  return { frontmatter, body }
}

function SkillPreviewPanel({ raw }: { raw: string }) {
  const { t } = useTranslation('workspace')
  const { frontmatter, body } = useMemo(() => parseSkillMd(raw), [raw])
  const allowedTools = frontmatter['allowed-tools']?.split(',').map(s => s.trim()).filter(Boolean) ?? []
  const fmDesc = frontmatter['description']
  const otherFields = Object.entries(frontmatter).filter(([k]) => !['name', 'description', 'allowed-tools'].includes(k))

  return (
    <Box>
      {Object.keys(frontmatter).length > 0 && (
        <Box sx={{ px: 2.5, py: 1.5, bgcolor: 'action.hover', borderBottom: '1px solid', borderColor: 'divider' }}>
          {allowedTools.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
              <Typography variant="caption" color="text.secondary">{t('skills.content.allowedTools')}</Typography>
              {allowedTools.map(tool => (
                <Chip key={tool} label={tool} size="small" variant="outlined" sx={{ height: 20, fontSize: 11, borderColor: 'divider', color: 'text.secondary' }} />
              ))}
            </Box>
          )}
          {fmDesc && <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>{fmDesc}</Typography>}
          {otherFields.map(([k, v]) => (
            <Typography key={k} variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.25 }}>{k}: {v}</Typography>
          ))}
        </Box>
      )}
      {body ? (
        <Box sx={{ px: 2.5, py: 2 }}><MarkdownRenderer>{body}</MarkdownRenderer></Box>
      ) : (
        <Box sx={{ px: 2.5, py: 2 }}>
          <Typography variant="body2" color="text.disabled">{t('skills.content.noContent')}</Typography>
        </Box>
      )}
    </Box>
  )
}

export default function ExtensionsTab({
  workspace,
  onNavigateToComm,
}: {
  workspace: WorkspaceDetail
  onNavigateToComm: (prefill: string) => void
}) {
  const theme = useTheme()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const queryClient = useQueryClient()

  // ── 已部署技能列表（本地状态）──
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])
  const [syncing, setSyncing] = useState(false)

  // ── 添加技能对话框 ──
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [addSearch, setAddSearch] = useState('')
  const [addSelected, setAddSelected] = useState<Set<string>>(new Set())
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')

  // ── 动态技能 ──
  const [dynamicSkills, setDynamicSkills] = useState<DynamicSkillItem[]>([])
  const [deletingDynamic, setDeletingDynamic] = useState<string | null>(null)
  const [promotingDynamic, setPromotingDynamic] = useState<string | null>(null)
  const [deleteConfirmDynamic, setDeleteConfirmDynamic] = useState<string | null>(null)

  // ── 动态技能详情 Drawer ──
  const [drawerDynamic, setDrawerDynamic] = useState<DynamicSkillItem | null>(null)
  const [drawerFiles, setDrawerFiles] = useState<DynamicSkillDirEntry[]>([])
  const [drawerFilesLoading, setDrawerFilesLoading] = useState(false)
  const [dynSelectedFile, setDynSelectedFile] = useState<string | null>(null)
  const [dynFileContent, setDynFileContent] = useState<string | null>(null)
  const [dynFileLoading, setDynFileLoading] = useState(false)
  const [dynViewMode, setDynViewMode] = useState<'preview' | 'source'>('preview')
  const [dynEditing, setDynEditing] = useState(false)
  const [dynEditBuffer, setDynEditBuffer] = useState('')
  const [dynDirty, setDynDirty] = useState(false)
  const [dynSaving, setDynSaving] = useState(false)
  const [dynUnsavedTarget, setDynUnsavedTarget] = useState<string | null>(null)

  // ── CC设计对话框 ──
  const [ccDesignOpen, setCcDesignOpen] = useState(false)

  // ── 所有可用技能候选（内置 + 用户库）──
  const { data: allSkills = [] } = useQuery({
    queryKey: ['skills-all'],
    queryFn: () => skillsLibraryApi.getAll(),
  })

  // ── 自动注入列表 ──
  const { data: autoInjectList = [] } = useQuery({
    queryKey: ['skills-auto-inject'],
    queryFn: () => skillsLibraryApi.getAutoInject(),
  })
  const autoInjectSet = useMemo(() => new Set(autoInjectList), [autoInjectList])

  // ── 所有技能的 map（name -> AllSkillItem）──
  const allSkillsMap = useMemo<Record<string, AllSkillItem>>(
    () => Object.fromEntries(allSkills.map(s => [s.name, s])),
    [allSkills]
  )

  // ── 工作区已选技能（服务端，作为"原始状态"对比用）──
  const { data: serverSkills = [] } = useQuery({
    queryKey: ['workspace-skills', workspace.id],
    queryFn: () => workspaceApi.getWorkspaceSkills(workspace.id),
  })

  useEffect(() => {
    setSelectedSkills(serverSkills)
  }, [serverSkills])

  // ── 是否有未保存改动 ──
  const hasUnsavedChanges = useMemo(() => {
    if (selectedSkills.length !== serverSkills.length) return true
    return selectedSkills.some((s, i) => s !== serverSkills[i])
  }, [selectedSkills, serverSkills])

  // ── 加载动态技能 ──
  useEffect(() => {
    dynamicSkillApi.list(workspace.id).then(setDynamicSkills).catch(() => setDynamicSkills([]))
  }, [workspace.id])

  const refreshDynamicSkills = useCallback(() => {
    dynamicSkillApi.list(workspace.id).then(setDynamicSkills).catch(() => setDynamicSkills([]))
  }, [workspace.id])

  // ── 同步到沙盒 ──
  const handleSync = async () => {
    setSyncing(true)
    try {
      await workspaceApi.updateWorkspaceSkills(workspace.id, selectedSkills)
      await queryClient.invalidateQueries({ queryKey: ['workspace-skills', workspace.id] })
      notification.success(t('detail.extensions.notifications.syncSuccess'))
    } catch (err) {
      notification.error(t('detail.extensions.notifications.syncFailed', { message: (err as Error).message }))
    } finally {
      setSyncing(false)
    }
  }

  // ── 移除已部署技能 ──
  const handleRemoveSkill = (name: string) => {
    setSelectedSkills(prev => prev.filter(s => s !== name))
  }

  // ── 添加技能对话框 ──
  const handleOpenAddDialog = () => {
    setAddSearch('')
    setAddSelected(new Set())
    setSourceFilter('all')
    setAddDialogOpen(true)
  }

  const handleConfirmAdd = () => {
    if (addSelected.size === 0) {
      setAddDialogOpen(false)
      return
    }
    setSelectedSkills(prev => {
      const next = [...prev]
      addSelected.forEach(name => {
        if (!next.includes(name)) next.push(name)
      })
      return next
    })
    setAddDialogOpen(false)
  }

  // ── 添加对话框中可选的技能（排除已选，按 source 过滤）──
  const availableToAdd = useMemo(
    () => allSkills.filter(s => !selectedSkills.includes(s.name)),
    [allSkills, selectedSkills]
  )

  const filteredAvailable = useMemo(() => {
    let list = availableToAdd
    if (sourceFilter !== 'all') {
      list = list.filter(s => s.source === sourceFilter)
    }
    if (addSearch.trim()) {
      const q = addSearch.toLowerCase()
      list = list.filter(
        s =>
          s.name.toLowerCase().includes(q) ||
          s.display_name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q)
      )
    }
    // Auto-inject skills first
    return [...list].sort((a, b) => {
      const aAuto = autoInjectSet.has(a.name) ? 0 : 1
      const bAuto = autoInjectSet.has(b.name) ? 0 : 1
      return aAuto - bAuto
    })
  }, [availableToAdd, sourceFilter, addSearch, autoInjectSet])

  // ── 已部署列表详情 ──
  const selectedSkillsDetail = useMemo(
    () =>
      selectedSkills.map(name => {
        const info = allSkillsMap[name]
        return {
          name,
          display_name: info?.display_name ?? name,
          description: info?.description ?? '',
          source: info?.source ?? ('user' as 'builtin' | 'user'),
          isPending: !serverSkills.includes(name),
        }
      }),
    [selectedSkills, allSkillsMap, serverSkills]
  )

  // ── 判断动态技能是否已晋升到技能库 ──
  const isPromotedToLibrary = useCallback(
    (dirName: string) => {
      const item = allSkillsMap[dirName]
      return !!item && item.source === 'user'
    },
    [allSkillsMap],
  )

  // ── 动态技能操作 ──
  const confirmDeleteDynamic = async () => {
    if (!deleteConfirmDynamic) return
    setDeletingDynamic(deleteConfirmDynamic)
    try {
      await dynamicSkillApi.delete(workspace.id, deleteConfirmDynamic)
      notification.success(t('detail.extensions.notifications.deleteDynamicSuccess', { name: deleteConfirmDynamic }))
      setDeleteConfirmDynamic(null)
      refreshDynamicSkills()
    } catch (err) {
      notification.error(t('detail.extensions.notifications.deleteDynamicFailed', { message: (err as Error).message }))
    } finally {
      setDeletingDynamic(null)
    }
  }

  const handlePromoteDynamic = async (dirName: string, force = false) => {
    setPromotingDynamic(dirName)
    try {
      await dynamicSkillApi.promote(workspace.id, dirName, force)
      notification.success(
        force
          ? t('detail.extensions.notifications.updateLibrarySuccess', { name: dirName })
          : t('detail.extensions.notifications.promoteSuccess', { name: dirName }),
      )
      refreshDynamicSkills()
      queryClient.invalidateQueries({ queryKey: ['skills-all'] })
    } catch (err) {
      notification.error(t('detail.extensions.notifications.promoteFailed', { message: (err as Error).message }))
    } finally {
      setPromotingDynamic(null)
    }
  }

  // ── 动态技能详情 Drawer ──
  const loadDynFileContent = useCallback(
    async (dirName: string, relPath: string) => {
      setDynFileLoading(true)
      setDynFileContent(null)
      try {
        const content = await dynamicSkillApi.getFile(workspace.id, dirName, relPath)
        setDynFileContent(content)
        setDynEditBuffer(content)
        setDynDirty(false)
      } catch {
        setDynFileContent(null)
      } finally {
        setDynFileLoading(false)
      }
    },
    [workspace.id],
  )

  const selectDynFile = useCallback(
    (dirName: string, relPath: string) => {
      if (dynDirty) {
        setDynUnsavedTarget(relPath)
        return
      }
      setDynSelectedFile(relPath)
      setDynEditing(false)
      setDynViewMode('preview')
      loadDynFileContent(dirName, relPath)
    },
    [dynDirty, loadDynFileContent],
  )

  const openDynDrawer = useCallback(
    async (skill: DynamicSkillItem) => {
      setDrawerDynamic(skill)
      setDrawerFiles([])
      setDynSelectedFile(null)
      setDynFileContent(null)
      setDynEditing(false)
      setDynDirty(false)
      setDynViewMode('preview')
      setDrawerFilesLoading(true)
      try {
        const entries = await dynamicSkillApi.getDir(workspace.id, skill.dir_name)
        setDrawerFiles(entries)
        const skillMd = entries.find(e => e.type === 'file' && e.name === 'SKILL.md')
        if (skillMd) {
          setDynSelectedFile(skillMd.rel_path)
          loadDynFileContent(skill.dir_name, skillMd.rel_path)
        }
      } catch {
        setDrawerFiles([])
      } finally {
        setDrawerFilesLoading(false)
      }
    },
    [workspace.id, loadDynFileContent],
  )

  const closeDynDrawer = useCallback(() => {
    if (dynDirty) {
      setDynUnsavedTarget('__close__')
      return
    }
    setDrawerDynamic(null)
    setDynSelectedFile(null)
    setDynFileContent(null)
    setDynEditing(false)
    setDynDirty(false)
  }, [dynDirty])

  const handleDynSave = useCallback(async () => {
    if (!drawerDynamic || !dynSelectedFile) return
    setDynSaving(true)
    try {
      await dynamicSkillApi.saveFile(workspace.id, drawerDynamic.dir_name, dynSelectedFile, dynEditBuffer)
      setDynFileContent(dynEditBuffer)
      setDynDirty(false)
      setDynEditing(false)
      notification.success(t('detail.extensions.notifications.saveDynamicSuccess', { name: drawerDynamic.dir_name }))
      refreshDynamicSkills()
    } catch (err) {
      notification.error(t('detail.extensions.notifications.saveDynamicFailed', { message: (err as Error).message }))
    } finally {
      setDynSaving(false)
    }
  }, [drawerDynamic, dynSelectedFile, dynEditBuffer, workspace.id, notification, t, refreshDynamicSkills])

  const handleDynDiscardAndSwitch = useCallback(() => {
    const target = dynUnsavedTarget
    setDynDirty(false)
    setDynEditing(false)
    setDynUnsavedTarget(null)
    if (target === '__close__') {
      setDrawerDynamic(null)
      setDynSelectedFile(null)
      setDynFileContent(null)
    } else if (target && drawerDynamic) {
      setDynSelectedFile(target)
      setDynViewMode('preview')
      loadDynFileContent(drawerDynamic.dir_name, target)
    }
  }, [dynUnsavedTarget, drawerDynamic, loadDynFileContent])

  // ── CC 设计跳转 ──
  const handleCCDesignConfirm = () => {
    const prefillText = `请使用 skill-creator 技能指导，帮我设计一个新的 CC 技能。

我的技能需求：
（在这里描述你需要的技能功能，越详细越好）

设计完成后，请将技能目录创建在 ~/.claude/skills/dynamic/{suggested_name}/ 路径下，写入 SKILL.md，并向我报告创建结果（技能名称、描述、保存路径）。
注意：技能名称使用小写字母和连字符，不超过 64 字符。`
    setCcDesignOpen(false)
    onNavigateToComm(prefillText)
  }

  // ── MCP ──
  // JSONC 注释剥离（逐字符解析，正确处理字符串内的 //）
  const stripJsoncComments = (text: string): string => {
    let result = ''
    let i = 0
    let inString = false
    let escaped = false
    while (i < text.length) {
      const ch = text[i]
      if (escaped) { result += ch; escaped = false; i++; continue }
      if (ch === '\\' && inString) { result += ch; escaped = true; i++; continue }
      if (ch === '"') { inString = !inString; result += ch; i++; continue }
      if (!inString) {
        if (ch === '/' && text[i + 1] === '/') {
          while (i < text.length && text[i] !== '\n') i++
          continue
        }
        if (ch === '/' && text[i + 1] === '*') {
          i += 2
          while (i < text.length && !(text[i] === '*' && text[i + 1] === '/')) i++
          i += 2
          continue
        }
      }
      result += ch; i++
    }
    return result
  }

  const MCP_TEMPLATE = `{
  "mcpServers": {

    // ── npx 方式：运行 npm 包（Node.js，无需预装）──────────────────────────
    // 以 GitHub MCP Server 为例，更多官方包见：
    // https://github.com/modelcontextprotocol/servers
    // "github": {
    //   "command": "npx",
    //   "args": ["-y", "@modelcontextprotocol/server-github"],
    //   "env": {
    //     "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-pat>"
    //   }
    // },

    // ── uvx 方式：运行 Python 包（uv，无需预装）────────────────────────────
    // 以 mcp-server-fetch 为例（HTTP 请求与网页抓取）
    // "fetch": {
    //   "command": "uvx",
    //   "args": ["mcp-server-fetch"]
    // },

    // ── Docker 方式：容器化运行（隔离环境）────────────────────────────────
    // "my-service": {
    //   "command": "docker",
    //   "args": [
    //     "run", "--rm", "-i",
    //     "--network", "host",
    //     "my-mcp-image:latest"
    //   ]
    // },

    // ── 远程 SSE/HTTP 方式：连接已部署的远端 MCP 服务器 ──────────────────
    // "remote-mcp": {
    //   "url": "https://your-mcp-server.example.com/mcp",
    //   "headers": {
    //     "Authorization": "Bearer <your-token>"
    //   }
    // },

    // ── 本地脚本方式：直接运行本地文件（node / python）────────────────────
    // "local-server": {
    //   "command": "node",
    //   "args": ["/absolute/path/to/your-mcp-server.js"]
    // }

  }
}`

  const [mcpText, setMcpText] = useState('')
  const [mcpError, setMcpError] = useState<string | null>(null)
  const [savingMcp, setSavingMcp] = useState(false)
  const [mcpTemplateOpen, setMcpTemplateOpen] = useState(false)

  const { data: mcpData } = useQuery({
    queryKey: ['workspace-mcp', workspace.id],
    queryFn: () => workspaceApi.getMcpConfig(workspace.id),
  })

  useEffect(() => {
    if (mcpData !== undefined) setMcpText(JSON.stringify(mcpData, null, 2))
  }, [mcpData])

  const validateMcpText = (v: string): string | null => {
    try {
      JSON.parse(stripJsoncComments(v))
      return null
    } catch {
      return t('detail.extensions.mcpJsonError')
    }
  }

  const handleMcpChange = (v: string) => {
    setMcpText(v)
    setMcpError(validateMcpText(v))
  }

  const handleSaveMcp = async () => {
    const err = validateMcpText(mcpText)
    if (err) {
      notification.warning(t('detail.extensions.mcpJsonErrorFix'))
      return
    }
    setSavingMcp(true)
    try {
      await workspaceApi.updateMcpConfig(workspace.id, JSON.parse(stripJsoncComments(mcpText)))
      notification.success(t('detail.extensions.mcpSaveSuccess'))
    } catch (e) {
      notification.error(t('detail.extensions.mcpSaveFailed', { message: (e as Error).message }))
    } finally {
      setSavingMcp(false)
    }
  }

  const handleApplyTemplate = () => {
    setMcpText(MCP_TEMPLATE)
    setMcpError(null)
    setMcpTemplateOpen(false)
  }

  const ROW_SX = {
    display: 'flex',
    alignItems: 'center',
    px: 1.5,
    py: 0.75,
    borderRadius: 1,
    border: '1px solid',
    gap: 1,
  }

  return (
    <Stack spacing={2}>
      {/* 扩展技能卡片 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent>
          {/* 标题行 */}
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              {t('detail.extensions.skillsCardTitle')}
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Button
              size="small"
              variant={hasUnsavedChanges ? 'contained' : 'outlined'}
              startIcon={syncing ? <CircularProgress size={14} color="inherit" /> : <SyncIcon />}
              onClick={handleSync}
              disabled={syncing}
            >
              {t('detail.extensions.syncBtn')}
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<AddIcon sx={{ fontSize: 14 }} />}
              onClick={handleOpenAddDialog}
            >
              {t('detail.extensions.addSkillBtn')}
            </Button>
          </Box>

          {/* 已部署列表 */}
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.75, display: 'block', fontWeight: 500 }}>
            {t('detail.extensions.deployedLabel', { count: selectedSkills.length })}
          </Typography>
          {selectedSkillsDetail.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
              {t('detail.extensions.deployedEmpty')}
            </Typography>
          ) : (
            <Stack spacing={0.5} sx={{ mb: 2 }}>
              {selectedSkillsDetail.map(skill => (
                <Box
                  key={skill.name}
                  sx={{
                    ...ROW_SX,
                    borderColor: skill.isPending
                      ? 'warning.main'
                      : skill.source === 'builtin' ? 'primary.main' : skill.source === 'repo' ? 'secondary.main' : 'success.main',
                    bgcolor: skill.isPending ? 'warning.main' + '12' : 'action.selected',
                  }}
                >
                  <Chip
                    label={
                      skill.source === 'builtin' ? t('detail.extensions.skillChipBuiltin')
                        : skill.source === 'repo' ? t('detail.extensions.skillChipRepo')
                          : t('detail.extensions.skillChipUser')
                    }
                    size="small"
                    color={skill.source === 'builtin' ? 'primary' : skill.source === 'repo' ? 'secondary' : 'success'}
                    variant="outlined"
                    sx={{ fontSize: '0.65rem', height: 20, flexShrink: 0 }}
                  />
                  {skill.isPending && (
                    <Chip
                      label={t('detail.extensions.skillChipPending')}
                      size="small"
                      color="warning"
                      sx={{ fontSize: '0.65rem', height: 20, flexShrink: 0 }}
                    />
                  )}
                  {autoInjectSet.has(skill.name) && (
                    <Chip
                      label={t('detail.extensions.skillChipAutoInject')}
                      size="small"
                      sx={{
                        fontSize: '0.6rem',
                        height: 18,
                        bgcolor: 'warning.main',
                        color: 'warning.contrastText',
                        fontWeight: 600,
                        flexShrink: 0,
                      }}
                    />
                  )}
                  <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {skill.display_name !== skill.name ? `${skill.display_name} (${skill.name})` : skill.name}
                    </Typography>
                    {skill.description && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        {skill.description}
                      </Typography>
                    )}
                  </Box>
                  <Tooltip title={t('detail.extensions.removeTooltip')}>
                    <IconButton size="small" color="error" onClick={() => handleRemoveSkill(skill.name)}>
                      <DeleteIcon sx={{ fontSize: 15 }} />
                    </IconButton>
                  </Tooltip>
                </Box>
              ))}
            </Stack>
          )}

          {/* CC 创建技能区 */}
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.75 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
              {t('detail.extensions.ccCreatedLabel', { count: dynamicSkills.length })}
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Tooltip title={t('detail.extensions.refreshDynamicTooltip')}>
              <IconButton size="small" onClick={refreshDynamicSkills}>
                <RefreshIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </Tooltip>
          </Box>
          {dynamicSkills.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
              {t('detail.extensions.ccCreatedEmpty')}
            </Typography>
          ) : (
            <Stack spacing={0.5}>
              {dynamicSkills.map(skill => {
                const promoted = isPromotedToLibrary(skill.dir_name)
                return (
                  <Box key={skill.dir_name} sx={{ ...ROW_SX, borderColor: promoted ? 'success.main' : 'divider' }}>
                    <Chip
                      label={t('detail.extensions.skillChipCC')}
                      size="small"
                      color="secondary"
                      variant="outlined"
                      sx={{ fontSize: '0.65rem', height: 20, flexShrink: 0 }}
                    />
                    {promoted && (
                      <Chip
                        label={t('detail.extensions.skillChipPromoted')}
                        size="small"
                        color="success"
                        variant="outlined"
                        sx={{ fontSize: '0.6rem', height: 18, flexShrink: 0 }}
                      />
                    )}
                    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {skill.name || skill.dir_name}
                      </Typography>
                      {skill.description && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                          {skill.description}
                        </Typography>
                      )}
                    </Box>
                    <Box sx={{ display: 'flex', gap: 0.5, flexShrink: 0 }}>
                      <Tooltip title={t('detail.extensions.viewDetailTooltip')}>
                        <IconButton size="small" onClick={() => openDynDrawer(skill)}>
                          <ViewIcon sx={{ fontSize: 15 }} />
                        </IconButton>
                      </Tooltip>
                      {promoted ? (
                        <Tooltip title={t('detail.extensions.updateLibraryTooltip')}>
                          <span>
                            <IconButton
                              size="small"
                              color="success"
                              disabled={promotingDynamic === skill.dir_name}
                              onClick={() => handlePromoteDynamic(skill.dir_name, true)}
                            >
                              {promotingDynamic === skill.dir_name ? (
                                <CircularProgress size={14} />
                              ) : (
                                <UpdateIcon sx={{ fontSize: 15 }} />
                              )}
                            </IconButton>
                          </span>
                        </Tooltip>
                      ) : (
                        <Tooltip title={t('detail.extensions.promoteTooltip')}>
                          <span>
                            <IconButton
                              size="small"
                              color="primary"
                              disabled={promotingDynamic === skill.dir_name}
                              onClick={() => handlePromoteDynamic(skill.dir_name)}
                            >
                              {promotingDynamic === skill.dir_name ? (
                                <CircularProgress size={14} />
                              ) : (
                                <ArrowForwardIcon sx={{ fontSize: 15 }} />
                              )}
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                      <Tooltip title={t('detail.extensions.deleteTooltip')}>
                        <span>
                          <IconButton
                            size="small"
                            color="error"
                            disabled={deletingDynamic === skill.dir_name}
                            onClick={() => setDeleteConfirmDynamic(skill.dir_name)}
                          >
                            {deletingDynamic === skill.dir_name ? (
                              <CircularProgress size={14} />
                            ) : (
                              <DeleteIcon sx={{ fontSize: 15 }} />
                            )}
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Box>
                  </Box>
                )
              })}
            </Stack>
          )}

          <Divider sx={{ my: 1.5 }} />
          <Button
            variant="outlined"
            size="small"
            startIcon={<ExtensionIcon />}
            onClick={() => setCcDesignOpen(true)}
          >
            {t('detail.extensions.ccDesignBtn')}
          </Button>
        </CardContent>
      </Card>

      {/* MCP 服务配置 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1 }}>
              {t('detail.extensions.mcpTitle')}
            </Typography>
            <Tooltip title={t('detail.extensions.fillTemplateTooltip')}>
              <Button
                size="small"
                variant="outlined"
                onClick={() => setMcpTemplateOpen(true)}
              >
                {t('detail.extensions.fillTemplateBtn')}
              </Button>
            </Tooltip>
            <Button
              size="small"
              variant="contained"
              startIcon={savingMcp ? <CircularProgress size={14} color="inherit" /> : <SaveIcon />}
              onClick={handleSaveMcp}
              disabled={savingMcp || !!mcpError}
            >
              {t('detail.extensions.mcpSave')}
            </Button>
          </Box>
          {mcpError && <Alert severity="error" sx={{ mb: 1, py: 0 }}>{mcpError}</Alert>}
          <Box
            sx={{
              border: '1px solid',
              borderColor: mcpError ? 'error.main' : 'divider',
              borderRadius: 1,
              overflow: 'hidden',
            }}
          >
            <Editor
              height="320px"
              language="jsonc"
              value={mcpText}
              onChange={v => handleMcpChange(v ?? '')}
              theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'vs'}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: 'on',
                wordWrap: 'off',
                scrollBeyondLastLine: false,
                renderLineHighlight: 'none',
                tabSize: 2,
                folding: true,
                formatOnPaste: true,
              }}
            />
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            {t('detail.extensions.mcpFormatHint')}
          </Typography>
        </CardContent>
      </Card>

      {/* 添加技能 对话框 */}
      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('detail.extensions.addSkillDialog.title')}</DialogTitle>
        <DialogContent sx={{ pt: '12px !important', pb: 0 }}>
          <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
            <TextField
              fullWidth
              size="small"
              placeholder={t('detail.extensions.addSkillDialog.searchPlaceholder')}
              value={addSearch}
              onChange={e => setAddSearch(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ fontSize: 18 }} />
                  </InputAdornment>
                ),
              }}
            />
            <ToggleButtonGroup
              size="small"
              exclusive
              value={sourceFilter}
              onChange={(_, v: SourceFilter | null) => { if (v !== null) setSourceFilter(v) }}
              sx={{ flexShrink: 0 }}
            >
              <ToggleButton value="all" sx={{ px: 1.5, py: 0.5, fontSize: '0.75rem' }}>{t('detail.extensions.addSkillDialog.filterAll')}</ToggleButton>
              <ToggleButton value="builtin" sx={{ px: 1.5, py: 0.5, fontSize: '0.75rem' }}>{t('detail.extensions.addSkillDialog.filterBuiltin')}</ToggleButton>
              <ToggleButton value="user" sx={{ px: 1.5, py: 0.5, fontSize: '0.75rem' }}>{t('detail.extensions.addSkillDialog.filterUser')}</ToggleButton>
              <ToggleButton value="repo" sx={{ px: 1.5, py: 0.5, fontSize: '0.75rem' }}>{t('detail.extensions.addSkillDialog.filterRepo')}</ToggleButton>
            </ToggleButtonGroup>
          </Box>
          {filteredAvailable.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
              {availableToAdd.length === 0 ? t('detail.extensions.addSkillDialog.allAdded') : t('detail.extensions.addSkillDialog.noMatch')}
            </Typography>
          ) : (
            <List dense sx={{ maxHeight: 360, overflow: 'auto' }}>
              {filteredAvailable.map(skill => (
                <ListItem
                  key={skill.name}
                  onClick={() =>
                    setAddSelected(prev => {
                      const next = new Set(prev)
                      if (next.has(skill.name)) next.delete(skill.name)
                      else next.add(skill.name)
                      return next
                    })
                  }
                  sx={{ borderRadius: 1, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <Checkbox edge="start" checked={addSelected.has(skill.name)} size="small" disableRipple />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                        <Chip
                          label={
                            skill.source === 'builtin' ? t('detail.extensions.skillChipBuiltin')
                              : skill.source === 'repo' ? t('detail.extensions.skillChipRepo')
                                : t('detail.extensions.skillChipUser')
                          }
                          size="small"
                          color={skill.source === 'builtin' ? 'primary' : skill.source === 'repo' ? 'secondary' : 'success'}
                          variant="outlined"
                          sx={{ fontSize: '0.6rem', height: 18 }}
                        />
                        {autoInjectSet.has(skill.name) && (
                          <Chip
                            label={t('detail.extensions.skillChipAutoInject')}
                            size="small"
                            sx={{ fontSize: '0.55rem', height: 16, bgcolor: 'warning.main', color: 'warning.contrastText', fontWeight: 600 }}
                          />
                        )}
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {skill.display_name !== skill.name ? `${skill.display_name} (${skill.name})` : skill.name}
                        </Typography>
                      </Box>
                    }
                    secondary={skill.description}
                  />
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Typography variant="caption" color="text.secondary" sx={{ flexGrow: 1, pl: 2 }}>
            {t('detail.extensions.addSkillDialog.selectedCount', { count: addSelected.size })}
          </Typography>
          <Button onClick={() => setAddDialogOpen(false)}>{t('detail.extensions.addSkillDialog.cancel')}</Button>
          <Button variant="contained" onClick={handleConfirmAdd} disabled={addSelected.size === 0}>
            {t('detail.extensions.addSkillDialog.addBtn')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 让 CC 设计新技能 对话框 */}
      <Dialog open={ccDesignOpen} onClose={() => setCcDesignOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('detail.extensions.ccDesignDialog.title')}</DialogTitle>
        <DialogContent sx={{ pt: '16px !important' }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            <Box sx={{ whiteSpace: 'pre-line' }}>{t('detail.extensions.ccDesignDialog.info')}</Box>
          </Alert>
          <Typography variant="body2" color="text.secondary">
            {t('detail.extensions.ccDesignDialog.desc')}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCcDesignOpen(false)}>{t('detail.extensions.ccDesignDialog.cancel')}</Button>
          <Button variant="contained" startIcon={<ExtensionIcon />} onClick={handleCCDesignConfirm}>
            {t('detail.extensions.ccDesignDialog.confirmBtn')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 动态技能详情 Drawer */}
      <Drawer
        anchor="right"
        open={!!drawerDynamic}
        onClose={closeDynDrawer}
        PaperProps={{
          sx: {
            width: { xs: '100%', sm: 720, md: 820 },
            maxWidth: '100vw',
            mt: { xs: '56px', sm: '64px' },
            height: { xs: 'calc(100% - 56px)', sm: 'calc(100% - 64px)' },
          },
        }}
      >
        {drawerDynamic && (
          <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Drawer header */}
            <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.3 }} noWrap>
                    {drawerDynamic.name || drawerDynamic.dir_name}
                  </Typography>
                  <Chip label={t('detail.extensions.skillChipCC')} size="small" color="secondary" variant="outlined" sx={{ fontSize: '0.65rem', height: 20 }} />
                  {isPromotedToLibrary(drawerDynamic.dir_name) && (
                    <Chip label={t('detail.extensions.skillChipPromoted')} size="small" color="success" variant="outlined" sx={{ fontSize: '0.6rem', height: 18 }} />
                  )}
                </Box>
                {drawerDynamic.name && drawerDynamic.name !== drawerDynamic.dir_name && (
                  <Typography variant="caption" color="text.disabled">{drawerDynamic.dir_name}</Typography>
                )}
                {drawerDynamic.description && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>{drawerDynamic.description}</Typography>
                )}
              </Box>
              {isPromotedToLibrary(drawerDynamic.dir_name) ? (
                <Tooltip title={t('detail.extensions.updateLibraryTooltip')}>
                  <span>
                    <IconButton
                      size="small"
                      color="success"
                      disabled={promotingDynamic === drawerDynamic.dir_name}
                      onClick={() => handlePromoteDynamic(drawerDynamic.dir_name, true)}
                    >
                      {promotingDynamic === drawerDynamic.dir_name ? <CircularProgress size={16} /> : <UpdateIcon fontSize="small" />}
                    </IconButton>
                  </span>
                </Tooltip>
              ) : (
                <Tooltip title={t('detail.extensions.promoteTooltip')}>
                  <span>
                    <IconButton
                      size="small"
                      color="primary"
                      disabled={promotingDynamic === drawerDynamic.dir_name}
                      onClick={() => handlePromoteDynamic(drawerDynamic.dir_name)}
                    >
                      {promotingDynamic === drawerDynamic.dir_name ? <CircularProgress size={16} /> : <ArrowForwardIcon fontSize="small" />}
                    </IconButton>
                  </span>
                </Tooltip>
              )}
              <IconButton size="small" onClick={closeDynDrawer}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>

            {/* Drawer body: file tree + content pane */}
            <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
              {/* Left: File tree */}
              <Box
                sx={{
                  width: 200,
                  minWidth: 200,
                  borderRight: '1px solid',
                  borderColor: 'divider',
                  overflow: 'auto',
                  bgcolor: (th) => alpha(th.palette.background.default, 0.5),
                }}
              >
                <Box sx={{ px: 1.5, py: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    {t('skills.drawer.files')}
                  </Typography>
                  <Typography variant="caption" color="text.disabled">
                    ({drawerFiles.filter(e => e.type === 'file').length})
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
                        selected={dynSelectedFile === entry.rel_path}
                        disabled={entry.type === 'dir'}
                        onClick={() => {
                          if (entry.type === 'file') selectDynFile(drawerDynamic.dir_name, entry.rel_path)
                        }}
                        sx={{
                          pl: 1 + (entry.rel_path.split('/').length - 1) * 1.5,
                          py: 0.25,
                          minHeight: 30,
                          '&.Mui-selected': { bgcolor: (th) => alpha(th.palette.primary.main, 0.12) },
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
                        {entry.type === 'file' && dynSelectedFile === entry.rel_path && dynDirty && (
                          <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: 'warning.main', flexShrink: 0, ml: 0.5 }} />
                        )}
                      </ListItemButton>
                    ))}
                  </List>
                )}
              </Box>

              {/* Right: Content pane */}
              <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
                {/* Content toolbar */}
                {dynSelectedFile && (
                  <Box
                    sx={{
                      px: 1.5,
                      py: 0.75,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 0.5,
                      borderBottom: '1px solid',
                      borderColor: 'divider',
                      bgcolor: (th) => alpha(th.palette.background.default, 0.3),
                    }}
                  >
                    <Typography variant="caption" sx={{ fontWeight: 500, flex: 1 }} noWrap>
                      {dynSelectedFile}
                    </Typography>

                    {dynDirty && (
                      <Chip label={t('skills.drawer.modified')} size="small" color="warning" sx={{ height: 18, fontSize: '0.6rem' }} />
                    )}

                    {isTextFile(dynSelectedFile) && (
                      <ToggleButtonGroup
                        size="small"
                        value={dynEditing ? 'source' : dynViewMode}
                        exclusive
                        onChange={(_, v) => {
                          if (v === 'source' || v === 'preview') {
                            setDynViewMode(v)
                            if (v === 'preview') setDynEditing(false)
                          }
                        }}
                        disabled={dynEditing}
                      >
                        <ToggleButton value="preview" sx={{ py: 0.25, px: 0.75 }}>
                          <Tooltip title={t('skills.drawer.preview')}><PreviewIcon sx={{ fontSize: 16 }} /></Tooltip>
                        </ToggleButton>
                        <ToggleButton value="source" sx={{ py: 0.25, px: 0.75 }}>
                          <Tooltip title={t('skills.drawer.source_code')}><CodeIcon sx={{ fontSize: 16 }} /></Tooltip>
                        </ToggleButton>
                      </ToggleButtonGroup>
                    )}

                    {isTextFile(dynSelectedFile) && (
                      dynEditing ? (
                        <Stack direction="row" spacing={0.5}>
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={dynSaving ? <CircularProgress size={12} color="inherit" /> : <SaveIcon sx={{ fontSize: 14 }} />}
                            onClick={handleDynSave}
                            disabled={dynSaving || !dynDirty}
                            sx={{ minWidth: 0, px: 1, py: 0.25, fontSize: '0.7rem' }}
                          >
                            {dynSaving ? t('skills.drawer.saving') : t('skills.drawer.save')}
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => {
                              setDynEditing(false)
                              setDynEditBuffer(dynFileContent ?? '')
                              setDynDirty(false)
                              setDynViewMode('source')
                            }}
                            disabled={dynSaving}
                            sx={{ minWidth: 0, px: 1, py: 0.25, fontSize: '0.7rem' }}
                          >
                            {t('skills.drawer.cancel_edit')}
                          </Button>
                        </Stack>
                      ) : (
                        <Tooltip title={t('skills.drawer.edit')}>
                          <IconButton
                            size="small"
                            onClick={() => {
                              setDynEditing(true)
                              setDynEditBuffer(dynFileContent ?? '')
                              setDynDirty(false)
                              setDynViewMode('source')
                            }}
                          >
                            <EditIcon sx={{ fontSize: 16 }} />
                          </IconButton>
                        </Tooltip>
                      )
                    )}
                  </Box>
                )}

                {/* Content body */}
                <Box sx={{ flex: 1, overflow: 'auto' }}>
                  {!dynSelectedFile ? (
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 1 }}>
                      <ExtensionIcon sx={{ fontSize: 48, opacity: 0.15 }} />
                      <Typography variant="body2" color="text.disabled">{t('skills.drawer.noContent')}</Typography>
                    </Box>
                  ) : dynFileLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                      <CircularProgress size={24} />
                    </Box>
                  ) : !isTextFile(dynSelectedFile) ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                      <Typography variant="body2" color="text.disabled">{t('skills.drawer.binaryFile')}</Typography>
                    </Box>
                  ) : dynEditing ? (
                    <Editor
                      key={`dyn-edit-${dynSelectedFile}`}
                      height="100%"
                      language={getMonacoLanguage(dynSelectedFile)}
                      value={dynEditBuffer}
                      onChange={v => {
                        const val = v ?? ''
                        setDynEditBuffer(val)
                        setDynDirty(val !== (dynFileContent ?? ''))
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
                  ) : dynViewMode === 'source' ? (
                    <Editor
                      key={`dyn-readonly-${dynSelectedFile}`}
                      height="100%"
                      language={getMonacoLanguage(dynSelectedFile)}
                      value={dynFileContent ?? ''}
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
                    dynFileContent !== null && dynSelectedFile.toLowerCase().endsWith('.md') ? (
                      <SkillPreviewPanel raw={dynFileContent} />
                    ) : (
                      <Editor
                        key={`dyn-preview-${dynSelectedFile}`}
                        height="100%"
                        language={getMonacoLanguage(dynSelectedFile)}
                        value={dynFileContent ?? ''}
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

      {/* 动态技能未保存确认对话框 */}
      <Dialog open={!!dynUnsavedTarget} onClose={() => setDynUnsavedTarget(null)}>
        <DialogTitle>{t('skills.drawer.unsavedTitle')}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t('skills.drawer.unsavedConfirm')}</DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDynUnsavedTarget(null)}>{t('skills.drawer.keepEditing')}</Button>
          <Button variant="contained" color="warning" onClick={handleDynDiscardAndSwitch}>{t('skills.drawer.discard')}</Button>
        </DialogActions>
      </Dialog>

      {/* 删除动态技能确认 对话框 */}
      <Dialog
        open={!!deleteConfirmDynamic}
        onClose={() => !deletingDynamic && setDeleteConfirmDynamic(null)}
        maxWidth="xs"
      >
        <DialogTitle>{t('detail.extensions.deleteDynamicDialog.title')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t('detail.extensions.deleteDynamicDialog.content', { name: deleteConfirmDynamic })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmDynamic(null)} disabled={!!deletingDynamic}>
            {t('detail.extensions.deleteDynamicDialog.cancel')}
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={confirmDeleteDynamic}
            disabled={!!deletingDynamic}
          >
            {deletingDynamic ? <CircularProgress size={20} /> : t('detail.extensions.deleteDynamicDialog.delete')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* MCP 模板确认对话框 */}
      <Dialog open={mcpTemplateOpen} onClose={() => setMcpTemplateOpen(false)} maxWidth="xs">
        <DialogTitle>{t('detail.extensions.mcpTemplateDialog.title')}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 1.5 }}>
            {t('detail.extensions.mcpTemplateDialog.warning')}
          </Alert>
          <DialogContentText>
            {t('detail.extensions.mcpTemplateDialog.desc')}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMcpTemplateOpen(false)}>{t('detail.extensions.mcpTemplateDialog.cancel')}</Button>
          <Button variant="contained" color="warning" onClick={handleApplyTemplate}>
            {t('detail.extensions.mcpTemplateDialog.confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
