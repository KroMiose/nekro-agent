import { useState, useEffect, useCallback, useMemo, ReactNode } from 'react'
import {
  Box,
  Paper,
  TextField,
  Switch,
  FormControlLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  MenuItem,
  InputAdornment,
  Typography,
  Chip,
  Button,
  List,
  ListItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  useTheme,
  useMediaQuery,
  Stack,
  Tooltip,
  Alert,
} from '@mui/material'
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Search as SearchIcon,
  Launch as LaunchIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  InfoOutlined as InfoIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { UNIFIED_TABLE_STYLES, CHIP_VARIANTS } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'

export interface ConfigItem {
  key: string
  value: string | number | boolean | Array<string | number | boolean> | Record<string, unknown>
  title: string
  description?: string
  placeholder?: string
  type: string
  is_complex?: boolean
  element_type?: string
  key_type?: string
  value_type?: string
  field_schema?: Record<
    string,
    {
      type: string
      title: string
      description: string
      default?: unknown
      required: boolean
      is_secret?: boolean
      is_textarea?: boolean
      placeholder?: string
      is_complex?: boolean
      element_type?: string
      key_type?: string
      value_type?: string
    }
  >
  enum?: string[]
  is_secret?: boolean
  is_textarea?: boolean
  ref_model_groups?: boolean
  is_hidden?: boolean
  required?: boolean
  model_type?: string
  sub_item_name?: string
  enable_toggle?: string
  overridable?: boolean
}

export interface ModelGroupConfig {
  CHAT_MODEL: string
  CHAT_PROXY: string
  BASE_URL: string
  API_KEY: string
  MODEL_TYPE?: string
  TEMPERATURE?: number | null
  TOP_P?: number | null
  TOP_K?: number | null
  PRESENCE_PENALTY?: number | null
  FREQUENCY_PENALTY?: number | null
  EXTRA_BODY?: string | null
  ENABLE_VISION?: boolean
  ENABLE_COT?: boolean
}

export interface ModelTypeOption {
  value: string
  label: string
  description?: string
  color?: string
  icon?: string
}

export interface ConfigService {
  getConfigList: (configKey: string) => Promise<ConfigItem[]>
  getModelGroups?: () => Promise<Record<string, ModelGroupConfig>>
  getModelTypes?: () => Promise<ModelTypeOption[]>
  batchUpdateConfig: (configKey: string, configs: Record<string, string>) => Promise<void>
  saveConfig: (configKey: string) => Promise<void>
  reloadConfig: (configKey: string) => Promise<void>
}

interface ExpandedRowsState {
  [configKey: string]: boolean
}

const getTypeColor = (type: string, isComplex: boolean = false) => {
  if (isComplex) {
    switch (type) {
      case 'list':
        return 'secondary'
      case 'dict':
        return 'error'
      case 'object':
        return 'warning'
      default:
        return 'default'
    }
  }

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
    case 'dict':
      return 'primary'
    default:
      return 'default'
  }
}

export interface ConfigTableProps {
  configKey: string
  configService: ConfigService
  configs: ConfigItem[]
  loading?: boolean
  searchText?: string
  onSearchChange?: (text: string) => void
  onRefresh?: () => void
  showSearchBar?: boolean
  showToolbar?: boolean
  title?: string
  emptyMessage?: string
  infoBox?: ReactNode
  isOverridePage?: boolean
}

interface ConfirmDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  content: ReactNode
}

const ConfirmDialog = ({ open, onClose, onConfirm, title, content }: ConfirmDialogProps) => (
  <Dialog open={open} onClose={onClose}>
    <DialogTitle>{title}</DialogTitle>
    <DialogContent>{content}</DialogContent>
    <DialogActions>
      <Button onClick={onClose}>取消</Button>
      <Button onClick={onConfirm} color="primary" autoFocus>
        确认
      </Button>
    </DialogActions>
  </Dialog>
)

export default function ConfigTable({
  configKey,
  configService,
  configs,
  loading = false,
  searchText = '',
  onSearchChange,
  onRefresh,
  showSearchBar = true,
  showToolbar = true,
  title,
  emptyMessage = '暂无配置项',
  infoBox,
  isOverridePage = false,
}: ConfigTableProps) {
  const navigate = useNavigate()
  const notification = useNotification()
  const theme = useTheme()
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  const [editingValues, setEditingValues] = useState<Record<string, string>>({})
  const [visibleSecrets, setVisibleSecrets] = useState<Record<string, boolean>>({})
  const [reloadConfirmOpen, setReloadConfirmOpen] = useState(false)
  const [saveWarningOpen, setSaveWarningOpen] = useState(false)
  const [emptyRequiredFields, setEmptyRequiredFields] = useState<string[]>([])
  const [modelGroups, setModelGroups] = useState<Record<string, ModelGroupConfig>>({})
  const [modelTypes, setModelTypes] = useState<ModelTypeOption[]>([])
  const [expandedRows, setExpandedRows] = useState<ExpandedRowsState>({})

  useEffect(() => {
    const loadData = async () => {
      try {
        if (configService.getModelGroups) {
          const groups = await configService.getModelGroups()
          setModelGroups(groups)
        }
        if (configService.getModelTypes) {
          const types = await configService.getModelTypes()
          setModelTypes(types)
        }
      } catch (error) {
        console.error('加载模型数据失败:', error)
      }
    }
    loadData()
  }, [configService])

  const modelTypeMap = useMemo(
    () => Object.fromEntries(modelTypes.map(mt => [mt.value, mt])),
    [modelTypes]
  )

  const enableStateMap = useMemo(() => {
    const map = new Map<string, boolean>()
    if (!configs) {
      return map
    }
    configs.forEach(config => {
      if (config.key.startsWith('enable_')) {
        const currentValue = editingValues[config.key]
        try {
          const value = currentValue !== undefined ? JSON.parse(currentValue) : config.value
          map.set(config.key, value as boolean)
        } catch {
          map.set(config.key, config.value as boolean)
        }
      }
    })
    return map
  }, [configs, editingValues])

  const checkRequiredFields = useCallback(() => {
    const emptyFields = configs
      .filter(config => {
        if (!config.required) return false
        if (isOverridePage && config.enable_toggle && !enableStateMap.get(config.enable_toggle)) {
          return false
        }
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
  }, [configs, editingValues, isOverridePage, enableStateMap])

  const handleSaveAllChanges = useCallback(
    async (force: boolean = false) => {
      if (!force && !checkRequiredFields()) {
        return
      }
      try {
        await configService.batchUpdateConfig(configKey, editingValues)
        await configService.saveConfig(configKey)
        notification.success('所有修改已保存并导出到配置文件')
        setEditingValues({})
        setSaveWarningOpen(false)
        onRefresh?.()
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '保存失败'
        notification.error(errorMessage)
      }
    },
    [checkRequiredFields, editingValues, configService, configKey, notification, onRefresh]
  )

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSaveAllChanges(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleSaveAllChanges])

  const handleReloadConfig = async () => {
    try {
      await configService.reloadConfig(configKey)
      notification.success('配置已重载')
      setReloadConfirmOpen(false)
      setEditingValues({})
      onRefresh?.()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '重载失败'
      notification.error(errorMessage)
    }
  }

  const toggleSecretVisibility = (key: string) => {
    setVisibleSecrets(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleConfigChange = (key: string, value: string) => {
    setEditingValues(prev => ({ ...prev, [key]: value }))
  }

  const filteredConfigs = useMemo(() => {
    if (!configs) {
      return []
    }

    let processedConfigs = configs.filter(config => !config.is_hidden)

    if (isOverridePage) {
      processedConfigs = processedConfigs.filter(config => !config.key.startsWith('enable_'))
    } else {
      processedConfigs = processedConfigs.filter(config => {
        if (config.enable_toggle && enableStateMap.get(config.enable_toggle) === false) {
          return false
        }
        return true
      })
    }

    if (searchText) {
      const lowerSearchText = searchText.toLowerCase()
      return processedConfigs.filter(
        config =>
          config.title.toLowerCase().includes(lowerSearchText) ||
          config.key.toLowerCase().includes(lowerSearchText) ||
          (config.description && config.description.toLowerCase().includes(lowerSearchText))
      )
    }

    return processedConfigs
  }, [configs, searchText, isOverridePage, enableStateMap])

  useEffect(() => {
    if (configs) {
      const initialValues: Record<string, string> = {}
      configs.forEach(config => {
        const value =
          typeof config.value === 'object' && config.value !== null
            ? JSON.stringify(config.value, null, 2)
            : String(config.value)
        initialValues[config.key] = value
      })
      setEditingValues(initialValues)
    }
  }, [configs])

  const renderConfigInput = (config: ConfigItem, disabled: boolean = false) => {
    const isEditing = Object.prototype.hasOwnProperty.call(editingValues, config.key)
    const rawValue = isEditing ? editingValues[config.key] : String(config.value)
    const isSecret = config.is_secret

    if (config.ref_model_groups) {
      const typeOption = modelTypeMap[config.model_type as string]
      let entries = Object.entries(modelGroups)
      if (typeOption) {
        entries = entries.filter(([, group]) => group.MODEL_TYPE === typeOption.value)
      }
      const modelGroupNames = entries.map(([name]) => name)
      const isInvalidValue = !modelGroupNames.includes(rawValue)

      return (
        <Box sx={{ width: '100%', display: 'flex', alignItems: 'center', gap: 1 }}>
          <TextField
            select
            value={rawValue}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            sx={{ flex: 1 }}
            error={isInvalidValue}
            helperText={isInvalidValue ? '当前选择的模型组已不存在' : undefined}
            placeholder={config.placeholder}
            disabled={disabled}
          >
            {modelGroupNames.map(name => (
              <MenuItem key={name} value={name}>
                {name}
              </MenuItem>
            ))}
          </TextField>
          {typeOption && (
            <Button
              variant="outlined"
              color={
                (['primary', 'secondary', 'success', 'warning', 'info', 'error'].includes(
                  typeOption?.color || ''
                )
                  ? typeOption?.color
                  : 'info') as 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error'
              }
              size="small"
              endIcon={<LaunchIcon fontSize={isSmall ? 'small' : 'inherit'} />}
              onClick={() => navigate('/settings/model-groups')}
              sx={{
                flexShrink: 0,
                borderRadius: 999,
                fontWeight: 600,
                px: isSmall ? 1 : 1.5,
                py: isSmall ? 0.1 : 0.4,
                minWidth: 'auto',
                height: isSmall ? 24 : 28,
                fontSize: isSmall ? '0.68rem' : '0.8rem',
              }}
              aria-label="跳转到模型组配置页面"
              disabled={disabled}
            >
              {`${typeOption.label}模型组`}
            </Button>
          )}
        </Box>
      )
    }

    if (config.enum) {
      return (
        <TextField
          select
          value={rawValue}
          onChange={e => handleConfigChange(config.key, e.target.value)}
          size="small"
          fullWidth
          placeholder={config.placeholder}
          disabled={disabled}
        >
          {config.enum.map(option => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </TextField>
      )
    }

    if (
      config.type === 'list' ||
      config.is_complex ||
      (config.type === 'dict' && !config.is_complex)
    ) {
      const isExpanded = expandedRows[config.key] || false
      let displayValue: string
      try {
        const parsedValue = isEditing ? JSON.parse(rawValue) : config.value
        if (config.type === 'list') {
          displayValue = `列表 (${(Array.isArray(parsedValue) ? parsedValue : []).length} 项)`
        } else {
          displayValue = `对象 (${
            Object.keys(typeof parsedValue === 'object' && parsedValue ? parsedValue : {}).length
          } 项)`
        }
      } catch {
        displayValue = '无效的JSON'
      }

      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
          <TextField
            value={isExpanded ? rawValue : displayValue}
            size="small"
            fullWidth
            multiline={isExpanded}
            rows={isExpanded ? Math.min(15, rawValue.split('\n').length) : 1}
            onClick={() =>
              !disabled && !isExpanded && setExpandedRows(prev => ({ ...prev, [config.key]: true }))
            }
            onChange={e => handleConfigChange(config.key, e.target.value)}
            InputProps={{
              readOnly: !isExpanded,
              sx: { cursor: isExpanded ? 'text' : 'pointer' },
            }}
            disabled={disabled}
          />
          <IconButton
            size="small"
            onClick={() => setExpandedRows(prev => ({ ...prev, [config.key]: !prev[config.key] }))}
            disabled={disabled}
          >
            {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      )
    }

    switch (config.type) {
      case 'bool':
        return (
          <FormControlLabel
            control={
              <Switch
                checked={rawValue === 'true'}
                onChange={e => handleConfigChange(config.key, String(e.target.checked))}
                color="primary"
                disabled={disabled}
              />
            }
            label={rawValue === 'true' ? '是' : '否'}
            disabled={disabled}
          />
        )
      case 'int':
      case 'float':
        return (
          <TextField
            type="number"
            value={rawValue}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            fullWidth
            placeholder={config.placeholder}
            disabled={disabled}
          />
        )
      default:
        return (
          <TextField
            value={rawValue}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            fullWidth
            type="text"
            placeholder={config.placeholder}
            multiline={config.is_textarea}
            minRows={config.is_textarea ? 3 : 1}
            maxRows={config.is_textarea ? 8 : 1}
            disabled={disabled}
            InputProps={{
              style:
                isSecret && !visibleSecrets[config.key]
                  ? ({
                      '-webkit-text-security': 'disc',
                      'text-security': 'disc',
                    } as React.CSSProperties)
                  : undefined,
              endAdornment: isSecret ? (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => toggleSecretVisibility(config.key)}
                    edge="end"
                    disabled={disabled}
                  >
                    {visibleSecrets[config.key] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </InputAdornment>
              ) : undefined,
            }}
          />
        )
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Stack direction="column" spacing={2} sx={{ flexShrink: 0 }}>
        {title && (
          <Typography variant="h5" component="h2" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
        )}
        {infoBox && <Alert severity="info">{infoBox}</Alert>}
        {showToolbar && (
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} justifyContent="space-between">
            {showSearchBar && (
              <TextField
                size="small"
                sx={{ flexGrow: 1 }}
                placeholder="搜索配置项 (名称/关键字/描述)"
                value={searchText}
                onChange={e => onSearchChange?.(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
              />
            )}
            <Stack direction="row" spacing={1} sx={{ flexShrink: 0 }}>
              <Button
                variant="contained"
                color="primary"
                size="small"
                onClick={() => handleSaveAllChanges(false)}
                startIcon={<SaveIcon />}
                disabled={Object.keys(editingValues).length === 0}
              >
                保存更改
              </Button>
              <Button
                variant="outlined"
                color="secondary"
                size="small"
                onClick={() => setReloadConfirmOpen(true)}
                startIcon={<RefreshIcon />}
              >
                重载配置
              </Button>
            </Stack>
          </Stack>
        )}
      </Stack>

      <Paper
        elevation={3}
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          overflow: 'hidden',
          ...UNIFIED_TABLE_STYLES.paper,
        }}
      >
        <TableContainer sx={{ flex: 1, overflow: 'auto', ...UNIFIED_TABLE_STYLES.scrollbar }}>
          <Table stickyHeader size={isSmall ? 'small' : 'medium'}>
            <TableHead>
              <TableRow sx={UNIFIED_TABLE_STYLES.header}>
                {isOverridePage && (
                  <TableCell sx={{ width: '10%', minWidth: 80 }}>启用覆盖</TableCell>
                )}
                <TableCell sx={{ width: '20%', minWidth: 200 }}>配置项</TableCell>
                <TableCell sx={{ width: '5%', minWidth: 80 }}>属性</TableCell>
                <TableCell sx={{ width: '5%', minWidth: 80 }}>类型</TableCell>
                <TableCell sx={{ width: '50%', minWidth: 300 }}>值</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredConfigs.map(config => {
                const isEnabled =
                  isOverridePage && config.enable_toggle
                    ? (enableStateMap.get(config.enable_toggle) ?? false)
                    : true

                return (
                  <TableRow
                    key={config.key}
                    sx={{
                      ...UNIFIED_TABLE_STYLES.row,
                      transition: 'opacity 0.2s, background-color 0.2s',
                      ...(!isEnabled &&
                        isOverridePage && {
                          opacity: 0.6,
                          '&:hover': {
                            bgcolor: 'transparent',
                          },
                        }),
                    }}
                  >
                    {isOverridePage && (
                      <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
                        {config.enable_toggle ? (
                          <Switch
                            checked={isEnabled}
                            onChange={e =>
                              handleConfigChange(
                                config.enable_toggle as string,
                                String(e.target.checked)
                              )
                            }
                            color="primary"
                            size="small"
                          />
                        ) : (
                          <Tooltip title="此配置项不支持单独禁用" arrow>
                            <Box sx={{ textAlign: 'center' }}>-</Box>
                          </Tooltip>
                        )}
                      </TableCell>
                    )}
                    <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
                      <Stack spacing={0.5}>
                        <Box
                          sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5 }}
                        >
                          {config.required && (
                            <Typography component="span" color="error" sx={{ fontWeight: 'bold' }}>
                              *
                            </Typography>
                          )}
                          <Typography
                            variant="body2"
                            sx={{ fontWeight: 600, color: 'text.primary' }}
                          >
                            {config.title}
                          </Typography>
                          {config.description && (
                            <Tooltip title={config.description} arrow>
                              <InfoIcon
                                sx={{
                                  fontSize: '1rem',
                                  color: 'text.secondary',
                                  verticalAlign: 'middle',
                                  cursor: 'help',
                                }}
                              />
                            </Tooltip>
                          )}
                        </Box>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ fontFamily: 'monospace' }}
                        >
                          {config.key}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
                      <Stack spacing={1} direction="row" alignItems="center">
                        {config.overridable && configKey === 'system' && (
                          <Chip
                            label="可覆盖"
                            size="small"
                            color="info"
                            variant="outlined"
                            sx={{ ...CHIP_VARIANTS.base(isSmall) }}
                          />
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
                      <Chip
                        label={config.type}
                        size="small"
                        color={getTypeColor(config.type, config.is_complex)}
                        variant="outlined"
                        sx={CHIP_VARIANTS.base(isSmall)}
                      />
                    </TableCell>
                    <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
                      {renderConfigInput(config, isOverridePage ? !isEnabled : false)}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>
        {filteredConfigs.length === 0 && (
          <Box
            sx={{
              p: 4,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              height: '100%',
            }}
          >
            <Typography variant="body1" color="textSecondary">
              {emptyMessage}
            </Typography>
          </Box>
        )}
      </Paper>
      <ConfirmDialog
        open={reloadConfirmOpen}
        onClose={() => setReloadConfirmOpen(false)}
        title="确认重载配置"
        content="重载配置将丢失所有未保存的修改，是否继续？"
        onConfirm={handleReloadConfig}
      />
      <ConfirmDialog
        open={saveWarningOpen}
        onClose={() => setSaveWarningOpen(false)}
        title="保存警告"
        content={
          <Box>
            <Typography sx={{ mb: 1 }}>
              {emptyRequiredFields.length > 0
                ? '以下必填项未填写，是否仍要继续保存？'
                : '是否仍要继续保存？'}
            </Typography>
            {emptyRequiredFields.length > 0 && (
              <List dense>
                {emptyRequiredFields.map((field, index) => (
                  <ListItem key={index} sx={{ py: 0 }}>
                    <Typography color="error">• {field}</Typography>
                  </ListItem>
                ))}
              </List>
            )}
          </Box>
        }
        onConfirm={() => handleSaveAllChanges(true)}
      />
    </Box>
  )
}
