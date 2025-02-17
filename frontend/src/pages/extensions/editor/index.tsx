import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Box,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Typography,
  Divider,
  CircularProgress,
  Alert,
  SelectChangeEvent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Tooltip,
  Snackbar,
  DialogContentText,
  ButtonGroup,
} from '@mui/material'
import {
  Save as SaveIcon,
  Add as AddIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Extension as ExtensionIcon,
  AutoAwesome as AutoAwesomeIcon,
} from '@mui/icons-material'
import { Editor } from '@monaco-editor/react'
import { useTheme } from '@mui/material/styles'
import {
  extensionsApi,
  streamGenerateCode,
  deleteExtensionFile,
} from '../../../services/api/extensions'

// 新建扩展对话框组件
interface NewExtensionDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: (name: string, description: string) => void
}

function NewExtensionDialog({ open, onClose, onConfirm }: NewExtensionDialogProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')

  const handleConfirm = () => {
    if (!name) {
      setError('请输入扩展名称')
      return
    }
    if (!name.match(/^[a-z][a-z0-9_]*$/)) {
      setError('扩展名称只能包含小写字母、数字和下划线，且必须以字母开头')
      return
    }
    if (!description) {
      setError('请输入扩展描述')
      return
    }
    onConfirm(name, description)
    handleClose()
  }

  const handleClose = () => {
    setName('')
    setDescription('')
    setError('')
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>新建扩展</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          {error && (
            <Alert severity="error" onClose={() => setError('')}>
              {error}
            </Alert>
          )}
          <TextField
            label="扩展名称"
            value={name}
            onChange={e => setName(e.target.value)}
            helperText="只能包含小写字母、数字和下划线，且必须以字母开头"
            fullWidth
            required
          />
          <TextField
            label="扩展描述"
            value={description}
            onChange={e => setDescription(e.target.value)}
            fullWidth
            required
            multiline
            rows={2}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>取消</Button>
        <Button onClick={handleConfirm} variant="contained">
          创建
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// 主页面组件
export default function ExtensionsEditorPage() {
  const [selectedFile, setSelectedFile] = useState<string>('')
  const [files, setFiles] = useState<string[]>([])
  const [code, setCode] = useState<string>('')
  const [originalCode, setOriginalCode] = useState<string>('')
  const [prompt, setPrompt] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')
  const [generatedCode, setGeneratedCode] = useState<string>('')
  const [isNewExtensionDialogOpen, setIsNewExtensionDialogOpen] = useState(false)
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [fileToDelete, setFileToDelete] = useState<string | null>(null)
  const [reloadExtDialogOpen, setReloadExtDialogOpen] = useState(false)
  const theme = useTheme()
  const generatedCodeRef = useRef<HTMLDivElement>(null)

  // 加载文件列表
  useEffect(() => {
    const loadFiles = async () => {
      try {
        const files = (await extensionsApi.getExtensionFiles()) as string[]
        setFiles(files)
        if (files.length > 0 && !selectedFile) {
          setSelectedFile(files[0])
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : '未知错误'
        setError('加载文件列表失败: ' + errorMessage)
        console.error('Failed to load files:', err)
      }
    }
    loadFiles()
  }, [selectedFile])

  // 加载选中文件的内容
  useEffect(() => {
    const loadFileContent = async () => {
      if (!selectedFile) return
      setIsLoading(true)
      try {
        const content = (await extensionsApi.getExtensionFiles(selectedFile)) as string
        setCode(content)
        setOriginalCode(content)
        setHasUnsavedChanges(false)
        setError('')
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : '未知错误'
        setError('加载文件内容失败: ' + errorMessage)
        console.error('Failed to load file content:', err)
      } finally {
        setIsLoading(false)
      }
    }
    loadFileContent()
  }, [selectedFile])

  // 保存文件内容
  const handleSave = useCallback(async () => {
    if (!selectedFile || !code) return
    setIsSaving(true)
    try {
      await extensionsApi.saveExtensionFile(selectedFile, code)
      setOriginalCode(code)
      setHasUnsavedChanges(false)
      setSuccess('保存成功')
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '未知错误'
      setError('保存失败: ' + errorMessage)
    } finally {
      setIsSaving(false)
    }
  }, [code, selectedFile, setError, setHasUnsavedChanges, setIsSaving, setOriginalCode, setSuccess])

  // 监听保存快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleSave])

  // 滚动到底部的函数
  const scrollToBottom = useCallback(() => {
    if (generatedCodeRef.current) {
      const element = generatedCodeRef.current
      element.scrollTo({
        top: element.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [])

  // 生成代码
  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError('请输入提示词')
      return
    }

    setIsGenerating(true)
    setError('')
    setGeneratedCode('')

    try {
      const cleanup = streamGenerateCode(
        selectedFile,
        prompt,
        code,
        data => {
          try {
            const jsonData = JSON.parse(data)
            if (jsonData.type === 'content') {
              setGeneratedCode(prev => {
                const newCode = prev + jsonData.content
                requestAnimationFrame(scrollToBottom)
                return newCode
              })
            } else if (jsonData.type === 'error') {
              setError(jsonData.error)
              setIsGenerating(false)
            } else if (jsonData.type === 'done') {
              setIsGenerating(false)
            }
          } catch (err) {
            console.error('解析消息失败:', err)
          }
        },
        error => {
          console.error('生成代码失败:', error)
          setError(`生成代码失败: ${error.message}`)
          setIsGenerating(false)
        }
      )

      return cleanup
    } catch (err) {
      console.error('启动代码生成失败:', err)
      setError('启动代码生成失败')
      setIsGenerating(false)
    }
  }

  // 应用生成的代码
  const handleApplyCode = async () => {
    if (!selectedFile || !generatedCode) return
    setIsApplying(true)
    try {
      const result = await extensionsApi.applyGeneratedCode(selectedFile, prompt, generatedCode)
      setCode(result)
      setHasUnsavedChanges(true)
      setSuccess('代码应用成功')
    } catch (error) {
      setError(error instanceof Error ? error.message : '代码应用失败')
    } finally {
      setIsApplying(false)
    }
  }

  // 处理文件选择
  const handleFileSelect = (event: SelectChangeEvent<string>) => {
    if (hasUnsavedChanges) {
      if (window.confirm('当前文件有未保存的更改，确定要切换文件吗？')) {
        setSelectedFile(event.target.value)
      }
    } else {
      setSelectedFile(event.target.value)
    }
  }

  // 重置代码
  const handleResetCode = () => {
    setCode(originalCode)
    setHasUnsavedChanges(false)
    setIsResetDialogOpen(false)
  }

  // 处理代码变更
  const handleCodeChange = useCallback(
    (value: string | undefined) => {
      const newCode = value || ''
      setCode(newCode)
      setHasUnsavedChanges(newCode !== originalCode)
    },
    [originalCode]
  )

  // 导入扩展文件
  const handleImportFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.py')) {
      setError('只能导入 Python 文件')
      return
    }

    const reader = new FileReader()
    reader.onload = async e => {
      try {
        const content = e.target?.result as string
        await extensionsApi.saveExtensionFile(file.name, content)
        // 重新加载文件列表
        const files = (await extensionsApi.getExtensionFiles()) as string[]
        setFiles(files)
        setSelectedFile(file.name)
        setError('')
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : '未知错误'
        setError('导入文件失败: ' + errorMessage)
      }
    }
    reader.readAsText(file)
  }

  // 创建新扩展
  const handleCreateNewExtension = async (name: string, description: string) => {
    const fileName = `${name}.py`
    try {
      // 获取模板内容
      const template = await extensionsApi.generateExtensionTemplate(name, description)
      // 保存文件
      await extensionsApi.saveExtensionFile(fileName, template)
      // 重新加载文件列表
      const files = (await extensionsApi.getExtensionFiles()) as string[]
      setFiles(files)
      setSelectedFile(fileName)
      setError('')
      setIsNewExtensionDialogOpen(false)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '未知错误'
      setError('创建扩展失败: ' + errorMessage)
      console.error('Failed to create extension:', err)
    }
  }

  const handleDeleteConfirm = async () => {
    if (fileToDelete) {
      try {
        await deleteExtensionFile(fileToDelete)
        setSuccess('文件删除成功')
        // 如果删除的是当前选中的文件，清空编辑器
        if (fileToDelete === selectedFile) {
          setSelectedFile('')
          setCode('')
        }
        // 重新加载文件列表
        const files = (await extensionsApi.getExtensionFiles()) as string[]
        setFiles(files)
      } catch (err) {
        setError(`删除文件失败: ${err}`)
      }
    }
    setDeleteDialogOpen(false)
    setFileToDelete(null)
  }

  // 重载扩展
  const handleReloadExt = async () => {
    try {
      setIsGenerating(true)
      await extensionsApi.reloadExtensions()
      // 重新加载文件列表
      const files = (await extensionsApi.getExtensionFiles()) as string[]
      setFiles(files)
      setSuccess('扩展重载成功')
      setReloadExtDialogOpen(false)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '未知错误'
      setError('重载扩展失败: ' + errorMessage)
      console.error('Failed to reload extensions:', err)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 2,
        height: 'calc(100vh - 120px)',
      }}
    >
      {/* 左侧编辑器区域 */}
      <Paper
        elevation={3}
        sx={{
          flex: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          p: 2,
          minWidth: 0,
        }}
      >
        {/* 顶部工具栏 */}
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', gap: 2, flex: 1 }}>
            <FormControl sx={{ flex: 1 }}>
              <InputLabel>选择扩展文件</InputLabel>
              <Select value={selectedFile} label="选择扩展文件" onChange={handleFileSelect}>
                {files.map(file => (
                  <MenuItem
                    key={file}
                    value={file}
                    sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                  >
                    {file}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Tooltip title="新建扩展">
                <IconButton color="primary" onClick={() => setIsNewExtensionDialogOpen(true)}>
                  <AddIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="导入扩展">
                <IconButton color="primary" component="label">
                  <input type="file" hidden accept=".py" onChange={handleImportFile} />
                  <UploadIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="保存 (Ctrl+S)">
                <span>
                  <IconButton
                    color="primary"
                    onClick={handleSave}
                    disabled={!hasUnsavedChanges || isSaving}
                  >
                    {isSaving ? <CircularProgress size={24} /> : <SaveIcon />}
                  </IconButton>
                </span>
              </Tooltip>
            </Box>
          </Box>
        </Box>

        {/* 错误提示 */}
        {error && (
          <Alert severity="error" onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* 成功提示 */}
        <Snackbar
          open={!!success}
          autoHideDuration={3000}
          onClose={() => setSuccess('')}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <Alert onClose={() => setSuccess('')} severity="success" sx={{ width: '100%' }}>
            {success}
          </Alert>
        </Snackbar>

        {/* 代码编辑器 */}
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {(isLoading || isApplying) && (
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: theme =>
                  `${theme.palette.background.paper}${isApplying ? '80' : 'FF'}`,
                zIndex: 1,
                transition: 'background-color 0.3s ease',
              }}
            >
              <CircularProgress size={40} sx={{ mb: 2 }} />
              <Typography>{isLoading ? '加载中...' : '正在应用修改意见...'}</Typography>
            </Box>
          )}
          <Editor
            height="100%"
            defaultLanguage="python"
            theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'light'}
            value={code}
            onChange={handleCodeChange}
            loading={<CircularProgress />}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              tabSize: 4,
              insertSpaces: true,
              autoIndent: 'full',
              formatOnPaste: true,
              formatOnType: true,
              scrollBeyondLastLine: false,
            }}
          />
        </Box>
      </Paper>

      {/* 右侧区域 */}
      <Paper
        elevation={3}
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          p: 2,
          minWidth: 0,
        }}
      >
        {/* 操作区 */}
        <Box>
          <Typography variant="h6" sx={{ mb: 1 }}>
            操作区
          </Typography>
          <ButtonGroup variant="outlined" fullWidth>
            <Button
              startIcon={<RefreshIcon />}
              onClick={() => setIsResetDialogOpen(true)}
              disabled={!hasUnsavedChanges}
              color="warning"
            >
              重载代码
            </Button>
            <Button
              startIcon={<DeleteIcon />}
              onClick={() => {
                if (selectedFile) {
                  setFileToDelete(selectedFile)
                  setDeleteDialogOpen(true)
                }
              }}
              color="error"
              disabled={!selectedFile}
            >
              删除扩展
            </Button>
            <Tooltip title="修改后的扩展需要重载才能生效" arrow placement="top">
              <Button
                startIcon={<ExtensionIcon />}
                onClick={() => setReloadExtDialogOpen(true)}
                color="primary"
              >
                重载扩展
              </Button>
            </Tooltip>
          </ButtonGroup>
        </Box>

        <Divider />

        <Typography variant="h6">扩展需求</Typography>

        {/* 提示词输入框 */}
        <TextField
          multiline
          rows={4}
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          label="需求提示词"
          placeholder="描述你想要实现的扩展功能..."
          onKeyDown={e => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
              e.preventDefault()
              if (prompt.trim() && !isGenerating) {
                handleGenerate()
              }
            }
          }}
        />

        <Button
          variant="contained"
          color="primary"
          startIcon={<AutoAwesomeIcon />}
          onClick={handleGenerate}
          disabled={isGenerating || isApplying}
          sx={{
            background: theme => theme.palette.primary.main,
            '&:hover': {
              background: theme => theme.palette.primary.dark,
            },
          }}
        >
          {isGenerating ? (
            <CircularProgress size={24} />
          ) : (
            <>
              AI 生成
              <Box
                component="span"
                sx={{
                  ml: 1,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '2px',
                  opacity: 0.8,
                  fontSize: '0.75em',
                }}
              >
                <Box
                  component="span"
                  sx={{
                    border: '1px solid rgba(255,255,255,0.3)',
                    borderRadius: '4px',
                    padding: '1px 4px',
                    lineHeight: 1,
                    fontFamily: 'monospace',
                    background: 'rgba(255,255,255,0.1)',
                  }}
                >
                  {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}
                </Box>
                <Box component="span" sx={{ mx: '2px' }}>
                  +
                </Box>
                <Box
                  component="span"
                  sx={{
                    border: '1px solid rgba(255,255,255,0.3)',
                    borderRadius: '4px',
                    padding: '1px 4px',
                    lineHeight: 1,
                    fontFamily: 'monospace',
                    background: 'rgba(255,255,255,0.1)',
                  }}
                >
                  Enter
                </Box>
              </Box>
            </>
          )}
        </Button>

        <Divider />
        <Typography variant="h6">生成结果</Typography>

        {/* 生成结果区域 */}
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            overflow: 'auto',
            position: 'relative',
            p: 2,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {isApplying && (
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: 'rgba(0, 0, 0, 0.3)',
                zIndex: 1,
              }}
            >
              <CircularProgress />
            </Box>
          )}
          {generatedCode ? (
            <>
              <Box
                ref={generatedCodeRef}
                sx={{
                  flex: 1,
                  minHeight: 0,
                  maxHeight: '100%',
                  overflow: 'auto',
                  bgcolor: theme.palette.mode === 'dark' ? '#1E1E1E' : '#f5f5f5',
                  p: 2,
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  fontSize: '14px',
                  '&::-webkit-scrollbar': {
                    width: '8px',
                  },
                  '&::-webkit-scrollbar-track': {
                    background: 'transparent',
                  },
                  '&::-webkit-scrollbar-thumb': {
                    background: theme.palette.mode === 'dark' ? '#555' : '#ccc',
                    borderRadius: '4px',
                  },
                }}
              >
                {generatedCode}
              </Box>
              <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  variant="contained"
                  color="success"
                  onClick={handleApplyCode}
                  startIcon={<SaveIcon />}
                >
                  应用到编辑器
                </Button>
              </Box>
            </>
          ) : (
            <Box
              sx={{
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'text.secondary',
              }}
            >
              {isGenerating ? (
                <Box sx={{ textAlign: 'center' }}>
                  <CircularProgress size={40} sx={{ mb: 2 }} />
                  <Typography>正在生成代码...</Typography>
                </Box>
              ) : (
                <Typography>生成的代码将在这里显示...</Typography>
              )}
            </Box>
          )}
        </Box>
      </Paper>

      {/* 新建扩展对话框 */}
      <NewExtensionDialog
        open={isNewExtensionDialogOpen}
        onClose={() => setIsNewExtensionDialogOpen(false)}
        onConfirm={handleCreateNewExtension}
      />

      {/* 重置代码确认对话框 */}
      <Dialog open={isResetDialogOpen} onClose={() => setIsResetDialogOpen(false)}>
        <DialogTitle>确认重置代码？</DialogTitle>
        <DialogContent>
          <Typography>
            这将丢弃当前所有未保存的更改，并恢复到服务器上的代码版本。此操作无法撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsResetDialogOpen(false)}>取消</Button>
          <Button onClick={handleResetCode} color="warning" variant="contained">
            重置
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <DialogContentText>确定要删除文件 {fileToDelete} 吗？此操作不可恢复。</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>取消</Button>
          <Button onClick={handleDeleteConfirm} color="error">
            删除
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add new reload extension dialog */}
      <Dialog open={reloadExtDialogOpen} onClose={() => setReloadExtDialogOpen(false)}>
        <DialogTitle>确认重载扩展</DialogTitle>
        <DialogContent>
          <DialogContentText>这将重新加载所有扩展文件并更新应用。确定要继续吗？</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReloadExtDialogOpen(false)}>取消</Button>
          <Button onClick={handleReloadExt} color="primary" variant="contained">
            重载
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
