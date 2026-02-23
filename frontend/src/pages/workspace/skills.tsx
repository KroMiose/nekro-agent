import { useState, useMemo, useRef } from 'react'
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
  Collapse,
  Divider,
  Paper,
  Tabs,
  Tab,
} from '@mui/material'
import {
  Extension as ExtensionIcon,
  Delete as DeleteIcon,
  ChevronRight,
  ExpandMore,
  GitHub as GitHubIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Search as SearchIcon,
  AccountTree as TreeViewIcon,
  ViewModule as GridViewIcon,
  Upload as UploadIcon,
  Article as ArticleIcon,
  Description as DescriptionIcon,
  Close as CloseIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { skillsLibraryApi, builtinSkillApi, SkillTreeNode, SkillItem } from '../../services/api/workspace'
import { useNotification } from '../../hooks/useNotification'
import { CARD_VARIANTS } from '../../theme/variants'
import MarkdownRenderer from '../../components/common/MarkdownRenderer'

// ─────────────────────────────────────────────────────────────
// 辅助函数
// ─────────────────────────────────────────────────────────────

function collectSkills(nodes: SkillTreeNode[]): SkillTreeNode[] {
  const skills: SkillTreeNode[] = []
  for (const node of nodes) {
    if (node.type === 'skill') skills.push(node)
    if (node.children) skills.push(...collectSkills(node.children))
  }
  return skills
}

function autoDeriveName(url: string): string {
  const segment = url.trim().split('/').pop() ?? ''
  return segment
    .replace(/\.git$/i, '')
    .replace(/[^a-zA-Z0-9_-]/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase()
}

// ─────────────────────────────────────────────────────────────
// SKILL.md 解析 & 元信息渲染
// ─────────────────────────────────────────────────────────────

interface SkillMdData {
  frontmatter: Record<string, string>
  body: string
}

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

function SkillContentPanel({ raw }: { raw: string }) {
  const { frontmatter, body } = useMemo(() => parseSkillMd(raw), [raw])
  const allowedTools =
    frontmatter['allowed-tools']
      ?.split(',')
      .map(t => t.trim())
      .filter(Boolean) ?? []
  const fmName = frontmatter['name']
  const fmDesc = frontmatter['description']
  const otherFields = Object.entries(frontmatter).filter(
    ([k]) => !['name', 'description', 'allowed-tools'].includes(k),
  )
  const hasMeta = Object.keys(frontmatter).length > 0

  return (
    <Box sx={{ maxHeight: 460, overflow: 'auto' }}>
      {/* 元信息头部 */}
      {hasMeta && (
        <Box
          sx={{
            px: 2,
            py: 1.25,
            bgcolor: 'action.hover',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {/* 名称 + 工具标签行 */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 0.75 }}>
            {fmName && (
              <Chip label={fmName} size="small" color="primary" sx={{ fontWeight: 600, fontSize: 11, height: 20 }} />
            )}
            {allowedTools.length > 0 && (
              <>
                <Typography variant="caption" color="text.disabled" sx={{ mx: 0.25 }}>
                  允许工具:
                </Typography>
                {allowedTools.map(tool => (
                  <Chip
                    key={tool}
                    label={tool}
                    size="small"
                    variant="outlined"
                    sx={{ height: 18, fontSize: 10, borderColor: 'divider', color: 'text.secondary' }}
                  />
                ))}
              </>
            )}
          </Box>
          {/* 描述 */}
          {fmDesc && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: 'block', mt: 0.75, lineHeight: 1.5 }}
            >
              {fmDesc}
            </Typography>
          )}
          {/* 其他字段 */}
          {otherFields.map(([k, v]) => (
            <Typography key={k} variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.25 }}>
              {k}: {v}
            </Typography>
          ))}
        </Box>
      )}
      {/* 正文 */}
      {body ? (
        <Box sx={{ px: 2, py: 1.5 }}>
          <MarkdownRenderer>{body}</MarkdownRenderer>
        </Box>
      ) : !hasMeta ? (
        <Box sx={{ px: 2, py: 1.5 }}>
          <Typography variant="caption" color="text.disabled">暂无内容</Typography>
        </Box>
      ) : null}
    </Box>
  )
}

// ─────────────────────────────────────────────────────────────
// 树节点组件
// ─────────────────────────────────────────────────────────────

interface SkillNodeRowProps {
  node: SkillTreeNode
  depth: number
  isTopLevel: boolean
  expandedNodes: Set<string>
  expandedContent: string | null
  contentCache: Record<string, string>
  pullingPath: string | null
  onToggleExpand: (path: string) => void
  onToggleContent: (node: SkillTreeNode) => void
  onDelete: (name: string) => void
  onPull: (path: string) => void
}

function SkillNodeRow({
  node,
  depth,
  isTopLevel,
  expandedNodes,
  expandedContent,
  contentCache,
  pullingPath,
  onToggleExpand,
  onToggleContent,
  onDelete,
  onPull,
}: SkillNodeRowProps) {
  const INDENT = 20
  const isTreeExpanded = expandedNodes.has(node.path)
  const isContentExpanded = expandedContent === node.path
  const isPulling = pullingPath === node.path

  // 是否有子节点（可树展开）
  const hasChildren = !!node.children?.length
  // skill 节点：有子文档时可树展开；dir/repo：有子节点时可树展开
  const canTreeExpand = hasChildren
  // skill 和 doc 类型可展开内容
  const canShowContent = node.type === 'skill' || node.type === 'doc'

  // 整行可交互
  const canInteract = canShowContent || canTreeExpand

  // 点击行（不含 chevron）
  const handleRowClick = () => {
    if (canShowContent) onToggleContent(node)
    else if (canTreeExpand) onToggleExpand(node.path)
  }

  // 点击折叠箭头（与行点击分离）
  const handleChevronClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (canTreeExpand) {
      onToggleExpand(node.path)
    } else if (canShowContent) {
      onToggleContent(node)
    }
  }

  // chevron 方向：有子节点时反映树展开状态；否则反映内容展开状态
  const chevronDown = canTreeExpand ? isTreeExpanded : isContentExpanded
  const showChevron = canInteract

  return (
    <Box>
      {/* 行 */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          minHeight: 34,
          pl: 1,
          pr: 1,
          gap: 0.5,
          cursor: canInteract ? 'pointer' : 'default',
          bgcolor: isContentExpanded ? 'action.selected' : 'transparent',
          '&:hover': { bgcolor: isContentExpanded ? 'action.selected' : 'action.hover' },
          userSelect: 'none',
          transition: 'background-color 0.15s',
        }}
        onClick={handleRowClick}
      >
        {/* 缩进 */}
        {depth > 0 && <Box sx={{ width: depth * INDENT, flexShrink: 0 }} />}

        {/* 左侧折叠箭头 */}
        <Box
          sx={{ width: 20, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'text.secondary' }}
          onClick={handleChevronClick}
        >
          {showChevron
            ? chevronDown
              ? <ExpandMore sx={{ fontSize: 16 }} />
              : <ChevronRight sx={{ fontSize: 16 }} />
            : null}
        </Box>

        {/* 节点图标 */}
        {node.type === 'skill' && <ArticleIcon sx={{ fontSize: 16, color: 'primary.main', flexShrink: 0 }} />}
        {node.type === 'doc' && <DescriptionIcon sx={{ fontSize: 16, color: 'text.secondary', flexShrink: 0 }} />}
        {node.type === 'repo' && <GitHubIcon sx={{ fontSize: 16, color: 'text.secondary', flexShrink: 0 }} />}
        {node.type === 'dir' && (
          isTreeExpanded
            ? <FolderOpenIcon sx={{ fontSize: 16, color: 'warning.main', flexShrink: 0 }} />
            : <FolderIcon sx={{ fontSize: 16, color: 'warning.main', flexShrink: 0 }} />
        )}

        {/* 名称 + 描述（baseline 对齐） */}
        <Box sx={{ flexGrow: 1, minWidth: 0, display: 'flex', alignItems: 'baseline', gap: 1, overflow: 'hidden' }}>
          <Typography variant="body2" sx={{ fontWeight: node.type === 'skill' ? 500 : 400, flexShrink: 0 }}>
            {node.type === 'skill' ? (node.skill_name || node.name) : node.name}
          </Typography>
          {/* skill 描述 */}
          {node.type === 'skill' && node.skill_description && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
            >
              {node.skill_description}
            </Typography>
          )}
          {/* repo 元信息 */}
          {node.type === 'repo' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, overflow: 'hidden' }}>
              {node.repo_branch && (
                <Chip label={node.repo_branch} size="small" variant="outlined" sx={{ height: 16, fontSize: 10, flexShrink: 0 }} />
              )}
              {node.repo_url && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                >
                  {node.repo_url}
                </Typography>
              )}
            </Box>
          )}
        </Box>

        {/* 操作区 */}
        <Box
          sx={{ display: 'flex', alignItems: 'center', gap: 0.25, flexShrink: 0 }}
          onClick={e => e.stopPropagation()}
        >
          {node.type === 'repo' && (
            <Tooltip title="拉取更新">
              <span>
                <IconButton size="small" color="primary" onClick={() => onPull(node.path)} disabled={isPulling}>
                  {isPulling ? <CircularProgress size={14} /> : <RefreshIcon sx={{ fontSize: 14 }} />}
                </IconButton>
              </span>
            </Tooltip>
          )}
          {isTopLevel && (
            <Tooltip title="删除">
              <IconButton size="small" color="error" onClick={() => onDelete(node.name)}>
                <DeleteIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>

      {/* skill / doc 展开内容 */}
      {canShowContent && (
        <Collapse in={isContentExpanded}>
          <Box
            sx={{
              ml: `${depth * INDENT + 28}px`,
              borderLeft: '2px solid',
              borderColor: node.type === 'doc' ? 'text.disabled' : 'primary.main',
              borderBottom: '1px solid',
              borderBottomColor: 'divider',
            }}
          >
            {contentCache[node.path] === undefined ? (
              <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                <CircularProgress size={14} />
                <Typography variant="caption" color="text.secondary">加载中...</Typography>
              </Box>
            ) : (
              <SkillContentPanel raw={contentCache[node.path] || ''} />
            )}
          </Box>
        </Collapse>
      )}

      {/* 子节点（dir/repo，以及有附属文档的 skill） */}
      {hasChildren && (
        <Collapse in={isTreeExpanded}>
          <Box sx={{ borderLeft: '1px solid', borderColor: 'divider', ml: `${depth * INDENT + 28}px` }}>
            {node.children!.map(child => (
              <SkillNodeRow
                key={child.path}
                node={child}
                depth={depth + 1}
                isTopLevel={false}
                expandedNodes={expandedNodes}
                expandedContent={expandedContent}
                contentCache={contentCache}
                pullingPath={pullingPath}
                onToggleExpand={onToggleExpand}
                onToggleContent={onToggleContent}
                onDelete={onDelete}
                onPull={onPull}
              />
            ))}
          </Box>
        </Collapse>
      )}
    </Box>
  )
}

// ─────────────────────────────────────────────────────────────
// 平铺视图 - Skill 卡片
// ─────────────────────────────────────────────────────────────

interface SkillCardProps {
  node: SkillTreeNode
  isTopLevel: boolean
  expandedContent: string | null
  contentCache: Record<string, string>
  onDelete: (name: string) => void
  onToggleContent: (node: SkillTreeNode) => void
}

function SkillCard({ node, isTopLevel, expandedContent, contentCache, onDelete, onToggleContent }: SkillCardProps) {
  const isContentExpanded = expandedContent === node.path

  return (
    <Card sx={{ ...CARD_VARIANTS.default.styles, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          p: 2,
          pb: 1,
          gap: 1.5,
          cursor: 'pointer',
          '&:hover': { bgcolor: 'action.hover' },
        }}
        onClick={() => onToggleContent(node)}
      >
        <ExtensionIcon color="primary" sx={{ mt: 0.25, flexShrink: 0 }} />
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="body1" sx={{ fontWeight: 600 }}>
            {node.skill_name || node.name}
          </Typography>
          {node.skill_description && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {node.skill_description}
            </Typography>
          )}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1, flexWrap: 'wrap' }}>
            <Chip label={node.path} size="small" variant="outlined" sx={{ fontSize: 11, height: 20 }} />
            {node.has_git && (
              <Chip icon={<GitHubIcon sx={{ fontSize: '14px !important' }} />} label="git" size="small" sx={{ fontSize: 11, height: 20 }} />
            )}
          </Box>
        </Box>
        <Stack direction="row" spacing={0.5} onClick={e => e.stopPropagation()}>
          {isTopLevel && (
            <Tooltip title="删除">
              <IconButton size="small" color="error" onClick={() => onDelete(node.name)}>
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          <Tooltip title={isContentExpanded ? '收起' : '查看 SKILL.md'}>
            <IconButton size="small" onClick={() => onToggleContent(node)}>
              <ArticleIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      <Collapse in={isContentExpanded}>
        <Divider />
        <Box sx={{ maxHeight: 380, overflow: 'auto' }}>
          {contentCache[node.path] === undefined ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={20} />
            </Box>
          ) : (
            <SkillContentPanel raw={contentCache[node.path] || ''} />
          )}
        </Box>
      </Collapse>
    </Card>
  )
}

// ─────────────────────────────────────────────────────────────
// 主页面
// ─────────────────────────────────────────────────────────────

export default function SkillsLibraryPage() {
  const queryClient = useQueryClient()
  const notification = useNotification()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 页面 Tab
  const [pageTab, setPageTab] = useState(0)

  // 视图模式和搜索
  const [viewMode, setViewMode] = useState<'tree' | 'flat'>('tree')
  const [searchQuery, setSearchQuery] = useState('')

  // 树展开状态
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [expandedContent, setExpandedContent] = useState<string | null>(null)
  const [contentCache, setContentCache] = useState<Record<string, string>>({})

  // 操作状态
  const [pullingPath, setPullingPath] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  // 内置技能内容展开状态（独立，避免与用户技能库混用）
  const [builtinExpandedContent, setBuiltinExpandedContent] = useState<string | null>(null)
  const [builtinContentCache, setBuiltinContentCache] = useState<Record<string, string>>({})

  // 添加 Skill 对话框
  const [cloneDialogOpen, setCloneDialogOpen] = useState(false)
  const [cloneUrl, setCloneUrl] = useState('')
  const [cloneTargetDir, setCloneTargetDir] = useState('')
  const [cloneUrlTouched, setCloneUrlTouched] = useState(false)

  // 数据获取
  const { data: treeData, isLoading, error, refetch } = useQuery({
    queryKey: ['skills-tree'],
    queryFn: skillsLibraryApi.getTree,
  })

  const { data: builtinSkills = [], isLoading: builtinLoading, refetch: refetchBuiltin } = useQuery<SkillItem[]>({
    queryKey: ['skills-builtin'],
    queryFn: builtinSkillApi.getList,
  })

  // 所有技能（扁平）
  const allSkills = useMemo(() => collectSkills(treeData ?? []), [treeData])

  // 搜索过滤
  const filteredSkills = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return allSkills
    return allSkills.filter(
      s =>
        (s.skill_name ?? s.name).toLowerCase().includes(q) ||
        (s.skill_description ?? '').toLowerCase().includes(q) ||
        s.path.toLowerCase().includes(q),
    )
  }, [allSkills, searchQuery])

  // 是否展示搜索结果（覆盖树视图）
  const isSearching = searchQuery.trim().length > 0

  // 内置技能搜索过滤
  const filteredBuiltinSkills = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return builtinSkills
    return builtinSkills.filter(
      s => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q),
    )
  }, [builtinSkills, searchQuery])

  // 将 SkillItem[] 转为 SkillTreeNode[] 以复用 SkillNodeRow / SkillCard
  const builtinNodes = useMemo<SkillTreeNode[]>(
    () =>
      filteredBuiltinSkills.map(s => ({
        name: s.name,
        path: s.name,
        type: 'skill' as const,
        skill_name: s.name,
        skill_description: s.description,
        has_git: false,
        children: s.docs && s.docs.length > 0
          ? s.docs.map(docName => ({
              name: docName,
              path: `${s.name}/${docName}`,
              type: 'doc' as const,
              has_git: false,
            }))
          : null,
      })),
    [filteredBuiltinSkills],
  )

  // 节点展开切换
  const handleToggleExpand = (path: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  // 内容展开切换
  const handleToggleContent = async (node: SkillTreeNode) => {
    if (expandedContent === node.path) {
      setExpandedContent(null)
      return
    }
    setExpandedContent(node.path)
    if (!(node.path in contentCache)) {
      // 标记加载中（undefined = 未加载，null/string = 已加载）
      setContentCache(prev => ({ ...prev, [node.path]: undefined as unknown as string }))
      try {
        let content: string
        if (node.type === 'doc') {
          content = await skillsLibraryApi.getFile(node.path)
        } else {
          content = await skillsLibraryApi.getContent(node.path)
        }
        setContentCache(prev => ({ ...prev, [node.path]: content }))
      } catch {
        setContentCache(prev => ({ ...prev, [node.path]: '' }))
      }
    }
  }

  // 内置技能内容展开切换
  const handleToggleBuiltinContent = async (node: SkillTreeNode) => {
    if (builtinExpandedContent === node.path) {
      setBuiltinExpandedContent(null)
      return
    }
    setBuiltinExpandedContent(node.path)
    if (!(node.path in builtinContentCache)) {
      setBuiltinContentCache(prev => ({ ...prev, [node.path]: undefined as unknown as string }))
      try {
        let content: string
        if (node.type === 'doc') {
          // path 格式为 "skill-name/doc-file.md"
          const slashIdx = node.path.indexOf('/')
          const skillName = slashIdx > 0 ? node.path.slice(0, slashIdx) : node.path
          const filename = slashIdx > 0 ? node.path.slice(slashIdx + 1) : node.name
          content = await builtinSkillApi.getDoc(skillName, filename)
        } else {
          content = await builtinSkillApi.getContent(node.name)
        }
        setBuiltinContentCache(prev => ({ ...prev, [node.path]: content }))
      } catch {
        setBuiltinContentCache(prev => ({ ...prev, [node.path]: '' }))
      }
    }
  }

  // 删除
  const deleteMutation = useMutation({
    mutationFn: (name: string) => skillsLibraryApi.delete(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills-tree'] })
      notification.success('Skill 已删除')
      setDeleteTarget(null)
    },
    onError: (err: Error) => notification.error(`删除失败：${err.message}`),
  })

  // Pull 更新
  const handlePull = async (path: string) => {
    setPullingPath(path)
    try {
      const output = await skillsLibraryApi.pull(path)
      notification.success(output ? `更新完成：${output.slice(0, 120)}` : '已是最新')
      queryClient.invalidateQueries({ queryKey: ['skills-tree'] })
    } catch (err) {
      notification.error(`更新失败：${(err as Error).message}`)
    } finally {
      setPullingPath(null)
    }
  }

  // Clone
  const cloneMutation = useMutation({
    mutationFn: () => skillsLibraryApi.clone(cloneUrl.trim(), cloneTargetDir.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills-tree'] })
      notification.success(`已克隆到 ${cloneTargetDir}`)
      setCloneDialogOpen(false)
      setCloneUrl('')
      setCloneTargetDir('')
      setCloneUrlTouched(false)
    },
    onError: (err: Error) => notification.error(`克隆失败：${err.message}`),
  })

  // Upload (保留 zip 支持)
  const uploadMutation = useMutation({
    mutationFn: (file: File) => skillsLibraryApi.upload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills-tree'] })
      notification.success('Skill 上传成功')
    },
    onError: (err: Error) => notification.error(`上传失败：${err.message}`),
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.zip')) {
      notification.warning('请选择 .zip 格式的文件')
      return
    }
    uploadMutation.mutate(file)
    e.target.value = ''
  }

  const handleCloneUrlChange = (url: string) => {
    setCloneUrl(url)
    // 只有用户没手动修改过目标目录名时才自动派生
    if (!cloneUrlTouched) {
      setCloneTargetDir(autoDeriveName(url))
    }
  }

  // 顶级节点集合，用于判断节点是否为顶层
  const topLevelNames = useMemo(
    () => new Set((treeData ?? []).map(n => n.name)),
    [treeData],
  )

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* 合并导航行：Tabs + 操作区同行 */}
      <Box sx={{ display: 'flex', alignItems: 'center', borderColor: 'divider', mb: 2.5 }}>
        <Tabs
          value={pageTab}
          onChange={(_, v) => setPageTab(v)}
          sx={{ minHeight: 40, borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="用户技能库" sx={{ minHeight: 40, py: 0.75 }} />
          <Tab label={`内置技能${builtinSkills.length > 0 ? `（${builtinSkills.length}）` : ''}`} sx={{ minHeight: 40, py: 0.75 }} />
        </Tabs>

        <Box sx={{ flexGrow: 1 }} />

        {/* 操作区（搜索/视图/刷新对两个Tab均显示，上传/添加仅用户Tab） */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* 统计文字 */}
          <Typography variant="body2" color="text.secondary" sx={{ flexShrink: 0, mr: 0.5 }}>
            {pageTab === 0 && !isLoading && !error && (
              isSearching
                ? `${filteredSkills.length} / ${allSkills.length} 个技能`
                : `共 ${allSkills.length} 个技能`
            )}
            {pageTab === 1 && !builtinLoading && (
              isSearching
                ? `${filteredBuiltinSkills.length} / ${builtinSkills.length} 个技能`
                : `共 ${builtinSkills.length} 个技能`
            )}
          </Typography>

          {/* 搜索 */}
          <TextField
            size="small"
            placeholder="搜索技能..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            sx={{ width: 180 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: searchQuery ? (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setSearchQuery('')}>
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ) : undefined,
            }}
          />

          {/* 视图切换 */}
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(_, v) => v && setViewMode(v)}
            size="small"
          >
            <ToggleButton value="tree" aria-label="目录树">
              <Tooltip title="目录树视图">
                <TreeViewIcon fontSize="small" />
              </Tooltip>
            </ToggleButton>
            <ToggleButton value="flat" aria-label="平铺视图">
              <Tooltip title="平铺视图">
                <GridViewIcon fontSize="small" />
              </Tooltip>
            </ToggleButton>
          </ToggleButtonGroup>

          {/* 刷新 */}
          <Tooltip title="刷新">
            <IconButton
              onClick={() => pageTab === 0 ? refetch() : refetchBuiltin()}
              disabled={pageTab === 0 ? isLoading : builtinLoading}
              size="small"
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          {/* 上传 zip（仅用户Tab） */}
          {pageTab === 0 && (
            <>
              <input
                type="file"
                accept=".zip"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
              <Tooltip title="上传 Skill（.zip 格式）">
                <Button
                  variant="outlined"
                  startIcon={
                    uploadMutation.isPending ? <CircularProgress size={16} color="inherit" /> : <UploadIcon />
                  }
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadMutation.isPending}
                  size="small"
                >
                  上传 ZIP
                </Button>
              </Tooltip>

              {/* 添加 Skill（git clone） */}
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => setCloneDialogOpen(true)}
                size="small"
              >
                添加 Skill
              </Button>
            </>
          )}
        </Box>
      </Box>

      {/* ── 内置技能 Tab ── */}
      {pageTab === 1 && (
        <Box>
          {builtinLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
              <CircularProgress />
            </Box>
          ) : builtinNodes.length === 0 ? (
            <Box sx={{ textAlign: 'center', pt: 8 }}>
              <Typography color="text.secondary">
                {isSearching ? '没有匹配的技能' : '暂无内置技能'}
              </Typography>
            </Box>
          ) : viewMode === 'flat' ? (
            /* 平铺卡片视图 - 复用 SkillCard */
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 2 }}>
              {builtinNodes.map(node => (
                <SkillCard
                  key={node.path}
                  node={node}
                  isTopLevel={false}
                  expandedContent={builtinExpandedContent}
                  contentCache={builtinContentCache}
                  onDelete={() => {}}
                  onToggleContent={handleToggleBuiltinContent}
                />
              ))}
            </Box>
          ) : (
            /* 目录树视图 - 复用 SkillNodeRow */
            <Paper variant="outlined" sx={{ borderRadius: 2, overflow: 'hidden' }}>
              {builtinNodes.map((node, index) => (
                <Box key={node.path}>
                  {index > 0 && <Divider />}
                  <SkillNodeRow
                    node={node}
                    depth={0}
                    isTopLevel={false}
                    expandedNodes={expandedNodes}
                    expandedContent={builtinExpandedContent}
                    contentCache={builtinContentCache}
                    pullingPath={null}
                    onToggleExpand={handleToggleExpand}
                    onToggleContent={handleToggleBuiltinContent}
                    onDelete={() => {}}
                    onPull={() => {}}
                  />
                </Box>
              ))}
            </Paper>
          )}
        </Box>
      )}

      {/* ── 用户技能库 Tab 内容 ── */}
      {pageTab === 0 && <>

      {/* 错误提示 */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          加载 Skills 库失败：{(error as Error).message}
        </Alert>
      )}

      {/* 加载状态 */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}>
          <CircularProgress />
        </Box>
      ) : !treeData || treeData.length === 0 ? (
        /* 空状态 */
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pt: 8,
            gap: 2,
          }}
        >
          <ExtensionIcon sx={{ fontSize: 64, opacity: 0.3 }} />
          <Typography variant="h6" color="text.secondary">
            Skills 库为空
          </Typography>
          <Typography variant="body2" color="text.secondary">
            点击"添加 Skill"从 git 仓库克隆，或"上传 ZIP"添加本地包
          </Typography>
        </Box>
      ) : isSearching || viewMode === 'flat' ? (
        /* 平铺视图 / 搜索结果 */
        filteredSkills.length === 0 ? (
          <Box sx={{ textAlign: 'center', pt: 8 }}>
            <Typography color="text.secondary">没有匹配的技能</Typography>
          </Box>
        ) : (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: 2,
            }}
          >
            {filteredSkills.map(node => (
              <SkillCard
                key={node.path}
                node={node}
                isTopLevel={topLevelNames.has(node.name) && !node.path.includes('/')}
                expandedContent={expandedContent}
                contentCache={contentCache}
                onDelete={name => setDeleteTarget(name)}
                onToggleContent={handleToggleContent}
              />
            ))}
          </Box>
        )
      ) : (
        /* 目录树视图 */
        <Paper variant="outlined" sx={{ borderRadius: 2, overflow: 'hidden' }}>
          {treeData.map((node, index) => (
            <Box key={node.path}>
              {index > 0 && <Divider />}
              <SkillNodeRow
                node={node}
                depth={0}
                isTopLevel
                expandedNodes={expandedNodes}
                expandedContent={expandedContent}
                contentCache={contentCache}
                pullingPath={pullingPath}
                onToggleExpand={handleToggleExpand}
                onToggleContent={handleToggleContent}
                onDelete={name => setDeleteTarget(name)}
                onPull={handlePull}
              />
            </Box>
          ))}
        </Paper>
      )}

      {/* ── 添加 Skill 对话框 ── */}
      <Dialog
        open={cloneDialogOpen}
        onClose={() => !cloneMutation.isPending && setCloneDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>添加 Skill</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField
              label="Git 仓库地址"
              placeholder="https://github.com/user/my-skill.git"
              value={cloneUrl}
              onChange={e => handleCloneUrlChange(e.target.value)}
              fullWidth
              autoFocus
              disabled={cloneMutation.isPending}
            />
            <TextField
              label="保存目录名"
              helperText={
                cloneTargetDir
                  ? `将保存到：skills/${cloneTargetDir}`
                  : '自动生成自仓库名，可手动修改'
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
            取消
          </Button>
          <Button
            variant="contained"
            onClick={() => cloneMutation.mutate()}
            disabled={cloneMutation.isPending || !cloneUrl.trim() || !cloneTargetDir.trim()}
            startIcon={cloneMutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            {cloneMutation.isPending ? '克隆中...' : '克隆'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── 删除确认对话框 ── */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => !deleteMutation.isPending && setDeleteTarget(null)}
      >
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            确定要删除 <strong>{deleteTarget}</strong> 吗？此操作不可撤销，目录下的所有文件将被永久删除。
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setDeleteTarget(null)}
            disabled={deleteMutation.isPending}
          >
            取消
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget)}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? <CircularProgress size={20} /> : '删除'}
          </Button>
        </DialogActions>
      </Dialog>
      </>}
    </Box>
  )
}
