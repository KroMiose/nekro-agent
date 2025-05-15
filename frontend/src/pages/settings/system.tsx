import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Box,
  Paper,
  TextField,
  Switch,
  FormControlLabel,
  Stack,
  Alert,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  MenuItem,
  InputAdornment,
  Typography,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  List,
  ListItem,
  tooltipClasses,
  TooltipProps,
  useTheme,
  useMediaQuery,
  SxProps,
  Theme,
} from '@mui/material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { configApi, ConfigItem, ModelTypeOption } from '../../services/api/config'
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Tune as TuneIcon,
  HelpOutline as HelpOutlineIcon,
  Search as SearchIcon,
  Launch as LaunchIcon,
} from '@mui/icons-material'
import { styled } from '@mui/material/styles'
import { useNavigate, useLocation } from 'react-router-dom'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'

// 添加自定义 Tooltip 样式
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

// 添加列表编辑对话框组件
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

// 添加类型颜色选择函数到组件外部
const getTypeColor = (type: string) => {
  switch (type) {
    case 'str':
      return 'warning'
    case 'int':
      return 'info'
    case 'float':
      return 'info'
    case 'bool':
      return 'success'
    case 'list':
      return 'primary'
    default:
      return 'default'
  }
}

export default function SettingsPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [message, setMessage] = useState<string>('')
  const [editingValues, setEditingValues] = useState<Record<string, string>>({})
  const [visibleSecrets, setVisibleSecrets] = useState<Record<string, boolean>>({})
  const [reloadConfirmOpen, setReloadConfirmOpen] = useState(false)
  const [saveWarningOpen, setSaveWarningOpen] = useState(false)
  const [emptyRequiredFields, setEmptyRequiredFields] = useState<string[]>([])
  const [searchText, setSearchText] = useState<string>('')
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  // 将列表编辑状态提升到组件级别
  const [listEditState, setListEditState] = useState<{
    open: boolean
    configKey: string | null
  }>({
    open: false,
    configKey: null,
  })

  // 从URL中获取搜索参数
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search)
    const searchParamValue = searchParams.get('search')
    if (searchParamValue) {
      setSearchText(searchParamValue)
    }
  }, [location.search])

  // 获取配置列表
  const { data: configs = [] } = useQuery({
    queryKey: ['configs'],
    queryFn: () => configApi.getConfigList(),
  })

  // 获取模型组列表
  const { data: modelGroups = {} } = useQuery({
    queryKey: ['model-groups'],
    queryFn: () => configApi.getModelGroups(),
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

  // 检查必填项
  const checkRequiredFields = useCallback(() => {
    const emptyFields = configs
      .filter(config => {
        if (!config.required) return false
        const currentValue =
          editingValues[config.key] !== undefined ? editingValues[config.key] : String(config.value)
        return !currentValue || currentValue === '' || currentValue === '[]'
      })
      .map(config => config.title || config.key)

    setEmptyRequiredFields(emptyFields)
    if (emptyFields.length > 0) {
      setSaveWarningOpen(true)
      return false
    }
    return true
  }, [configs, editingValues])

  // 修改保存函数
  const handleSaveAllChanges = useCallback(
    async (force: boolean = false) => {
      if (!force && !checkRequiredFields()) {
        return
      }

      try {
        await configApi.batchUpdateConfig(editingValues)
        await configApi.saveConfig()
        setMessage('所有修改已保存并导出到配置文件')
        queryClient.setQueryData(['configs'], (oldData: ConfigItem[] | undefined) => {
          if (!oldData) return oldData
          return oldData.map(item =>
            editingValues[item.key] !== undefined
              ? { ...item, value: editingValues[item.key] }
              : item
          )
        })
        setEditingValues({})
        setSaveWarningOpen(false)
      } catch (error) {
        if (error instanceof Error) {
          setMessage(error.message)
        } else {
          setMessage('保存失败')
        }
      }
    },
    [
      checkRequiredFields,
      editingValues,
      queryClient,
      setEditingValues,
      setMessage,
      setSaveWarningOpen,
    ]
  )

  //监听保存快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSaveAllChanges(false) // 明确传递参数
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleSaveAllChanges])

  // 重载配置
  const handleReloadConfig = async () => {
    try {
      await configApi.reloadConfig()
      setMessage('配置已重载')
      queryClient.invalidateQueries({ queryKey: ['configs'] })
      queryClient.invalidateQueries({ queryKey: ['model-groups'] })
      setReloadConfirmOpen(false)
      // 清除编辑状态
      setEditingValues({})
    } catch (error) {
      if (error instanceof Error) {
        setMessage(error.message)
      } else {
        setMessage('重载失败')
      }
    }
  }

  // 切换密钥显示状态
  const toggleSecretVisibility = (key: string) => {
    setVisibleSecrets(prev => ({
      ...prev,
      [key]: !prev[key],
    }))
  }

  // 处理配置修改
  const handleConfigChange = (key: string, value: string) => {
    setEditingValues(prev => ({
      ...prev,
      [key]: value,
    }))
  }

  // 修改配置输入渲染函数
  const renderConfigInput = (config: ConfigItem) => {
    const isEditing = config.key in editingValues
    const displayValue = isEditing ? editingValues[config.key] : String(config.value)
    const isSecret = config.is_secret

    // 处理列表类型
    if (config.type === 'list') {
      const itemType = config.element_type || 'str'
      const currentValue = Array.isArray(config.value) ? config.value : []

      return (
        <Box sx={{ width: '100%' }}>
          <TextField
            value={displayValue}
            size="small"
            fullWidth
            sx={{
              '& .MuiInputBase-root': {
                width: '100%',
              },
            }}
            InputProps={{
              readOnly: true,
              startAdornment: (
                <InputAdornment position="start">
                  <Chip
                    label={`${itemType}[]`}
                    size="small"
                    color={getTypeColor(itemType)}
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
              value={isEditing ? JSON.parse(displayValue) : currentValue}
              onChange={newValue => handleConfigChange(config.key, JSON.stringify(newValue))}
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
      const isInvalidValue = !modelGroupNames.includes(displayValue)

      return (
        <Box sx={{ width: '100%', display: 'flex', alignItems: 'center', gap: 1 }}>
          <TextField
            select
            value={displayValue}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            sx={{ flex: 1 }}
            error={isInvalidValue}
            helperText={isInvalidValue ? '当前选择的模型组已不存在' : undefined}
            placeholder={config.placeholder}
          >
            {modelGroupNames.map(name => (
              <MenuItem key={name} value={name}>
                {name}
              </MenuItem>
            ))}
          </TextField>

          {typeOption && (
            <Chip
              label={`${typeOption.label}模型组`}
              size="small"
              color={
                (typeOption?.color as
                  | 'primary'
                  | 'secondary'
                  | 'success'
                  | 'warning'
                  | 'info'
                  | 'error'
                  | 'default') || 'primary'
              }
              variant="outlined"
              sx={{
                height: isSmall ? 20 : 24,
                fontSize: isSmall ? '0.65rem' : '0.75rem',
                '& .MuiChip-label': {
                  px: isSmall ? 0.5 : 0.75,
                },
                flexShrink: 0,
              }}
            />
          )}

          <Tooltip title="配置模型组">
            <IconButton
              size="small"
              onClick={() => navigate('/settings/model-groups')}
              sx={{ flexShrink: 0 }}
            >
              <LaunchIcon fontSize={isSmall ? 'small' : 'inherit'} />
            </IconButton>
          </Tooltip>
        </Box>
      )
    }

    // 如果是枚举类型，显示选择器
    if (config.enum) {
      return (
        <TextField
          select
          value={displayValue}
          onChange={e => handleConfigChange(config.key, e.target.value)}
          size="small"
          fullWidth
          placeholder={config.placeholder}
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
                checked={displayValue === 'true'}
                onChange={e => handleConfigChange(config.key, String(e.target.checked))}
                color="primary"
              />
            }
            label={displayValue === 'true' ? '是' : '否'}
          />
        )
      case 'int':
      case 'float':
        return (
          <TextField
            type="number"
            value={displayValue}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            fullWidth
            placeholder={config.placeholder}
            autoComplete="off"
          />
        )
      default:
        return (
          <TextField
            value={displayValue}
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
              autoComplete: 'new-password',
              form: {
                autoComplete: 'off',
              },
              style:
                isSecret && !visibleSecrets[config.key]
                  ? ({
                      '-webkit-text-security': 'disc',
                      'text-security': 'disc',
                    } as React.CSSProperties)
                  : undefined,
            }}
            InputProps={
              isSecret
                ? {
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={() => toggleSecretVisibility(config.key)} edge="end">
                          {visibleSecrets[config.key] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }
                : undefined
            }
          />
        )
    }
  }

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        p: 2,
      }}
    >
      {/* 顶部工具栏 */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          mb: 2,
          flexShrink: 0,
          flexDirection: 'row',
          gap: 1,
          alignItems: 'center',
        }}
      >
        {/* 搜索框 */}
        <TextField
          size="small"
          variant="outlined"
          placeholder="搜索配置名称或键"
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
          sx={{ flex: 1 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon color="action" />
              </InputAdornment>
            ),
          }}
        />
        <Stack direction="row" spacing={1}>
          <Tooltip title="保存修改">
            <span>
              <IconButton
                onClick={() => handleSaveAllChanges()}
                color="primary"
                disabled={Object.keys(editingValues).length === 0}
                size={isSmall ? 'small' : 'medium'}
              >
                <SaveIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="重载配置">
            <IconButton
              onClick={() => setReloadConfirmOpen(true)}
              color="primary"
              size={isSmall ? 'small' : 'medium'}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* 表格容器 */}
      <Paper
        elevation={3}
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          overflow: 'hidden',
          ...(UNIFIED_TABLE_STYLES.paper as SxProps<Theme>)
        }}
      >
        <TableContainer
          sx={{
            flex: 1,
            overflow: 'auto',
            ...(UNIFIED_TABLE_STYLES.scrollbar as SxProps<Theme>)
          }}
        >
          <Table stickyHeader size={isSmall ? 'small' : 'medium'}>
            <TableHead>
              <TableRow>
                <TableCell width={isMobile ? '40%' : '25%'} sx={{ 
                  py: isSmall ? 1 : 1.5,
                  ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>)
                }}>
                  配置项
                </TableCell>
                <TableCell width={isMobile ? '20%' : '10%'} sx={{ 
                  py: isSmall ? 1 : 1.5,
                  ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>)
                }}>
                  类型
                </TableCell>
                <TableCell width={isMobile ? '40%' : '65%'} sx={{ 
                  py: isSmall ? 1 : 1.5,
                  ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>)
                }}>
                  值
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {configs
                .filter(
                  config =>
                    !config.is_hidden &&
                    ((config.title || '').toLowerCase().includes(searchText.toLowerCase()) ||
                      config.key.toLowerCase().includes(searchText.toLowerCase()))
                )
                .map(config => (
                  <TableRow 
                    key={config.key}
                    sx={UNIFIED_TABLE_STYLES.row as SxProps<Theme>}
                  >
                    <TableCell sx={{ 
                      py: isSmall ? 0.75 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>)
                    }}>
                      <Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          <Typography
                            variant="subtitle2"
                            sx={{
                              fontWeight: 'bold',
                              fontSize: isSmall ? '0.75rem' : 'inherit',
                              mr: 0.5,
                            }}
                          >
                            {config.title || config.key}
                            {config.required && (
                              <Typography component="span" color="error" sx={{ ml: 0.5 }}>
                                *
                              </Typography>
                            )}
                          </Typography>
                          {config.description && (
                            <HtmlTooltip
                              title={
                                <div dangerouslySetInnerHTML={{ __html: config.description }} />
                              }
                              placement="right"
                            >
                              <IconButton
                                size="small"
                                sx={{ ml: 0.5, opacity: 0.6, p: isSmall ? 0.3 : 0.5 }}
                              >
                                <HelpOutlineIcon fontSize={isSmall ? 'small' : 'medium'} />
                              </IconButton>
                            </HtmlTooltip>
                          )}
                        </Box>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ fontSize: isSmall ? '0.65rem' : '0.75rem' }}
                        >
                          {config.key}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ 
                      py: isSmall ? 0.75 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>)
                    }}>
                      <Chip
                        label={config.type}
                        size="small"
                        color={getTypeColor(config.type)}
                        variant="outlined"
                        sx={{
                          height: isSmall ? 20 : 24,
                          fontSize: isSmall ? '0.65rem' : '0.75rem',
                          '& .MuiChip-label': {
                            px: isSmall ? 0.5 : 0.75,
                          },
                        }}
                      />
                    </TableCell>
                    <TableCell sx={{ 
                      py: isSmall ? 0.75 : 1.5,
                      ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>)
                    }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        {renderConfigInput(config)}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 添加重载确认对话框 */}
      <Dialog
        open={reloadConfirmOpen}
        onClose={() => setReloadConfirmOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>确认重载配置？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            重载配置将从配置文件中重新读取所有配置项，包括基本配置和模型组配置，未保存的修改将会丢失。是否继续？
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
            onClick={handleReloadConfig}
            color="primary"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            确认
          </Button>
        </DialogActions>
      </Dialog>

      {/* 添加必填项警告对话框 */}
      <Dialog
        open={saveWarningOpen}
        onClose={() => setSaveWarningOpen(false)}
        fullWidth
        maxWidth="xs"
      >
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
            onClick={() => handleSaveAllChanges(true)}
            color="warning"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            继续保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={!!message}
        autoHideDuration={3000}
        onClose={() => setMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setMessage('')}
          severity="info"
          variant="filled"
          sx={{ width: '100%' }}
        >
          {message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
