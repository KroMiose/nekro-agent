import React, { useState, useEffect, useCallback } from 'react'
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
  ButtonGroup,
  Link,
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
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Method, Plugin, PluginConfig, pluginsApi, MethodType } from '../../services/api/plugins'
import { useNavigate } from 'react-router-dom'

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

// 方法类型对应的颜色映射
const METHOD_TYPE_COLORS: Record<MethodType, 'primary' | 'success' | 'warning' | 'info'> = {
  tool: 'primary',
  behavior: 'success',
  agent: 'warning',
  multimodal_agent: 'info',
}

// 配置类型颜色映射
const CONFIG_TYPE_COLORS: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'default'> = {
  str: 'warning',
  int: 'info',
  float: 'info',
  bool: 'success',
  list: 'primary',
}

// 插件类型对应的颜色映射
const PLUGIN_TYPE_COLORS: Record<
  string,
  'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'default'
> = {
  builtin: 'primary',
  package: 'info',
  local: 'warning',
}

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
            <IconButton onClick={handleAddItem} color="primary">
              <AddIcon />
            </IconButton>
          </Box>
          <List sx={{ maxHeight: 300, overflow: 'auto' }}>
            {items.map((item, index) => (
              <ListItem
                key={index}
                secondaryAction={
                  <IconButton edge="end" onClick={() => handleDeleteItem(index)}>
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
      <DialogActions>
        <Button onClick={onClose}>取消</Button>
        <Button onClick={handleSave} color="primary">
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
  const queryClient = useQueryClient()
  const navigate = useNavigate()

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
    enabled: !!plugin && activeTab === 1,
  })

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
    if (plugin.isBuiltin) return '内置'
    if (plugin.isPackage) return '云端'
    return '本地'
  }

  // 渲染配置输入控件
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
                    color={CONFIG_TYPE_COLORS[itemType] || 'default'}
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
      // 根据 model_type 过滤模型组，如未指定则全部展示
      const modelGroupNames = Object.entries(modelGroups)
        // 跳过第一个元素（模型组名），只使用 group 进行过滤
        .filter(([, group]) => !config.model_type || group.MODEL_TYPE === config.model_type)
        .map(([name]) => name)
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
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <IconButton onClick={onBack} sx={{ mr: 2 }}>
          <ArrowBackIcon />
        </IconButton>
        <Typography
          variant="h5"
          component="div"
          sx={{ flexGrow: 1, display: 'flex', alignItems: 'center' }}
        >
          {plugin.name}
          <Switch
            checked={plugin.enabled}
            onChange={() => onToggleEnabled(plugin.id, !plugin.enabled)}
            color="success"
            size="small"
            sx={{ ml: 1 }}
          />
          <Chip
            label={getPluginTypeText()}
            size="small"
            color={PLUGIN_TYPE_COLORS[getPluginType()]}
            sx={{ ml: 1 }}
          />
        </Typography>
        <ButtonGroup variant="outlined" sx={{ mr: 1 }}>
          {!plugin.isBuiltin && (
            <Button
              startIcon={plugin.isPackage ? <DeleteIcon /> : <EditIcon />}
              onClick={() =>
                plugin.isPackage ? setDeleteConfirmOpen(true) : handleNavigateToEditor()
              }
              color={plugin.isPackage ? 'error' : 'warning'}
            >
              {plugin.isPackage ? '删除' : '编辑'}
            </Button>
          )}
          {plugin.isPackage && (
            <Button
              startIcon={<RefreshIcon />}
              onClick={() => setUpdateConfirmOpen(true)}
              color="success"
            >
              更新
            </Button>
          )}
          <Button
            startIcon={<DeleteIcon />}
            onClick={() => setResetDataConfirmOpen(true)}
            color="warning"
          >
            重置
          </Button>
          <Button startIcon={<RefreshIcon />} onClick={() => setReloadConfirmOpen(true)}>
            重载
          </Button>
        </ButtonGroup>
      </Box>

      <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} sx={{ mb: 2 }}>
        <Tab
          icon={<InfoIcon sx={{ fontSize: 20 }} />}
          label="基本信息"
          sx={{
            flexDirection: 'row',
            '& .MuiTab-iconWrapper': {
              marginRight: 1,
              marginBottom: '0 !important',
            },
            minHeight: 40,
            padding: '6px 16px',
          }}
        />
        {plugin.hasConfig && (
          <Tab
            icon={<SettingsIcon sx={{ fontSize: 20 }} />}
            label="配置"
            sx={{
              flexDirection: 'row',
              '& .MuiTab-iconWrapper': {
                marginRight: 1,
                marginBottom: '0 !important',
              },
              minHeight: 40,
              padding: '6px 16px',
            }}
          />
        )}
        <Tab
          icon={<CodeIcon sx={{ fontSize: 20 }} />}
          label="方法"
          sx={{
            flexDirection: 'row',
            '& .MuiTab-iconWrapper': {
              marginRight: 1,
              marginBottom: '0 !important',
            },
            minHeight: 40,
            padding: '6px 16px',
          }}
        />
        <Tab
          icon={<WebhookIcon sx={{ fontSize: 20 }} />}
          label="Webhook"
          sx={{
            flexDirection: 'row',
            '& .MuiTab-iconWrapper': {
              marginRight: 1,
              marginBottom: '0 !important',
            },
            minHeight: 40,
            padding: '6px 16px',
          }}
        />
        <Tab
          icon={<StorageIcon sx={{ fontSize: 20 }} />}
          label="数据管理"
          sx={{
            flexDirection: 'row',
            '& .MuiTab-iconWrapper': {
              marginRight: 1,
              marginBottom: '0 !important',
            },
            minHeight: 40,
            padding: '6px 16px',
          }}
        />
      </Tabs>

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
                    }}
                  >
                    <Typography variant="subtitle1">插件配置</Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ fontStyle: 'italic' }}
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
                    <Table size="small" stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell width="30%">配置项</TableCell>
                          <TableCell width="10%">类型</TableCell>
                          <TableCell width="60%">值</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {pluginConfig
                          .filter(item => !item.is_hidden)
                          .map(item => (
                            <TableRow key={item.key}>
                              <TableCell component="th" scope="row">
                                <Box>
                                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
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
                                          <HelpOutlineIcon fontSize="small" />
                                        </IconButton>
                                      </HtmlTooltip>
                                    )}
                                  </Box>
                                  <Typography variant="caption" color="text.secondary">
                                    {item.key}
                                  </Typography>
                                </Box>
                              </TableCell>
                              <TableCell>
                                <Chip
                                  label={item.type}
                                  size="small"
                                  color={CONFIG_TYPE_COLORS[item.type] || 'default'}
                                  variant="outlined"
                                />
                              </TableCell>
                              <TableCell>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  {renderConfigInput(item)}
                                  {item.ref_model_groups && (
                                    <Chip
                                      label="模型组"
                                      size="small"
                                      color="primary"
                                      variant="outlined"
                                    />
                                  )}
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
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              插件方法
            </Typography>
            {plugin.methods && plugin.methods.length > 0 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>方法名</TableCell>
                      <TableCell>类型</TableCell>
                      <TableCell>描述</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {plugin.methods.map((method: Method) => (
                      <TableRow key={method.name}>
                        <TableCell>
                          <Typography
                            variant="body2"
                            sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}
                          >
                            {method.name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={method.type}
                            color={METHOD_TYPE_COLORS[method.type]}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>{method.description}</TableCell>
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
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              Webhook 接入点
            </Typography>
            {plugin.webhooks && plugin.webhooks.length > 0 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell width={150}>接入点</TableCell>
                      <TableCell>名称</TableCell>
                      <TableCell width={132} align="center">
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
                              sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}
                            >
                              {webhook.endpoint}
                            </Typography>
                          </TableCell>
                          <TableCell>{webhook.name}</TableCell>
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
                              }}
                            >
                              复制接入点
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
                                <KeyboardArrowUpIcon />
                              ) : (
                                <KeyboardArrowDownIcon />
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
                                <Typography variant="body2" color="text.secondary" sx={{ pl: 2 }}>
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
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell width={150}>会话</TableCell>
                      <TableCell width={150}>用户</TableCell>
                      <TableCell>存储键</TableCell>
                      <TableCell width={132} align="center">
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
                            <Typography variant="body2">
                              {data.target_chat_key || '全局'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{data.target_user_id || '全局'}</Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {data.data_key}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Stack direction="row" spacing={1} justifyContent="flex-end">
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
                                }}
                              >
                                复制
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                startIcon={<DeleteIcon fontSize="small" />}
                                onClick={() => deleteDataMutation.mutate(data.id)}
                                sx={{
                                  textTransform: 'none',
                                  '&:hover': {
                                    backgroundColor: 'transparent',
                                    textDecoration: 'underline',
                                  },
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
                                <KeyboardArrowUpIcon />
                              ) : (
                                <KeyboardArrowDownIcon />
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
        <DialogActions>
          <Button onClick={() => setResetDataConfirmOpen(false)}>取消</Button>
          <Button
            onClick={() => {
              resetDataMutation.mutate()
              setResetDataConfirmOpen(false)
            }}
            color="error"
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
        <DialogActions>
          <Button onClick={() => setReloadConfirmOpen(false)}>取消</Button>
          <Button
            onClick={() => {
              reloadMutation.mutate()
              setReloadConfirmOpen(false)
            }}
            color="primary"
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
        <DialogActions>
          <Button onClick={() => setSaveWarningOpen(false)}>取消</Button>
          <Button onClick={() => handleSaveConfig(true)} color="warning">
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
        <DialogActions>
          <Button onClick={() => setDeleteConfirmOpen(false)}>取消</Button>
          <Button
            onClick={() => {
              removePackageMutation.mutate()
              setDeleteConfirmOpen(false)
            }}
            color="error"
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
        <DialogActions>
          <Button onClick={() => setUpdateConfirmOpen(false)}>取消</Button>
          <Button
            onClick={() => {
              updatePackageMutation.mutate()
              setUpdateConfirmOpen(false)
            }}
            color="primary"
          >
            确认更新
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

  // 获取插件列表
  const { data: plugins = [], isLoading } = useQuery({
    queryKey: ['plugins'],
    queryFn: async () => {
      const list = await pluginsApi.getPlugins()
      // 获取每个插件的详细信息
      const detailedPlugins = await Promise.all(
        list.map(async plugin => {
          const detail = await pluginsApi.getPluginDetail(plugin.id)
          return detail || plugin
        })
      )
      return detailedPlugins
    },
  })

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
    <Box sx={{ display: 'flex', height: 'calc(100vh - 120px)', flexDirection: 'column', gap: 2 }}>
      {/* 主要内容区 */}
      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
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
              <List sx={{ flex: 1 }}>
                {filteredPlugins.map(plugin => (
                  <React.Fragment key={plugin.id}>
                    <ListItem
                      onClick={() => setSelectedPlugin(plugin)}
                      sx={{
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'action.hover' },
                        bgcolor: selectedPlugin?.id === plugin.id ? 'action.selected' : 'inherit',
                      }}
                    >
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
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {/* 插件类型标签 */}
                            {plugin.isBuiltin && (
                              <Chip
                                label="内置"
                                size="small"
                                color="primary"
                                sx={{ mr: 1, height: 20 }}
                              />
                            )}
                            {plugin.isPackage && (
                              <Chip
                                label="云端"
                                size="small"
                                color="info"
                                sx={{ mr: 1, height: 20 }}
                              />
                            )}
                            {!plugin.isBuiltin && !plugin.isPackage && (
                              <Chip
                                label="本地"
                                size="small"
                                color="warning"
                                sx={{ mr: 1, height: 20 }}
                              />
                            )}
                            <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                              {plugin.name}
                            </Typography>
                            {plugin.hasConfig && (
                              <Tooltip title="有配置项">
                                <SettingsIcon
                                  fontSize="small"
                                  sx={{ ml: 1, opacity: 0.6, fontSize: 16 }}
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
                            }}
                          >
                            {plugin.description}
                          </Typography>
                        }
                      />
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
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
              }}
            >
              <Typography variant="h6" color="text.secondary">
                请从左侧选择一个插件查看详情喵～
              </Typography>
            </Box>
          )}
        </Paper>
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
    </Box>
  )
}
