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
  DialogContentText,
  ButtonGroup,
  Menu,
  useTheme,
  useMediaQuery,
  Stack,
  Fab,
  Tabs,
  Tab,
  Drawer,
  AppBar,
  Toolbar,
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
  Code as CodeIcon,
  Edit as EditIcon,
  Menu as MenuIcon,
} from '@mui/icons-material'
import { Editor } from '@monaco-editor/react'
import { pluginEditorApi, streamGenerateCode } from '../../services/api/plugin-editor'
import { reloadPlugins } from '../../services/api/plugins'
import { alpha } from '@mui/material/styles'
import { useNotification } from '../../hooks/useNotification'
import { CARD_STYLES, BORDER_RADIUS } from '../../theme/variants'

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
  const [isNewPluginDialogOpen, setIsNewPluginDialogOpen] = useState(false)
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [fileToDelete, setFileToDelete] = useState<string>('')
  const [reloadExtDialogOpen, setReloadExtDialogOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [isDisableDialogOpen, setIsDisableDialogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState(0)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const open = Boolean(anchorEl)
  const theme = useTheme()
  const generatedCodeRef = useRef<HTMLDivElement>(null)
  const [isCopied, setIsCopied] = useState(false)
  const [abortController, setAbortController] = useState<AbortController | null>(null)
  const [generatedCode, setGeneratedCode] = useState<string>('')

  // 使用ref追踪加载状态，防止循环加载
  const isLoadingFilesRef = useRef(false)
  const isLoadingContentRef = useRef(false)
  const initializedRef = useRef(false)
  const prevSelectedFileRef = useRef<string>('')

  // 响应式设计
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  // 使用新的通知系统
  const notification = useNotification()

  // 页面初始化时加载文件列表
  useEffect(() => {
    // 如果已经初始化过或正在加载文件列表，则不执行
    if (initializedRef.current || isLoadingFilesRef.current) return

    const loadFiles = async () => {
      isLoadingFilesRef.current = true
      try {
        console.log('初始化加载文件列表')
        const files = await pluginEditorApi.getPluginFiles()
        setFiles(files)

        // 仅在第一次加载时自动选择第一个文件
        if (files.length > 0 && !selectedFile && !initializedRef.current) {
          const firstFile = files[0]
          console.log('选择第一个文件:', firstFile)
          setSelectedFile(firstFile)
          prevSelectedFileRef.current = firstFile

          // 直接加载第一个文件内容
          isLoadingContentRef.current = true
          try {
            const content = await pluginEditorApi.getPluginFileContent(firstFile)
            setCode(content || '')
            setOriginalCode(content || '')
            setHasUnsavedChanges(false)
          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error)
            console.error('加载初始文件内容失败:', errorMsg)
            notification.error('加载初始文件内容失败: ' + errorMsg)
          } finally {
            isLoadingContentRef.current = false
          }
        }

        // 标记为已初始化
        initializedRef.current = true
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : '未知错误'
        console.error('加载文件列表失败:', err)
        setError('加载文件列表失败: ' + errorMessage)
        notification.error('加载文件列表失败: ' + errorMessage)
      } finally {
        isLoadingFilesRef.current = false
      }
    }

    loadFiles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notification]) // 有意省略selectedFile以避免循环加载

  // 加载选中文件的内容
  useEffect(() => {
    if (!selectedFile || isLoadingContentRef.current) return

    // 如果文件没变且已有内容，不重新加载
    if (selectedFile === prevSelectedFileRef.current && code) return

    const loadFileContent = async () => {
      console.log('加载文件内容:', selectedFile)
      isLoadingContentRef.current = true
      setIsLoading(true)
      prevSelectedFileRef.current = selectedFile

      try {
        const content = await pluginEditorApi.getPluginFileContent(selectedFile)
        setCode(content || '')
        setOriginalCode(content || '')
        setHasUnsavedChanges(false)
        setError('')
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : '未知错误'
        setError('加载文件内容失败: ' + errorMessage)
        notification.error('加载文件内容失败: ' + errorMessage)
        console.error('Failed to load file content:', err)
      } finally {
        setIsLoading(false)
        isLoadingContentRef.current = false
      }
    }

    loadFileContent()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFile, notification]) // 有意省略code以避免循环加载

  // 保存文件内容
  const handleSave = useCallback(async () => {
    if (!selectedFile || !code) return
    setIsSaving(true)
    try {
      await pluginEditorApi.savePluginFile(selectedFile, code)
      setOriginalCode(code)
      setHasUnsavedChanges(false)
      notification.success('保存成功')
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '未知错误'
      setError('保存失败: ' + errorMessage)
      notification.error('保存失败: ' + errorMessage)
    } finally {
      setIsSaving(false)
    }
  }, [code, selectedFile, notification])

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
      notification.error('请输入提示词')
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
              notification.error(jsonData.error)
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
            notification.error(`生成代码失败: ${error.message}`)
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
      notification.error('启动代码生成失败')
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
      notification.success('代码应用成功')

      // 在移动设备上，自动切换到编辑器标签
      if (isMobile) {
        setActiveTab(0)
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '代码应用失败'
      setError(errorMsg)
      notification.error(errorMsg)
    } finally {
      setIsApplying(false)
    }
  }

  // 处理文件选择
  const handleFileSelect = async (event: SelectChangeEvent<string>) => {
    const newSelectedFile = event.target.value

    if (newSelectedFile !== selectedFile) {
      if (hasUnsavedChanges && selectedFile) {
        setFileToDelete(selectedFile)
        setDeleteDialogOpen(true)
        return
      }

      // 避免重复加载
      if (isLoadingContentRef.current) return

      // 直接设置选择的文件
      setSelectedFile(newSelectedFile)

      if (isMobile) {
        setDrawerOpen(false)
      }
    }
  }

  // 重置代码
  const handleResetCode = () => {
    setCode(originalCode)
    setHasUnsavedChanges(false)
    setIsResetDialogOpen(false)
    notification.info('代码已重置')
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
      notification.error('只能导入 Python 文件')
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
        notification.success('文件导入成功')
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : '未知错误'
        notification.error('导入文件失败: ' + errorMessage)
      }
    }
    reader.readAsText(file)
  }

  // 创建新插件
  const handleCreateNewPlugin = async (name: string, description: string) => {
    const fileName = `${name}.py`
    try {
      setIsLoading(true)
      isLoadingContentRef.current = true

      // 获取模板内容
      const template = await pluginEditorApi.generatePluginTemplate(name, description)
      // 保存文件
      await pluginEditorApi.savePluginFile(fileName, template || '')

      // 重新加载文件列表
      const files = await pluginEditorApi.getPluginFiles()
      setFiles(files)

      // 更新编辑器内容
      setSelectedFile(fileName)
      prevSelectedFileRef.current = fileName
      setCode(template || '')
      setOriginalCode(template || '')
      setHasUnsavedChanges(false)
      setIsNewPluginDialogOpen(false)
      notification.success('插件创建成功')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '未知错误'
      notification.error('创建插件失败: ' + errorMessage)
      console.error('Failed to create extension:', err)
    } finally {
      setIsLoading(false)
      isLoadingContentRef.current = false
    }
  }

  // 处理删除文件
  const handleDeleteConfirm = async () => {
    if (fileToDelete) {
      try {
        setIsLoading(true)
        isLoadingFilesRef.current = true

        await pluginEditorApi.deletePluginFile(fileToDelete)
        notification.success('文件删除成功')

        // 重新加载文件列表
        const files = await pluginEditorApi.getPluginFiles()
        setFiles(files)

        // 如果删除的是当前选中的文件，清空编辑器并选择新的文件（如果有）
        if (fileToDelete === selectedFile) {
          setCode('')
          setOriginalCode('')

          if (files.length > 0) {
            const newSelectedFile = files[0]
            setSelectedFile(newSelectedFile)
            prevSelectedFileRef.current = newSelectedFile

            // 加载新选中的文件内容
            try {
              isLoadingContentRef.current = true
              const content = await pluginEditorApi.getPluginFileContent(newSelectedFile)
              setCode(content || '')
              setOriginalCode(content || '')
              setHasUnsavedChanges(false)
            } catch (error) {
              console.error('加载新文件内容失败:', error)
            } finally {
              isLoadingContentRef.current = false
            }
          } else {
            setSelectedFile('')
            prevSelectedFileRef.current = ''
          }
        }
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error)
        notification.error('删除失败: ' + errorMsg)
      } finally {
        setIsLoading(false)
        isLoadingFilesRef.current = false
        setDeleteDialogOpen(false)
        setFileToDelete('')
      }
    }
  }

  // 重载插件
  const handleReloadExt = async () => {
    if (!selectedFile) {
      notification.error('请先选择一个插件文件')
      return
    }

    try {
      setIsGenerating(true)
      isLoadingFilesRef.current = true // 防止加载插件同时加载文件列表

      // 获取模块名称：去掉扩展名(.py或.disabled)的文件名
      const moduleName = selectedFile.replace(/\.(py|disabled)$/, '')
      if (!moduleName) {
        notification.error('无法获取有效的模块名')
        return
      }

      const result = await reloadPlugins(moduleName)
      if (!result.success) {
        notification.error(result.errorMsg || '重载插件失败: 未知错误')
        setReloadExtDialogOpen(false)
        return
      }

      // 重新加载文件列表但不自动选择文件
      const files = await pluginEditorApi.getPluginFiles()
      setFiles(files)

      // 保持当前选中文件不变
      notification.success(`插件 ${moduleName} 重载成功`)
      setReloadExtDialogOpen(false)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '未知错误'
      notification.error(errorMessage)
      console.error('Failed to reload plugins:', err)
    } finally {
      setIsGenerating(false)
      isLoadingFilesRef.current = false // 恢复文件列表加载状态
    }
  }

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  // 处理启用/禁用插件
  const handleTogglePlugin = async () => {
    if (!selectedFile) return

    try {
      setIsLoading(true)
      isLoadingContentRef.current = true

      const isDisabled = selectedFile.endsWith('.disabled')
      const newFileName = isDisabled
        ? selectedFile.replace('.disabled', '')
        : `${selectedFile}.disabled`

      // 保存文件内容到新文件名
      await pluginEditorApi.savePluginFile(newFileName, code)
      // 删除旧文件
      await pluginEditorApi.deletePluginFile(selectedFile)

      // 更新状态
      setSelectedFile(newFileName)
      prevSelectedFileRef.current = newFileName
      setHasUnsavedChanges(false)

      // 更新文件列表
      const files = await pluginEditorApi.getPluginFiles()
      setFiles(files)

      notification.success(`插件${isDisabled ? '启用' : '禁用'}成功，请重载插件使更改生效`)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      notification.error(
        `${selectedFile.endsWith('.disabled') ? '启用' : '禁用'}插件失败: ${errorMsg}`
      )
    } finally {
      setIsLoading(false)
      isLoadingContentRef.current = false
      setIsDisableDialogOpen(false)
    }
  }

  const handleCopyCode = () => {
    if (generatedCode) {
      navigator.clipboard.writeText(generatedCode)
      setIsCopied(true)
      notification.success('代码已复制到剪贴板')
      setTimeout(() => setIsCopied(false), 2000)
    }
  }

  const handleClearCode = () => {
    setGeneratedCode('')
    notification.info('生成结果已清空')
  }

  // 切换抽屉
  const toggleDrawer = () => {
    setDrawerOpen(!drawerOpen)
  }

  // 移动端Tab切换
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue)
  }

  // 渲染文件选择器
  const renderFileSelector = () => (
    <Box sx={{ mb: 2 }}>
      <FormControl fullWidth>
        <InputLabel>选择插件文件</InputLabel>
        <Select
          value={selectedFile}
          label="选择插件文件"
          onChange={handleFileSelect}
          sx={{
            '& .MuiSelect-select': {
              paddingY: isSmall ? 1 : 1.5,
            },
            '& .MuiListItem-root.Mui-selected': {
              backgroundColor: theme =>
                alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.3 : 0.1),
              color: theme => theme.palette.primary.main,
              fontWeight: 'bold',
            },
          }}
          MenuProps={{
            PaperProps: {
              sx: {
                '& .MuiMenuItem-root.Mui-selected': {
                  backgroundColor: theme =>
                    alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.3 : 0.1),
                  color: theme => theme.palette.primary.main,
                  fontWeight: 'bold',
                },
              },
            },
          }}
        >
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
                  '&.Mui-selected': {
                    backgroundColor: theme =>
                      alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.2 : 0.1),
                    color: theme =>
                      theme.palette.mode === 'dark'
                        ? theme.palette.primary.light
                        : theme.palette.primary.main,
                    fontWeight: 'bold',
                  },
                  '&.Mui-selected.Mui-disabled': {
                    color: theme => alpha(theme.palette.error.main, 0.7),
                    fontWeight: 'bold',
                    opacity: 0.8,
                  },
                }}
              >
                <Box component="span" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {isDisabled && <BlockIcon color="error" fontSize="small" sx={{ opacity: 0.7 }} />}
                  {isDisabled ? file.replace('.disabled', '') + ' (已禁用)' : file}
                </Box>
              </MenuItem>
            )
          })}
        </Select>
      </FormControl>
    </Box>
  )

  // 渲染文件操作按钮
  const renderFileActions = () => (
    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
      <Tooltip title="新建插件">
        <IconButton
          color="primary"
          onClick={() => setIsNewPluginDialogOpen(true)}
          size={isSmall ? 'small' : 'medium'}
        >
          <AddIcon />
        </IconButton>
      </Tooltip>
      <Tooltip title="导入插件">
        <IconButton color="primary" component="label" size={isSmall ? 'small' : 'medium'}>
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
            size={isSmall ? 'small' : 'medium'}
          >
            {isSaving ? <CircularProgress size={isSmall ? 18 : 24} /> : <SaveIcon />}
          </IconButton>
        </span>
      </Tooltip>
    </Box>
  )

  // 渲染操作区按钮组
  const renderOperationButtons = () => (
    <ButtonGroup variant="outlined" fullWidth sx={{ flexWrap: isMobile ? 'wrap' : 'nowrap' }}>
      <Button
        startIcon={<RefreshIcon />}
        onClick={() => setIsResetDialogOpen(true)}
        disabled={!hasUnsavedChanges}
        color="warning"
        sx={{
          flex: isMobile ? '1 1 calc(50% - 4px)' : 'auto',
          mb: isMobile ? 1 : 0,
        }}
        size={isSmall ? 'small' : 'medium'}
      >
        {isSmall ? '重置' : '重置代码'}
      </Button>
      <Tooltip title="修改后的插件需要重载才能生效" arrow placement="top">
        <Button
          startIcon={<ExtensionIcon />}
          onClick={() => setReloadExtDialogOpen(true)}
          color="primary"
          sx={{
            flex: isMobile ? '1 1 calc(50% - 4px)' : 'auto',
            mb: isMobile ? 1 : 0,
          }}
          size={isSmall ? 'small' : 'medium'}
        >
          {isSmall ? '重载' : '重载插件'}
        </Button>
      </Tooltip>
      <Button
        startIcon={<PowerIcon />}
        onClick={() => setIsDisableDialogOpen(true)}
        disabled={!selectedFile}
        color={selectedFile?.endsWith('.disabled') ? 'success' : 'warning'}
        sx={{
          flex: isMobile ? '1 1 calc(50% - 4px)' : 'auto',
          mb: isMobile ? 1 : 0,
        }}
        size={isSmall ? 'small' : 'medium'}
      >
        {isSmall
          ? selectedFile?.endsWith('.disabled')
            ? '启用'
            : '禁用'
          : selectedFile?.endsWith('.disabled')
            ? '启用插件'
            : '禁用插件'}
      </Button>
      <Button
        id="more-button"
        aria-controls={open ? 'more-menu' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        onClick={handleMenuClick}
        sx={{
          maxWidth: isMobile ? 'calc(50% - 4px)' : '50px',
          flex: isMobile ? '1 1 calc(50% - 4px)' : 'auto',
        }}
        size={isSmall ? 'small' : 'medium'}
      >
        <MoreVertIcon />
      </Button>
    </ButtonGroup>
  )

  // 渲染主结构
  return (
    <Box
      sx={{
        height: 'calc(100vh - 64px)',
        display: 'flex',
        flexDirection: 'column',
        p: 2,
      }}
    >
      {/* 移动设备顶部导航栏 */}
      {isMobile && (
        <AppBar
          position="static"
          color="default"
          elevation={0}
          sx={{
            backgroundColor: 'transparent',
            backdropFilter: 'blur(10px)',
            borderBottom: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
            mb: 2,
          }}
        >
          <Toolbar variant="dense" disableGutters sx={{ px: 1 }}>
            <IconButton color="inherit" edge="start" onClick={toggleDrawer} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
            <Typography
              variant="subtitle1"
              component="div"
              sx={{ flexGrow: 1, fontWeight: 'medium' }}
            >
              {selectedFile ? selectedFile : '插件编辑器'}
            </Typography>
            {selectedFile && (
              <Tooltip
                title={hasUnsavedChanges ? '保存 (Ctrl+S)' : '已保存'}
                arrow
                placement="bottom"
              >
                <span>
                  <IconButton
                    color="primary"
                    onClick={handleSave}
                    disabled={!hasUnsavedChanges || isSaving}
                    size="small"
                    sx={{
                      backgroundColor: hasUnsavedChanges
                        ? theme => alpha(theme.palette.primary.main, 0.1)
                        : 'transparent',
                      '&:hover': {
                        backgroundColor: theme => alpha(theme.palette.primary.main, 0.2),
                      },
                    }}
                  >
                    {isSaving ? <CircularProgress size={18} /> : <SaveIcon />}
                  </IconButton>
                </span>
              </Tooltip>
            )}
          </Toolbar>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="fullWidth"
            indicatorColor="primary"
            textColor="primary"
            sx={{
              '& .MuiTab-root': {
                color: theme => alpha(theme.palette.common.white, 0.7),
                minHeight: '36px',
                padding: '6px 12px',
                '&.Mui-selected': {
                  color: 'common.white',
                  fontWeight: 'bold',
                  textShadow: '0 1px 2px rgba(0,0,0,0.2)',
                },
              },
              '& .MuiTabs-indicator': {
                backgroundColor: 'common.white',
                height: 3,
              },
            }}
          >
            <Tab
              icon={<CodeIcon fontSize="small" />}
              iconPosition="start"
              label="编辑器"
              sx={{
                display: 'flex',
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
                '& .MuiTab-iconWrapper': {
                  marginRight: 0,
                  marginBottom: '0 !important',
                },
              }}
            />
            <Tab
              icon={<EditIcon fontSize="small" />}
              iconPosition="start"
              label="生成器"
              sx={{
                display: 'flex',
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
                '& .MuiTab-iconWrapper': {
                  marginRight: 0,
                  marginBottom: '0 !important',
                },
              }}
            />
          </Tabs>
        </AppBar>
      )}

      {/* 移动端侧边抽屉 */}
      {isMobile && (
        <Drawer
          anchor="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          sx={{
            '& .MuiDrawer-paper': {
              width: '80%',
              maxWidth: 320,
              p: 2,
              pt: 8,
            },
          }}
        >
          <Box sx={{ mb: 2 }}>
            <Typography variant="h6">文件管理</Typography>
          </Box>
          {renderFileSelector()}

          <Box sx={{ mt: 2, display: 'flex', gap: 1, justifyContent: 'space-between' }}>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => {
                setIsNewPluginDialogOpen(true)
                setDrawerOpen(false)
              }}
              size={isSmall ? 'small' : 'medium'}
              fullWidth
              sx={{
                fontWeight: 'medium',
              }}
            >
              新建插件
            </Button>
            <Button
              variant="outlined"
              startIcon={<UploadIcon />}
              component="label"
              size={isSmall ? 'small' : 'medium'}
              fullWidth
              sx={{
                fontWeight: 'medium',
              }}
            >
              导入插件
              <input type="file" hidden accept=".py" onChange={handleImportFile} />
            </Button>
          </Box>

          <Divider sx={{ my: 2 }} />

          <Typography variant="h6" sx={{ mb: 1 }}>
            操作
          </Typography>
          <Stack spacing={1}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => {
                setIsResetDialogOpen(true)
                setDrawerOpen(false)
              }}
              disabled={!hasUnsavedChanges}
              color="warning"
              size={isSmall ? 'small' : 'medium'}
              fullWidth
              sx={{
                fontWeight: 'medium',
                opacity: hasUnsavedChanges ? 1 : 0.7,
              }}
            >
              重置代码
            </Button>

            <Button
              variant="outlined"
              startIcon={<ExtensionIcon />}
              onClick={() => {
                setReloadExtDialogOpen(true)
                setDrawerOpen(false)
              }}
              color="primary"
              size={isSmall ? 'small' : 'medium'}
              fullWidth
              sx={{
                fontWeight: 'medium',
              }}
            >
              重载插件
            </Button>

            <Button
              variant="outlined"
              startIcon={<PowerIcon />}
              onClick={() => {
                setIsDisableDialogOpen(true)
                setDrawerOpen(false)
              }}
              disabled={!selectedFile}
              color={selectedFile?.endsWith('.disabled') ? 'success' : 'warning'}
              size={isSmall ? 'small' : 'medium'}
              fullWidth
              sx={{
                fontWeight: 'medium',
                ...(selectedFile?.endsWith('.disabled') && {
                  borderColor: theme => alpha(theme.palette.success.main, 0.5),
                  color: 'success.main',
                  '&:hover': {
                    borderColor: 'success.main',
                    backgroundColor: theme => alpha(theme.palette.success.main, 0.1),
                  },
                }),
                ...(!selectedFile?.endsWith('.disabled') &&
                  selectedFile && {
                    borderColor: theme => alpha(theme.palette.warning.main, 0.5),
                    color: 'warning.main',
                    '&:hover': {
                      borderColor: 'warning.main',
                      backgroundColor: theme => alpha(theme.palette.warning.main, 0.1),
                    },
                  }),
              }}
            >
              {selectedFile?.endsWith('.disabled') ? '启用插件' : '禁用插件'}
            </Button>

            <Button
              variant="outlined"
              startIcon={<DeleteIcon />}
              onClick={() => {
                if (selectedFile) {
                  setFileToDelete(selectedFile)
                  setDeleteDialogOpen(true)
                  setDrawerOpen(false)
                } else {
                  notification.error('请先选择一个文件')
                }
              }}
              disabled={!selectedFile}
              color="error"
              size={isSmall ? 'small' : 'medium'}
              fullWidth
              sx={{
                fontWeight: 'medium',
                opacity: selectedFile ? 1 : 0.7,
              }}
            >
              删除插件
            </Button>
          </Stack>
        </Drawer>
      )}

      {/* 桌面布局 */}
      {!isMobile ? (
        <Box
          sx={{
            display: 'flex',
            gap: 2,
            height: '100%',
          }}
        >
          {/* 左侧编辑器区域 */}
          <Paper
            elevation={3}
            sx={{
              ...CARD_STYLES.DEFAULT,
              flex: 2,
              display: 'flex',
              flexDirection: 'column',
              gap: 1,
              p: 2,
              minWidth: 0,
            }}
          >
            {/* 顶部工具栏 */}
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', gap: 2, flex: 1 }}>
                <FormControl sx={{ flex: 1 }}>
                  <InputLabel>选择插件文件</InputLabel>
                  <Select
                    value={selectedFile}
                    label="选择插件文件"
                    onChange={handleFileSelect}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          maxHeight: 300,
                          '& .MuiMenuItem-root.Mui-selected': {
                            backgroundColor: theme =>
                              alpha(
                                theme.palette.primary.main,
                                theme.palette.mode === 'dark' ? 0.25 : 0.1
                              ),
                            color: theme =>
                              theme.palette.mode === 'dark'
                                ? theme.palette.primary.light
                                : theme.palette.primary.main,
                            fontWeight: 'bold',
                          },
                        },
                      },
                    }}
                  >
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
                            '&.Mui-selected': {
                              backgroundColor: theme =>
                                alpha(
                                  theme.palette.primary.main,
                                  theme.palette.mode === 'dark' ? 0.25 : 0.1
                                ),
                              color: theme =>
                                theme.palette.mode === 'dark'
                                  ? theme.palette.primary.light
                                  : theme.palette.primary.main,
                              fontWeight: 'bold',
                            },
                            '&.Mui-selected.Mui-disabled': {
                              color: theme => alpha(theme.palette.error.main, 0.8),
                              fontWeight: 'bold',
                              opacity: 0.9,
                              textShadow: '0 0 1px rgba(0,0,0,0.2)',
                            },
                          }}
                        >
                          <Box
                            component="span"
                            sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                          >
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
                  {renderFileActions()}
                </Box>
              </Box>
            </Box>

            {/* 错误提示 */}
            {error && (
              <Alert severity="error" onClose={() => setError('')}>
                {error}
              </Alert>
            )}

            {/* 代码编辑器 */}
            <Box
              sx={{
                flex: 1,
                border: 1,
                borderColor: 'divider',
                borderRadius: BORDER_RADIUS.DEFAULT,
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
                      `${alpha(theme.palette.background.paper, isApplying ? 0.8 : 1)}`,
                    backdropFilter: 'blur(4px)',
                    zIndex: 1,
                  }}
                >
                  <CircularProgress size={36} sx={{ mb: 1 }} />
                  <Typography variant="body2">
                    {isLoading ? '加载中...' : '正在应用修订方案...'}
                  </Typography>
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
                onMount={editor => {
                  if (isMobile) {
                    // 获取Monaco编辑器的DOM元素
                    const editorElement = editor.getDomNode()
                    if (editorElement) {
                      // 阻止编辑器内的触摸事件冒泡到外层容器
                      editorElement.addEventListener(
                        'touchmove',
                        e => {
                          e.stopPropagation()
                        },
                        { passive: true }
                      )

                      // 找到实际的滚动容器并设置样式
                      const scrollElement = editorElement.querySelector(
                        '.monaco-scrollable-element'
                      )
                      if (scrollElement instanceof HTMLElement) {
                        scrollElement.style.overflowY = 'auto'
                        scrollElement.style.touchAction = 'pan-y'
                      }
                    }
                  }
                }}
              />
            </Box>
          </Paper>

          {/* 右侧区域 */}
          <Paper
            elevation={3}
            sx={{
              ...CARD_STYLES.DEFAULT,
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              p: 2,
              minWidth: '430px',
              maxWidth: '460px',
              overflow: 'hidden',
            }}
          >
            {/* 操作区 */}
            <Box>
              <Typography variant="h6" sx={{ mb: 1 }}>
                操作区
              </Typography>
              {renderOperationButtons()}
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
                          notification.success('文件导出成功')
                        } else {
                          notification.error('导出功能暂不可用')
                        }
                      } catch (err) {
                        notification.error(
                          '文件导出失败: ' + (err instanceof Error ? err.message : String(err))
                        )
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
                        notification.success('文件删除成功')
                        // 重新加载文件列表
                        const files = await pluginEditorApi.getPluginFiles()
                        setFiles(files)
                        setSelectedFile('')
                        setCode('')
                      } catch (err) {
                        notification.error(
                          '删除失败: ' + (err instanceof Error ? err.message : String(err))
                        )
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

            {/* 生成器内容 - PC端不受activeTab影响，始终显示 */}
            <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, overflowY: 'hidden' }}>
              <Paper
                elevation={3}
                sx={{
                  ...CARD_STYLES.DEFAULT,
                  display: 'flex',
                  flexDirection: 'column',
                  flex: 1,
                  p: 1.5,
                  minHeight: 0,
                  overflow: 'hidden',
                }}
              >
                {/* 顶部输入区域 */}
                <TextField
                  multiline
                  rows={4}
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  label="修订需求"
                  placeholder="描述你想要实现的插件功能或修订需求..."
                  onKeyDown={e => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      e.preventDefault()
                      if (prompt.trim() && !isGenerating) {
                        handleGenerate()
                      }
                    }
                  }}
                  size="small"
                  sx={{ mb: 1 }}
                  fullWidth
                />

                <Button
                  variant="contained"
                  color="primary"
                  fullWidth
                  startIcon={isGenerating ? undefined : <AutoAwesomeIcon />}
                  onClick={handleGenerate}
                  disabled={!prompt.trim() || isApplying}
                  size="small"
                  sx={{
                    position: 'relative',
                    overflow: 'hidden',
                    background: theme => theme.palette.primary.main,
                    color: 'white !important',
                    py: 0.75,
                    mb: 1.5,
                    '& .MuiButton-startIcon': {
                      color: 'white',
                      margin: 0,
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
                    '&:hover': {
                      transform: 'none', // 覆盖全局按钮悬浮时的移动效果
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
                  {isGenerating ? (
                    <>
                      <CircularProgress size={16} sx={{ mr: 1, color: 'white' }} />
                      <Box
                        component="span"
                        sx={{
                          color: 'white',
                          fontWeight: 'bold',
                          textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                          fontSize: '0.85rem',
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
                          textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                          fontSize: '0.85rem',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        AI 生成 (Ctrl+Enter)
                      </Box>
                    </>
                  )}
                </Button>

                {/* 结果显示区域 */}
                <Box
                  sx={{
                    flex: 1,
                    minHeight: 0,
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: BORDER_RADIUS.DEFAULT,
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
                        backdropFilter: 'blur(4px)',
                        zIndex: 1,
                      }}
                    >
                      <CircularProgress size={32} />
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
                          p: 1.5,
                          height: '100%',
                          overflow: 'auto',
                          bgcolor: theme.palette.mode === 'dark' ? '#1E1E1E' : '#f5f5f5',
                          fontFamily: 'Consolas, Monaco, "Andale Mono", monospace',
                          fontSize: '13px',
                          lineHeight: '1.5',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-all',
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
                            <CircularProgress size={32} sx={{ mb: 1 }} />
                            <Typography variant="body2">正在生成修订方案...</Typography>
                          </Box>
                        ) : (
                          <Typography variant="body2">生成的修订方案将在这里显示...</Typography>
                        )}
                      </Box>
                    )}
                  </Box>
                  <Divider />
                  <Box
                    sx={{
                      p: 1,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      <Tooltip title={isCopied ? '已复制到剪贴板！' : '复制代码'}>
                        <Button
                          startIcon={<ContentCopyIcon sx={{ fontSize: '0.9rem' }} />}
                          onClick={handleCopyCode}
                          disabled={!generatedCode}
                          size="small"
                          variant="outlined"
                          sx={{ py: 0.5, px: 1, minWidth: 'auto' }}
                        >
                          {isCopied ? '已复制' : '复制'}
                        </Button>
                      </Tooltip>
                      <Tooltip title="清空生成结果">
                        <Button
                          startIcon={<ClearIcon sx={{ fontSize: '0.9rem' }} />}
                          onClick={handleClearCode}
                          disabled={!generatedCode}
                          color="warning"
                          size="small"
                          variant="outlined"
                          sx={{ py: 0.5, px: 1, minWidth: 'auto' }}
                        >
                          清空
                        </Button>
                      </Tooltip>
                    </Box>
                    <Button
                      variant="contained"
                      color="success"
                      onClick={handleApplyCode}
                      startIcon={<SaveIcon sx={{ fontSize: '0.9rem' }} />}
                      disabled={!generatedCode || isGenerating}
                      size="small"
                      sx={{
                        position: 'relative',
                        overflow: 'hidden',
                        background: theme => theme.palette.success.main,
                        color: 'white !important',
                        py: 0.5,
                        px: 1,
                        '& .MuiButton-startIcon': {
                          color: 'white',
                          marginRight: '4px',
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
                        '&:hover': {
                          transform: 'none', // 覆盖全局按钮悬浮时的移动效果
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
                      {isApplying ? '应用中...' : '应用方案'}
                    </Button>
                  </Box>
                </Box>
              </Paper>
            </Box>
          </Paper>
        </Box>
      ) : (
        /* 移动端布局 */
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'hidden',
            WebkitOverflowScrolling: 'touch', // 增强iOS滚动行为
          }}
        >
          {/* 分页内容 */}
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              overflowY: 'hidden',
            }}
          >
            {/* 编辑器内容 */}
            {activeTab === 0 && (
              <Paper
                elevation={3}
                sx={{
                  ...CARD_STYLES.DEFAULT,
                  flex: 1,
                  p: 1.5,
                  mb: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden',
                }}
              >
                {/* 代码编辑器 */}
                <Box
                  sx={{
                    flex: 1,
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: BORDER_RADIUS.DEFAULT,
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
                          `${alpha(theme.palette.background.paper, isApplying ? 0.8 : 1)}`,
                        backdropFilter: 'blur(4px)',
                        zIndex: 1,
                      }}
                    >
                      <CircularProgress size={36} sx={{ mb: 1 }} />
                      <Typography variant="body2">
                        {isLoading ? '加载中...' : '正在应用修订方案...'}
                      </Typography>
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
                    onMount={editor => {
                      if (isMobile) {
                        // 获取Monaco编辑器的DOM元素
                        const editorElement = editor.getDomNode()
                        if (editorElement) {
                          // 阻止编辑器内的触摸事件冒泡到外层容器
                          editorElement.addEventListener(
                            'touchmove',
                            e => {
                              e.stopPropagation()
                            },
                            { passive: true }
                          )

                          // 找到实际的滚动容器并设置样式
                          const scrollElement = editorElement.querySelector(
                            '.monaco-scrollable-element'
                          )
                          if (scrollElement instanceof HTMLElement) {
                            scrollElement.style.overflowY = 'auto'
                            scrollElement.style.touchAction = 'pan-y'
                          }
                        }
                      }
                    }}
                  />
                </Box>
              </Paper>
            )}

            {/* 生成器内容 */}
            {activeTab === 1 && (
              <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, overflowY: 'hidden' }}>
                <Paper
                  elevation={3}
                  sx={{
                    ...CARD_STYLES.DEFAULT,
                    display: 'flex',
                    flexDirection: 'column',
                    flex: 1,
                    p: 1.5,
                    minHeight: 0,
                    overflow: 'hidden',
                  }}
                >
                  {/* 顶部输入区域 */}
                  <TextField
                    multiline
                    rows={2}
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
                    size="small"
                    sx={{ mb: 1 }}
                    fullWidth
                  />

                  <Button
                    variant="contained"
                    color="primary"
                    fullWidth
                    startIcon={isGenerating ? undefined : <AutoAwesomeIcon />}
                    onClick={handleGenerate}
                    disabled={!prompt.trim() || isApplying}
                    size="small"
                    sx={{
                      position: 'relative',
                      overflow: 'hidden',
                      background: theme => theme.palette.primary.main,
                      color: 'white !important',
                      py: 0.75,
                      mb: 1.5,
                      '& .MuiButton-startIcon': {
                        color: 'white',
                        margin: 0,
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
                      '&:hover': {
                        transform: 'none', // 覆盖全局按钮悬浮时的移动效果
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
                    {isGenerating ? (
                      <>
                        <CircularProgress size={16} sx={{ mr: 1, color: 'white' }} />
                        <Box
                          component="span"
                          sx={{
                            color: 'white',
                            fontWeight: 'bold',
                            textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                            fontSize: '0.85rem',
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
                            textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                            fontSize: '0.85rem',
                            display: 'flex',
                            alignItems: 'center',
                          }}
                        >
                          AI 生成 (Ctrl+Enter)
                        </Box>
                      </>
                    )}
                  </Button>

                  {/* 结果显示区域 */}
                  <Box
                    sx={{
                      flex: 1,
                      minHeight: 0,
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: BORDER_RADIUS.DEFAULT,
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
                          backdropFilter: 'blur(4px)',
                          zIndex: 1,
                        }}
                      >
                        <CircularProgress size={32} />
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
                            p: 1.5,
                            height: '100%',
                            overflow: 'auto',
                            bgcolor: theme.palette.mode === 'dark' ? '#1E1E1E' : '#f5f5f5',
                            fontFamily: 'Consolas, Monaco, "Andale Mono", monospace',
                            fontSize: '13px',
                            lineHeight: '1.5',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-all',
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
                              <CircularProgress size={32} sx={{ mb: 1 }} />
                              <Typography variant="body2">正在生成修订方案...</Typography>
                            </Box>
                          ) : (
                            <Typography variant="body2">生成的修订方案将在这里显示...</Typography>
                          )}
                        </Box>
                      )}
                    </Box>
                    <Divider />
                    <Box
                      sx={{
                        p: 1,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title={isCopied ? '已复制到剪贴板！' : '复制代码'}>
                          <Button
                            startIcon={<ContentCopyIcon sx={{ fontSize: '0.9rem' }} />}
                            onClick={handleCopyCode}
                            disabled={!generatedCode}
                            size="small"
                            variant="outlined"
                            sx={{ py: 0.5, px: 1, minWidth: 'auto' }}
                          >
                            {isCopied ? '已复制' : '复制'}
                          </Button>
                        </Tooltip>
                        <Tooltip title="清空生成结果">
                          <Button
                            startIcon={<ClearIcon sx={{ fontSize: '0.9rem' }} />}
                            onClick={handleClearCode}
                            disabled={!generatedCode}
                            color="warning"
                            size="small"
                            variant="outlined"
                            sx={{ py: 0.5, px: 1, minWidth: 'auto' }}
                          >
                            清空
                          </Button>
                        </Tooltip>
                      </Box>
                      <Button
                        variant="contained"
                        color="success"
                        onClick={handleApplyCode}
                        startIcon={<SaveIcon sx={{ fontSize: '0.9rem' }} />}
                        disabled={!generatedCode || isGenerating}
                        size="small"
                        sx={{
                          position: 'relative',
                          overflow: 'hidden',
                          background: theme => theme.palette.success.main,
                          color: 'white !important',
                          py: 0.5,
                          px: 1,
                          '& .MuiButton-startIcon': {
                            color: 'white',
                            marginRight: '4px',
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
                          '&:hover': {
                            transform: 'none', // 覆盖全局按钮悬浮时的移动效果
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
                        {isApplying ? '应用中...' : '应用方案'}
                      </Button>
                    </Box>
                  </Box>
                </Paper>
              </Box>
            )}
          </Box>
        </Box>
      )}

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

      {/* 重载插件对话框 */}
      <Dialog open={reloadExtDialogOpen} onClose={() => setReloadExtDialogOpen(false)}>
        <DialogTitle>确认重载插件</DialogTitle>
        <DialogContent>
          <DialogContentText>
            这将重新加载当前插件文件 "{selectedFile?.replace(/\.(py|disabled)$/, '')}"
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

      {/* 启用/禁用插件对话框 */}
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

      {/* 错误信息显示 */}
      {error && (
        <Alert
          severity="error"
          onClose={() => setError('')}
          sx={{
            position: 'fixed',
            bottom: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            maxWidth: '90%',
            width: 'auto',
            zIndex: 9999,
            boxShadow: theme => `0 4px 20px ${alpha(theme.palette.error.main, 0.25)}`,
          }}
        >
          {error}
        </Alert>
      )}

      {/* 移动端底部保存按钮 */}
      {isMobile && hasUnsavedChanges && (
        <Fab
          color="primary"
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            zIndex: 1000,
            boxShadow: theme => `0 4px 12px ${alpha(theme.palette.primary.main, 0.4)}`,
          }}
          onClick={handleSave}
          disabled={isSaving}
        >
          {isSaving ? <CircularProgress size={24} color="inherit" /> : <SaveIcon />}
        </Fab>
      )}
    </Box>
  )
}
