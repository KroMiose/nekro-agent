import { useState, useEffect } from 'react'
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
  MenuItem,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Skeleton,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Add as AddIcon,
  ExpandMore as ExpandMoreIcon,
  ChevronRight as ChevronRightIcon,
  Psychology as PsychologyIcon,
  Title as TitleIcon,
  Share as ShareIcon,
  FolderOpen as FolderOpenIcon,
  InsertDriveFile as FileIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  workspaceApi as _workspaceApi,
  WorkspaceDetail,
  memoryApi,
  MemoryTreeNode,
} from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { CHIP_VARIANTS } from '../../../theme/variants'
import { useTheme } from '@mui/material/styles'
import { Editor } from '@monaco-editor/react'
import { useTranslation } from 'react-i18next'

const CATEGORY_OPTIONS = ['context', 'preference', 'task', 'knowledge', 'environment']

function MemoryFileTree({
  nodes,
  selectedPath,
  onSelect,
  showTitle = false,
  depth = 0,
}: {
  nodes: MemoryTreeNode[]
  selectedPath: string | null
  onSelect: (path: string) => void
  showTitle?: boolean
  depth?: number
}) {
  const { t } = useTranslation('workspace')
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  return (
    <Box>
      {nodes.map(node => (
        <Box key={node.path}>
          {node.type === 'dir' ? (
            <>
              <Box
                onClick={() => setExpanded(e => ({ ...e, [node.path]: !e[node.path] }))}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                  pl: depth * 2 + 1,
                  py: 0.5,
                  cursor: 'pointer',
                  borderRadius: 1,
                  '&:hover': { bgcolor: 'action.hover' },
                  color: 'text.secondary',
                  fontSize: 13,
                }}
              >
                {expanded[node.path] ? (
                  <ExpandMoreIcon sx={{ fontSize: 16 }} />
                ) : (
                  <ChevronRightIcon sx={{ fontSize: 16 }} />
                )}
                <FolderOpenIcon sx={{ fontSize: 15, color: 'warning.main' }} />
                <Typography variant="body2" sx={{ fontSize: 13 }}>
                  {node.name}
                </Typography>
              </Box>
              {expanded[node.path] && node.children && (
                <MemoryFileTree
                  nodes={node.children}
                  selectedPath={selectedPath}
                  onSelect={onSelect}
                  showTitle={showTitle}
                  depth={depth + 1}
                />
              )}
            </>
          ) : (
            <Box
              onClick={() => onSelect(node.path)}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
                pl: depth * 2 + 2,
                py: 0.5,
                cursor: 'pointer',
                borderRadius: 1,
                bgcolor: selectedPath === node.path ? 'action.selected' : 'transparent',
                '&:hover': {
                  bgcolor: selectedPath === node.path ? 'action.selected' : 'action.hover',
                },
                fontSize: 13,
              }}
            >
              {node.path === '_na_context.md' ? (
                <PsychologyIcon sx={{ fontSize: 15, color: 'primary.main' }} />
              ) : (
                <FileIcon sx={{ fontSize: 15, color: 'text.disabled' }} />
              )}
              <Typography
                variant="body2"
                sx={{
                  fontSize: 13,
                  color: node.path === '_na_context.md' ? 'primary.main' : 'text.primary',
                  fontWeight: node.path === '_na_context.md' ? 600 : 400,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {showTitle ? node.meta?.title || node.name : node.name}
                {showTitle && node.meta?.title && node.meta.title !== node.name && (
                  <Typography
                    component="span"
                    sx={{ fontSize: 11, color: 'text.disabled', ml: 0.5 }}
                  >
                    {node.name}
                  </Typography>
                )}
              </Typography>
              {node.meta?.shared && (
                <Tooltip title={t('detail.memory.metadata.sharedToNA')}>
                  <ShareIcon
                    sx={{ fontSize: 13, color: 'success.main', ml: 'auto', mr: 1, flexShrink: 0 }}
                  />
                </Tooltip>
              )}
            </Box>
          )}
        </Box>
      ))}
    </Box>
  )
}

export default function MemoryTab({ workspace }: { workspace: WorkspaceDetail }) {
  const queryClient = useQueryClient()
  const theme = useTheme()
  const notification = useNotification()
  const { t } = useTranslation('workspace')
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [editRaw, setEditRaw] = useState('')
  const [showTitle, setShowTitle] = useState(false)
  const [newFileDialog, setNewFileDialog] = useState(false)
  const [newFileName, setNewFileName] = useState('')
  const [newFileCategory, setNewFileCategory] = useState('context')
  const [deleteDialog, setDeleteDialog] = useState(false)
  const [resetMemoryDialog, setResetMemoryDialog] = useState(false)

  const {
    data: tree = [],
    isLoading: treeLoading,
    refetch: refetchTree,
  } = useQuery({
    queryKey: ['memory-tree', workspace.id],
    queryFn: () => memoryApi.getTree(workspace.id),
  })

  const { data: fileContent, isLoading: fileLoading } = useQuery({
    queryKey: ['memory-file', workspace.id, selectedPath],
    queryFn: () => (selectedPath ? memoryApi.getFile(workspace.id, selectedPath) : null),
    enabled: !!selectedPath,
  })

  useEffect(() => {
    if (fileContent) {
      setEditRaw(fileContent.raw)
    }
  }, [fileContent])

  const saveMutation = useMutation({
    mutationFn: () => memoryApi.putFile(workspace.id, selectedPath!, editRaw),
    onSuccess: () => {
      notification.success(t('detail.memory.notifications.saveSuccess'))
      queryClient.invalidateQueries({ queryKey: ['memory-tree', workspace.id] })
      queryClient.invalidateQueries({ queryKey: ['memory-file', workspace.id, selectedPath] })
    },
    onError: () => notification.error(t('detail.memory.notifications.saveFailed')),
  })

  const deleteMutation = useMutation({
    mutationFn: () => memoryApi.deleteFile(workspace.id, selectedPath!),
    onSuccess: () => {
      notification.success(t('detail.memory.notifications.deleteSuccess'))
      setSelectedPath(null)
      setEditRaw('')
      setDeleteDialog(false)
      queryClient.invalidateQueries({ queryKey: ['memory-tree', workspace.id] })
    },
    onError: () => notification.error(t('detail.memory.notifications.deleteFailed')),
  })

  const resetMemoryMutation = useMutation({
    mutationFn: () => memoryApi.resetMemory(workspace.id),
    onSuccess: () => {
      notification.success(t('detail.memory.notifications.resetSuccess'))
      setSelectedPath(null)
      setEditRaw('')
      setResetMemoryDialog(false)
      queryClient.invalidateQueries({ queryKey: ['memory-tree', workspace.id] })
    },
    onError: () => notification.error(t('detail.memory.notifications.resetFailed')),
  })

  const createMutation = useMutation({
    mutationFn: () => {
      const today = new Date().toISOString().slice(0, 10)
      const fileName = newFileName.endsWith('.md') ? newFileName : `${newFileName}.md`
      const path = `${newFileCategory}/${fileName}`
      const raw = `---\ntitle: "${newFileName}"\ncategory: ${newFileCategory}\ntags: []\nshared: false\nupdated: "${today}"\n---\n\n`
      return memoryApi.putFile(workspace.id, path, raw).then(() => path)
    },
    onSuccess: path => {
      notification.success(t('detail.memory.notifications.createSuccess'))
      setNewFileDialog(false)
      setNewFileName('')
      setNewFileCategory('context')
      queryClient.invalidateQueries({ queryKey: ['memory-tree', workspace.id] })
      setSelectedPath(path)
    },
    onError: () => notification.error(t('detail.memory.notifications.createFailed')),
  })

  const isNaContext = selectedPath === '_na_context.md'
  const charCount = fileContent ? fileContent.content.length : 0

  return (
    <Box sx={{ display: 'flex', height: '100%', minHeight: 500, gap: 2 }}>
      {/* 左侧：文件树 */}
      <Card sx={{ width: 220, flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1 }, flex: 1, overflow: 'auto' }}>
          <Box
            sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}
          >
            <Typography
              variant="subtitle2"
              sx={{ fontSize: 12, color: 'text.secondary', fontWeight: 600 }}
            >
              {t('detail.memory.treeTitle')}
            </Typography>
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <Tooltip title={showTitle ? t('detail.memory.toggleFileTooltip_filename') : t('detail.memory.toggleTitleTooltip_title')}>
                <IconButton size="small" onClick={() => setShowTitle(v => !v)}>
                  <TitleIcon
                    sx={{ fontSize: 16, color: showTitle ? 'primary.main' : 'text.secondary' }}
                  />
                </IconButton>
              </Tooltip>
              <Tooltip title={t('detail.memory.newFileTooltip')}>
                <IconButton size="small" onClick={() => setNewFileDialog(true)}>
                  <AddIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
              <Tooltip title={t('detail.memory.refreshTooltip')}>
                <IconButton size="small" onClick={() => refetchTree()} disabled={treeLoading}>
                  {treeLoading ? (
                    <CircularProgress size={14} />
                  ) : (
                    <RefreshIcon sx={{ fontSize: 16 }} />
                  )}
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          {tree.length === 0 && !treeLoading ? (
            <Typography
              variant="body2"
              sx={{ color: 'text.disabled', fontSize: 12, textAlign: 'center', py: 2 }}
            >
              {t('detail.memory.emptyHint')}
            </Typography>
          ) : (
            <MemoryFileTree
              nodes={tree}
              selectedPath={selectedPath}
              onSelect={setSelectedPath}
              showTitle={showTitle}
            />
          )}
        </CardContent>
        {/* 底部：重置记忆库按钮（固定，不随内容滚动） */}
        <Box sx={{ px: 1.5, py: 1, borderTop: '1px solid', borderColor: 'divider', flexShrink: 0 }}>
          <Button
            fullWidth
            size="small"
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon sx={{ fontSize: 14 }} />}
            onClick={() => setResetMemoryDialog(true)}
            sx={{ fontSize: '0.72rem' }}
          >
            {t('detail.memory.buttons.resetMemory')}
          </Button>
        </Box>
      </Card>

      {/* 右侧：编辑区 */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 1.5, overflow: 'hidden' }}>
        {!selectedPath ? (
          <Card sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Box sx={{ textAlign: 'center', color: 'text.disabled' }}>
              <PsychologyIcon sx={{ fontSize: 48, mb: 1, opacity: 0.3 }} />
              <Typography variant="body2">{t('detail.memory.editorHint')}</Typography>
            </Box>
          </Card>
        ) : (
          <>
            {/* 文件属性 */}
            <Card>
              <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                {fileLoading ? (
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Skeleton variant="text" width={140} height={38} />
                    <Skeleton variant="rounded" width={72} height={20} />
                    <Skeleton variant="rounded" width={72} height={20} />
                  </Box>
                ) : (
                  <Box
                    sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start', flexWrap: 'wrap' }}
                  >
                    <Box sx={{ flex: 1, minWidth: 160 }}>
                      <Typography variant="caption" color="text.secondary">
                        {t('detail.memory.metadata.title')}
                      </Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {fileContent?.meta.title || selectedPath}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {t('detail.memory.metadata.category')}
                      </Typography>
                      <Box sx={{ mt: 0.3 }}>
                        <Chip
                          label={fileContent?.meta.category || '—'}
                          size="small"
                          sx={CHIP_VARIANTS.base(true)}
                        />
                      </Box>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {t('detail.memory.metadata.shared')}
                      </Typography>
                      <Box sx={{ mt: 0.3 }}>
                        <Chip
                          label={fileContent?.meta.shared ? t('detail.memory.metadata.yes') : t('detail.memory.metadata.no')}
                          size="small"
                          sx={CHIP_VARIANTS.getCustomColorChip(
                            fileContent?.meta.shared ? '#4caf50' : '#9e9e9e',
                            true
                          )}
                        />
                      </Box>
                    </Box>
                    {fileContent?.meta.tags?.length ? (
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          {t('detail.memory.metadata.tags')}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5, mt: 0.3, flexWrap: 'wrap' }}>
                          {fileContent.meta.tags.map(tag => (
                            <Chip key={tag} label={tag} size="small" sx={CHIP_VARIANTS.base(true)} />
                          ))}
                        </Box>
                      </Box>
                    ) : null}
                    {isNaContext && (
                      <Box sx={{ ml: 'auto' }}>
                        <Typography
                          variant="caption"
                          color={charCount > 500 ? 'warning.main' : 'text.secondary'}
                        >
                          {t('detail.memory.charCount', { count: charCount })}
                        </Typography>
                      </Box>
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>

            {/* 编辑器 */}
            <Card sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ flex: 1, overflow: 'hidden' }}>
                {fileLoading ? (
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                    }}
                  >
                    <CircularProgress size={32} />
                  </Box>
                ) : (
                  <Editor
                    height="100%"
                    defaultLanguage="markdown"
                    value={editRaw}
                    onChange={v => setEditRaw(v ?? '')}
                    theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'vs'}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 13,
                      lineNumbers: 'on',
                      wordWrap: 'on',
                      scrollBeyondLastLine: false,
                      renderLineHighlight: 'none',
                    }}
                  />
                )}
              </Box>
            </Card>

            {/* 操作按钮 */}
            <Box
              sx={{
                display: 'flex',
                gap: 1,
                justifyContent: 'flex-end',
                visibility: fileLoading ? 'hidden' : 'visible',
              }}
            >
              <Button
                variant="outlined"
                color="error"
                size="small"
                startIcon={<DeleteIcon />}
                onClick={() => setDeleteDialog(true)}
              >
                {t('detail.memory.buttons.delete')}
              </Button>
              <Button
                variant="contained"
                size="small"
                startIcon={
                  saveMutation.isPending ? (
                    <CircularProgress size={14} color="inherit" />
                  ) : (
                    <SaveIcon />
                  )
                }
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
              >
                {t('detail.memory.buttons.save')}
              </Button>
            </Box>
          </>
        )}
      </Box>

      {/* 新建文件弹窗 */}
      <Dialog open={newFileDialog} onClose={() => setNewFileDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{t('detail.memory.newFileDialog.title')}</DialogTitle>
        <DialogContent
          sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '20px !important' }}
        >
          <TextField
            label={t('detail.memory.newFileDialog.categoryLabel')}
            select
            value={newFileCategory}
            onChange={e => setNewFileCategory(e.target.value)}
            size="small"
            fullWidth
          >
            {CATEGORY_OPTIONS.map(c => (
              <MenuItem key={c} value={c}>
                {c}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label={t('detail.memory.newFileDialog.fileNameLabel')}
            value={newFileName}
            onChange={e => setNewFileName(e.target.value)}
            size="small"
            fullWidth
            placeholder={t('detail.memory.newFileDialog.fileNamePlaceholder')}
            helperText={t('detail.memory.newFileDialog.willCreate', { path: `${newFileCategory}/${newFileName || 'filename'}.md` })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewFileDialog(false)}>{t('detail.memory.newFileDialog.cancel')}</Button>
          <Button
            variant="contained"
            disabled={!newFileName.trim() || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            {t('detail.memory.newFileDialog.create')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除确认弹窗 */}
      <Dialog open={deleteDialog} onClose={() => setDeleteDialog(false)} maxWidth="xs">
        <DialogTitle>{t('detail.memory.deleteDialog.title')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t('detail.memory.deleteDialog.content', { path: selectedPath })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog(false)}>{t('detail.memory.deleteDialog.cancel')}</Button>
          <Button
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
            onClick={() => deleteMutation.mutate()}
          >
            {t('detail.memory.deleteDialog.delete')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 重置记忆库确认对话框 */}
      <Dialog
        open={resetMemoryDialog}
        onClose={() => !resetMemoryMutation.isPending && setResetMemoryDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ color: 'error.main' }}>{t('detail.memory.resetDialog.title')}</DialogTitle>
        <DialogContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            <strong>{t('detail.memory.resetDialog.warning')}</strong>
          </Alert>
          <DialogContentText>
            {t('detail.memory.resetDialog.content')}
          </DialogContentText>
          <DialogContentText sx={{ mt: 1.5, color: 'warning.main', fontSize: '0.85rem' }}>
            {t('detail.memory.resetDialog.hint')}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setResetMemoryDialog(false)}
            disabled={resetMemoryMutation.isPending}
          >
            {t('detail.memory.resetDialog.cancel')}
          </Button>
          <Button
            variant="contained"
            color="error"
            disabled={resetMemoryMutation.isPending}
            onClick={() => resetMemoryMutation.mutate()}
          >
            {resetMemoryMutation.isPending ? <CircularProgress size={20} /> : t('detail.memory.resetDialog.confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
