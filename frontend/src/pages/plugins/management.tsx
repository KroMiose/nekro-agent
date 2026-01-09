import React, { useState, useEffect } from 'react'
import {
  Box,
  List,
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
  Menu,
  MenuItem,
} from '@mui/material'
import MarkdownRenderer from '../../components/common/MarkdownRenderer'
import {
  Refresh as RefreshIcon,
  Code as CodeIcon,
  Settings as SettingsIcon,
  InfoOutlined as InfoIcon,
  ArrowBack as ArrowBackIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  ContentCopy as ContentCopyIcon,
  WebhookOutlined as WebhookIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
  Storage as StorageIcon,
  Extension as ExtensionIcon,
  Description as DescriptionIcon,
  Person as PersonIcon,
  VpnKey as VpnKeyIcon,
  Link as LinkIcon,
  Category as CategoryIcon,
  Bookmark as BookmarkIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Method, Plugin, pluginsApi } from '../../services/api/plugins'

import { unifiedConfigApi, createConfigService } from '../../services/api/unified-config'
import ConfigTable from '../../components/common/ConfigTable'
import { useNavigate } from 'react-router-dom'
import {
  pluginTypeColors,
  methodTypeColors,
  CHIP_VARIANTS,
  CARD_VARIANTS,
} from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'
import { useTranslation } from 'react-i18next'
import { getLocalizedText } from '../../services/api/types'

// 添加 server_addr 配置
const server_addr = window.location.origin

// 插件国际化辅助函数
const getPluginName = (plugin: Plugin, language: string) => {
  return getLocalizedText(plugin.i18n_name, plugin.name, language)
}

const getPluginDescription = (plugin: Plugin, language: string) => {
  return getLocalizedText(plugin.i18n_description, plugin.description, language)
}

interface PluginDetailProps {
  plugin: Plugin
  onBack: () => void
  onToggleEnabled: (id: string, enabled: boolean) => void
}

// 插件详情组件
function PluginDetails({ plugin, onBack, onToggleEnabled }: PluginDetailProps) {
  const [activeTab, setActiveTab] = useState(0)
  const [reloadConfirmOpen, setReloadConfirmOpen] = useState(false)
  const [resetDataConfirmOpen, setResetDataConfirmOpen] = useState(false)
  const [errorDetailOpen, setErrorDetailOpen] = useState(false)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [expandedDataRows, setExpandedDataRows] = useState<Set<number>>(new Set())
  const [updateConfirmOpen, setUpdateConfirmOpen] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [deleteDataConfirmOpen, setDeleteDataConfirmOpen] = useState(false)
  const [deleteDataId, setDeleteDataId] = useState<number | null>(null)
  const [clearDataOnDelete, setClearDataOnDelete] = useState(false) // 新增：删除时是否清除数据的状态
  const [moreMenuAnchorEl, setMoreMenuAnchorEl] = useState<null | HTMLElement>(null) // 更多操作菜单锚点
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const notification = useNotification()
  const { t, i18n } = useTranslation('plugins')

  // 获取插件配置
  const { data: pluginConfig, isLoading: configLoading } = useQuery({
    queryKey: ['plugin-config', plugin?.id],
    queryFn: () => unifiedConfigApi.getPluginConfig(plugin?.id),
    enabled: !!plugin && activeTab === 1 && plugin.hasConfig,
  })

  // 获取插件文档
  const {
    data: pluginDocs,
    isLoading: docsLoading,
    error: docsError,
  } = useQuery({
    queryKey: ['plugin-docs', plugin?.id],
    queryFn: () => pluginsApi.getPluginDocs(plugin.id),
    enabled: !!plugin && activeTab === 0,
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
        throw new Error(t('messages.invalidModuleName'))
      }
      const result = await pluginsApi.reloadPlugins(plugin.moduleName)
      if (!result.success) {
        throw new Error(result.errorMsg || t('messages.reloadFailed'))
      }
      return true
    },
    onSuccess: () => {
      notification.success(t('messages.reloadSuccess', { name: plugin.name }))
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-config', plugin.id] })
    },
    onError: (error: Error) => {
      notification.error(error.message)
    },
  })

  // 删除单条数据
  const deleteDataMutation = useMutation({
    mutationFn: (dataId: number) => pluginsApi.deletePluginData(plugin.id, dataId),
    onSuccess: () => {
      notification.success(t('messages.dataDeleted'))
      queryClient.invalidateQueries({ queryKey: ['plugin-data', plugin.id] })
    },
    onError: (error: Error) => {
      notification.error(`${t('messages.deleteFailed')}: ${error.message}`)
    },
  })

  // 删除插件所有数据
  const resetDataMutation = useMutation({
    mutationFn: () => pluginsApi.resetPluginData(plugin.id),
    onSuccess: () => {
      notification.success(t('messages.dataResetSuccess'))
      queryClient.invalidateQueries({ queryKey: ['plugin-data', plugin.id] })
    },
    onError: (error: Error) => {
      notification.error(`${t('messages.resetFailed')}: ${error.message}`)
    },
  })

  // 删除云端插件
  const removePackageMutation = useMutation({
    mutationFn: () => pluginsApi.removePackage(plugin.moduleName, clearDataOnDelete),
    onSuccess: () => {
      notification.success(
        clearDataOnDelete
          ? t('messages.deleteWithDataSuccess', { name: plugin.name })
          : t('messages.deleteSuccess', { name: plugin.name })
      )
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      onBack() // 返回插件列表
    },
    onError: (error: Error) => {
      notification.error(`${t('messages.deleteFailed')}: ${error.message}`)
    },
  })

  // 更新云端插件
  const updatePackageMutation = useMutation({
    mutationFn: async () => {
      if (!plugin.moduleName) {
        throw new Error(t('messages.invalidModuleName'))
      }
      const result = await pluginsApi.updatePackage(plugin.moduleName)
      if (!result.success) {
        throw new Error(result.errorMsg || t('messages.updateFailed'))
      }
      return true
    },
    onSuccess: () => {
      notification.success(t('messages.updateSuccess', { name: plugin.name }))
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-config', plugin.id] })
    },
    onError: (error: Error) => {
      notification.error(error.message)
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
    return t(`types.${type}`)
  }

  // 按钮点击处理函数
  const handleNavigateToEditor = () => {
    navigate('/plugins/editor')
  }

  useEffect(() => {
    // 如果当前tab不存在（例如从有配置的插件切换到没配置的），则重置
    const tabCount = 1 + (plugin.hasConfig ? 1 : 0) + 1 + 1 + 1 // info + config? + methods + webhook + data
    if (activeTab >= tabCount) {
      setActiveTab(0)
    }
  }, [plugin, activeTab])

  if (!plugin) return null

  const pluginTabs = [
    { label: t('tabs.info'), icon: <InfoIcon />, isVisible: true },
    { label: t('tabs.config'), icon: <SettingsIcon />, isVisible: plugin.hasConfig },
    { label: t('tabs.methods'), icon: <CodeIcon />, isVisible: true },
    { label: t('tabs.webhook'), icon: <WebhookIcon />, isVisible: true },
    { label: t('tabs.data'), icon: <StorageIcon />, isVisible: true },
  ].filter(tab => tab.isVisible)

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        gap: 2,
      }}
    >
      {/* 标题和总开关 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, p: 2, flexShrink: 0 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 2,
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              flexGrow: 1,
              overflow: 'hidden',
            }}
          >
            {isMobile && (
              <IconButton onClick={onBack} edge="start">
                <ArrowBackIcon />
              </IconButton>
            )}
            <Chip
              label={getPluginTypeText()}
              size="small"
              color={pluginTypeColors[getPluginType()]}
              sx={CHIP_VARIANTS.base(isSmall)}
            />
            <Typography
              variant="h6"
              component="div"
              sx={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontWeight: 600,
              }}
            >
              {getPluginName(plugin, i18n.language)}
            </Typography>
          </Box>
          {plugin.loadFailed ? (
            // 加载失败时显示错误信息
            <Chip
              label={t('status.loadFailed')}
              color="error"
              size="small"
              sx={{ mr: 0, ml: 'auto', fontWeight: 600 }}
            />
          ) : (
            // 正常加载时显示开关
            <FormControlLabel
              control={
                <Switch
                  checked={plugin.enabled}
                  onChange={e => onToggleEnabled(plugin.id, e.target.checked)}
                  color="primary"
                />
              }
              label={plugin.enabled ? t('status.enabled') : t('status.disabled')}
              sx={{ mr: 0, ml: 'auto' }}
            />
          )}
        </Box>
      </Card>

      {/* 选项卡导航 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles }}>
        <Box sx={{ display: 'flex', alignItems: 'center', px: { xs: 1, sm: 1.5 } }}>
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="scrollable"
            scrollButtons="auto"
            allowScrollButtonsMobile
            sx={{
              flexGrow: 1,
              '& .MuiTab-root': {
                minHeight: 48,
                minWidth: 'auto',
                fontSize: '0.875rem',
                fontWeight: 600,
                textTransform: 'none',
                transition: 'all 0.2s ease',
                borderRadius: '8px',
                mx: 0.5,
                px: { xs: 1.5, sm: 2 },
                flexDirection: 'row',
                gap: 1,
                '& .MuiTab-iconWrapper': {
                  marginBottom: 0,
                  mr: 0.5,
                },
                '&:hover': {
                  backgroundColor: theme.palette.action.hover,
                },
                '&.Mui-selected': {
                  color: theme.palette.primary.main,
                  backgroundColor: theme.palette.action.selected,
                },
              },
              '& .MuiTabs-indicator': {
                height: 3,
                borderRadius: '2px',
                backgroundColor: theme.palette.primary.main,
                boxShadow: `0 0 8px ${theme.palette.primary.main}`,
              },
            }}
          >
            {pluginTabs.map(tab => (
              <Tab key={tab.label} label={tab.label} icon={tab.icon} />
            ))}
          </Tabs>

          {/* 操作按钮组 */}
          <Stack direction="row" spacing={1} sx={{ pl: 2, flexShrink: 0 }}>
            {isMobile ? (
              // 移动端：只显示更多操作按钮
              <>
                <IconButton
                  size="small"
                  onClick={event => setMoreMenuAnchorEl(event.currentTarget)}
                  sx={{ border: 1, borderColor: 'divider' }}
                >
                  <MoreVertIcon />
                </IconButton>
                <Menu
                  anchorEl={moreMenuAnchorEl}
                  open={Boolean(moreMenuAnchorEl)}
                  onClose={() => setMoreMenuAnchorEl(null)}
                  transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                  anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
                >
                  {!plugin.isBuiltin && (
                    <MenuItem
                      onClick={() => {
                        if (plugin.isPackage) {
                          setDeleteConfirmOpen(true)
                        } else {
                          handleNavigateToEditor()
                        }
                        setMoreMenuAnchorEl(null)
                      }}
                      sx={{ color: plugin.isPackage ? 'error.main' : 'warning.main' }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {plugin.isPackage ? (
                          <DeleteIcon fontSize="small" />
                        ) : (
                          <EditIcon fontSize="small" />
                        )}
                        {plugin.isPackage ? t('actions.delete') : t('actions.edit')}
                      </Box>
                    </MenuItem>
                  )}
                  {plugin.isPackage && (
                    <MenuItem
                      onClick={() => {
                        setUpdateConfirmOpen(true)
                        setMoreMenuAnchorEl(null)
                      }}
                      sx={{ color: 'success.main' }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <RefreshIcon fontSize="small" />
                        {t('actions.update')}
                      </Box>
                    </MenuItem>
                  )}
                  <MenuItem
                    onClick={() => {
                      setResetDataConfirmOpen(true)
                      setMoreMenuAnchorEl(null)
                    }}
                    disabled={plugin.loadFailed}
                    sx={{ color: plugin.loadFailed ? 'text.disabled' : 'warning.main' }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <DeleteIcon fontSize="small" />
                      {t('actions.reset')}
                    </Box>
                  </MenuItem>
                  <MenuItem
                    onClick={() => {
                      setReloadConfirmOpen(true)
                      setMoreMenuAnchorEl(null)
                    }}
                    disabled={plugin.isBuiltin || (plugin.loadFailed && plugin.isPackage)}
                    sx={{
                      color:
                        plugin.isBuiltin || (plugin.loadFailed && plugin.isPackage)
                          ? 'text.disabled'
                          : 'primary.main',
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <RefreshIcon fontSize="small" />
                      {t('actions.reload')}
                    </Box>
                  </MenuItem>
                </Menu>
              </>
            ) : (
              // 桌面端：显示所有按钮
              <>
                {!plugin.isBuiltin && (
                  <Button
                    variant="outlined"
                    startIcon={plugin.isPackage ? <DeleteIcon /> : <EditIcon />}
                    onClick={() =>
                      plugin.isPackage ? setDeleteConfirmOpen(true) : handleNavigateToEditor()
                    }
                    color={plugin.isPackage ? 'error' : 'warning'}
                    size="small"
                  >
                    {plugin.isPackage ? t('actions.delete') : t('actions.edit')}
                  </Button>
                )}
                {plugin.isPackage && (
                  <Button
                    variant="outlined"
                    startIcon={<RefreshIcon />}
                    onClick={() => setUpdateConfirmOpen(true)}
                    color="success"
                    size="small"
                  >
                    {t('actions.update')}
                  </Button>
                )}
                <Button
                  variant="outlined"
                  startIcon={<DeleteIcon />}
                  onClick={() => setResetDataConfirmOpen(true)}
                  disabled={plugin.loadFailed}
                  color="warning"
                  size="small"
                >
                  {t('actions.reset')}
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<RefreshIcon />}
                  onClick={() => setReloadConfirmOpen(true)}
                  disabled={plugin.isBuiltin || (plugin.loadFailed && plugin.isPackage)}
                  size="small"
                >
                  {t('actions.reload')}
                </Button>
              </>
            )}
          </Stack>
        </Box>
      </Card>

      {/* 选项卡内容 */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {activeTab === 0 && (
          <Stack spacing={2}>
            {/* 插件信息 */}
            <Card sx={CARD_VARIANTS.default.styles}>
              <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                {plugin.loadFailed ? (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    <Typography sx={{ fontWeight: 600, mb: 1 }}>
                      {t('status.loadFailed')}
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                      {plugin.description}
                    </Typography>
                    {plugin.errorType && (
                      <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
                        {t('info.errorType')}：{plugin.errorType}
                      </Typography>
                    )}
                    {plugin.filePath && (
                      <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                        {t('info.filePath')}：{plugin.filePath}
                      </Typography>
                    )}
                    {plugin.stackTrace && (
                      <Button
                        size="small"
                        onClick={() => setErrorDetailOpen(true)}
                        sx={{ mt: 1.5, textTransform: 'none' }}
                      >
                        {t('actions.viewDetails')}
                      </Button>
                    )}
                  </Alert>
                ) : (
                  <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.6, mb: 3 }}>
                    {getPluginDescription(plugin, i18n.language)}
                  </Typography>
                )}
                <Divider />
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' },
                    gap: 2,
                    mt: 3,
                  }}
                >
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <PersonIcon color="action" />
                    <Typography variant="body2">
                      <strong>{t('info.author')}：</strong> {plugin.author}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <VpnKeyIcon color="action" />
                    <Typography variant="body2">
                      <strong>{t('info.moduleName')}：</strong> {plugin.moduleName}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <BookmarkIcon color="action" />
                    <Typography variant="body2">
                      <strong>{t('info.version')}：</strong> {plugin.version}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <CategoryIcon color="action" />
                    <Typography variant="body2">
                      <strong>{t('info.type')}：</strong> {getPluginTypeText()}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <LinkIcon color="action" />
                    <Typography variant="body2">
                      <strong>{t('info.link')}：</strong>{' '}
                      <Link
                        href={plugin.url}
                        target="_blank"
                        rel="noreferrer"
                        sx={{ verticalAlign: 'middle' }}
                      >
                        {plugin.url || t('info.none')}
                      </Link>
                    </Typography>
                  </Stack>
                </Box>
              </CardContent>
            </Card>

            {/* 插件文档 */}
            {docsLoading ? (
              <Card sx={CARD_VARIANTS.default.styles}>
                <CardContent sx={{ textAlign: 'center', p: 3 }}>
                  <CircularProgress size={32} />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    {t('info.loadingDocs')}
                  </Typography>
                </CardContent>
              </Card>
            ) : docsError ? (
              <Alert severity="error" sx={{ m: 2 }}>
                {t('info.loadDocsFailed')}：{(docsError as Error).message}
              </Alert>
            ) : pluginDocs?.exists ? (
              <Card sx={CARD_VARIANTS.default.styles}>
                <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                    <DescriptionIcon color="primary" />
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {t('info.pluginDocs')}
                    </Typography>
                  </Box>
                  <MarkdownRenderer>{pluginDocs.docs || ''}</MarkdownRenderer>
                </CardContent>
              </Card>
            ) : (
              <Alert severity="info" icon={<InfoIcon />}>
                {t('info.noDocs')}
              </Alert>
            )}
          </Stack>
        )}

        {/* 配置项 */}
        {plugin.hasConfig && activeTab === 1 && (
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
                emptyMessage={t('config.noConfig')}
              />
            ) : (
              <Card sx={CARD_VARIANTS.default.styles}>
                <CardContent>
                  <Alert severity="info">{t('config.noConfig')}</Alert>
                </CardContent>
              </Card>
            )}
          </Box>
        )}

        {/* 方法列表 */}
        {activeTab === (plugin.hasConfig ? 2 : 1) && (
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              {plugin.methods && plugin.methods.length > 0 ? (
                <TableContainer>
                  <Table size={isSmall ? 'small' : 'medium'}>
                    <TableHead>
                      <TableRow>
                        <TableCell width={isMobile ? '30%' : '20%'} sx={{ py: isSmall ? 1 : 1.5 }}>
                          {t('methods.name')}
                        </TableCell>
                        <TableCell width={isMobile ? '25%' : '15%'} sx={{ py: isSmall ? 1 : 1.5 }}>
                          {t('methods.type')}
                        </TableCell>
                        <TableCell sx={{ py: isSmall ? 1 : 1.5 }}>
                          {t('methods.description')}
                        </TableCell>
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
                              title={t(`methodDescriptions.${method.type}`)}
                              arrow
                              placement="top"
                            >
                              <Chip
                                label={t(`methodTypes.${method.type}`)}
                                color={methodTypeColors[method.type]}
                                size="small"
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
                  {t('methods.noMethods')}
                </Alert>
              )}
            </CardContent>
          </Card>
        )}

        {/* Webhook 列表 */}
        {activeTab === (plugin.hasConfig ? 3 : 2) && (
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ p: isSmall ? 1.5 : 2 }}>
              {plugin.webhooks && plugin.webhooks.length > 0 ? (
                <TableContainer>
                  <Table size={isSmall ? 'small' : 'medium'}>
                    <TableHead>
                      <TableRow>
                        <TableCell width={isSmall ? 100 : 150} sx={{ py: isSmall ? 1 : 1.5 }}>
                          {t('webhook.endpoint')}
                        </TableCell>
                        <TableCell sx={{ py: isSmall ? 1 : 1.5 }}>{t('webhook.name')}</TableCell>
                        <TableCell
                          width={isSmall ? 80 : 132}
                          align="center"
                          sx={{ py: isSmall ? 1 : 1.5 }}
                        >
                          {t('webhook.actions')}
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
                                  notification.success(t('webhook.copied'))
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
                                {t('webhook.copy')}
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
                                borderBottom: expandedRows.has(webhook.endpoint)
                                  ? undefined
                                  : 'none',
                              }}
                            >
                              <Collapse
                                in={expandedRows.has(webhook.endpoint)}
                                timeout="auto"
                                unmountOnExit
                              >
                                <Box sx={{ py: 2 }}>
                                  <Typography variant="subtitle2" gutterBottom>
                                    {t('webhook.description')}
                                  </Typography>
                                  <Typography
                                    variant="body2"
                                    color="text.secondary"
                                    sx={{
                                      pl: 2,
                                      fontSize: isSmall ? '0.75rem' : '0.875rem',
                                    }}
                                  >
                                    {webhook.description || t('data.noData')}
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
                  {t('webhook.noEndpoints') || 'No webhook endpoints defined for this plugin.'}
                </Alert>
              )}
            </CardContent>
          </Card>
        )}

        {/* 数据管理 */}
        {activeTab === 4 && (
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent>
              {isDataLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', pt: 4 }}>
                  <CircularProgress />
                </Box>
              ) : pluginData.length > 0 ? (
                <TableContainer>
                  <Table size={isSmall ? 'small' : 'medium'}>
                    <TableHead>
                      <TableRow>
                        <TableCell width={isMobile ? 80 : 150}>{t('data.channel')}</TableCell>
                        <TableCell width={isMobile ? 80 : 150}>{t('data.user')}</TableCell>
                        <TableCell>{t('data.storageKey')}</TableCell>
                        <TableCell width={isMobile ? 100 : 132} align="center">
                          {t('data.actions')}
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
                                {data.target_chat_key || t('data.global')}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography
                                variant="body2"
                                sx={{ fontSize: isSmall ? '0.7rem' : '0.875rem' }}
                              >
                                {data.target_user_id || t('data.global')}
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
                                    notification.success(t('messages.dataCopied'))
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
                                  {t('actions.copy')}
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
                                  {t('data.delete')}
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
                                    {t('data.value')}
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
                  {t('data.noData')}
                </Alert>
              )}
            </CardContent>
          </Card>
        )}
      </Box>

      {/* 重置数据确认对话框 */}
      <Dialog open={resetDataConfirmOpen} onClose={() => setResetDataConfirmOpen(false)}>
        <DialogTitle>{t('dialogs.resetTitle')}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t('dialogs.resetMessage', { name: plugin.name })}</DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setResetDataConfirmOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('actions.cancel')}
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
            {t('actions.confirm')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 重载确认对话框 */}
      <Dialog open={reloadConfirmOpen} onClose={() => setReloadConfirmOpen(false)}>
        <DialogTitle>{t('dialogs.reloadTitle')}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t('dialogs.reloadMessage', { name: plugin.name })}</DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setReloadConfirmOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('actions.cancel')}
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
            {t('actions.confirm')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除云端插件确认对话框 */}
      <Dialog open={deleteConfirmOpen} onClose={() => setDeleteConfirmOpen(false)}>
        <DialogTitle>{t('dialogs.deleteTitle')}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t('dialogs.deleteMessage', { name: plugin.name })}</DialogContentText>
          <FormControlLabel
            control={
              <Switch
                checked={clearDataOnDelete}
                onChange={e => setClearDataOnDelete(e.target.checked)}
                color="error"
              />
            }
            label={t('dialogs.deleteDataOption')}
            sx={{ mt: 2, mb: 1 }}
          />
          {clearDataOnDelete && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              {t('dialogs.deleteDataWarning')}
            </Alert>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => {
              setDeleteConfirmOpen(false)
              setClearDataOnDelete(false) // 重置勾选状态
            }}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('actions.cancel')}
          </Button>
          <Button
            onClick={() => {
              removePackageMutation.mutate()
              setDeleteConfirmOpen(false)
              setClearDataOnDelete(false) // 重置勾选状态
            }}
            color="error"
            variant="contained"
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('actions.confirm')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 更新云端插件确认对话框 */}
      <Dialog open={updateConfirmOpen} onClose={() => setUpdateConfirmOpen(false)} maxWidth="md">
        <DialogTitle>{t('dialogs.updateTitle')}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2" component="div">
              {t('dialogs.updateSecurityWarning')}
            </Typography>
          </Alert>

          <DialogContentText sx={{ mt: 2 }}>
            {t('dialogs.updateConfirmMessage', { name: plugin.name })}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setUpdateConfirmOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('actions.cancel')}
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
            {t('actions.confirm')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除数据确认对话框 */}
      <Dialog open={deleteDataConfirmOpen} onClose={() => setDeleteDataConfirmOpen(false)}>
        <DialogTitle>{t('dialogs.deleteDataTitle')}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t('dialogs.deleteDataMessage')}</DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setDeleteDataConfirmOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('actions.cancel')}
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
            {t('data.confirm')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 错误详情对话框 */}
      <Dialog open={errorDetailOpen} onClose={() => setErrorDetailOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{t('status.loadFailed')}</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
              {t('info.errorType')}
            </Typography>
            <Typography
              variant="body2"
              sx={{ fontFamily: 'monospace', mb: 2, p: 1.5, bgcolor: 'grey.100', borderRadius: 1 }}
            >
              {plugin.errorType}
            </Typography>

            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
              {t('info.filePath')}
            </Typography>
            <Typography
              variant="body2"
              sx={{ fontFamily: 'monospace', mb: 2, p: 1.5, bgcolor: 'grey.100', borderRadius: 1 }}
            >
              {plugin.filePath}
            </Typography>

            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
              {t('info.stackTrace')}
            </Typography>
            <Box
              sx={{
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                p: 1.5,
                bgcolor: 'grey.900',
                color: 'grey.100',
                borderRadius: 1,
                overflow: 'auto',
                maxHeight: '400px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {plugin.stackTrace}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setErrorDetailOpen(false)}
            sx={{ minWidth: { xs: 64, sm: 80 }, minHeight: { xs: 36, sm: 40 } }}
          >
            {t('actions.cancel')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default function PluginsManagementPage() {
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null)
  const queryClient = useQueryClient()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const [drawerOpen, setDrawerOpen] = useState(false)
  const notification = useNotification()
  const { t, i18n } = useTranslation('plugins')

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
      notification.success(t(variables.enabled ? 'status.enabled' : 'status.disabled'))

      // 如果是当前选中的插件，更新其状态
      if (selectedPlugin && selectedPlugin.id === variables.id) {
        setSelectedPlugin(prev => (prev ? { ...prev, enabled: variables.enabled } : null))
      }
    },
    onError: (error: Error) => {
      notification.error(t('messages.updateFailedWithMessage', { message: error.message }))
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

  const [searchTerm, setSearchTerm] = useState('')
  // 过滤插件列表
  const filteredPlugins = plugins
    .filter(
      plugin => {
        const name = getPluginName(plugin, i18n.language).toLowerCase()
        const description = getPluginDescription(plugin, i18n.language).toLowerCase()
        const search = searchTerm.toLowerCase()
        return name.includes(search) || description.includes(search)
      }
    )
    .sort((a, b) => {
      // 基础交互插件(模块名为"basic")固定放在最前面
      if (a.moduleName === 'basic') return -1
      if (b.moduleName === 'basic') return 1

      // 失败的插件排在最后
      if (a.loadFailed !== b.loadFailed) {
        return a.loadFailed ? 1 : -1
      }

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
      return getPluginName(a, i18n.language).localeCompare(getPluginName(b, i18n.language))
    })

  const pluginListContent = (
    <>
      <Box sx={{ p: 1.5, borderBottom: 1, borderColor: 'divider' }}>
        <TextField
          placeholder={t('list.search')}
          size="small"
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          variant="outlined"
          fullWidth
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
            },
          }}
        />
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : filteredPlugins.length > 0 ? (
          <List sx={{ flex: 1, padding: 0 }}>
            {filteredPlugins.map(plugin => (
              <React.Fragment key={plugin.id}>
                <ListItemButton
                  onClick={() => handleSelectPlugin(plugin)}
                  selected={selectedPlugin?.id === plugin.id}
                  sx={{
                    py: 1.5,
                    px: 2,
                    '&.Mui-selected': {
                      backgroundColor: theme.palette.action.selected,
                      '&:hover': {
                        backgroundColor: theme.palette.action.hover,
                      },
                    },
                  }}
                >
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      bgcolor: plugin.loadFailed
                        ? 'error.main'
                        : plugin.enabled
                        ? 'success.main'
                        : 'grey.400',
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
                          mb: 0.5,
                        }}
                      >
                        <Chip
                          label={t(`types.${getPluginType(plugin)}`)}
                          size="small"
                          color={pluginTypeColors[getPluginType(plugin)]}
                          sx={CHIP_VARIANTS.base(isSmall)}
                        />
                        <Typography
                          variant="body1"
                          sx={{
                            fontWeight: 'bold',
                            fontSize: '0.9rem',
                            ml: 0.5,
                          }}
                        >
                          {getPluginName(plugin, i18n.language)}
                        </Typography>
                        {plugin.hasConfig && (
                          <Tooltip title={t('list.hasConfig')}>
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
                          maxWidth: 240,
                          fontSize: isSmall ? '0.75rem' : 'inherit',
                          color: 'text.secondary',
                        }}
                      >
                        {getPluginDescription(plugin, i18n.language)}
                      </Typography>
                    }
                  />
                </ListItemButton>
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
              textAlign: 'center',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              {t('list.noMatch')}
            </Typography>
          </Box>
        )}
      </Box>
    </>
  )

  return (
    <Box
      sx={{
        display: 'flex',
        height: 'calc(100vh - 64px)',
        gap: 1,
        p: 2,
      }}
    >
      {isMobile ? (
        <>
          <Drawer
            anchor="left"
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            PaperProps={{
              sx: {
                width: isSmall ? '85%' : '75%',
                maxWidth: 320,
                boxShadow: 3,
                backgroundColor: 'transparent',
                backdropFilter: 'blur(20px)',
                borderRight: `1px solid ${theme.palette.divider}`,
                display: 'flex',
                flexDirection: 'column',
              },
            }}
          >
            {pluginListContent}
          </Drawer>

          {/* 移动端主内容区 */}
          <Box sx={{ flex: 1, overflow: 'auto' }}>
            {selectedPlugin ? (
              <PluginDetails
                plugin={selectedPlugin}
                onBack={() => setSelectedPlugin(null)}
                onToggleEnabled={handleToggleEnabled}
              />
            ) : (
              <Card
                sx={{
                  ...CARD_VARIANTS.default.styles,
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
                  {t('welcome.title')}
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  {t('welcome.hintMobile')}
                </Typography>
              </Card>
            )}
          </Box>
        </>
      ) : (
        // 桌面端布局
        <>
          {/* 左侧插件列表 */}
          <Card
            sx={{
              ...CARD_VARIANTS.default.styles,
              width: 320,
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {pluginListContent}
          </Card>

          {/* 右侧插件详情 */}
          <Box sx={{ flex: 1, overflow: 'auto' }}>
            {selectedPlugin ? (
              <PluginDetails
                plugin={selectedPlugin}
                onBack={() => setSelectedPlugin(null)}
                onToggleEnabled={handleToggleEnabled}
              />
            ) : (
              <Card
                sx={{
                  ...CARD_VARIANTS.default.styles,
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
                  {t('welcome.title')}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('welcome.hintDesktop')}
                </Typography>
              </Card>
            )}
          </Box>
        </>
      )}

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
