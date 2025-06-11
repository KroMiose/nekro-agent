import React, { useState, useEffect } from 'react'
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
  Stack,
  Collapse,
  Link,
  useMediaQuery,
  useTheme,
  Drawer,
  Fab,
  ListItemButton,
} from '@mui/material'

import {
  Refresh as RefreshIcon,
  Code as CodeIcon,
  Settings as SettingsIcon,
  Info as InfoIcon,
  ArrowBack as ArrowBackIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  ContentCopy as ContentCopyIcon,
  WebhookOutlined as WebhookIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
  Storage as StorageIcon,
  Extension as ExtensionIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Method, Plugin, pluginsApi } from '../../services/api/plugins'

import { unifiedConfigApi, createConfigService } from '../../services/api/unified-config'
import ConfigTable from '../../components/common/ConfigTable'
import { useNavigate } from 'react-router-dom'
import {
  pluginTypeColors,
  pluginTypeTexts,
  methodTypeColors,
  methodTypeTexts,
  methodTypeDescriptions,
} from '../../theme/variants'
import { CHIP_VARIANTS } from '../../theme/variants'

// 添加 server_addr 配置
const server_addr = window.location.origin

interface PluginDetailProps {
  plugin: Plugin
  onBack: () => void
  onToggleEnabled: (id: string, enabled: boolean) => void
}

// 插件详情组件
function PluginDetails({ plugin, onBack, onToggleEnabled }: PluginDetailProps) {
  const [activeTab, setActiveTab] = useState(0)
  const [message, setMessage] = useState('')
  const [reloadConfirmOpen, setReloadConfirmOpen] = useState(false)
  const [resetDataConfirmOpen, setResetDataConfirmOpen] = useState(false)
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

  // 获取插件配置
  const { data: pluginConfig, isLoading: configLoading } = useQuery({
    queryKey: ['plugin-config', plugin?.id],
    queryFn: () => unifiedConfigApi.getPluginConfig(plugin?.id),
    enabled: !!plugin && activeTab === 1 && plugin.hasConfig,
  })

  // 获取插件数据
  const { data: pluginData = [], isLoading: isDataLoading } = useQuery({
    queryKey: ['plugin-data', plugin?.id],
    queryFn: () => pluginsApi.getPluginData(plugin.id),
    enabled: !!plugin && activeTab === 4,
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
      setMessage('数据已删除')
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
      setMessage('所有数据已重置')
      queryClient.invalidateQueries({ queryKey: ['plugin-data', plugin.id] })
    },
    onError: (error: Error) => {
      setMessage(`重置失败: ${error.message}`)
    },
  })

  // 删除云端插件
  const removePackageMutation = useMutation({
    mutationFn: () => pluginsApi.removePackage(plugin.moduleName),
    onSuccess: () => {
      setMessage(`云端插件 ${plugin.name} 已删除～`)
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      onBack() // 返回插件列表
    },
    onError: (error: Error) => {
      setMessage(`删除失败: ${error.message}`)
    },
  })

  // 更新云端插件
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
      setMessage(`云端插件 ${plugin.name} 已更新至最新版本～`)
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-config', plugin.id] })
    },
    onError: (error: Error) => {
      setMessage(error.message)
    },
  })

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
        <Box
          sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1, overflow: 'hidden' }}
        >
          <Chip
            label={getPluginTypeText()}
            size="small"
            color={pluginTypeColors[getPluginType()]}
            variant="outlined"
            sx={{ height: 22, fontSize: '0.7rem' }}
          />
          <Typography
            variant={isMobile ? 'subtitle1' : 'h6'}
            component="div"
            sx={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
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

      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
        }}
      >
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
            },
          }}
          variant={isMobile ? 'scrollable' : 'standard'}
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
          {pluginConfig && pluginConfig.length > 0 ? (
            <ConfigTable
              configKey={`plugin_${plugin.id}`}
              configService={createConfigService(`plugin_${plugin.id}`)}
              configs={pluginConfig}
              loading={configLoading}
              onRefresh={() =>
                queryClient.invalidateQueries({ queryKey: ['plugin-config', plugin.id] })
              }
              emptyMessage="此插件没有可配置项"
            />
          ) : (
            <Alert severity="info">此插件没有可配置项</Alert>
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
                <Table size={isSmall ? 'small' : 'medium'}>
                  <TableHead>
                    <TableRow>
                      <TableCell width={isMobile ? '30%' : '20%'} sx={{ py: isSmall ? 1 : 1.5 }}>
                        方法名
                      </TableCell>
                      <TableCell width={isMobile ? '25%' : '15%'} sx={{ py: isSmall ? 1 : 1.5 }}>
                        类型
                      </TableCell>
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
                              wordBreak: 'break-all',
                            }}
                          >
                            {method.name}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ py: isSmall ? 0.75 : 1.25 }}>
                          <Tooltip
                            title={methodTypeDescriptions[method.type] || ''}
                            arrow
                            placement="top"
                          >
                            <Chip
                              label={methodTypeTexts[method.type] || method.type}
                              color={methodTypeColors[method.type]}
                              size="small"
                              variant="outlined"
                              sx={CHIP_VARIANTS.base(isSmall)}
                            />
                          </Tooltip>
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
                此插件没有定义方法
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
                <Table size={isSmall ? 'small' : 'medium'}>
                  <TableHead>
                    <TableRow>
                      <TableCell width={isSmall ? 100 : 150} sx={{ py: isSmall ? 1 : 1.5 }}>
                        接入点
                      </TableCell>
                      <TableCell sx={{ py: isSmall ? 1 : 1.5 }}>名称</TableCell>
                      <TableCell
                        width={isSmall ? 80 : 132}
                        align="center"
                        sx={{ py: isSmall ? 1 : 1.5 }}
                      >
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
                                wordBreak: 'break-all',
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
                                    fontSize: isSmall ? '0.9rem' : '1rem',
                                  },
                                },
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
                                <KeyboardArrowUpIcon fontSize={isSmall ? 'small' : 'medium'} />
                              ) : (
                                <KeyboardArrowDownIcon fontSize={isSmall ? 'small' : 'medium'} />
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
                                    fontSize: isSmall ? '0.75rem' : '0.875rem',
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
                <Table size={isSmall ? 'small' : 'medium'}>
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
                                wordBreak: 'break-all',
                              }}
                            >
                              {data.data_key}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Stack
                              direction="row"
                              spacing={0.5}
                              justifyContent="flex-end"
                              flexWrap="wrap"
                            >
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
                                      fontSize: isSmall ? '0.9rem' : '1rem',
                                    },
                                  },
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
                                      fontSize: isSmall ? '0.9rem' : '1rem',
                                    },
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
                                <KeyboardArrowUpIcon fontSize={isSmall ? 'small' : 'medium'} />
                              ) : (
                                <KeyboardArrowDownIcon fontSize={isSmall ? 'small' : 'medium'} />
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
                                    fontSize: isSmall ? '0.75rem' : '0.875rem',
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
                此插件暂无存储数据
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

      {/* 删除云端插件确认对话框 */}
      <Dialog open={deleteConfirmOpen} onClose={() => setDeleteConfirmOpen(false)}>
        <DialogTitle>确认删除云端插件？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            此操作将删除云端插件 "{plugin.name}"，包括其所有文件和配置。此操作不可恢复，是否继续？
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

      {/* 更新云端插件确认对话框 */}
      <Dialog open={updateConfirmOpen} onClose={() => setUpdateConfirmOpen(false)} maxWidth="md">
        <DialogTitle>确认更新云端插件？</DialogTitle>
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
            此操作将从远程仓库更新云端插件 "{plugin.name}"
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
      setMessage(`插件已${variables.enabled ? '启用' : '禁用'}`)

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
        height: 'calc(100vh - 90px)',
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
                            bgcolor:
                              selectedPlugin?.id === plugin.id ? 'action.selected' : 'inherit',
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
                                <Box
                                  sx={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    flexWrap: 'wrap',
                                    gap: 0.5,
                                  }}
                                >
                                  <Chip
                                    label={pluginTypeTexts[getPluginType(plugin)]}
                                    size="small"
                                    color={pluginTypeColors[getPluginType(plugin)]}
                                    variant="outlined"
                                    sx={{
                                      height: 18,
                                      fontSize: '0.65rem',
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
                                    fontSize: isSmall ? '0.75rem' : 'inherit',
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
                      没有找到匹配的插件
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
                    请点击右下角按钮选择一个插件来查看详情
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
                            bgcolor:
                              selectedPlugin?.id === plugin.id ? 'action.selected' : 'inherit',
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
                                    color={pluginTypeColors[getPluginType(plugin)]}
                                    size="small"
                                    variant="outlined"
                                    label={pluginTypeTexts[getPluginType(plugin)]}
                                    sx={CHIP_VARIANTS.base(isSmall)}
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
                                    fontSize: isSmall ? '0.75rem' : 'inherit',
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
                      没有找到匹配的插件
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
                    请从左侧选择一个插件查看详情
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
          size={isSmall ? 'medium' : 'large'}
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
