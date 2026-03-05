import { useState, useEffect, useMemo } from 'react'
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
  ListItemIcon,
  ListItemText,
  ToggleButtonGroup,
  ToggleButton,
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
} from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS } from '../../../theme/variants'
import { useTranslation } from 'react-i18next'

type SourceFilter = 'all' | 'builtin' | 'user'

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
  const [editDynamic, setEditDynamic] = useState<DynamicSkillItem | null>(null)
  const [editContent, setEditContent] = useState('')
  const [savingDynamic, setSavingDynamic] = useState(false)

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

  const refreshDynamicSkills = () => {
    dynamicSkillApi.list(workspace.id).then(setDynamicSkills).catch(() => setDynamicSkills([]))
  }

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

  const handlePromoteDynamic = async (dirName: string) => {
    setPromotingDynamic(dirName)
    try {
      await dynamicSkillApi.promote(workspace.id, dirName)
      notification.success(t('detail.extensions.notifications.promoteSuccess', { name: dirName }))
      refreshDynamicSkills()
    } catch (err) {
      notification.error(t('detail.extensions.notifications.promoteFailed', { message: (err as Error).message }))
    } finally {
      setPromotingDynamic(null)
    }
  }

  const handleEditDynamic = async (item: DynamicSkillItem) => {
    setEditDynamic(item)
    setEditContent('')
    try {
      const data = await dynamicSkillApi.get(workspace.id, item.dir_name)
      setEditContent(data.content)
    } catch (err) {
      notification.error(t('detail.extensions.notifications.loadContentFailed', { message: (err as Error).message }))
    }
  }

  const handleSaveDynamic = async () => {
    if (!editDynamic) return
    setSavingDynamic(true)
    try {
      await dynamicSkillApi.put(workspace.id, editDynamic.dir_name, editContent)
      notification.success(t('detail.extensions.notifications.saveDynamicSuccess', { name: editDynamic.dir_name }))
      setEditDynamic(null)
      refreshDynamicSkills()
    } catch (err) {
      notification.error(t('detail.extensions.notifications.saveDynamicFailed', { message: (err as Error).message }))
    } finally {
      setSavingDynamic(false)
    }
  }

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
                      : skill.source === 'builtin' ? 'primary.main' : 'success.main',
                    bgcolor: skill.isPending ? 'warning.main' + '12' : 'action.selected',
                  }}
                >
                  <Chip
                    label={skill.source === 'builtin' ? t('detail.extensions.skillChipBuiltin') : t('detail.extensions.skillChipUser')}
                    size="small"
                    color={skill.source === 'builtin' ? 'primary' : 'success'}
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
              {dynamicSkills.map(skill => (
                <Box key={skill.dir_name} sx={{ ...ROW_SX, borderColor: 'divider' }}>
                  <Chip
                    label={t('detail.extensions.skillChipCC')}
                    size="small"
                    color="secondary"
                    variant="outlined"
                    sx={{ fontSize: '0.65rem', height: 20, flexShrink: 0 }}
                  />
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
                    <Tooltip title={t('detail.extensions.editSkillTooltip')}>
                      <IconButton size="small" onClick={() => handleEditDynamic(skill)}>
                        <EditIcon sx={{ fontSize: 15 }} />
                      </IconButton>
                    </Tooltip>
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
              ))}
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
                          label={skill.source === 'builtin' ? t('detail.extensions.skillChipBuiltin') : t('detail.extensions.skillChipUser')}
                          size="small"
                          color={skill.source === 'builtin' ? 'primary' : 'success'}
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

      {/* 编辑动态技能 对话框 */}
      <Dialog
        open={!!editDynamic}
        onClose={() => !savingDynamic && setEditDynamic(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{t('detail.extensions.editDynamicDialog.title', { name: editDynamic?.dir_name })}</DialogTitle>
        <DialogContent sx={{ pt: '16px !important' }}>
          <TextField
            fullWidth
            multiline
            minRows={16}
            size="small"
            label={t('detail.extensions.editDynamicDialog.contentLabel')}
            value={editContent}
            onChange={e => setEditContent(e.target.value)}
            disabled={savingDynamic}
            inputProps={{ style: { fontFamily: '"SFMono-Regular", Consolas, monospace', fontSize: '0.82rem' } }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDynamic(null)} disabled={savingDynamic}>
            {t('detail.extensions.editDynamicDialog.cancel')}
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveDynamic}
            disabled={savingDynamic}
            startIcon={savingDynamic ? <CircularProgress size={14} color="inherit" /> : <SaveIcon />}
          >
            {t('detail.extensions.editDynamicDialog.save')}
          </Button>
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
