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
      notification.success('已同步到沙盒')
    } catch (err) {
      notification.error(`同步失败：${(err as Error).message}`)
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
    return list
  }, [availableToAdd, sourceFilter, addSearch])

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
      notification.success(`动态技能 ${deleteConfirmDynamic} 已删除`)
      setDeleteConfirmDynamic(null)
      refreshDynamicSkills()
    } catch (err) {
      notification.error(`删除失败：${(err as Error).message}`)
    } finally {
      setDeletingDynamic(null)
    }
  }

  const handlePromoteDynamic = async (dirName: string) => {
    setPromotingDynamic(dirName)
    try {
      await dynamicSkillApi.promote(workspace.id, dirName)
      notification.success(`动态技能 ${dirName} 已晋升为用户技能`)
      refreshDynamicSkills()
    } catch (err) {
      notification.error(`晋升失败：${(err as Error).message}`)
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
      notification.error(`加载技能内容失败：${(err as Error).message}`)
    }
  }

  const handleSaveDynamic = async () => {
    if (!editDynamic) return
    setSavingDynamic(true)
    try {
      await dynamicSkillApi.put(workspace.id, editDynamic.dir_name, editContent)
      notification.success(`动态技能 ${editDynamic.dir_name} 已保存`)
      setEditDynamic(null)
      refreshDynamicSkills()
    } catch (err) {
      notification.error(`保存失败：${(err as Error).message}`)
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
              扩展技能
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Button
              size="small"
              variant={hasUnsavedChanges ? 'contained' : 'outlined'}
              startIcon={syncing ? <CircularProgress size={14} color="inherit" /> : <SyncIcon />}
              onClick={handleSync}
              disabled={syncing}
            >
              同步到沙盒
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<AddIcon sx={{ fontSize: 14 }} />}
              onClick={handleOpenAddDialog}
            >
              添加技能
            </Button>
          </Box>

          {/* 已部署列表 */}
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.75, display: 'block', fontWeight: 500 }}>
            已部署（{selectedSkills.length}）
          </Typography>
          {selectedSkillsDetail.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
              暂未部署任何技能，点击「添加技能」从内置或技能库中挑选
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
                    label={skill.source === 'builtin' ? '内置' : '技能库'}
                    size="small"
                    color={skill.source === 'builtin' ? 'primary' : 'success'}
                    variant="outlined"
                    sx={{ fontSize: '0.65rem', height: 20, flexShrink: 0 }}
                  />
                  {skill.isPending && (
                    <Chip
                      label="待同步"
                      size="small"
                      color="warning"
                      sx={{ fontSize: '0.65rem', height: 20, flexShrink: 0 }}
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
                  <Tooltip title="从已部署列表移除（点击「同步到沙盒」生效）">
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
              CC 创建（{dynamicSkills.length}）
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Tooltip title="刷新动态技能列表">
              <IconButton size="small" onClick={refreshDynamicSkills}>
                <RefreshIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </Tooltip>
          </Box>
          {dynamicSkills.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
              暂无动态技能
            </Typography>
          ) : (
            <Stack spacing={0.5}>
              {dynamicSkills.map(skill => (
                <Box key={skill.dir_name} sx={{ ...ROW_SX, borderColor: 'divider' }}>
                  <Chip
                    label="CC创建"
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
                    <Tooltip title="编辑 SKILL.md">
                      <IconButton size="small" onClick={() => handleEditDynamic(skill)}>
                        <EditIcon sx={{ fontSize: 15 }} />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="晋升为技能库">
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
                    <Tooltip title="删除">
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
            让 CC 设计新技能
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
            <Tooltip title="填充常用 MCP 服务配置模板（会覆盖现有内容）">
              <Button
                size="small"
                variant="outlined"
                onClick={() => setMcpTemplateOpen(true)}
              >
                填充模板
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
            支持 JSONC 格式（// 和 /* */ 注释），保存时自动转换为 JSON
          </Typography>
        </CardContent>
      </Card>

      {/* 添加技能 对话框 */}
      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>添加技能</DialogTitle>
        <DialogContent sx={{ pt: '12px !important', pb: 0 }}>
          <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
            <TextField
              fullWidth
              size="small"
              placeholder="搜索技能名称或描述…"
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
              <ToggleButton value="all" sx={{ px: 1.5, py: 0.5, fontSize: '0.75rem' }}>全部</ToggleButton>
              <ToggleButton value="builtin" sx={{ px: 1.5, py: 0.5, fontSize: '0.75rem' }}>内置</ToggleButton>
              <ToggleButton value="user" sx={{ px: 1.5, py: 0.5, fontSize: '0.75rem' }}>技能库</ToggleButton>
            </ToggleButtonGroup>
          </Box>
          {filteredAvailable.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
              {availableToAdd.length === 0 ? '所有技能均已添加' : '无匹配结果'}
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
                          label={skill.source === 'builtin' ? '内置' : '技能库'}
                          size="small"
                          color={skill.source === 'builtin' ? 'primary' : 'success'}
                          variant="outlined"
                          sx={{ fontSize: '0.6rem', height: 18 }}
                        />
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
            已选 {addSelected.size} 个
          </Typography>
          <Button onClick={() => setAddDialogOpen(false)}>取消</Button>
          <Button variant="contained" onClick={handleConfirmAdd} disabled={addSelected.size === 0}>
            添加到列表
          </Button>
        </DialogActions>
      </Dialog>

      {/* 让 CC 设计新技能 对话框 */}
      <Dialog open={ccDesignOpen} onClose={() => setCcDesignOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>让 CC 设计新技能</DialogTitle>
        <DialogContent sx={{ pt: '16px !important' }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            点击确认后将跳转到「沙盒通讯」页，并预填充设计提示词。<br />
            你可以在输入框中补充具体需求后再发送，与 CC 逐步交互打磨技能。
          </Alert>
          <Typography variant="body2" color="text.secondary">
            CC 会使用 skill-creator 技能指导，将设计好的技能保存在动态技能目录中，你可以随时从扩展能力页面查看、编辑或晋升。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCcDesignOpen(false)}>取消</Button>
          <Button variant="contained" startIcon={<ExtensionIcon />} onClick={handleCCDesignConfirm}>
            前往沙盒通讯
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
        <DialogTitle>编辑动态技能 {editDynamic?.dir_name}</DialogTitle>
        <DialogContent sx={{ pt: '16px !important' }}>
          <TextField
            fullWidth
            multiline
            minRows={16}
            size="small"
            label="SKILL.md 内容"
            value={editContent}
            onChange={e => setEditContent(e.target.value)}
            disabled={savingDynamic}
            inputProps={{ style: { fontFamily: '"SFMono-Regular", Consolas, monospace', fontSize: '0.82rem' } }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDynamic(null)} disabled={savingDynamic}>
            取消
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveDynamic}
            disabled={savingDynamic}
            startIcon={savingDynamic ? <CircularProgress size={14} color="inherit" /> : <SaveIcon />}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除动态技能确认 对话框 */}
      <Dialog
        open={!!deleteConfirmDynamic}
        onClose={() => !deletingDynamic && setDeleteConfirmDynamic(null)}
        maxWidth="xs"
      >
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            确定要删除动态技能 <strong>{deleteConfirmDynamic}</strong> 吗？此操作不可恢复。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmDynamic(null)} disabled={!!deletingDynamic}>
            取消
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={confirmDeleteDynamic}
            disabled={!!deletingDynamic}
          >
            {deletingDynamic ? <CircularProgress size={20} /> : '删除'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* MCP 模板确认对话框 */}
      <Dialog open={mcpTemplateOpen} onClose={() => setMcpTemplateOpen(false)} maxWidth="xs">
        <DialogTitle>填充 MCP 配置模板</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 1.5 }}>
            此操作会覆盖现有 MCP 配置内容，请确认已备份或无需保留现有配置。
          </Alert>
          <DialogContentText>
            模板中包含常用 MCP 服务（Filesystem、GitHub、Brave Search、Fetch、Memory、PostgreSQL）的 JSONC 示例，默认均已注释，按需取消注释并填写参数即可。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMcpTemplateOpen(false)}>取消</Button>
          <Button variant="contained" color="warning" onClick={handleApplyTemplate}>
            确认填充
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
