import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Box,
  Paper,
  TextField,
  Switch,
  FormControlLabel,
  Stack,
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
  useTheme,
  useMediaQuery,
  SxProps,
  Theme,
} from '@mui/material'
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  HelpOutline as HelpOutlineIcon,
  Search as SearchIcon,
  Launch as LaunchIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material'
import { CircularProgress } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { UNIFIED_TABLE_STYLES, CHIP_VARIANTS } from '../../theme/variants'
import { ThemedTooltip } from './ThemedTooltip'
import { useNotification } from '../../hooks/useNotification'

// 使用主题化的 Tooltip 组件
const HtmlTooltip = ThemedTooltip

// 配置项类型定义
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
}

// 模型组配置类型
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

// 模型类型选项
export interface ModelTypeOption {
  value: string
  label: string
  description?: string
  color?: string
  icon?: string
}

// 配置服务接口
export interface ConfigService {
  getConfigList: (configKey: string) => Promise<ConfigItem[]>
  getModelGroups?: () => Promise<Record<string, ModelGroupConfig>>
  getModelTypes?: () => Promise<ModelTypeOption[]>
  batchUpdateConfig: (configKey: string, configs: Record<string, string>) => Promise<void>
  saveConfig: (configKey: string) => Promise<void>
  reloadConfig: (configKey: string) => Promise<void>
}

// 嵌套配置行展开状态
interface ExpandedRowsState {
  [configKey: string]: boolean
}

// 渲染嵌套配置的子行
function renderNestedConfigRows(
  config: ConfigItem,
  editingValues: Record<string, string>,
  handleConfigChange: (key: string, value: string) => void,
  level: number = 0,
  parentKey: string = '',
  isSmall: boolean = false,
  expandedRows?: ExpandedRowsState,
  setExpandedRows?: React.Dispatch<React.SetStateAction<ExpandedRowsState>>
): React.ReactNode[] {
  const rows: React.ReactNode[] = []
  const currentValue =
    editingValues[config.key] !== undefined ? JSON.parse(editingValues[config.key]) : config.value

  // 处理简单列表
  if (config.type === 'list' && !config.is_complex) {
    const listValue = Array.isArray(currentValue) ? currentValue : []
    const elementType = config.element_type || 'str'

    listValue.forEach((item: unknown, index: number) => {
      const subKey = `${parentKey}${config.key}[${index}]`

      rows.push(
        <TableRow
          key={subKey}
          sx={{
            ...(UNIFIED_TABLE_STYLES.nestedRow as SxProps<Theme>),
          }}
        >
          <TableCell
            sx={{
              py: isSmall ? 0.75 : 1.5,
              pl: 2 + level * 2,
              borderLeft: level > 0 ? `2px solid` : 'none',
              borderLeftColor: level > 0 ? 'divider' : 'transparent',
            }}
          >
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
          <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
            <Chip
              label={elementType}
              size="small"
              color={getTypeColor(elementType)}
              variant="outlined"
              sx={CHIP_VARIANTS.base(isSmall)}
            />
          </TableCell>
          <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
            {renderSimpleListInput(item, elementType, newValue => {
              const newList = [...listValue]
              newList[index] = newValue
              handleConfigChange(config.key, JSON.stringify(newList))
            })}
          </TableCell>
        </TableRow>
      )
    })

    // 添加新项的行
    rows.push(
      <TableRow
        key={`${config.key}-add`}
        sx={{
          ...(UNIFIED_TABLE_STYLES.nestedRow as SxProps<Theme>),
        }}
      >
        <TableCell
          sx={{
            py: isSmall ? 0.75 : 1.5,
            pl: 2 + level * 2,
            borderLeft: level > 0 ? `2px solid` : 'none',
            borderLeftColor: level > 0 ? 'divider' : 'transparent',
          }}
        >
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
        <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
        <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
      </TableRow>
    )
  }

  // 处理复合列表和字典
  if (config.is_complex) {
    if (config.type === 'list') {
      const listValue = Array.isArray(currentValue) ? currentValue : []

      // 渲染每个列表项
      listValue.forEach((item: unknown, index: number) => {
        // 首先添加一个删除按钮行
        rows.push(
          <TableRow
            key={`${config.key}[${index}]-header`}
            sx={{
              ...(UNIFIED_TABLE_STYLES.nestedRow as SxProps<Theme>),
            }}
          >
            <TableCell
              sx={{
                py: isSmall ? 0.75 : 1.5,
                pl: 2 + level * 2,
                borderLeft: level > 0 ? `2px solid` : 'none',
                borderLeftColor: level > 0 ? 'divider' : 'transparent',
              }}
            >
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
            <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
            <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
          </TableRow>
        )

        // 为每个复合对象创建子配置项
        if (item && typeof item === 'object' && config.field_schema) {
          Object.entries(config.field_schema).forEach(([fieldName, fieldSchema]) => {
            const fieldValue = (item as Record<string, unknown>)[fieldName]
            const subKey = `${parentKey}${config.key}[${index}].${fieldName}`

            rows.push(
              <TableRow
                key={subKey}
                sx={{
                  ...(UNIFIED_TABLE_STYLES.nestedRow as SxProps<Theme>),
                }}
              >
                <TableCell
                  sx={{
                    py: isSmall ? 0.75 : 1.5,
                    pl: 4 + level * 2,
                    borderLeft: level > 0 ? `2px solid` : 'none',
                    borderLeftColor: level > 0 ? 'divider' : 'transparent',
                  }}
                >
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
                <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
                  <Chip
                    label={fieldSchema.type}
                    size="small"
                    color={getTypeColor(fieldSchema.type)}
                    variant="outlined"
                    sx={CHIP_VARIANTS.base(isSmall)}
                  />
                </TableCell>
                <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
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

            // 如果是 list 类型字段且已展开，添加嵌套的列表编辑行
            if (fieldSchema.type === 'list' && expandedRows?.[subKey]) {
              const fieldListValue = Array.isArray(fieldValue) ? fieldValue : []
              const fieldElementType = fieldSchema.element_type || 'str'

              fieldListValue.forEach((listItem: unknown, listIndex: number) => {
                const listItemKey = `${subKey}[${listIndex}]`
                rows.push(
                  <TableRow
                    key={listItemKey}
                    sx={{
                      ...(UNIFIED_TABLE_STYLES.nestedRow as SxProps<Theme>),
                    }}
                  >
                    <TableCell
                      sx={{
                        py: isSmall ? 0.75 : 1.5,
                        pl: 6 + level * 2,
                        borderLeft: level > 0 ? `2px solid` : 'none',
                        borderLeftColor: level > 0 ? 'divider' : 'transparent',
                      }}
                    >
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
                    <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
                      <Chip
                        label={fieldElementType}
                        size="small"
                        color={getTypeColor(fieldElementType)}
                        variant="outlined"
                        sx={CHIP_VARIANTS.base(isSmall)}
                      />
                    </TableCell>
                    <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
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

              // 添加新列表项的按钮
              rows.push(
                <TableRow
                  key={`${subKey}-add`}
                  sx={{
                    ...(UNIFIED_TABLE_STYLES.nestedRow as SxProps<Theme>),
                  }}
                >
                  <TableCell
                    sx={{
                      py: isSmall ? 0.75 : 1.5,
                      pl: 6 + level * 2,
                      borderLeft: level > 0 ? `2px solid` : 'none',
                      borderLeftColor: level > 0 ? 'divider' : 'transparent',
                    }}
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
                  <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
                  <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
                </TableRow>
              )
            }
          })
        }
      })

      // 添加"添加新项"按钮
      rows.push(
        <TableRow
          key={`${config.key}-add-complex`}
          sx={{
            ...(UNIFIED_TABLE_STYLES.nestedRow as SxProps<Theme>),
          }}
        >
          <TableCell
            sx={{
              py: isSmall ? 0.75 : 1.5,
              pl: 2 + level * 2,
              borderLeft: level > 0 ? `2px solid` : 'none',
              borderLeftColor: level > 0 ? 'divider' : 'transparent',
            }}
          >
            <Button
              variant="text"
              size="small"
              startIcon={<AddIcon />}
              onClick={() => {
                // 创建默认对象
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
          <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
          <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
        </TableRow>
      )
    }
  }

  // 处理简单字典类型
  if (config.type === 'dict' && !config.is_complex) {
    const dictValue =
      currentValue && typeof currentValue === 'object'
        ? (currentValue as Record<string, unknown>)
        : {}
    const valueType = config.value_type || 'str'

    Object.entries(dictValue).forEach(([key, value]) => {
      rows.push(
        <TableRow
          key={`${config.key}.${key}`}
          sx={{
            ...(UNIFIED_TABLE_STYLES.nestedRow as SxProps<Theme>),
          }}
        >
          <TableCell
            sx={{
              py: isSmall ? 0.75 : 1.5,
              pl: 2 + level * 2,
              borderLeft: level > 0 ? `2px solid` : 'none',
              borderLeftColor: level > 0 ? 'divider' : 'transparent',
            }}
          >
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
          <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
            <Chip
              label={valueType}
              size="small"
              color={getTypeColor(valueType)}
              variant="outlined"
              sx={CHIP_VARIANTS.base(isSmall)}
            />
          </TableCell>
          <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }}>
            {renderSimpleListInput(value, valueType, newValue => {
              const newDict = { ...dictValue, [key]: newValue }
              handleConfigChange(config.key, JSON.stringify(newDict))
            })}
          </TableCell>
        </TableRow>
      )
    })

    // 添加新键值对的输入行
    rows.push(
      <TableRow
        key={`${config.key}-add-dict`}
        sx={{
          ...(UNIFIED_TABLE_STYLES.nestedRow as SxProps<Theme>),
        }}
      >
        <TableCell
          sx={{
            py: isSmall ? 0.75 : 1.5,
            pl: 2 + level * 2,
            borderLeft: level > 0 ? `2px solid` : 'none',
            borderLeftColor: level > 0 ? 'divider' : 'transparent',
          }}
        >
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
        <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
        <TableCell sx={{ py: isSmall ? 0.75 : 1.5 }} />
      </TableRow>
    )
  }

  return rows
}

// 渲染简单列表输入框
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
                ? parseInt(e.target.value) || 0
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

// 渲染字段输入框
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
                ? parseInt(e.target.value) || 0
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
      // 对于列表类型字段，提供展开/折叠功能
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

      // 如果没有展开状态管理，回退到简单显示
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
          inputProps={{
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

// 获取类型的默认值
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

// 配置表格组件属性
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
}

// 类型颜色选择函数
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
  emptyMessage = '暂无配置项',
}: ConfigTableProps) {
  const navigate = useNavigate()
  const notification = useNotification()
  const [editingValues, setEditingValues] = useState<Record<string, string>>({})
  const [visibleSecrets, setVisibleSecrets] = useState<Record<string, boolean>>({})
  const [reloadConfirmOpen, setReloadConfirmOpen] = useState(false)
  const [saveWarningOpen, setSaveWarningOpen] = useState(false)
  const [emptyRequiredFields, setEmptyRequiredFields] = useState<string[]>([])
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  // 模型组和模型类型数据
  const [modelGroups, setModelGroups] = useState<Record<string, ModelGroupConfig>>({})
  const [modelTypes, setModelTypes] = useState<ModelTypeOption[]>([])

  // 展开状态管理
  const [expandedRows, setExpandedRows] = useState<ExpandedRowsState>({})

  // 加载模型组和模型类型数据
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

  // 保存函数
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

  // 监听保存快捷键
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

  // 重载配置
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

  // 渲染配置输入组件
  const renderConfigInput = (config: ConfigItem) => {
    const isEditing = config.key in editingValues
    const displayValue = isEditing ? editingValues[config.key] : String(config.value)
    const isSecret = config.is_secret

    // 处理列表和复合类型 - 显示展开/折叠按钮
    if (config.type === 'list' || (config.is_complex && config.type === 'dict')) {
      const currentValue = isEditing ? JSON.parse(displayValue) : config.value
      const isExpanded = expandedRows[config.key] || false

      const getDisplayValue = () => {
        if (config.type === 'list') {
          const listValue = Array.isArray(currentValue) ? currentValue : []
          return `列表 (${listValue.length} 项)`
        } else {
          const dictValue =
            currentValue && typeof currentValue === 'object'
              ? (currentValue as Record<string, unknown>)
              : {}
          return `对象 (${Object.keys(dictValue).length} 项)`
        }
      }

      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
          <TextField
            value={getDisplayValue()}
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
            onClick={() => setExpandedRows(prev => ({ ...prev, [config.key]: !prev[config.key] }))}
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
            onClick={() => setExpandedRows(prev => ({ ...prev, [config.key]: !prev[config.key] }))}
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
                letterSpacing: 0.5,
                textTransform: 'none',
                boxShadow: 'none',
                transition: 'background 0.2s',
                '&:hover': {
                  bgcolor: 'action.hover',
                  boxShadow: 1,
                },
              }}
              aria-label="跳转到模型组配置页面"
            >
              {`${typeOption.label}模型组`}
            </Button>
          )}
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

    // 处理简单dict类型
    if (config.type === 'dict' && !config.is_complex) {
      const currentValue = isEditing ? JSON.parse(displayValue || '{}') : config.value || {}
      const isExpanded = expandedRows[config.key] || false

      const getDisplayValue = () => {
        const dictValue =
          currentValue && typeof currentValue === 'object'
            ? (currentValue as Record<string, unknown>)
            : {}
        return `字典 (${Object.keys(dictValue).length} 项)`
      }

      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
          <TextField
            value={getDisplayValue()}
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
            onClick={() => setExpandedRows(prev => ({ ...prev, [config.key]: !prev[config.key] }))}
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
            onClick={() => setExpandedRows(prev => ({ ...prev, [config.key]: !prev[config.key] }))}
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

  // 过滤配置项
  const filteredConfigs = configs.filter(
    config =>
      !config.is_hidden &&
      ((config.title || '').toLowerCase().includes(searchText.toLowerCase()) ||
        config.key.toLowerCase().includes(searchText.toLowerCase()))
  )

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 顶部工具栏 */}
      {showToolbar && (
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
          {showSearchBar && (
            <TextField
              size="small"
              variant="outlined"
              placeholder="搜索配置名称或键"
              value={searchText}
              onChange={e => onSearchChange?.(e.target.value)}
              sx={{ flex: 1 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
            />
          )}
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
      )}

      {/* 表格容器 */}
      <Paper
        elevation={3}
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          overflow: 'hidden',
          ...(UNIFIED_TABLE_STYLES.paper as SxProps<Theme>),
        }}
      >
        <TableContainer
          sx={{
            flex: 1,
            overflow: 'auto',
            ...(UNIFIED_TABLE_STYLES.scrollbar as SxProps<Theme>),
          }}
        >
          <Table stickyHeader size={isSmall ? 'small' : 'medium'}>
            <TableHead>
              <TableRow>
                <TableCell
                  width={isMobile ? '40%' : '25%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  配置项
                </TableCell>
                <TableCell
                  width={isMobile ? '20%' : '10%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  类型
                </TableCell>
                <TableCell
                  width={isMobile ? '40%' : '65%'}
                  sx={{
                    py: isSmall ? 1 : 1.5,
                    ...(UNIFIED_TABLE_STYLES.header as SxProps<Theme>),
                  }}
                >
                  值
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell
                    colSpan={3}
                    sx={{
                      textAlign: 'center',
                      py: 4,
                    }}
                  >
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : filteredConfigs.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={3}
                    sx={{
                      textAlign: 'center',
                      py: 4,
                      color: 'text.secondary',
                    }}
                  >
                    {emptyMessage}
                  </TableCell>
                </TableRow>
              ) : (
                filteredConfigs.flatMap(config => {
                  const mainRow = (
                    <TableRow key={config.key} sx={UNIFIED_TABLE_STYLES.row as SxProps<Theme>}>
                      <TableCell
                        sx={{
                          py: isSmall ? 0.75 : 1.5,
                          ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                        }}
                      >
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
                            sx={{ fontSize: isSmall ? '0.65rem' : '0.75rem' }}
                          >
                            {config.key}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell
                        sx={{
                          py: isSmall ? 0.75 : 1.5,
                          ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                        }}
                      >
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                          <Chip
                            label={config.is_complex ? `${config.type}` : config.type}
                            size="small"
                            color={getTypeColor(config.type, config.is_complex)}
                            variant="outlined"
                            sx={CHIP_VARIANTS.base(isSmall)}
                          />
                        </Box>
                      </TableCell>
                      <TableCell
                        sx={{
                          py: isSmall ? 0.75 : 1.5,
                          ...(UNIFIED_TABLE_STYLES.cell as SxProps<Theme>),
                        }}
                      >
                        <Box
                          sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}
                        >
                          {renderConfigInput(config)}
                        </Box>
                      </TableCell>
                    </TableRow>
                  )

                  // 添加嵌套行（如果展开）
                  const nestedRows =
                    expandedRows[config.key] && (config.type === 'list' || config.type === 'dict')
                      ? renderNestedConfigRows(
                          config,
                          editingValues,
                          handleConfigChange,
                          1,
                          '',
                          isSmall,
                          expandedRows,
                          setExpandedRows
                        )
                      : []

                  return [mainRow, ...nestedRows]
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 重载确认对话框 */}
      <Dialog
        open={reloadConfirmOpen}
        onClose={() => setReloadConfirmOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>确认重载配置？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            重载配置将从配置文件中重新读取所有配置项，未保存的修改将会丢失。是否继续？
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

      {/* 必填项警告对话框 */}
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
    </Box>
  )
}
