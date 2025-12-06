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
<<<<<<< HEAD
  Avatar,
=======
<<<<<<< HEAD
  Avatar,
=======
<<<<<<< HEAD
  Avatar,
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
  SxProps,
  Theme,
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
  Add as AddIcon,
  Delete as DeleteIcon,
  HelpOutline as HelpOutlineIcon,
<<<<<<< HEAD
  RestartAlt as RestartIcon,
=======
<<<<<<< HEAD
  RestartAlt as RestartIcon,
=======
<<<<<<< HEAD
  RestartAlt as RestartIcon,
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { UNIFIED_TABLE_STYLES, CHIP_VARIANTS } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'
<<<<<<< HEAD
import { restartApi } from '../../services/api/restart'
import { ThemedTooltip } from './ThemedTooltip'
import { presetsApi, Preset } from '../../services/api/presets'
=======
<<<<<<< HEAD
import { restartApi } from '../../services/api/restart'
import { ThemedTooltip } from './ThemedTooltip'
import { presetsApi, Preset } from '../../services/api/presets'
=======
<<<<<<< HEAD
import { restartApi } from '../../services/api/restart'
import { ThemedTooltip } from './ThemedTooltip'
import { presetsApi, Preset } from '../../services/api/presets'
=======
import { ThemedTooltip } from './ThemedTooltip'
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

const HtmlTooltip = ThemedTooltip

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
<<<<<<< HEAD
      is_need_restart?: boolean
=======
<<<<<<< HEAD
      is_need_restart?: boolean
=======
<<<<<<< HEAD
      is_need_restart?: boolean
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
    }
  >
  enum?: string[]
  is_secret?: boolean
  is_textarea?: boolean
  ref_model_groups?: boolean
<<<<<<< HEAD
  ref_presets?: boolean
  ref_presets_multiple?: boolean
=======
<<<<<<< HEAD
  ref_presets?: boolean
  ref_presets_multiple?: boolean
=======
<<<<<<< HEAD
  ref_presets?: boolean
  ref_presets_multiple?: boolean
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  is_hidden?: boolean
  required?: boolean
  model_type?: string
  sub_item_name?: string
  enable_toggle?: string
  overridable?: boolean
<<<<<<< HEAD
  is_need_restart?: boolean
=======
<<<<<<< HEAD
  is_need_restart?: boolean
=======
<<<<<<< HEAD
  is_need_restart?: boolean
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
    case 'preset':
      return 'secondary'
    case 'presets':
      return 'secondary'
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
    default:
      return 'default'
  }
}

function renderSimpleListInput(
  value: unknown,
  elementType: string,
  onChange: (value: unknown) => void
): React.ReactNode {
  switch (elementType) {
    case 'bool':
      return (
        <FormControlLabel
          control={
            <Switch
              checked={Boolean(value)}
              onChange={e => onChange(e.target.checked)}
              size="small"
              color="primary"
            />
          }
          label={value ? '是' : '否'}
        />
      )
    case 'int':
    case 'float':
      return (
        <TextField
          type="number"
          value={value || ''}
          onChange={e =>
            onChange(
              elementType === 'int'
                ? parseInt(e.target.value, 10) || 0
                : parseFloat(e.target.value) || 0
            )
          }
          size="small"
          fullWidth
          variant="outlined"
        />
      )
    default:
      return (
        <TextField
          value={String(value || '')}
          onChange={e => onChange(e.target.value)}
          size="small"
          fullWidth
          variant="outlined"
        />
      )
  }
}

function renderFieldInput(
  value: unknown,
  fieldSchema: {
    type: string
    is_secret?: boolean
    is_textarea?: boolean
    placeholder?: string
    is_complex?: boolean
    element_type?: string
  },
  onChange: (value: unknown) => void,
  fieldKey?: string,
  expandedRows?: ExpandedRowsState,
  setExpandedRows?: React.Dispatch<React.SetStateAction<ExpandedRowsState>>
): React.ReactNode {
  switch (fieldSchema.type) {
    case 'bool':
    case 'boolean':
      return (
        <FormControlLabel
          control={
            <Switch
              checked={Boolean(value)}
              onChange={e => onChange(e.target.checked)}
              size="small"
              color="primary"
            />
          }
          label={value ? '是' : '否'}
        />
      )
    case 'int':
    case 'float':
    case 'number':
      return (
        <TextField
          type="number"
          value={value || ''}
          onChange={e =>
            onChange(
              fieldSchema.type === 'int'
                ? parseInt(e.target.value, 10) || 0
                : parseFloat(e.target.value) || 0
            )
          }
          size="small"
          fullWidth
          placeholder={fieldSchema.placeholder}
          variant="outlined"
        />
      )
    case 'list': {
      if (fieldKey && expandedRows && setExpandedRows) {
        const listValue = Array.isArray(value) ? value : []
        const isExpanded = expandedRows[fieldKey] || false

        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
            <TextField
              value={`列表 (${listValue.length} 项)`}
              size="small"
              fullWidth
              InputProps={{
                readOnly: true,
                sx: {
                  cursor: 'pointer',
                  bgcolor: 'transparent',
                  '&:hover': {
                    bgcolor: 'action.hover',
                  },
                },
              }}
              onClick={() => setExpandedRows(prev => ({ ...prev, [fieldKey]: !prev[fieldKey] }))}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'primary.main',
                  },
                },
              }}
            />
            <IconButton
              size="small"
              onClick={() => setExpandedRows(prev => ({ ...prev, [fieldKey]: !prev[fieldKey] }))}
              sx={{
                flexShrink: 0,
                color: 'text.secondary',
                '&:hover': {
                  bgcolor: 'action.hover',
                  color: 'primary.main',
                },
              }}
            >
              {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        )
      }

      const listValue = Array.isArray(value) ? value : []
      return (
        <TextField
          value={`列表 (${listValue.length} 项)`}
          size="small"
          fullWidth
          InputProps={{ readOnly: true }}
          variant="outlined"
        />
      )
    }
    default:
      return (
        <TextField
          type="text"
          value={String(value || '')}
          onChange={e => onChange(e.target.value)}
          size="small"
          fullWidth
          placeholder={fieldSchema.placeholder}
          variant="outlined"
          multiline={fieldSchema.is_textarea}
          minRows={fieldSchema.is_textarea ? 2 : 1}
          maxRows={fieldSchema.is_textarea ? 4 : 1}
          InputProps={{
            style: fieldSchema.is_secret
              ? ({
                  '-webkit-text-security': 'disc',
                  'text-security': 'disc',
                } as React.CSSProperties)
              : undefined,
          }}
        />
      )
  }
}

function getDefaultValueForType(type: string): unknown {
  switch (type) {
    case 'bool':
    case 'boolean':
      return false
    case 'int':
    case 'float':
    case 'number':
      return 0
    case 'list':
      return []
    case 'dict':
      return {}
    default:
      return ''
  }
}

function renderNestedConfigRows(
  config: ConfigItem,
  editingValues: Record<string, string>,
  handleConfigChange: (key: string, value: string) => void,
  isOverridePage: boolean,
  isSmall: boolean,
  expandedRows: ExpandedRowsState,
  setExpandedRows: React.Dispatch<React.SetStateAction<ExpandedRowsState>>,
  level: number = 0,
  parentKey: string = ''
): React.ReactNode[] {
  const rows: React.ReactNode[] = []
  let currentValue
  try {
    currentValue =
      editingValues[config.key] !== undefined
        ? JSON.parse(editingValues[config.key])
        : config.value
  } catch {
    currentValue = config.value
  }

  const tableCellStyle: SxProps<Theme> = {
    py: isSmall ? 0.75 : 1.5,
    pl: 2 + level * 2,
    borderLeft: level > 0 ? `2px solid` : 'none',
    borderLeftColor: level > 0 ? 'divider' : 'transparent',
  }

  if (config.type === 'list' && !config.is_complex) {
    const listValue = Array.isArray(currentValue) ? currentValue : []
    const elementType = config.element_type || 'str'

    listValue.forEach((item: unknown, index: number) => {
      const subKey = `${parentKey}${config.key}[${index}]`
      rows.push(
        <TableRow key={subKey} sx={{ ...UNIFIED_TABLE_STYLES.nestedRow }}>
          {isOverridePage && <TableCell sx={tableCellStyle} />}
          <TableCell sx={tableCellStyle}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" sx={{ fontSize: isSmall ? '0.75rem' : 'inherit' }}>
                {config.sub_item_name ? `${config.sub_item_name}[${index}]` : `[${index}]`}
              </Typography>
              <IconButton
                size="small"
                onClick={() => {
                  const newList = listValue.filter((_, i) => i !== index)
                  handleConfigChange(config.key, JSON.stringify(newList))
                }}
                sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' } }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          </TableCell>
          <TableCell />
          <TableCell>
            <Chip
              label={elementType}
              size="small"
              color={getTypeColor(elementType)}
              variant="outlined"
              sx={CHIP_VARIANTS.base(isSmall)}
            />
          </TableCell>
          <TableCell>
            {renderSimpleListInput(item, elementType, newValue => {
              const newList = [...listValue]
              newList[index] = newValue
              handleConfigChange(config.key, JSON.stringify(newList))
            })}
          </TableCell>
        </TableRow>
      )
    })
    rows.push(
      <TableRow key={`${config.key}-add`} sx={{ ...UNIFIED_TABLE_STYLES.nestedRow }}>
        <TableCell sx={tableCellStyle} colSpan={isOverridePage ? 5 : 4}>
          <Button
            variant="text"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => {
              const defaultValue = getDefaultValueForType(elementType)
              const newList = [...listValue, defaultValue]
              handleConfigChange(config.key, JSON.stringify(newList))
            }}
            sx={{ color: 'primary.main' }}
          >
            添加{config.sub_item_name || '项目'}
          </Button>
        </TableCell>
      </TableRow>
    )
  }

  if (config.is_complex) {
    if (config.type === 'list') {
      const listValue = Array.isArray(currentValue) ? currentValue : []
      listValue.forEach((item: unknown, index: number) => {
        rows.push(
          <TableRow
            key={`${config.key}[${index}]-header`}
            sx={{ ...UNIFIED_TABLE_STYLES.nestedRow }}
          >
            <TableCell sx={tableCellStyle} colSpan={isOverridePage ? 5 : 4}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: 'bold',
                    fontSize: isSmall ? '0.75rem' : 'inherit',
                  }}
                >
                  {config.sub_item_name || '项目'} [{index}]
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => {
                    const newList = listValue.filter((_, i) => i !== index)
                    handleConfigChange(config.key, JSON.stringify(newList))
                  }}
                  sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' } }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            </TableCell>
          </TableRow>
        )
        if (item && typeof item === 'object' && config.field_schema) {
          Object.entries(config.field_schema).forEach(([fieldName, fieldSchema]) => {
            const fieldValue = (item as Record<string, unknown>)[fieldName]
            const subKey = `${parentKey}${config.key}[${index}].${fieldName}`
            rows.push(
              <TableRow key={subKey} sx={{ ...UNIFIED_TABLE_STYLES.nestedRow }}>
                {isOverridePage && <TableCell sx={{ ...tableCellStyle, pl: 4 + level * 2 }} />}
                <TableCell sx={{ ...tableCellStyle, pl: 4 + level * 2 }}>
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 'normal',
                          fontSize: isSmall ? '0.75rem' : 'inherit',
                          mr: 0.5,
                        }}
                      >
                        {fieldSchema.title || fieldName}
                      </Typography>
                      {fieldSchema.description && (
                        <HtmlTooltip
                          title={
                            <div dangerouslySetInnerHTML={{ __html: fieldSchema.description }} />
                          }
                          placement="right"
                        >
                          <IconButton
                            size="small"
                            sx={{
                              ml: 0.5,
                              p: isSmall ? 0.2 : 0.3,
                              color: 'primary.main',
                              '&:hover': {
                                color: 'primary.dark',
                                bgcolor: 'action.hover',
                              },
                            }}
                          >
                            <HelpOutlineIcon fontSize="inherit" />
                          </IconButton>
                        </HtmlTooltip>
                      )}
                    </Box>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        fontSize: isSmall ? '0.65rem' : '0.75rem',
                      }}
                    >
                      {fieldName}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell />
                <TableCell>
                  <Chip
                    label={fieldSchema.type}
                    size="small"
                    color={getTypeColor(fieldSchema.type)}
                    variant="outlined"
                    sx={CHIP_VARIANTS.base(isSmall)}
                  />
                </TableCell>
                <TableCell>
                  {renderFieldInput(
                    fieldValue,
                    fieldSchema,
                    newValue => {
                      const newList = [...listValue]
                      const newItem = { ...(newList[index] as Record<string, unknown>) }
                      newItem[fieldName] = newValue
                      newList[index] = newItem
                      handleConfigChange(config.key, JSON.stringify(newList))
                    },
                    subKey,
                    expandedRows,
                    setExpandedRows
                  )}
                </TableCell>
              </TableRow>
            )
            if (fieldSchema.type === 'list' && expandedRows?.[subKey]) {
              const fieldListValue = Array.isArray(fieldValue) ? fieldValue : []
              const fieldElementType = fieldSchema.element_type || 'str'
              fieldListValue.forEach((listItem: unknown, listIndex: number) => {
                const listItemKey = `${subKey}[${listIndex}]`
                rows.push(
                  <TableRow key={listItemKey} sx={{ ...UNIFIED_TABLE_STYLES.nestedRow }}>
                    {isOverridePage && <TableCell sx={{ ...tableCellStyle, pl: 6 + level * 2 }} />}
                    <TableCell sx={{ ...tableCellStyle, pl: 6 + level * 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography
                          variant="body2"
                          sx={{ fontSize: isSmall ? '0.75rem' : 'inherit' }}
                        >
                          {fieldSchema.title || fieldName}[{listIndex}]
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => {
                            const newFieldList = fieldListValue.filter((_, i) => i !== listIndex)
                            const newList = [...listValue]
                            const newItem = { ...(newList[index] as Record<string, unknown>) }
                            newItem[fieldName] = newFieldList
                            newList[index] = newItem
                            handleConfigChange(config.key, JSON.stringify(newList))
                          }}
                          sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' } }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    </TableCell>
                    <TableCell />
                    <TableCell>
                      <Chip
                        label={fieldElementType}
                        size="small"
                        color={getTypeColor(fieldElementType)}
                        variant="outlined"
                        sx={CHIP_VARIANTS.base(isSmall)}
                      />
                    </TableCell>
                    <TableCell>
                      {renderSimpleListInput(listItem, fieldElementType, newValue => {
                        const newFieldList = [...fieldListValue]
                        newFieldList[listIndex] = newValue
                        const newList = [...listValue]
                        const newItem = { ...(newList[index] as Record<string, unknown>) }
                        newItem[fieldName] = newFieldList
                        newList[index] = newItem
                        handleConfigChange(config.key, JSON.stringify(newList))
                      })}
                    </TableCell>
                  </TableRow>
                )
              })
              rows.push(
                <TableRow key={`${subKey}-add`} sx={{ ...UNIFIED_TABLE_STYLES.nestedRow }}>
                  <TableCell
                    sx={{ ...tableCellStyle, pl: 6 + level * 2 }}
                    colSpan={isOverridePage ? 5 : 4}
                  >
                    <Button
                      variant="text"
                      size="small"
                      startIcon={<AddIcon />}
                      onClick={() => {
                        const defaultValue = getDefaultValueForType(fieldElementType)
                        const newFieldList = [...fieldListValue, defaultValue]
                        const newList = [...listValue]
                        const newItem = { ...(newList[index] as Record<string, unknown>) }
                        newItem[fieldName] = newFieldList
                        newList[index] = newItem
                        handleConfigChange(config.key, JSON.stringify(newList))
                      }}
                      sx={{ color: 'primary.main' }}
                    >
                      添加{fieldSchema.title || fieldName}项目
                    </Button>
                  </TableCell>
                </TableRow>
              )
            }
          })
        }
      })
      rows.push(
        <TableRow key={`${config.key}-add-complex`} sx={{ ...UNIFIED_TABLE_STYLES.nestedRow }}>
          <TableCell sx={tableCellStyle} colSpan={isOverridePage ? 5 : 4}>
            <Button
              variant="text"
              size="small"
              startIcon={<AddIcon />}
              onClick={() => {
                const newItem: Record<string, unknown> = {}
                if (config.field_schema) {
                  Object.entries(config.field_schema).forEach(([fieldName, fieldSchema]) => {
                    newItem[fieldName] =
                      fieldSchema.default ?? getDefaultValueForType(fieldSchema.type)
                  })
                }
                const newList = [...listValue, newItem]
                handleConfigChange(config.key, JSON.stringify(newList))
              }}
              sx={{ color: 'primary.main' }}
            >
              添加新{config.sub_item_name || '项目'}
            </Button>
          </TableCell>
        </TableRow>
      )
    }
  }

  if (config.type === 'dict' && !config.is_complex) {
    const dictValue =
      currentValue && typeof currentValue === 'object'
        ? (currentValue as Record<string, unknown>)
        : {}
    const valueType = config.value_type || 'str'
    Object.entries(dictValue).forEach(([key, value]) => {
      rows.push(
        <TableRow key={`${config.key}.${key}`} sx={{ ...UNIFIED_TABLE_STYLES.nestedRow }}>
          {isOverridePage && <TableCell sx={tableCellStyle} />}
          <TableCell sx={tableCellStyle}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" sx={{ fontSize: isSmall ? '0.75rem' : 'inherit' }}>
                {key}
              </Typography>
              <IconButton
                size="small"
                onClick={() => {
                  const newDict = { ...dictValue }
                  delete newDict[key]
                  handleConfigChange(config.key, JSON.stringify(newDict))
                }}
                sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' } }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          </TableCell>
          <TableCell />
          <TableCell>
            <Chip
              label={valueType}
              size="small"
              color={getTypeColor(valueType)}
              variant="outlined"
              sx={CHIP_VARIANTS.base(isSmall)}
            />
          </TableCell>
          <TableCell>
            {renderSimpleListInput(value, valueType, newValue => {
              const newDict = { ...dictValue, [key]: newValue }
              handleConfigChange(config.key, JSON.stringify(newDict))
            })}
          </TableCell>
        </TableRow>
      )
    })
    rows.push(
      <TableRow key={`${config.key}-add-dict`} sx={{ ...UNIFIED_TABLE_STYLES.nestedRow }}>
        <TableCell sx={tableCellStyle} colSpan={isOverridePage ? 5 : 4}>
          <TextField
            size="small"
            placeholder="输入新键名，按回车添加"
            variant="outlined"
            onKeyPress={e => {
              if (e.key === 'Enter') {
                const target = e.target as HTMLInputElement
                const newKey = target.value.trim()
                if (newKey && !dictValue[newKey]) {
                  const defaultValue = getDefaultValueForType(valueType)
                  const newDict = { ...dictValue, [newKey]: defaultValue }
                  handleConfigChange(config.key, JSON.stringify(newDict))
                  target.value = ''
                }
              }
            }}
            sx={{ width: '200px' }}
          />
        </TableCell>
      </TableRow>
    )
  }
  return rows
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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
  disabled?: boolean
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
  disabled = false,
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
}: ConfigTableProps) {
  const navigate = useNavigate()
  const notification = useNotification()
  const theme = useTheme()
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  const [editingValues, setEditingValues] = useState<Record<string, string>>({})
  const [dirtyKeys, setDirtyKeys] = useState<Set<string>>(new Set())
  const [visibleSecrets, setVisibleSecrets] = useState<Record<string, boolean>>({})
  const [reloadConfirmOpen, setReloadConfirmOpen] = useState(false)
  const [saveWarningOpen, setSaveWarningOpen] = useState(false)
  const [emptyRequiredFields, setEmptyRequiredFields] = useState<string[]>([])
  const [modelGroups, setModelGroups] = useState<Record<string, ModelGroupConfig>>({})
  const [modelTypes, setModelTypes] = useState<ModelTypeOption[]>([])
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  const [presets, setPresets] = useState<Preset[]>([])
  const [expandedRows, setExpandedRows] = useState<ExpandedRowsState>({})
  const [restartDialogOpen, setRestartDialogOpen] = useState(false)
  const [isRestarting, setIsRestarting] = useState(false)
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
  const [expandedRows, setExpandedRows] = useState<ExpandedRowsState>({})
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
        
        // 加载人设数据
        const presetsResponse = await presetsApi.getList({
          page: 1,
          page_size: 1000, // 加载所有人设
        })
        setPresets(presetsResponse.items)
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  const presetMap = useMemo(
    () => Object.fromEntries(presets.map(preset => [preset.id.toString(), preset])),
    [presets]
  )

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
        const changedConfigs = Object.fromEntries(
          Array.from(dirtyKeys).map(key => [key, editingValues[key]])
        )
        await configService.batchUpdateConfig(configKey, changedConfigs)
        await configService.saveConfig(configKey)
        notification.success('所有修改已保存并导出到配置文件')
        setDirtyKeys(new Set())
        setSaveWarningOpen(false)
        onRefresh?.()
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

        // 检查是否有需要重启的配置项
        const needRestartConfigs = configs.filter(config => {
          if (!dirtyKeys.has(config.key)) return false
          
          // 首先检查配置项本身的 is_need_restart 属性
          if (config.is_need_restart === true) {
            return true
          }
          
          // 然后检查字段模式中的 is_need_restart 属性
          const fieldInfo = config.field_schema?.[config.key]
          if (fieldInfo && fieldInfo.is_need_restart === true) {
            return true
          }
          
          return false
        })

        if (needRestartConfigs.length > 0) {
          setRestartDialogOpen(true)
        }
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '保存失败'
        notification.error(errorMessage)
      }
    },
<<<<<<< HEAD
    [checkRequiredFields, editingValues, dirtyKeys, configService, configKey, notification, onRefresh, configs]
=======
<<<<<<< HEAD
    [checkRequiredFields, editingValues, dirtyKeys, configService, configKey, notification, onRefresh, configs]
=======
<<<<<<< HEAD
    [checkRequiredFields, editingValues, dirtyKeys, configService, configKey, notification, onRefresh, configs]
=======
    [checkRequiredFields, editingValues, dirtyKeys, configService, configKey, notification, onRefresh]
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
      setDirtyKeys(new Set())
      onRefresh?.()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '重载失败'
      notification.error(errorMessage)
    }
  }

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  // 处理重启系统
  const handleRestartSystem = async () => {
    setIsRestarting(true)
    try {
      const response = await restartApi.restartSystem()
      if (response.code === 200) {
        notification.success('系统重启请求已发送，请稍候...')
        setRestartDialogOpen(false)
      } else {
        notification.error(response.msg || '重启失败')
      }
    } catch (error) {
      console.error('重启系统失败:', error)
      notification.error('重启系统失败，请检查网络连接')
    } finally {
      setIsRestarting(false)
    }
  }

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  const toggleSecretVisibility = (key: string) => {
    setVisibleSecrets(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleConfigChange = (key: string, value: string) => {
    setEditingValues(prev => ({ ...prev, [key]: value }))
    setDirtyKeys(prev => new Set(prev).add(key))
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
      configs
        .filter(c => !c.is_hidden)
        .forEach(config => {
          const value =
            typeof config.value === 'object' && config.value !== null
              ? JSON.stringify(config.value, null, 2)
              : String(config.value)
          initialValues[config.key] = value
        })
      setEditingValues(initialValues)
      setDirtyKeys(new Set())
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

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
    if (config.ref_presets_multiple) {
      // 多人设选择器，rawValue 应该是 JSON 数组字符串
      let selectedIds: number[] = []
      try {
        const parsed = JSON.parse(rawValue || '[]')
        selectedIds = Array.isArray(parsed) ? parsed : []
      } catch {
        selectedIds = []
      }

      return (
        <Box sx={{ width: '100%', display: 'flex', alignItems: 'center', gap: 1 }}>
          <TextField
            select
            value={selectedIds}
            onChange={e => {
              const value = e.target.value as unknown as number[]
              handleConfigChange(config.key, JSON.stringify(value))
            }}
            size="small"
            sx={{ flex: 1 }}
            placeholder={config.placeholder || '选择多个人设'}
            disabled={disabled}
            SelectProps={{
              multiple: true,
              displayEmpty: true,
              renderValue: (selected) => {
                const selectedArray = selected as number[]
                if (selectedArray.length === 0) {
                  return <em>未选择人设</em>
                }
                return (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selectedArray.map(id => {
                      const preset = presetMap[id.toString()]
                      return preset ? (
                        <Chip
                          key={id}
                          size="small"
                          avatar={<Avatar src={preset.avatar} sx={{ width: 16, height: 16 }} />}
                          label={preset.title}
                          sx={{ height: 20, fontSize: '0.7rem' }}
                        />
                      ) : (
                        <Chip
                          key={id}
                          size="small"
                          label={`ID:${id}`}
                          color="error"
                          sx={{ height: 20, fontSize: '0.7rem' }}
                        />
                      )
                    })}
                  </Box>
                )
              }
            }}
          >
            {presets.map(preset => (
              <MenuItem key={preset.id} value={preset.id}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                  <Avatar
                    src={preset.avatar}
                    alt={preset.name}
                    sx={{ width: 20, height: 20 }}
                  />
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {preset.title}
                  </Typography>
                  {preset.is_remote && (
                    <Chip
                      label="云端"
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ height: 16, fontSize: '0.6rem' }}
                    />
                  )}
                </Box>
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="outlined"
            color="warning"
            size="small"
            onClick={() => handleConfigChange(config.key, JSON.stringify([]))}
            disabled={disabled || selectedIds.length === 0}
            sx={{
              flexShrink: 0,
              borderRadius: 999,
              fontWeight: 600,
              px: isSmall ? 1 : 1.5,
              py: isSmall ? 0.1 : 0.4,
              minWidth: 'auto',
              height: isSmall ? 24 : 28,
              fontSize: isSmall ? '0.68rem' : '0.8rem',
              mr: 1,
            }}
            aria-label="清空所有选择"
          >
            清空
          </Button>
          <Button
            variant="outlined"
            color="secondary"
            size="small"
            endIcon={<LaunchIcon fontSize={isSmall ? 'small' : 'inherit'} />}
            onClick={() => navigate('/presets')}
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
            aria-label="跳转到人设管理页面"
            disabled={disabled}
          >
            管理人设
          </Button>
        </Box>
      )
    }

    if (config.ref_presets) {
      // 对于人设选择器，rawValue 应该是数字字符串或 "-1"
      const numericValue = rawValue === '' ? '-1' : rawValue
      const selectedPreset = numericValue !== '-1' ? presetMap[numericValue] : null
      const isInvalidValue = Boolean(numericValue !== '-1' && !selectedPreset)

      return (
        <Box sx={{ width: '100%', display: 'flex', alignItems: 'center', gap: 1 }}>
          <TextField
            select
            value={numericValue}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            sx={{ flex: 1 }}
            error={isInvalidValue}
            helperText={isInvalidValue ? '当前选择的人设已不存在' : undefined}
            placeholder={config.placeholder || '选择人设'}
            disabled={disabled}
            SelectProps={{
              displayEmpty: true
            }}
          >
            <MenuItem value="-1">
              <em>默认人设</em>
            </MenuItem>
            {presets.map(preset => (
              <MenuItem key={preset.id} value={preset.id.toString()}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Avatar
                    src={preset.avatar}
                    alt={preset.name}
                    sx={{ width: 20, height: 20 }}
                  />
                  <Typography variant="body2">
                    {preset.title}
                  </Typography>
                  {preset.is_remote && (
                    <Chip
                      label="云端"
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ height: 16, fontSize: '0.6rem', ml: 0.5 }}
                    />
                  )}
                </Box>
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="outlined"
            color="secondary"
            size="small"
            endIcon={<LaunchIcon fontSize={isSmall ? 'small' : 'inherit'} />}
            onClick={() => navigate('/presets')}
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
            aria-label="跳转到人设管理页面"
            disabled={disabled}
          >
            管理人设
          </Button>
        </Box>
      )
    }

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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

      const canBeNested = config.type === 'list' || config.is_complex

      if (canBeNested) {
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
            <TextField
              value={displayValue}
              size="small"
              fullWidth
              InputProps={{
                readOnly: true,
                sx: {
                  cursor: 'pointer',
                  bgcolor: 'transparent',
                  '&:hover': { bgcolor: 'action.hover' },
                },
              }}
              onClick={() =>
                !disabled && setExpandedRows(prev => ({ ...prev, [config.key]: !prev[config.key] }))
              }
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'primary.main',
                  },
                },
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
<<<<<<< HEAD
                disabled={dirtyKeys.size === 0}
=======
<<<<<<< HEAD
                disabled={dirtyKeys.size === 0}
=======
<<<<<<< HEAD
                disabled={dirtyKeys.size === 0}
=======
                disabled={dirtyKeys.size === 0 || disabled}
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
              >
                保存更改
              </Button>
              <Button
                variant="outlined"
                color="secondary"
                size="small"
                onClick={() => setReloadConfirmOpen(true)}
                startIcon={<RefreshIcon />}
<<<<<<< HEAD
              >
                重置配置
=======
<<<<<<< HEAD
              >
                重置配置
=======
<<<<<<< HEAD
              >
                重置配置
=======
                disabled={disabled}
              >
                重载配置
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
                <TableCell sx={{ width: isOverridePage ? '45%' : '50%', minWidth: 300 }}>
                  值
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredConfigs.flatMap(config => {
                const isEnabled =
                  isOverridePage && config.enable_toggle
                    ? enableStateMap.get(config.enable_toggle) ?? false
                    : true

                const mainRow = (
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
                            <HtmlTooltip
                              title={
                                <div dangerouslySetInnerHTML={{ __html: config.description }} />
                              }
                              placement="right"
                            >
                              <IconButton
                                size="small"
                                sx={{
                                  p: 0.2,
                                  color: 'text.secondary',
                                  verticalAlign: 'middle',
                                  cursor: 'help',
                                }}
                              >
                                <HelpOutlineIcon sx={{ fontSize: '1rem' }} />
                              </IconButton>
                            </HtmlTooltip>
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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
                        label={
                          config.ref_presets_multiple ? 'presets' :
                          config.ref_presets ? 'preset' : 
                          config.type
                        }
                        size="small"
                        color={getTypeColor(
                          config.ref_presets_multiple ? 'presets' :
                          config.ref_presets ? 'preset' : 
                          config.type, 
                          config.is_complex
                        )}
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
                        label={config.type}
                        size="small"
                        color={getTypeColor(config.type, config.is_complex)}
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
                        variant="outlined"
                        sx={CHIP_VARIANTS.base(isSmall)}
                      />
                    </TableCell>
                    <TableCell sx={UNIFIED_TABLE_STYLES.cell}>
                      {renderConfigInput(config, isOverridePage ? !isEnabled : false)}
                    </TableCell>
                  </TableRow>
                )

                const canBeNested = config.type === 'list' || config.is_complex
                const nestedRows =
                  expandedRows[config.key] && canBeNested
                    ? renderNestedConfigRows(
                        config,
                        editingValues,
                        handleConfigChange,
                        isOverridePage,
                        isSmall,
                        expandedRows,
                        setExpandedRows,
                        1
                      )
                    : []

                return [mainRow, ...nestedRows]
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
<<<<<<< HEAD
        title="确认重置配置"
        content="重置配置将丢失所有未保存的修改，是否继续？"
=======
<<<<<<< HEAD
        title="确认重置配置"
        content="重置配置将丢失所有未保存的修改，是否继续？"
=======
<<<<<<< HEAD
        title="确认重置配置"
        content="重置配置将丢失所有未保存的修改，是否继续？"
=======
        title="确认重载配置"
        content="重载配置将丢失所有未保存的修改，是否继续？"
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
      
      {/* 重启系统确认对话框 */}
      <Dialog
        open={restartDialogOpen}
        onClose={() => !isRestarting && setRestartDialogOpen(false)}
        PaperProps={{
          sx: {
            borderRadius: '12px',
            maxWidth: '500px',
          },
        }}
      >
        <DialogTitle
          sx={{
            px: 3,
            py: 2,
            background: theme =>
              theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
          }}
        >
          重启系统确认
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          <Alert severity="warning" sx={{ mb: 2 }}>
            重启期间 WebUI 功能将无法正常使用，如果长时间未恢复请检查 NekroAgent 容器日志是否出现异常
          </Alert>
          <Typography sx={{ mt: 1, mb: 2 }}>
            检测到您修改了需要重启才能生效的配置项，确定要重启系统吗？重启过程可能需要大概一分钟，请耐心等待。
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button 
            onClick={() => setRestartDialogOpen(false)}
            disabled={isRestarting}
          >
            取消
          </Button>
          <Button 
            onClick={handleRestartSystem}
            color="error" 
            variant="contained"
            disabled={isRestarting}
            startIcon={<RestartIcon />}
          >
            {isRestarting ? '重启中...' : '确认重启'}
          </Button>
        </DialogActions>
      </Dialog>
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
    </Box>
  )
}