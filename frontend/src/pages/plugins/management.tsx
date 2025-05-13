import React, { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Box,
  Paper,
  List,
  ListItem,
  ListItemText,
  Typography,
  Divider,
  Switch,
  Button,
  Card,
  CardContent,
  TextField,
  Chip,
  Tab,
  Tabs,
  FormControlLabel,
  CircularProgress,
  Alert,
  Snackbar,
  IconButton,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  InputAdornment,
  MenuItem,
  tooltipClasses,
  TooltipProps,
  Stack,
  Collapse,
  Link,
  useMediaQuery,
  useTheme,
  Drawer,
  Fab,
  ListItemButton,
} from '@mui/material'
import { styled } from '@mui/material/styles'
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Code as CodeIcon,
  Settings as SettingsIcon,
  Info as InfoIcon,
  ArrowBack as ArrowBackIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  HelpOutline as HelpOutlineIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Tune as TuneIcon,
  ContentCopy as ContentCopyIcon,
  WebhookOutlined as WebhookIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
  Storage as StorageIcon,
  Launch as LaunchIcon,
  Extension as ExtensionIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Method, Plugin, PluginConfig, pluginsApi } from '../../services/api/plugins'
import { configApi, ModelTypeOption } from '../../services/api/config'
import { useNavigate } from 'react-router-dom'
import { 
  pluginTypeColors, 
  pluginTypeTexts, 
  configTypeColors, 
  methodTypeColors
} from '../../theme/constants'

// 自定义提示样式，支持富文本
const HtmlTooltip = styled(({ className, ...props }: TooltipProps) => (
  <Tooltip {...props} classes={{ popper: className }} />
))(({ theme }) => ({
  [`& .${tooltipClasses.tooltip}`]: {
    backgroundColor: theme.palette.mode === 'dark' ? '#424242' : '#f5f5f9',
    color: theme.palette.mode === 'dark' ? '#fff' : 'rgba(0, 0, 0, 0.87)',
    maxWidth: 300,
    fontSize: theme.typography.pxToRem(12),
    border: '1px solid #dadde9',
    '& a': {
      color: theme.palette.primary.main,
      textDecoration: 'none',
      '&:hover': {
        textDecoration: 'underline',
      },
    },
  },
}))

// 添加 server_addr 配置
const server_addr = window.location.origin

// 列表编辑对话框组件
interface ListEditDialogProps {
  open: boolean
  onClose: () => void
  value: Array<string | number | boolean>
  onChange: (value: Array<string | number | boolean>) => void
  itemType: string
  title: string
}

function ListEditDialog({ open, onClose, value, onChange, itemType, title }: ListEditDialogProps) {
  const [items, setItems] = useState<Array<string | number | boolean>>(value)
  const [newItem, setNewItem] = useState<string>('')

  const handleAddItem = () => {
    if (newItem.trim()) {
      let parsedItem: string | number | boolean
      try {
        switch (itemType) {
          case 'int':
            parsedItem = parseInt(newItem)
            break
          case 'float':
            parsedItem = parseFloat(newItem)
            break
          case 'bool':
            parsedItem = newItem.toLowerCase() === 'true'
            break
          default:
            parsedItem = newItem
        }
        if (!Number.isNaN(parsedItem)) {
          setItems([...items, parsedItem])
          setNewItem('')
        }
      } catch {
        // 忽略解析错误
      }
    }
  }

  const handleDeleteItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const handleSave = () => {
    onChange(items)
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={2}>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 1 }}>
            <TextField
              fullWidth
              size="small"
              value={newItem}
              onChange={e => setNewItem(e.target.value)}
              placeholder={`输入${itemType === 'bool' ? 'true/false' : itemType}类型的值`}
              onKeyPress={e => e.key === 'Enter' && handleAddItem()}
              autoComplete="off"
            />
            <IconButton onClick={handleAddItem} color="primary" sx={{ p: { xs: 1, sm: 1.2 } }}>
              <AddIcon />
            </IconButton>
          </Box>
          <List sx={{ maxHeight: 300, overflow: 'auto' }}>
            {items.map((item, index) => (
              <ListItem
                key={index}
                secondaryAction={
                  <IconButton edge="end" onClick={() => handleDeleteItem(index)} sx={{ p: { xs: 1, sm: 1.2 } }}>
                    <DeleteIcon />
                  </IconButton>
                }
              >
                <Typography>{String(item)}</Typography>
              </ListItem>
            ))}
          </List>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}>取消</Button>
        <Button 
          onClick={handleSave} 
          color="primary" 
          variant="contained"
          sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
        >
          保存
        </Button>
      </DialogActions>
    </Dialog>
  )
}

interface PluginDetailProps {
  plugin: Plugin
  onBack: () => void
  onToggleEnabled: (id: string, enabled: boolean) => void
}

// 插件详情组件
function PluginDetails({ plugin, onBack, onToggleEnabled }: PluginDetailProps) {
  const [activeTab, setActiveTab] = useState(0)
  const [configValues, setConfigValues] = useState<Record<string, unknown>>({})
  const [message, setMessage] = useState('')
  const [visibleSecrets, setVisibleSecrets] = useState<Record<string, boolean>>({})
  const [reloadConfirmOpen, setReloadConfirmOpen] = useState(false)
  const [resetDataConfirmOpen, setResetDataConfirmOpen] = useState(false)
  const [saveWarningOpen, setSaveWarningOpen] = useState(false)
  const [emptyRequiredFields, setEmptyRequiredFields] = useState<string[]>([])
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [expandedDataRows, setExpandedDataRows] = useState<Set<number>>(new Set())
  const [updateConfirmOpen, setUpdateConfirmOpen] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [deleteDataConfirmOpen, setDeleteDataConfirmOpen] = useState(false)
  const [deleteDataId, setDeleteDataId] = useState<number | null>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  // 列表编辑状态
  const [listEditState, setListEditState] = useState<{
    open: boolean
    configKey: string | null
  }>({
    open: false,
    configKey: null,
  })

  // 获取插件配置
  const { data: pluginConfig, isLoading: configLoading } = useQuery({
    queryKey: ['plugin-config', plugin?.id],
    queryFn: () => pluginsApi.getPluginConfig(plugin?.id),
    enabled: !!plugin && activeTab === 1 && plugin.hasConfig,
  })

  // 获取模型组列表
  const { data: modelGroups = {} } = useQuery({
    queryKey: ['model-groups'],
    queryFn: () => pluginsApi.getModelGroups(),
  })

  // 获取模型类型列表
  const { data: modelTypes = [] } = useQuery<ModelTypeOption[]>({
    queryKey: ['model-types'],
    queryFn: () => configApi.getModelTypes(),
  })
  const modelTypeMap = useMemo(
    () => Object.fromEntries(modelTypes.map(mt => [mt.value, mt])),
    [modelTypes]
  )

  // 获取插件数据
  const { data: pluginData = [], isLoading: isDataLoading } = useQuery({
    queryKey: ['plugin-data', plugin?.id],
    queryFn: () => pluginsApi.getPluginData(plugin.id),
    enabled: !!plugin && activeTab === 4,
  })

  useEffect(() => {
    if (pluginConfig) {
      const initialValues: Record<string, unknown> = {}
      pluginConfig.forEach(item => {
        initialValues[item.key] = item.value
      })
      setConfigValues(initialValues)
    }
  }, [pluginConfig])

  // 检查必填项
  const checkRequiredFields = useCallback(() => {
    if (!pluginConfig) return true

    const emptyFields = pluginConfig
      .filter(config => {
        if (!config.required) return false
        const currentValue =
          configValues[config.key] !== undefined ? configValues[config.key] : config.value
        return !currentValue || currentValue === '' || currentValue === '[]'
      })
      .map(config => config.title || config.key)

    setEmptyRequiredFields(emptyFields)
    if (emptyFields.length > 0) {
      setSaveWarningOpen(true)
      return false
    }
    return true
  }, [pluginConfig, configValues])

  // 保存插件配置
  const saveMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => {
      // 将所有值转换为字符串
      const stringValues: Record<string, string> = {}
      Object.entries(data).forEach(([key, value]) => {
        if (typeof value === 'boolean') {
          stringValues[key] = value ? 'true' : 'false'
        } else if (Array.isArray(value)) {
          stringValues[key] = JSON.stringify(value)
        } else if (value === null || value === undefined) {
          stringValues[key] = ''
        } else {
          stringValues[key] = String(value)
        }
      })
      return pluginsApi.savePluginConfig(plugin.id, stringValues)
    },
    onSuccess: () => {
      setMessage('配置已成功保存喵～ (≧ω≦)ノ')
      queryClient.invalidateQueries({ queryKey: ['plugin-config', plugin.id] })
      setEditingStatus({})
    },
    onError: (error: Error) => {
      setMessage(`保存失败: ${error.message} 呜呜呜 (ノ_<)`)
    },
  })

  // 重载插件
  const reloadMutation = useMutation({
    mutationFn: async () => {
      if (!plugin.moduleName) {
        throw new Error('无法获取有效的模块名')
      }
      const result = await pluginsApi.reloadPlugins(plugin.moduleName)
      if (!result.success) {
        throw new Error(result.errorMsg || '重载失败，请检查后端日志')
      }
      return true
    },
    onSuccess: () => {
      setMessage(`插件 ${plugin.name} 已重载～ (*￣▽￣)b`)
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-config', plugin.id] })
    },
    onError: (error: Error) => {
      setMessage(error.message)
    },
  })

  // 删除单条数据
  const deleteDataMutation = useMutation({
    mutationFn: (dataId: number) => pluginsApi.deletePluginData(plugin.id, dataId),
    onSuccess: () => {
      setMessage('数据已删除喵～')
      queryClient.invalidateQueries({ queryKey: ['plugin-data', plugin.id] })
    },
    onError: (error: Error) => {
      setMessage(`删除失败: ${error.message}`)
    },
  })

  // 删除插件所有数据
  const resetDataMutation = useMutation({
    mutationFn: () => pluginsApi.resetPluginData(plugin.id),
    onSuccess: () => {
      setMessage('所有数据已重置喵～')
      queryClient.invalidateQueries({ queryKey: ['plugin-data', plugin.id] })
    },
    onError: (error: Error) => {
      setMessage(`重置失败: ${error.message}`)
    },
  })

  // 删除插件包
  const removePackageMutation = useMutation({
    mutationFn: () => pluginsApi.removePackage(plugin.moduleName),
    onSuccess: () => {
      setMessage(`插件包 ${plugin.name} 已删除～`)
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      onBack() // 返回插件列表
    },
    onError: (error: Error) => {
      setMessage(`删除失败: ${error.message}`)
    },
  })

  // 更新插件包
  const updatePackageMutation = useMutation({
    mutationFn: async () => {
      if (!plugin.moduleName) {
        throw new Error('无法获取有效的模块名')
      }
      const result = await pluginsApi.updatePackage(plugin.moduleName)
      if (!result.success) {
        throw new Error(result.errorMsg || '更新失败，请检查后端日志')
      }
      return true
    },
    onSuccess: () => {
      setMessage(`插件包 ${plugin.name} 已更新至最新版本～`)
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-config', plugin.id] })
    },
    onError: (error: Error) => {
      setMessage(error.message)
    },
  })

  // 追踪哪些配置项已被编辑
  const [editingStatus, setEditingStatus] = useState<Record<string, boolean>>({})

  const handleConfigChange = (key: string, value: unknown) => {
    setConfigValues(prev => ({
      ...prev,
      [key]: value,
    }))
    setEditingStatus(prev => ({
      ...prev,
      [key]: true,
    }))
  }

  const handleSaveConfig = useCallback(
    (force: boolean = false) => {
      if (!force && !checkRequiredFields()) {
        return
      }
      saveMutation.mutate(configValues)
      setSaveWarningOpen(false)
    },
    [checkRequiredFields, configValues, saveMutation, setSaveWarningOpen]
  )

  // 切换密钥显示状态
  const toggleSecretVisibility = (key: string) => {
    setVisibleSecrets(prev => ({
      ...prev,
      [key]: !prev[key],
    }))
  }

  // 监听保存快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 仅当活跃标签是配置标签且有修改时才响应快捷键
      if (activeTab === 1 && Object.keys(editingStatus).length > 0) {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
          e.preventDefault()
          handleSaveConfig()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeTab, editingStatus, handleSaveConfig])

  // 获取插件类型
  const getPluginType = () => {
    if (plugin.isBuiltin) return 'builtin'
    if (plugin.isPackage) return 'package'
    return 'local'
  }

  // 获取插件类型中文名
  const getPluginTypeText = () => {
    const type = getPluginType()
    return pluginTypeTexts[type] || '未知'
  }

  // 插件配置项渲染函数
  const renderConfigInput = (config: PluginConfig) => {
    const currentValue =
      configValues[config.key] !== undefined ? configValues[config.key] : config.value

    const isEdited = editingStatus[config.key]
    const isSecret = config.is_secret

    // 处理列表类型
    if (config.type === 'list') {
      const itemType = config.element_type || 'str'
      let displayValue = '[]'

      try {
        if (typeof currentValue === 'string') {
          const parsed = JSON.parse(currentValue as string)
          displayValue = JSON.stringify(parsed)
        } else if (Array.isArray(currentValue)) {
          displayValue = JSON.stringify(currentValue)
        }
      } catch (e) {
        console.error('解析列表值失败:', e)
      }

      return (
        <Box sx={{ width: '100%' }}>
          <TextField
            value={displayValue}
            size="small"
            fullWidth
            sx={{
              '& .MuiInputBase-root': {
                width: '100%',
                ...(isEdited && {
                  backgroundColor: theme =>
                    theme.palette.mode === 'dark'
                      ? 'rgba(144, 202, 249, 0.08)'
                      : 'rgba(33, 150, 243, 0.08)',
                }),
              },
            }}
            InputProps={{
              readOnly: true,
              startAdornment: (
                <InputAdornment position="start">
                  <Chip
                    label={`${itemType}[]`}
                    size="small"
                    color={configTypeColors[itemType] || 'default'}
                    variant="outlined"
                    sx={{ mr: 1 }}
                  />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <Tooltip title="编辑列表">
                    <IconButton
                      onClick={() => setListEditState({ open: true, configKey: config.key })}
                      edge="end"
                    >
                      <TuneIcon />
                    </IconButton>
                  </Tooltip>
                </InputAdornment>
              ),
            }}
            autoComplete="off"
          />
          {listEditState.configKey === config.key && (
            <ListEditDialog
              open={listEditState.open}
              onClose={() => setListEditState({ open: false, configKey: null })}
              value={
                typeof currentValue === 'string'
                  ? JSON.parse(currentValue)
                  : Array.isArray(currentValue)
                    ? currentValue
                    : []
              }
              onChange={newValue => handleConfigChange(config.key, newValue)}
              itemType={itemType}
              title={`编辑${config.title || config.key}`}
            />
          )}
        </Box>
      )
    }

    // 如果是模型组引用，显示模型组选择器
    if (config.ref_model_groups) {
      const typeOption = modelTypeMap[config.model_type as string]
      let entries = Object.entries(modelGroups)
      if (typeOption) {
        entries = entries.filter(([, group]) => group.MODEL_TYPE === typeOption.value)
      }
      const modelGroupNames = entries.map(([name]) => name)
      const currentValueStr = String(currentValue)
      const isInvalidValue = !modelGroupNames.includes(currentValueStr)

      return (
        <TextField
          select
          value={currentValueStr}
          onChange={e => handleConfigChange(config.key, e.target.value)}
          size="small"
          fullWidth
          error={isInvalidValue}
          helperText={isInvalidValue ? '当前选择的模型组已不存在' : undefined}
          placeholder={config.placeholder}
          sx={{
            ...(isEdited && {
              '& .MuiInputBase-root': {
                backgroundColor: theme =>
                  theme.palette.mode === 'dark'
                    ? 'rgba(144, 202, 249, 0.08)'
                    : 'rgba(33, 150, 243, 0.08)',
              },
            }),
          }}
        >
          {modelGroupNames.map(name => (
            <MenuItem key={name} value={name}>
              {name}
            </MenuItem>
          ))}
        </TextField>
      )
    }

    // 如果是枚举类型，显示选择器
    if (config.enum) {
      return (
        <TextField
          select
          value={String(currentValue)}
          onChange={e => handleConfigChange(config.key, e.target.value)}
          size="small"
          fullWidth
          placeholder={config.placeholder}
          sx={{
            ...(isEdited && {
              '& .MuiInputBase-root': {
                backgroundColor: theme =>
                  theme.palette.mode === 'dark'
                    ? 'rgba(144, 202, 249, 0.08)'
                    : 'rgba(33, 150, 243, 0.08)',
              },
            }),
          }}
        >
          {config.enum.map(option => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </TextField>
      )
    }

    // 根据类型渲染不同的输入控件
    switch (config.type) {
      case 'bool':
        return (
          <FormControlLabel
            control={
              <Switch
                checked={currentValue === true || currentValue === 'true'}
                onChange={e => handleConfigChange(config.key, e.target.checked)}
                color="primary"
              />
            }
            label={currentValue === true || currentValue === 'true' ? '是' : '否'}
          />
        )
      case 'int':
      case 'float':
        return (
          <TextField
            type="number"
            value={String(currentValue)}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            fullWidth
            placeholder={config.placeholder}
            autoComplete="off"
            sx={{
              ...(isEdited && {
                '& .MuiInputBase-root': {
                  backgroundColor: theme =>
                    theme.palette.mode === 'dark'
                      ? 'rgba(144, 202, 249, 0.08)'
                      : 'rgba(33, 150, 243, 0.08)',
                },
              }),
            }}
          />
        )
      default:
        return (
          <TextField
            value={String(currentValue)}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            fullWidth
            type="text"
            placeholder={config.placeholder}
            autoComplete="off"
            name={`field_${Math.random().toString(36).slice(2)}`}
            multiline={config.is_textarea}
            minRows={config.is_textarea ? 3 : 1}
            maxRows={config.is_textarea ? 8 : 1}
            inputProps={{
              autoComplete: 'off',
              style:
                isSecret && !visibleSecrets[config.key]
                  ? ({
                      '-webkit-text-security': 'disc',
                      'text-security': 'disc',
                    } as React.CSSProperties)
                  : undefined,
            }}
            sx={{
              ...(isEdited && {
                '& .MuiInputBase-root': {
                  backgroundColor: theme =>
                    theme.palette.mode === 'dark'
                      ? 'rgba(144, 202, 249, 0.08)'
                      : 'rgba(33, 150, 243, 0.08)',
                },
              }),
            }}
            InputProps={{
              ...(isSecret
                ? {
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={() => toggleSecretVisibility(config.key)} edge="end">
                          {visibleSecrets[config.key] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }
                : {}),
            }}
          />
        )
    }
  }

  // 按钮点击处理函数
  const handleNavigateToEditor = () => {
    navigate('/plugins/editor')
  }

  if (!plugin) return null

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative',
      }}
    >
      {/* 返回按钮和标题栏 */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          mb: 2,
          pb: 1,
          borderBottom: 1,
          borderColor: 'divider',
          flexWrap: isMobile ? 'wrap' : 'nowrap',
          gap: 1,
        }}
      >
        <IconButton onClick={onBack} edge="start" sx={{ mr: 0.5 }}>
          <ArrowBackIcon />
        </IconButton>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1, overflow: 'hidden' }}>
          <Chip
            label={getPluginTypeText()}
            size="small"
            color={pluginTypeColors[getPluginType()]}
            variant="outlined"
            sx={{ height: 22, fontSize: '0.7rem' }}
          />
          <Typography
            variant={isMobile ? "subtitle1" : "h6"} 
            component="div"
            sx={{ 
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}
          >
            {plugin.name}
          </Typography>
        </Box>
        <FormControlLabel
          control={
            <Switch
              checked={plugin.enabled}
              onChange={e => onToggleEnabled(plugin.id, e.target.checked)}
              color="primary"
            />
          }
          label={plugin.enabled ? '已启用' : '已禁用'}
          sx={{ mr: 0, ml: { xs: 0, sm: 1 } }}
        />
      </Box>

      {/* 移动端操作按钮组 - 放在选项卡上方 */}
      {isMobile && (
        <Box sx={{ mb: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {!plugin.isBuiltin && (
            <Button
              startIcon={plugin.isPackage ? <DeleteIcon /> : <EditIcon />}
              onClick={() =>
                plugin.isPackage ? setDeleteConfirmOpen(true) : handleNavigateToEditor()
              }
              color={plugin.isPackage ? 'error' : 'warning'}
              size="small"
              variant="outlined"
              sx={{ flex: '1 0 auto', minWidth: '80px' }}
            >
              {plugin.isPackage ? '删除' : '编辑'}
            </Button>
          )}
          {plugin.isPackage && (
            <Button
              startIcon={<RefreshIcon />}
              onClick={() => setUpdateConfirmOpen(true)}
              color="success"
              size="small"
              variant="outlined"
              sx={{ flex: '1 0 auto', minWidth: '80px' }}
            >
              更新
            </Button>
          )}
          <Button
            startIcon={<DeleteIcon />}
            onClick={() => setResetDataConfirmOpen(true)}
            color="warning"
            size="small"
            variant="outlined"
            sx={{ flex: '1 0 auto', minWidth: '80px' }}
          >
            重置
          </Button>
          <Button 
            startIcon={<RefreshIcon />} 
            onClick={() => setReloadConfirmOpen(true)}
            size="small"
            variant="outlined"
            sx={{ flex: '1 0 auto', minWidth: '80px' }}
          >
            重载
          </Button>
        </Box>
      )}

      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        mb: 2,
      }}>
        <Tabs 
          value={activeTab} 
          onChange={(_, newValue) => setActiveTab(newValue)} 
          sx={{ 
            '& .MuiTabs-flexContainer': {
              flexWrap: isMobile ? 'wrap' : 'nowrap',
            },
            '& .MuiTab-root': {
              minWidth: isMobile ? 'auto' : 90,
              px: isSmall ? 1 : 2,
            }
          }}
          variant={isMobile ? "scrollable" : "standard"}
          scrollButtons="auto"
        >
          <Tab
            icon={<InfoIcon sx={{ fontSize: isSmall ? 16 : 20 }} />}
            label="基本信息"
            sx={{
              flexDirection: 'row',
              '& .MuiTab-iconWrapper': {
                marginRight: 1,
                marginBottom: '0 !important',
              },
              minHeight: isSmall ? 36 : 40,
              padding: isSmall ? '4px 8px' : '6px 16px',
              fontSize: isSmall ? '0.8rem' : 'inherit',
            }}
          />
          {plugin.hasConfig && (
            <Tab
              icon={<SettingsIcon sx={{ fontSize: isSmall ? 16 : 20 }} />}
              label="配置"
              sx={{
                flexDirection: 'row',
                '& .MuiTab-iconWrapper': {
                  marginRight: 1,
                  marginBottom: '0 !important',
                },
                minHeight: isSmall ? 36 : 40,
                padding: isSmall ? '4px 8px' : '6px 16px',
                fontSize: isSmall ? '0.8rem' : 'inherit',
              }}
            />
          )}
          <Tab
            icon={<CodeIcon sx={{ fontSize: isSmall ? 16 : 20 }} />}
            label="方法"
            sx={{
              flexDirection: 'row',
              '& .MuiTab-iconWrapper': {
                marginRight: 1,
                marginBottom: '0 !important',
              },
              minHeight: isSmall ? 36 : 40,
              padding: isSmall ? '4px 8px' : '6px 16px',
              fontSize: isSmall ? '0.8rem' : 'inherit',
            }}
          />
          <Tab
            icon={<WebhookIcon sx={{ fontSize: isSmall ? 16 : 20 }} />}
            label="Webhook"
            sx={{
              flexDirection: 'row',
              '& .MuiTab-iconWrapper': {
                marginRight: 1,
                marginBottom: '0 !important',
              },
              minHeight: isSmall ? 36 : 40,
              padding: isSmall ? '4px 8px' : '6px 16px',
              fontSize: isSmall ? '0.8rem' : 'inherit',
            }}
          />
          <Tab
            icon={<StorageIcon sx={{ fontSize: isSmall ? 16 : 20 }} />}
            label="数据管理"
            sx={{
              flexDirection: 'row',
              '& .MuiTab-iconWrapper': {
                marginRight: 1,
                marginBottom: '0 !important',
              },
              minHeight: isSmall ? 36 : 40,
              padding: isSmall ? '4px 8px' : '6px 16px',
              fontSize: isSmall ? '0.8rem' : 'inherit',
            }}
          />
        </Tabs>

        {/* 桌面端操作按钮组，放置在选项卡右侧 */}
        {!isMobile && (
          <Box sx={{ display: 'flex', gap: 1 }}>
            {!plugin.isBuiltin && (
              <Button
                startIcon={plugin.isPackage ? <DeleteIcon /> : <EditIcon />}
                onClick={() =>
                  plugin.isPackage ? setDeleteConfirmOpen(true) : handleNavigateToEditor()
                }
                color={plugin.isPackage ? 'error' : 'warning'}
                size="small"
                variant="outlined"
              >
                {plugin.isPackage ? '删除' : '编辑'}
              </Button>
            )}
            {plugin.isPackage && (
              <Button
                startIcon={<RefreshIcon />}
                onClick={() => setUpdateConfirmOpen(true)}
                color="success"
                size="small"
                variant="outlined"
              >
                更新
              </Button>
            )}
            <Button
              startIcon={<DeleteIcon />}
              onClick={() => setResetDataConfirmOpen(true)}
              color="warning"
              size="small"
              variant="outlined"
            >
              重置
            </Button>
            <Button 
              startIcon={<RefreshIcon />} 
              onClick={() => setReloadConfirmOpen(true)}
              size="small"
              variant="outlined"
            >
              重载
            </Button>
          </Box>
        )}
      </Box>

      {/* 基本信息 */}
      {activeTab === 0 && (
        <Card variant="outlined" sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              基本信息
            </Typography>
            <Typography variant="body2">
              <strong>名称：</strong> {plugin.name}
            </Typography>
            <Typography variant="body2">
              <strong>描述：</strong> {plugin.description}
            </Typography>
            <Typography variant="body2">
              <strong>作者：</strong> {plugin.author}
            </Typography>
            <Typography variant="body2">
              <strong>模块名：</strong> {plugin.moduleName}
            </Typography>
            <Typography variant="body2">
              <strong>版本：</strong> {plugin.version}
            </Typography>
            <Typography variant="body2">
              <strong>类型：</strong> {getPluginTypeText()}插件
            </Typography>
            <Typography variant="body2">
              <strong>链接：</strong>{' '}
              <Link href={plugin.url} target="_blank" rel="noreferrer">
                {plugin.url || '无'}
              </Link>
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* 配置项 */}
      {activeTab === 1 && plugin.hasConfig && (
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {configLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', pt: 4 }}>
              <CircularProgress />
            </Box>
          ) : pluginConfig && pluginConfig.length > 0 ? (
            <>
              <Card variant="outlined" sx={{ mb: 2, flex: 1, overflow: 'auto' }}>
                <CardContent>
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      mb: 2,
                      flexWrap: isMobile ? 'wrap' : 'nowrap',
                    }}
                  >
                    <Typography variant="subtitle1">插件配置</Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ 
                        fontStyle: 'italic',
                        mt: isMobile ? 1 : 0,
                        width: isMobile ? '100%' : 'auto'
                      }}
                    >
                      提示：按 Ctrl+S 可快速保存配置喵～
                    </Typography>
                  </Box>

                  <TableContainer
                    sx={{
                      maxHeight: 'calc(100vh - 350px)',
                      '&::-webkit-scrollbar': {
                        width: '8px',
                        height: '8px',
                      },
                      '&::-webkit-scrollbar-thumb': {
                        backgroundColor: 'rgba(0,0,0,0.2)',
                        borderRadius: '4px',
                      },
                    }}
                  >
                    <Table size={isSmall ? "small" : "medium"} stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell width={isMobile ? "40%" : "30%"} sx={{ py: isSmall ? 1 : 1.5 }}>配置项</TableCell>
                          <TableCell width={isMobile ? "15%" : "10%"} sx={{ py: isSmall ? 1 : 1.5 }}>类型</TableCell>
                          <TableCell width={isMobile ? "45%" : "60%"} sx={{ py: isSmall ? 1 : 1.5 }}>值</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {pluginConfig
                          .filter(item => !item.is_hidden)
                          .map(item => (
                            <TableRow key={item.key}>
                              <TableCell component="th" scope="row" sx={{ py: isSmall ? 0.75 : 1.25 }}>
                                <Box>
                                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                    <Typography 
                                      variant="subtitle2" 
                                      sx={{ 
                                        fontWeight: 'bold',
                                        fontSize: isSmall ? '0.75rem' : '0.875rem', 
                                      }}
                                    >
                                      {item.title || item.key}
                                      {item.required && (
                                        <Typography component="span" color="error" sx={{ ml: 0.5 }}>
                                          *
                                        </Typography>
                                      )}
                                    </Typography>

                                    {item.description && (
                                      <HtmlTooltip
                                        title={
                                          <div
                                            dangerouslySetInnerHTML={{ __html: item.description }}
                                          />
                                        }
                                        placement="right"
                                      >
                                        <IconButton size="small" sx={{ ml: 0.5, opacity: 0.6 }}>
                                          <HelpOutlineIcon sx={{ fontSize: isSmall ? 14 : 16 }} />
                                        </IconButton>
                                      </HtmlTooltip>
                                    )}
                                  </Box>
                                  <Typography 
                                    variant="caption" 
                                    color="text.secondary"
                                    sx={{ fontSize: isSmall ? '0.65rem' : '0.75rem' }}
                                  >
                                    {item.key}
                                  </Typography>
                                </Box>
                              </TableCell>
                              <TableCell sx={{ py: isSmall ? 0.75 : 1.25 }}>
                                <Chip
                                  label={item.type}
                                  size="small"
                                  color={configTypeColors[item.type] || 'default'}
                                  variant="outlined"
                                  sx={{ 
                                    fontSize: isSmall ? '0.65rem' : '0.75rem',
                                    height: isSmall ? 20 : 24,
                                    '& .MuiChip-label': {
                                      px: isSmall ? 0.5 : 0.75,
                                    }
                                  }}
                                />
                              </TableCell>
                              <TableCell sx={{ py: isSmall ? 0.75 : 1.25 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  {renderConfigInput(item)}
                                  {item.ref_model_groups &&
                                    (() => {
                                      const typeOption = modelTypeMap[item.model_type as string]
                                      const chipLabel = typeOption
                                        ? `${typeOption.label}模型组`
                                        : '模型组'
                                      const chipColor =
                                        (typeOption?.color as
                                          | 'primary'
                                          | 'secondary'
                                          | 'success'
                                          | 'warning'
                                          | 'info'
                                          | 'error'
                                          | 'default') || 'primary'
                                      return (
                                        <Box
                                          sx={{ 
                                            display: 'flex', 
                                            alignItems: 'center', 
                                            gap: 0.5,
                                            flexShrink: 0
                                          }}
                                        >
                                          <Chip
                                            label={chipLabel}
                                            size="small"
                                            color={chipColor}
                                            variant="outlined"
                                            sx={{ 
                                              fontSize: isSmall ? '0.65rem' : '0.75rem',
                                              height: isSmall ? 20 : 24,
                                              display: isMobile ? 'none' : 'flex',
                                              '& .MuiChip-label': {
                                                px: isSmall ? 0.5 : 0.75,
                                              }
                                            }}
                                          />
                                          <Tooltip title="配置模型组">
                                            <IconButton
                                              size="small"
                                              onClick={() => navigate('/settings/model-groups')}
                                            >
                                              <LaunchIcon fontSize="inherit" />
                                            </IconButton>
                                          </Tooltip>
                                        </Box>
                                      )
                                    })()}
                                </Box>
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={() => handleSaveConfig()}
                  disabled={Object.keys(editingStatus).length === 0 || saveMutation.isPending}
                  size={isSmall ? "small" : "medium"}
                >
                  {saveMutation.isPending ? '保存中...' : '保存配置'}
                </Button>
              </Box>
            </>
          ) : (
            <Alert severity="info">此插件没有可配置项喵～</Alert>
          )}
        </Box>
      )}

      {/* 方法列表 */}
      {activeTab === (plugin.hasConfig ? 2 : 1) && (
        <Card variant="outlined" sx={{ overflow: 'auto', maxHeight: 'calc(100vh - 300px)' }}>
          <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              插件方法
            </Typography>
            {plugin.methods && plugin.methods.length > 0 ? (
              <TableContainer>
                <Table size={isSmall ? "small" : "medium"}>
                  <TableHead>
                    <TableRow>
                      <TableCell width={isMobile ? "30%" : "20%"} sx={{ py: isSmall ? 1 : 1.5 }}>方法名</TableCell>
                      <TableCell width={isMobile ? "25%" : "15%"} sx={{ py: isSmall ? 1 : 1.5 }}>类型</TableCell>
                      <TableCell sx={{ py: isSmall ? 1 : 1.5 }}>描述</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {plugin.methods.map((method: Method) => (
                      <TableRow key={method.name}>
                        <TableCell sx={{ py: isSmall ? 0.75 : 1.25 }}>
                          <Typography
                            variant="body2"
                            sx={{ 
                              fontFamily: 'monospace', 
                              fontWeight: 'bold',
                              fontSize: isSmall ? '0.7rem' : '0.875rem',
                              overflowWrap: 'break-word',
                              wordBreak: 'break-all'
                            }}
                          >
                            {method.name}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ py: isSmall ? 0.75 : 1.25 }}>
                          <Chip
                            label={method.type}
                            color={methodTypeColors[method.type]}
                            size="small"
                            variant="outlined"
                            sx={{ 
                              fontSize: isSmall ? '0.65rem' : '0.75rem',
                              height: isSmall ? 20 : 24,
                              '& .MuiChip-label': {
                                px: isSmall ? 0.5 : 0.75,
                              }
                            }}
                          />
                        </TableCell>
                        <TableCell sx={{ py: isSmall ? 0.75 : 1.25 }}>
                          <Typography 
                            variant="body2" 
                            sx={{ fontSize: isSmall ? '0.75rem' : '0.875rem' }}
                          >
                            {method.description}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="info" sx={{ mt: 2 }}>
                此插件没有定义方法喵～
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Webhook 列表 */}
      {activeTab === (plugin.hasConfig ? 3 : 2) && (
        <Card variant="outlined" sx={{ overflow: 'auto', maxHeight: 'calc(100vh - 300px)' }}>
          <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Webhook 接入点
            </Typography>
            {plugin.webhooks && plugin.webhooks.length > 0 ? (
              <TableContainer>
                <Table size={isSmall ? "small" : "medium"}>
                  <TableHead>
                    <TableRow>
                      <TableCell width={isSmall ? 100 : 150} sx={{ py: isSmall ? 1 : 1.5 }}>接入点</TableCell>
                      <TableCell sx={{ py: isSmall ? 1 : 1.5 }}>名称</TableCell>
                      <TableCell width={isSmall ? 80 : 132} align="center" sx={{ py: isSmall ? 1 : 1.5 }}>
                        操作
                      </TableCell>
                      <TableCell width={36} padding="none" />
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {plugin.webhooks.map(webhook => (
                      <React.Fragment key={webhook.endpoint}>
                        <TableRow>
                          <TableCell>
                            <Typography
                              variant="body2"
                              sx={{ 
                                fontFamily: 'monospace', 
                                fontWeight: 'bold',
                                fontSize: isSmall ? '0.7rem' : '0.875rem',
                                overflowWrap: 'break-word',
                                wordBreak: 'break-all'
                              }}
                            >
                              {webhook.endpoint}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography 
                              variant="body2"
                              sx={{ fontSize: isSmall ? '0.75rem' : '0.875rem' }}
                            >
                              {webhook.name}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Button
                              size="small"
                              startIcon={<ContentCopyIcon fontSize="small" />}
                              onClick={() => {
                                const url = `${server_addr}/api/webhook/${webhook.endpoint}`
                                navigator.clipboard.writeText(url)
                                setMessage('已复制 Webhook 地址～')
                              }}
                              sx={{
                                textTransform: 'none',
                                color: 'primary.main',
                                '&:hover': {
                                  backgroundColor: 'transparent',
                                  textDecoration: 'underline',
                                },
                                fontSize: isSmall ? '0.7rem' : '0.8rem',
                                px: isSmall ? 0.5 : 1,
                                minWidth: 'auto',
                                '& .MuiButton-startIcon': {
                                  mr: isSmall ? 0.3 : 0.5,
                                  '& svg': {
                                    fontSize: isSmall ? '0.9rem' : '1rem'
                                  }
                                }
                              }}
                            >
                              复制
                            </Button>
                          </TableCell>
                          <TableCell padding="none">
                            <IconButton
                              size="small"
                              onClick={() => {
                                const newExpandedRows = new Set(expandedRows)
                                if (newExpandedRows.has(webhook.endpoint)) {
                                  newExpandedRows.delete(webhook.endpoint)
                                } else {
                                  newExpandedRows.add(webhook.endpoint)
                                }
                                setExpandedRows(newExpandedRows)
                              }}
                            >
                              {expandedRows.has(webhook.endpoint) ? (
                                <KeyboardArrowUpIcon fontSize={isSmall ? "small" : "medium"} />
                              ) : (
                                <KeyboardArrowDownIcon fontSize={isSmall ? "small" : "medium"} />
                              )}
                            </IconButton>
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell
                            colSpan={4}
                            sx={{
                              py: 0,
                              borderBottom: expandedRows.has(webhook.endpoint) ? undefined : 'none',
                            }}
                          >
                            <Collapse
                              in={expandedRows.has(webhook.endpoint)}
                              timeout="auto"
                              unmountOnExit
                            >
                              <Box sx={{ py: 2 }}>
                                <Typography variant="subtitle2" gutterBottom>
                                  描述
                                </Typography>
                                <Typography 
                                  variant="body2" 
                                  color="text.secondary" 
                                  sx={{ 
                                    pl: 2,
                                    fontSize: isSmall ? '0.75rem' : '0.875rem' 
                                  }}
                                >
                                  {webhook.description || '暂无描述'}
                                </Typography>
                              </Box>
                            </Collapse>
                          </TableCell>
                        </TableRow>
                      </React.Fragment>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="info" sx={{ mt: 2 }}>
                此插件没有定义 Webhook 接入点～
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* 数据管理 */}
      {activeTab === 4 && (
        <Card variant="outlined" sx={{ overflow: 'auto', maxHeight: 'calc(100vh - 300px)' }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              插件数据
            </Typography>
            {isDataLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', pt: 4 }}>
                <CircularProgress />
              </Box>
            ) : pluginData.length > 0 ? (
              <TableContainer>
                <Table size={isSmall ? "small" : "medium"}>
                  <TableHead>
                    <TableRow>
                      <TableCell width={isMobile ? 80 : 150}>会话</TableCell>
                      <TableCell width={isMobile ? 80 : 150}>用户</TableCell>
                      <TableCell>存储键</TableCell>
                      <TableCell width={isMobile ? 100 : 132} align="center">
                        操作
                      </TableCell>
                      <TableCell width={36} padding="none" />
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pluginData.map(data => (
                      <React.Fragment key={data.id}>
                        <TableRow>
                          <TableCell>
                            <Typography 
                              variant="body2"
                              sx={{ fontSize: isSmall ? '0.7rem' : '0.875rem' }}
                            >
                              {data.target_chat_key || '全局'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography 
                              variant="body2"
                              sx={{ fontSize: isSmall ? '0.7rem' : '0.875rem' }}
                            >
                              {data.target_user_id || '全局'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography 
                              variant="body2" 
                              sx={{ 
                                fontFamily: 'monospace',
                                fontSize: isSmall ? '0.7rem' : '0.875rem',
                                overflowWrap: 'break-word',
                                wordBreak: 'break-all'
                              }}
                            >
                              {data.data_key}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Stack direction="row" spacing={0.5} justifyContent="flex-end" flexWrap="wrap">
                              <Button
                                size="small"
                                startIcon={<ContentCopyIcon fontSize="small" />}
                                onClick={() => {
                                  navigator.clipboard.writeText(data.data_value)
                                  setMessage('已复制数据值～')
                                }}
                                sx={{
                                  textTransform: 'none',
                                  color: 'primary.main',
                                  '&:hover': {
                                    backgroundColor: 'transparent',
                                    textDecoration: 'underline',
                                  },
                                  fontSize: isSmall ? '0.7rem' : '0.8rem',
                                  px: isSmall ? 0.5 : 1,
                                  minWidth: 'auto',
                                  '& .MuiButton-startIcon': {
                                    mr: isSmall ? 0.3 : 0.5,
                                    '& svg': {
                                      fontSize: isSmall ? '0.9rem' : '1rem'
                                    }
                                  }
                                }}
                              >
                                复制
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                startIcon={<DeleteIcon fontSize="small" />}
                                onClick={() => {
                                  setDeleteDataId(data.id)
                                  setDeleteDataConfirmOpen(true)
                                }}
                                sx={{
                                  textTransform: 'none',
                                  '&:hover': {
                                    backgroundColor: 'transparent',
                                    textDecoration: 'underline',
                                  },
                                  fontSize: isSmall ? '0.7rem' : '0.8rem',
                                  px: isSmall ? 0.5 : 1,
                                  minWidth: 'auto',
                                  '& .MuiButton-startIcon': {
                                    mr: isSmall ? 0.3 : 0.5,
                                    '& svg': {
                                      fontSize: isSmall ? '0.9rem' : '1rem'
                                    }
                                  }
                                }}
                              >
                                删除
                              </Button>
                            </Stack>
                          </TableCell>
                          <TableCell padding="none">
                            <IconButton
                              size="small"
                              onClick={() => {
                                const newExpandedRows = new Set(expandedDataRows)
                                if (newExpandedRows.has(data.id)) {
                                  newExpandedRows.delete(data.id)
                                } else {
                                  newExpandedRows.add(data.id)
                                }
                                setExpandedDataRows(newExpandedRows)
                              }}
                            >
                              {expandedDataRows.has(data.id) ? (
                                <KeyboardArrowUpIcon fontSize={isSmall ? "small" : "medium"} />
                              ) : (
                                <KeyboardArrowDownIcon fontSize={isSmall ? "small" : "medium"} />
                              )}
                            </IconButton>
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell
                            colSpan={5}
                            sx={{
                              py: 0,
                              borderBottom: expandedDataRows.has(data.id) ? undefined : 'none',
                            }}
                          >
                            <Collapse
                              in={expandedDataRows.has(data.id)}
                              timeout="auto"
                              unmountOnExit
                            >
                              <Box sx={{ py: 2 }}>
                                <Typography variant="subtitle2" gutterBottom>
                                  数据值
                                </Typography>
                                <Typography
                                  variant="body2"
                                  color="text.secondary"
                                  sx={{
                                    pl: 2,
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-all',
                                    display: '-webkit-box',
                                    WebkitLineClamp: 10,
                                    WebkitBoxOrient: 'vertical',
                                    overflow: 'hidden',
                                    fontSize: isSmall ? '0.75rem' : '0.875rem'
                                  }}
                                >
                                  {data.data_value}
                                </Typography>
                              </Box>
                            </Collapse>
                          </TableCell>
                        </TableRow>
                      </React.Fragment>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="info" sx={{ mt: 2 }}>
                此插件暂无存储数据喵～
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* 重置数据确认对话框 */}
      <Dialog open={resetDataConfirmOpen} onClose={() => setResetDataConfirmOpen(false)}>
        <DialogTitle>确认重置数据？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            此操作将删除该插件的所有存储数据，包括全局数据、会话数据和用户数据。此操作不可恢复，是否继续？
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button 
            onClick={() => setResetDataConfirmOpen(false)} 
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            取消
          </Button>
          <Button
            onClick={() => {
              resetDataMutation.mutate()
              setResetDataConfirmOpen(false)
            }}
            color="error"
            variant="contained"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            确认重置
          </Button>
        </DialogActions>
      </Dialog>

      {/* 重载确认对话框 */}
      <Dialog open={reloadConfirmOpen} onClose={() => setReloadConfirmOpen(false)}>
        <DialogTitle>确认重载插件？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            重载插件将重新加载此插件的代码，可能会导致正在进行的操作中断。是否继续？
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button 
            onClick={() => setReloadConfirmOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            取消
          </Button>
          <Button
            onClick={() => {
              reloadMutation.mutate()
              setReloadConfirmOpen(false)
            }}
            color="primary"
            variant="contained"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            确认
          </Button>
        </DialogActions>
      </Dialog>

      {/* 必填项警告对话框 */}
      <Dialog open={saveWarningOpen} onClose={() => setSaveWarningOpen(false)}>
        <DialogTitle>存在未填写的必填项</DialogTitle>
        <DialogContent>
          <DialogContentText>
            以下必填项未填写：
            <List>
              {emptyRequiredFields.map((field, index) => (
                <ListItem key={index}>
                  <Typography color="error">• {field}</Typography>
                </ListItem>
              ))}
            </List>
            是否仍要继续保存？
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button 
            onClick={() => setSaveWarningOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            取消
          </Button>
          <Button 
            onClick={() => handleSaveConfig(true)} 
            color="warning"
            variant="contained"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            继续保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除插件包确认对话框 */}
      <Dialog open={deleteConfirmOpen} onClose={() => setDeleteConfirmOpen(false)}>
        <DialogTitle>确认删除插件包？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            此操作将删除插件包 "{plugin.name}"，包括其所有文件和配置。此操作不可恢复，是否继续？
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button 
            onClick={() => setDeleteConfirmOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            取消
          </Button>
          <Button
            onClick={() => {
              removePackageMutation.mutate()
              setDeleteConfirmOpen(false)
            }}
            color="error"
            variant="contained"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            确认删除
          </Button>
        </DialogActions>
      </Dialog>

      {/* 更新插件包确认对话框 */}
      <Dialog open={updateConfirmOpen} onClose={() => setUpdateConfirmOpen(false)} maxWidth="md">
        <DialogTitle>确认更新插件包？</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2" component="div">
              <strong>安全提示：</strong>{' '}
              插件更新可能包含原作者未经审核的代码变更，包括潜在的恶意代码或不安全内容。
              NekroAI社区仅作为插件分享平台，不具备对第三方平台托管的插件内容负责的能力。
              使用任何第三方插件都存在潜在风险，请自行评估插件的安全性。
            </Typography>
          </Alert>

          <DialogContentText sx={{ mt: 2 }}>
            此操作将从远程仓库更新插件包 "{plugin.name}"
            至最新版本。更新过程可能会导致当前配置变更，是否继续？
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button 
            onClick={() => setUpdateConfirmOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            取消
          </Button>
          <Button
            onClick={() => {
              updatePackageMutation.mutate()
              setUpdateConfirmOpen(false)
            }}
            color="primary"
            variant="contained"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            确认更新
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除数据确认对话框 */}
      <Dialog open={deleteDataConfirmOpen} onClose={() => setDeleteDataConfirmOpen(false)}>
        <DialogTitle>确认删除数据？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            此操作将删除该条存储数据，此操作不可恢复，是否继续？
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button 
            onClick={() => setDeleteDataConfirmOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            取消
          </Button>
          <Button
            onClick={() => {
              if (deleteDataId !== null) {
                deleteDataMutation.mutate(deleteDataId)
                setDeleteDataConfirmOpen(false)
                setDeleteDataId(null)
              }
            }}
            color="error"
            variant="contained"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            确认删除
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!message}
        autoHideDuration={3000}
        onClose={() => setMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setMessage('')}
          severity={message.includes('失败') ? 'error' : 'success'}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {message}
        </Alert>
      </Snackbar>
    </Box>
  )
}

export default function PluginsManagementPage() {
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null)
  const [message, setMessage] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const queryClient = useQueryClient()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const [drawerOpen, setDrawerOpen] = useState(false)

  // 获取插件列表 - 只获取基础列表，不获取详情
  const { data: plugins = [], isLoading } = useQuery({
    queryKey: ['plugins'],
    queryFn: () => pluginsApi.getPlugins(),
  })

  // 获取当前选中插件的详情
  const { data: pluginDetail } = useQuery({
    queryKey: ['plugin-detail', selectedPlugin?.id],
    queryFn: () => pluginsApi.getPluginDetail(selectedPlugin?.id as string),
    enabled: !!selectedPlugin?.id,
  })

  // 当获取到详情后更新选中的插件
  useEffect(() => {
    if (pluginDetail) {
      setSelectedPlugin(pluginDetail)
    }
  }, [pluginDetail])

  // 切换插件启用状态
  const toggleEnabledMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      pluginsApi.togglePluginEnabled(id, enabled),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      setMessage(`插件已${variables.enabled ? '启用' : '禁用'}喵～`)

      // 如果是当前选中的插件，更新其状态
      if (selectedPlugin && selectedPlugin.id === variables.id) {
        setSelectedPlugin(prev => (prev ? { ...prev, enabled: variables.enabled } : null))
      }
    },
    onError: (error: Error) => {
      setMessage(`更新失败: ${error.message}`)
    },
  })

  const handleToggleEnabled = (id: string, enabled: boolean) => {
    toggleEnabledMutation.mutate({ id, enabled })
  }

  // 处理选择插件的逻辑
  const handleSelectPlugin = (plugin: Plugin) => {
    setSelectedPlugin(plugin)
    if (isMobile) {
      setDrawerOpen(false)
    }
  }

  // 获取插件类型
  const getPluginType = (plugin: Plugin) => {
    if (plugin.isBuiltin) return 'builtin'
    if (plugin.isPackage) return 'package'
    return 'local'
  }

  // 过滤插件列表
  const filteredPlugins = plugins
    .filter(
      plugin =>
        plugin.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        plugin.description.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      // 基础交互插件(模块名为"basic")固定放在最前面
      if (a.moduleName === 'basic') return -1
      if (b.moduleName === 'basic') return 1

      // 优先按启用状态排序（启用的在前）
      if (a.enabled !== b.enabled) {
        return a.enabled ? -1 : 1
      }

      // 按照插件类型排序：内置 -> 云端 -> 本地
      const getTypeOrder = (plugin: Plugin) => {
        if (plugin.isBuiltin) return 0
        if (plugin.isPackage) return 1
        return 2 // 本地插件
      }

      const typeOrderA = getTypeOrder(a)
      const typeOrderB = getTypeOrder(b)

      if (typeOrderA !== typeOrderB) {
        return typeOrderA - typeOrderB
      }

      // 最后按名称字母顺序排序
      return a.name.localeCompare(b.name)
    })

  return (
    <Box 
          sx={{
            display: 'flex',
        height: 'calc(100vh - 120px)', 
            flexDirection: 'column',
        gap: 2, 
        position: 'relative',
      }}
    >
      {/* 主要内容区 */}
      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {isMobile ? (
          // 移动端布局
          <>
            <Drawer
              anchor="left"
              open={drawerOpen}
              onClose={() => setDrawerOpen(false)}
              sx={{
                '& .MuiDrawer-paper': {
                  width: isSmall ? '85%' : '75%',
                  maxWidth: 300,
                  boxShadow: 3,
                },
              }}
            >
              <Box sx={{ p: 1.5, borderBottom: 1, borderColor: 'divider' }}>
                <TextField
                  placeholder="搜索插件..."
                  size="small"
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  variant="outlined"
                  fullWidth
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 1,
                    },
                  }}
                />
              </Box>

              <Box
                sx={{
                  flex: 1,
                  overflow: 'auto',
                  '&::-webkit-scrollbar': {
                    width: '8px',
                  },
                  '&::-webkit-scrollbar-thumb': {
                    backgroundColor: 'rgba(0,0,0,0.2)',
                    borderRadius: '4px',
                  },
                }}
              >
                {isLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : filteredPlugins.length > 0 ? (
                  <List sx={{ flex: 1, padding: 0 }}>
                    {filteredPlugins.map(plugin => (
                      <React.Fragment key={plugin.id}>
                        <ListItem
                          disablePadding
                          onClick={() => handleSelectPlugin(plugin)}
                          sx={{
                            cursor: 'pointer',
                            '&:hover': { bgcolor: 'action.hover' },
                            bgcolor: selectedPlugin?.id === plugin.id ? 'action.selected' : 'inherit',
                          }}
                        >
                          <ListItemButton sx={{ py: 1 }}>
                            <Box
                              sx={{
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                bgcolor: plugin.enabled ? 'success.main' : 'error.main',
                                mr: 1.5,
                                flexShrink: 0,
                              }}
                            />
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5 }}>
                                  <Chip
                                    label={pluginTypeTexts[getPluginType(plugin)]}
                                    size="small"
                                    color={pluginTypeColors[getPluginType(plugin)]}
                                    variant="outlined"
                                    sx={{ 
                                      height: 18, 
                                      fontSize: '0.65rem'
                                    }}
                                  />
                                  <Typography 
                                    variant="body1" 
                                    sx={{ 
                                      fontWeight: 'bold',
                                      fontSize: '0.85rem',
                                      ml: 0.5,
                                    }}
                                  >
                                    {plugin.name}
                                  </Typography>
                                  {plugin.hasConfig && (
                                    <Tooltip title="有配置项">
                                      <SettingsIcon
                                        fontSize="small"
                                        sx={{ ml: 0.5, opacity: 0.6, fontSize: 16 }}
                                      />
                                    </Tooltip>
                                  )}
                                </Box>
                              }
                              secondary={
                                <Typography
                                  variant="body2"
                                  sx={{
                                    textOverflow: 'ellipsis',
                                    overflow: 'hidden',
                                    whiteSpace: 'nowrap',
                                    maxWidth: 200,
                                    fontSize: isSmall ? '0.75rem' : 'inherit'
                                  }}
                                >
                                  {plugin.description}
                                </Typography>
                              }
                            />
                          </ListItemButton>
                        </ListItem>
                        <Divider />
                      </React.Fragment>
                    ))}
                  </List>
                ) : (
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      height: '100%',
                      p: 2,
                    }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      没有找到匹配的插件喵～
                    </Typography>
                  </Box>
                )}
              </Box>
            </Drawer>

            {/* 移动端主内容区 */}
            <Paper sx={{ flex: 1, p: 2, overflow: 'auto' }}>
              {selectedPlugin ? (
                <PluginDetails
                  plugin={selectedPlugin}
                  onBack={() => setSelectedPlugin(null)}
                  onToggleEnabled={handleToggleEnabled}
                />
              ) : (
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    height: '100%',
                    p: 3,
                    textAlign: 'center',
                  }}
                >
                  <ExtensionIcon sx={{ fontSize: 60, mb: 2, opacity: 0.7 }} />
                  <Typography variant="h6" gutterBottom>
                    欢迎使用插件管理
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    请点击右下角按钮选择一个插件来查看详情喵～
                  </Typography>
                  {/* 移除选择插件按钮 */}
                </Box>
              )}
            </Paper>
          </>
        ) : (
          // 桌面端布局
          <>
            {/* 左侧插件列表 */}
            <Paper
              sx={{
                width: 300,
                overflow: 'hidden',
                mr: 2,
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <Box sx={{ p: 1.5, borderBottom: 1, borderColor: 'divider' }}>
                <TextField
                  placeholder="搜索插件..."
                  size="small"
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  variant="outlined"
                  fullWidth
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 1,
                    },
                  }}
                />
              </Box>

              <Box
                sx={{
                  flex: 1,
                  overflow: 'auto',
                  '&::-webkit-scrollbar': {
                    width: '8px',
                  },
                  '&::-webkit-scrollbar-thumb': {
                    backgroundColor: 'rgba(0,0,0,0.2)',
                    borderRadius: '4px',
                  },
                }}
              >
                {isLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : filteredPlugins.length > 0 ? (
                  <List sx={{ flex: 1, padding: 0 }}>
                    {filteredPlugins.map(plugin => (
                      <React.Fragment key={plugin.id}>
                        <ListItem
                          disablePadding
                          onClick={() => handleSelectPlugin(plugin)}
                          sx={{
                            cursor: 'pointer',
                            '&:hover': { bgcolor: 'action.hover' },
                            bgcolor: selectedPlugin?.id === plugin.id ? 'action.selected' : 'inherit',
                          }}
                        >
                          <ListItemButton sx={{ py: isSmall ? 0.75 : 1.25 }}>
                            <Box
                              sx={{
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                bgcolor: plugin.enabled ? 'success.main' : 'error.main',
                                mr: 1.5,
                                flexShrink: 0,
                              }}
                            />
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  <Chip
                                    label={pluginTypeTexts[getPluginType(plugin)]}
                                    size="small"
                                    color={pluginTypeColors[getPluginType(plugin)]}
                                    variant="outlined"
                                    sx={{ 
                                      height: 18, 
                                      fontSize: '0.65rem'
                                    }}
                                  />
                                  <Typography 
                                    variant="body1" 
                                    sx={{ 
                                      fontWeight: 'bold',
                                      fontSize: '0.85rem',
                                      ml: 0.5,
                                    }}
                                  >
                                    {plugin.name}
                                  </Typography>
                                  {plugin.hasConfig && (
                                    <Tooltip title="有配置项">
                                      <SettingsIcon
                                        fontSize="small"
                                        sx={{ ml: 0.5, opacity: 0.6, fontSize: 16 }}
                                      />
                                    </Tooltip>
                                  )}
                                </Box>
                              }
                              secondary={
                                <Typography
                                  variant="body2"
                                  sx={{
                                    textOverflow: 'ellipsis',
                                    overflow: 'hidden',
                                    whiteSpace: 'nowrap',
                                    maxWidth: 200,
                                    fontSize: isSmall ? '0.75rem' : 'inherit'
                                  }}
                                >
                                  {plugin.description}
                                </Typography>
                              }
                            />
                          </ListItemButton>
                        </ListItem>
                        <Divider />
                      </React.Fragment>
                    ))}
                  </List>
                ) : (
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      height: '100%',
                      p: 2,
                    }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      没有找到匹配的插件喵～
                    </Typography>
                  </Box>
                )}
              </Box>
            </Paper>

            {/* 右侧插件详情 */}
            <Paper sx={{ flex: 1, p: 2, overflow: 'auto' }}>
              {selectedPlugin ? (
                <PluginDetails
                  plugin={selectedPlugin}
                  onBack={() => setSelectedPlugin(null)}
                  onToggleEnabled={handleToggleEnabled}
                />
              ) : (
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    height: '100%',
                    p: 3,
                    textAlign: 'center',
                  }}
                >
                  <ExtensionIcon sx={{ fontSize: 60, mb: 2, opacity: 0.7 }} />
                  <Typography variant="h6" gutterBottom>
                    欢迎使用插件管理
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                请从左侧选择一个插件查看详情喵～
              </Typography>
                </Box>
              )}
            </Paper>
          </>
        )}
      </Box>

      <Snackbar
        open={!!message}
        autoHideDuration={3000}
        onClose={() => setMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setMessage('')}
          severity={message.includes('失败') ? 'error' : 'success'}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {message}
        </Alert>
      </Snackbar>
      
      {/* 移动端展示插件列表的Fab按钮 - 始终可见 */}
      {isMobile && (
        <Fab
          color="primary"
          size={isSmall ? "medium" : "large"}
          onClick={() => setDrawerOpen(true)}
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            zIndex: 1099,
            boxShadow: 3,
          }}
        >
          <ExtensionIcon />
        </Fab>
      )}
    </Box>
  )
}
