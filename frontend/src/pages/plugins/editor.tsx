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
  Menu,
} from '@mui/material'
import {
  Save as SaveIcon,
  Add as AddIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Extension as ExtensionIcon,
  AutoAwesome as AutoAwesomeIcon,
  MoreVert as MoreVertIcon,
  PowerSettingsNew as PowerIcon,
  ContentCopy as ContentCopyIcon,
  Clear as ClearIcon,
  Block as BlockIcon,
} from '@mui/icons-material'
import { Editor } from '@monaco-editor/react'
import { useTheme } from '@mui/material/styles'
import { pluginEditorApi, streamGenerateCode } from '../../services/api/plugin-editor'
import { reloadPlugins } from '../../services/api/plugins'

// 新建插件对话框组件
interface NewPluginDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: (name: string, description: string) => void
}

function NewPluginDialog({ open, onClose, onConfirm }: NewPluginDialogProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')

  const handleConfirm = () => {
    if (!name) {
      setError('请输入插件名称')
      return
    }
    if (!name.match(/^[a-z][a-z0-9_]*$/)) {
      setError('插件名称只能包含小写字母、数字和下划线，且必须以字母开头')
      return
    }
    if (!description) {
      setError('请输入插件描述')
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
      <DialogTitle>新建插件</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          {error && (
            <Alert severity="error" onClose={() => setError('')}>
              {error}
            </Alert>
          )}
          <TextField
            label="插件名称"
            value={name}
            onChange={e => setName(e.target.value)}
            helperText="只能包含小写字母、数字和下划线，且必须以字母开头"
            fullWidth
            required
          />
          <TextField
            label="插件描述"
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
export default function PluginsEditorPage() {
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
  const [isNewPluginDialogOpen, setIsNewPluginDialogOpen] = useState(false)
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [fileToDelete, setFileToDelete] = useState<string>('')
  const [reloadExtDialogOpen, setReloadExtDialogOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [isDisableDialogOpen, setIsDisableDialogOpen] = useState(false)
  const open = Boolean(anchorEl)
  const theme = useTheme()
  const generatedCodeRef = useRef<HTMLDivElement>(null)
  const [isCopied, setIsCopied] = useState(false)
  const [abortController, setAbortController] = useState<AbortController | null>(null)

  // 加载文件列表
  useEffect(() => {
    const loadFiles = async () => {
      try {
        const files = await pluginEditorApi.getPluginFiles()
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
        const content = await pluginEditorApi.getPluginFileContent(selectedFile)
        setCode(content || '')
        setOriginalCode(content || '')
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
      await pluginEditorApi.savePluginFile(selectedFile, code)
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

    if (isGenerating) {
      // 如果正在生成，则中断当前生成过程
      abortController?.abort()
      setIsGenerating(false)
      setAbortController(null)
      return
    }

    setIsGenerating(true)
    setError('')
    setGeneratedCode('')

    try {
      const controller = new AbortController()
      setAbortController(controller)

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
              setAbortController(null)
            } else if (jsonData.type === 'done') {
              setIsGenerating(false)
              setAbortController(null)
            }
          } catch (err) {
            console.error('解析消息失败:', err)
          }
        },
        error => {
          if (error.name !== 'AbortError') {
            console.error('生成代码失败:', error)
            setError(`生成代码失败: ${error.message}`)
          }
          setIsGenerating(false)
          setAbortController(null)
        },
        controller.signal
      )

      return () => {
        cleanup()
        controller.abort()
      }
    } catch (err) {
      console.error('启动代码生成失败:', err)
      setError('启动代码生成失败')
      setIsGenerating(false)
      setAbortController(null)
    }
  }

  // 组件卸载时中断生成
  useEffect(() => {
    return () => {
      abortController?.abort()
    }
  }, [abortController])

  // 应用生成的代码
  const handleApplyCode = async () => {
    if (!selectedFile || !generatedCode) return
    setIsApplying(true)
    try {
      const result = await pluginEditorApi.applyGeneratedCode(selectedFile, prompt, generatedCode)
      setCode(result || '')
      setHasUnsavedChanges(true)
      setSuccess('代码应用成功')
    } catch (error) {
      setError(error instanceof Error ? error.message : '代码应用失败')
    } finally {
      setIsApplying(false)
    }
  }

  // 处理文件选择
  const handleFileSelect = async (event: SelectChangeEvent<string>) => {
    const newSelectedFile = event.target.value
    if (newSelectedFile !== selectedFile) {
      if (hasUnsavedChanges && selectedFile) {
        setHasUnsavedChanges(false)
        setFileToDelete(selectedFile)
        setDeleteDialogOpen(true)
        return
      }

      setSelectedFile(newSelectedFile)
      if (newSelectedFile) {
        setIsLoading(true)
        try {
          const content = await pluginEditorApi.getPluginFileContent(newSelectedFile)
          setCode(content || '')
          setOriginalCode(content || '')
          setHasUnsavedChanges(false)
        } catch (error) {
          setError(`获取文件内容失败: ${error}`)
          setCode('')
          setOriginalCode('')
        } finally {
          setIsLoading(false)
        }
      } else {
        setCode('')
        setOriginalCode('')
      }
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

  // 导入插件文件
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
        await pluginEditorApi.savePluginFile(file.name, content)
        // 重新加载文件列表
        const files = await pluginEditorApi.getPluginFiles()
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

  // 创建新插件
  const handleCreateNewPlugin = async (name: string, description: string) => {
    const fileName = `${name}.py`
    try {
      // 获取模板内容
      const template = await pluginEditorApi.generatePluginTemplate(name, description)
      // 保存文件
      await pluginEditorApi.savePluginFile(fileName, template || '')
      // 重新加载文件列表
      const files = await pluginEditorApi.getPluginFiles()
      setFiles(files)
      setSelectedFile(fileName)
      setError('')
      setIsNewPluginDialogOpen(false)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '未知错误'
      setError('创建插件失败: ' + errorMessage)
      console.error('Failed to create extension:', err)
    }
  }

  const handleDeleteConfirm = async () => {
    if (fileToDelete) {
      try {
        await pluginEditorApi.deletePluginFile(fileToDelete)
        setSuccess('文件删除成功')
        // 如果删除的是当前选中的文件，清空编辑器
        if (fileToDelete === selectedFile) {
          setSelectedFile('')
          setCode('')
        }
        // 重新加载文件列表
        const files = await pluginEditorApi.getPluginFiles()
        setFiles(files)
      } catch (error) {
        setError('删除失败: ' + (error instanceof Error ? error.message : String(error)))
      }
      setDeleteDialogOpen(false)
      setFileToDelete('')
    }
  }

  // 重载插件
  const handleReloadExt = async () => {
    if (!selectedFile) {
      setError('请先选择一个插件文件')
      return
    }

    try {
      setIsGenerating(true)
      // 获取模块名称：去掉扩展名(.py或.disabled)的文件名
      const moduleName = selectedFile.replace(/\.(py|disabled)$/, '')
      if (!moduleName) {
        setError('无法获取有效的模块名')
        return
      }

      const result = await reloadPlugins(moduleName)
      if (!result.success) {
        setError(result.errorMsg || '重载插件失败: 未知错误')
        setReloadExtDialogOpen(false)
        return
      }

      // 重新加载文件列表
      const files = await pluginEditorApi.getPluginFiles()
      setFiles(files)
      setSuccess(`插件 ${moduleName} 重载成功`)
      setReloadExtDialogOpen(false)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '未知错误'
      setError(errorMessage)
      console.error('Failed to reload plugins:', err)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleTogglePlugin = async () => {
    if (!selectedFile) return

    try {
      const isDisabled = selectedFile.endsWith('.disabled')
      const newFileName = isDisabled
        ? selectedFile.replace('.disabled', '')
        : `${selectedFile}.disabled`

      await pluginEditorApi.savePluginFile(newFileName, code)
      await pluginEditorApi.deletePluginFile(selectedFile)

      // 更新文件列表和选中文件
      const files = await pluginEditorApi.getPluginFiles()
      setFiles(files)
      setSelectedFile(newFileName)

      setSuccess(`插件${isDisabled ? '启用' : '禁用'}成功，请重载插件使更改生效`)
      setIsDisableDialogOpen(false)
    } catch (err) {
      setError(`${selectedFile.endsWith('.disabled') ? '启用' : '禁用'}插件失败: ${err}`)
    }
  }

  const handleCopyCode = () => {
    if (generatedCode) {
      navigator.clipboard.writeText(generatedCode)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    }
  }

  const handleClearCode = () => {
    setGeneratedCode('')
  }

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 2,
        height: 'calc(100vh - 90px)',
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
              <InputLabel>选择插件文件</InputLabel>
              <Select value={selectedFile} label="选择插件文件" onChange={handleFileSelect}>
                {files.map(file => {
                  const isDisabled = file.endsWith('.disabled')
                  return (
                    <MenuItem
                      key={file}
                      value={file}
                      sx={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        color: isDisabled ? 'text.disabled' : 'text.primary',
                        ...(isDisabled && {
                          background: theme =>
                            theme.palette.mode === 'dark'
                              ? 'rgba(255, 0, 0, 0.08)'
                              : 'rgba(255, 0, 0, 0.05)',
                          fontStyle: 'italic',
                        }),
                      }}
                    >
                      <Box component="span" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {isDisabled && (
                          <BlockIcon color="error" fontSize="small" sx={{ opacity: 0.7 }} />
                        )}
                        {isDisabled ? file.replace('.disabled', '') + ' (已禁用)' : file}
                      </Box>
                    </MenuItem>
                  )
                })}
              </Select>
            </FormControl>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Tooltip title="新建插件">
                <IconButton color="primary" onClick={() => setIsNewPluginDialogOpen(true)}>
                  <AddIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="导入插件">
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
          minWidth: '420px',
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
              重置代码
            </Button>
            <Tooltip title="修改后的插件需要重载才能生效" arrow placement="top">
              <Button
                startIcon={<ExtensionIcon />}
                onClick={() => setReloadExtDialogOpen(true)}
                color="primary"
              >
                重载插件
              </Button>
            </Tooltip>
            <Button
              startIcon={<PowerIcon />}
              onClick={() => setIsDisableDialogOpen(true)}
              disabled={!selectedFile}
              color={selectedFile?.endsWith('.disabled') ? 'success' : 'warning'}
            >
              {selectedFile?.endsWith('.disabled') ? '启用插件' : '禁用插件'}
            </Button>
            <Button
              id="more-button"
              aria-controls={open ? 'more-menu' : undefined}
              aria-haspopup="true"
              aria-expanded={open ? 'true' : undefined}
              onClick={handleMenuClick}
              sx={{ maxWidth: '50px' }}
            >
              <MoreVertIcon />
            </Button>
          </ButtonGroup>
          <Menu
            id="more-menu"
            anchorEl={anchorEl}
            open={open}
            onClose={handleMenuClose}
            MenuListProps={{
              'aria-labelledby': 'more-button',
            }}
          >
            <MenuItem
              onClick={async () => {
                if (selectedFile) {
                  try {
                    // 如果存在导出功能，使用导出功能，否则提示功能不可用
                    if (typeof pluginEditorApi.exportPluginFile === 'function') {
                      await pluginEditorApi.exportPluginFile(selectedFile)
                      setSuccess('文件导出成功')
                    } else {
                      setError('导出功能暂不可用')
                    }
                  } catch (err) {
                    setError('文件导出失败: ' + (err instanceof Error ? err.message : String(err)))
                  }
                }
                handleMenuClose()
              }}
              disabled={!selectedFile}
            >
              导出
            </MenuItem>
            <MenuItem
              onClick={async () => {
                if (selectedFile) {
                  try {
                    await pluginEditorApi.deletePluginFile(selectedFile)
                    setSuccess('文件删除成功')
                    // 重新加载文件列表
                    const files = await pluginEditorApi.getPluginFiles()
                    setFiles(files)
                    setSelectedFile('')
                    setCode('')
                  } catch (err) {
                    setError('删除失败: ' + (err instanceof Error ? err.message : String(err)))
                  }
                }
                handleMenuClose()
              }}
              disabled={!selectedFile}
            >
              <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
              删除
            </MenuItem>
          </Menu>
        </Box>

        <Divider />

        <Typography variant="h6">插件需求</Typography>

        {/* 提示词输入框 */}
        <TextField
          multiline
          rows={4}
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          label="需求提示词"
          placeholder="描述你想要实现的插件功能..."
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
          startIcon={isGenerating ? undefined : <AutoAwesomeIcon />}
          onClick={handleGenerate}
          disabled={!prompt.trim() || isApplying}
          sx={{
            position: 'relative',
            overflow: 'hidden',
            background: theme => theme.palette.primary.main,
            color: 'white !important',
            '& .MuiButton-startIcon': {
              color: 'white',
            },
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: `linear-gradient(45deg, 
                #FF6B6B, 
                #4ECDC4,
                #45B7D1,
                #96C93D,
                #FF6B6B
              )`,
              backgroundSize: '400% 400%',
              opacity: 0.7,
              transition: 'opacity 0.3s ease',
              animation: isGenerating
                ? 'gradient-fast 3s ease infinite'
                : 'gradient 10s ease infinite',
            },
            '&:hover::before': {
              opacity: 1,
            },
            '& > *': {
              position: 'relative',
              zIndex: 1,
              color: 'white',
            },
            '@keyframes gradient': {
              '0%': {
                backgroundPosition: '0% 50%',
              },
              '50%': {
                backgroundPosition: '100% 50%',
              },
              '100%': {
                backgroundPosition: '0% 50%',
              },
            },
            '@keyframes gradient-fast': {
              '0%': {
                backgroundPosition: '0% 50%',
                transform: 'scale(1)',
              },
              '50%': {
                backgroundPosition: '100% 50%',
                transform: 'scale(1.02)',
              },
              '100%': {
                backgroundPosition: '0% 50%',
                transform: 'scale(1)',
              },
            },
            '&:disabled': {
              '&::before': {
                opacity: 0.2,
              },
              '& > *': {
                color: 'rgba(255, 255, 255, 0.7)',
              },
            },
          }}
        >
          {isGenerating ? (
            <>
              <CircularProgress size={24} sx={{ mr: 1, color: 'white' }} />
              <Box
                component="span"
                sx={{
                  color: 'white',
                  fontWeight: 'bold',
                  textShadow: '0 2px 4px rgba(0,0,0,0.5), 0 0 2px rgba(0,0,0,0.4)',
                  fontSize: '1rem',
                }}
              >
                点击中断生成
              </Box>
            </>
          ) : (
            <>
              <Box
                component="span"
                sx={{
                  color: 'white',
                  fontWeight: 'bold',
                  textShadow: '0 2px 4px rgba(0,0,0,0.5), 0 0 2px rgba(0,0,0,0.4)',
                  fontSize: '1rem',
                }}
              >
                AI 生成
              </Box>
              <Box
                component="span"
                sx={{
                  ml: 1,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  opacity: 0.8,
                  px: 0.5,
                }}
              >
                <Box
                  component="span"
                  sx={{
                    border: '1px solid rgba(255,255,255,0.3)',
                    borderRadius: '4px',
                    padding: '2px 6px',
                    background: 'rgba(255,255,255,0.1)',
                    fontFamily: '"Segoe UI", system-ui, sans-serif',
                  }}
                >
                  {navigator.platform.includes('Mac') ? (
                    '⌘'
                  ) : (
                    <Box
                      component="span"
                      sx={{
                        '& > span:first-of-type': { fontSize: '0.9em' },
                        '& > span:last-of-type': { fontSize: '0.85em' },
                      }}
                    >
                      <span>c</span>
                      <span>trl</span>
                    </Box>
                  )}
                </Box>
                <Box
                  component="span"
                  sx={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: 0.6,
                    px: 0.5,
                    fontSize: '0.85em',
                    color: 'rgba(255,255,255,0.8)',
                  }}
                >
                  +
                </Box>
                <Box
                  component="span"
                  sx={{
                    border: '1px solid rgba(255,255,255,0.3)',
                    borderRadius: '4px',
                    padding: '2px 6px',
                    background: 'rgba(255,255,255,0.1)',
                    fontFamily: '"Segoe UI", system-ui, sans-serif',
                  }}
                >
                  ↵
                </Box>
              </Box>
            </>
          )}
        </Button>

        <Divider />
        {/* 生成结果区域 */}
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            overflow: 'hidden',
            position: 'relative',
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
          <Box
            sx={{
              flex: 1,
              minHeight: 0,
              overflow: 'auto',
              position: 'relative',
            }}
          >
            {generatedCode ? (
              <Paper
                ref={generatedCodeRef}
                elevation={0}
                sx={{
                  p: 2,
                  height: '100%',
                  overflow: 'auto',
                  bgcolor: theme.palette.mode === 'dark' ? '#1E1E1E' : '#f5f5f5',
                  fontFamily: 'Consolas, Monaco, "Andale Mono", monospace',
                  fontSize: '14px',
                  lineHeight: '1.5',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
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
              </Paper>
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
          <Divider />
          <Box
            sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
          >
            <ButtonGroup size="small" variant="outlined">
              <Tooltip title={isCopied ? '已复制！' : '复制代码'}>
                <Button
                  startIcon={<ContentCopyIcon />}
                  onClick={handleCopyCode}
                  disabled={!generatedCode}
                >
                  {isCopied ? '已复制' : '复制'}
                </Button>
              </Tooltip>
              <Tooltip title="清空生成结果">
                <Button
                  startIcon={<ClearIcon />}
                  onClick={handleClearCode}
                  disabled={!generatedCode}
                  color="warning"
                >
                  清空
                </Button>
              </Tooltip>
            </ButtonGroup>
            <Button
              variant="contained"
              color="success"
              onClick={handleApplyCode}
              startIcon={<SaveIcon />}
              disabled={!generatedCode || isGenerating}
              sx={{
                position: 'relative',
                overflow: 'hidden',
                background: theme => theme.palette.success.main,
                color: 'white !important',
                '& .MuiButton-startIcon': {
                  color: 'white',
                },
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: `linear-gradient(45deg, 
                    #4CAF50,
                    #81C784,
                    #66BB6A,
                    #43A047,
                    #4CAF50
                  )`,
                  backgroundSize: '400% 400%',
                  opacity: 0.7,
                  transition: 'opacity 0.3s ease',
                  animation: 'gradient 10s ease infinite',
                },
                '&:hover::before': {
                  opacity: 1,
                },
                '& > *': {
                  position: 'relative',
                  zIndex: 1,
                  color: 'white',
                },
                '&:disabled': {
                  '&::before': {
                    opacity: 0.2,
                  },
                  '& > *': {
                    color: 'rgba(255, 255, 255, 0.7)',
                  },
                },
              }}
            >
              {isApplying ? (
                <>
                  <CircularProgress size={24} sx={{ mr: 1, color: 'white' }} />
                  <Box
                    component="span"
                    sx={{
                      color: 'white',
                      fontWeight: 'bold',
                      textShadow: '0 2px 4px rgba(0,0,0,0.5), 0 0 2px rgba(0,0,0,0.4)',
                      fontSize: '1rem',
                    }}
                  >
                    正在应用...
                  </Box>
                </>
              ) : (
                <>
                  <Box
                    component="span"
                    sx={{
                      color: 'white',
                      fontWeight: 'bold',
                      textShadow: '0 2px 4px rgba(0,0,0,0.5), 0 0 2px rgba(0,0,0,0.4)',
                      fontSize: '1rem',
                    }}
                  >
                    应用到编辑器
                  </Box>
                </>
              )}
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* 新建插件对话框 */}
      <NewPluginDialog
        open={isNewPluginDialogOpen}
        onClose={() => setIsNewPluginDialogOpen(false)}
        onConfirm={handleCreateNewPlugin}
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

      {/* Add new reload plugin dialog */}
      <Dialog open={reloadExtDialogOpen} onClose={() => setReloadExtDialogOpen(false)}>
        <DialogTitle>确认重载插件</DialogTitle>
        <DialogContent>
          <DialogContentText>
            这将重新加载当前插件文件 "{selectedFile.replace(/\.(py|disabled)$/, '')}"
            并更新应用。确定要继续吗？
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReloadExtDialogOpen(false)}>取消</Button>
          <Button onClick={handleReloadExt} color="primary" variant="contained">
            重载
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add new disable plugin dialog */}
      <Dialog open={isDisableDialogOpen} onClose={() => setIsDisableDialogOpen(false)}>
        <DialogTitle>
          {selectedFile?.endsWith('.disabled') ? '确认启用插件' : '确认禁用插件'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {selectedFile?.endsWith('.disabled')
              ? '这将启用当前插件，启用后需要重载插件才能生效。确定要继续吗？'
              : '这将禁用当前插件，禁用后需要重载插件才能生效。确定要继续吗？'}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsDisableDialogOpen(false)}>取消</Button>
          <Button
            onClick={handleTogglePlugin}
            color={selectedFile?.endsWith('.disabled') ? 'success' : 'warning'}
            variant="contained"
          >
            {selectedFile?.endsWith('.disabled') ? '启用' : '禁用'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
