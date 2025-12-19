import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  TextField,
  InputAdornment,
  IconButton,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  useTheme,
  Divider,
  FormControlLabel,
  FormControl,
  MenuItem,
  Checkbox,
  Link,
  Menu,
  useMediaQuery,
  ListItemIcon,
  ListItemText,
  List,
  ListItem,
  ListItemButton,
  ListItemAvatar,
  Avatar,
} from '@mui/material'
import {
  Search as SearchIcon,
  CloudDownload as CloudDownloadIcon,
  Info as InfoIcon,
  Update as UpdateIcon,
  GitHub as GitHubIcon,
  Link as LinkIcon,
  Code as CodeIcon,
  Add as AddIcon,
  Extension as ExtensionIcon,
  RemoveCircle as RemoveCircleIcon,
  Close as CloseIcon,
  Edit as EditIcon,
  MoreVert as MoreVertIcon,
  Flag as FlagIcon,
  Star as StarIcon,
  CallSplit as ForkIcon,
  Visibility as VisibilityIcon,
  BugReport as IssueIcon,
  ChatBubbleOutline as CommentIcon,
} from '@mui/icons-material'
import {
  pluginsMarketApi,
  CloudPlugin,
  PluginCreateRequest,
  PluginUpdateRequest,
  PluginRepoInfo,
} from '../../services/api/cloud/plugins_market'
import { removePackage, updatePackage } from '../../services/api/plugins'
import { formatLastActiveTime } from '../../utils/time'
import PaginationStyled from '../../components/common/PaginationStyled'
import { UI_STYLES, BORDER_RADIUS } from '../../theme/themeConfig'
import { CARD_VARIANTS } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'
import { useTranslation } from 'react-i18next'

// 防抖自定义Hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  return debouncedValue
}

// 插件卡片组件
const PluginCard = ({
  plugin,
  onDownload,
  onUpdate,
  onRemove,
  onUnpublish,
  onShowDetail,
  t,
}: {
  plugin: CloudPlugin
  onDownload: () => void
  onUpdate: () => void
  onRemove: () => void
  onUnpublish?: () => void
  onShowDetail: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}) => {
  const theme = useTheme()
  // 移除 isDark 判断
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const [iconError, setIconError] = useState(false)

  // 更多菜单状态
  const [moreMenuAnchor, setMoreMenuAnchor] = useState<null | HTMLElement>(null)
  const isMoreMenuOpen = Boolean(moreMenuAnchor)

  const handleMoreClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setMoreMenuAnchor(event.currentTarget)
  }

  const handleMoreClose = () => {
    setMoreMenuAnchor(null)
  }

  const handleReport = (e: React.MouseEvent) => {
    e.stopPropagation()
    // 打开GitHub插件举报页面
    const reportUrl = `https://github.com/KroMiose/nekro-agent/issues/new?template=plugin_report.yml&plugin_name=${encodeURIComponent(plugin.name)}&module_name=${encodeURIComponent(plugin.moduleName)}&repo_url=${encodeURIComponent(plugin.githubUrl || plugin.cloneUrl || '')}`
    window.open(reportUrl, '_blank')
  }

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <CardContent sx={{ flexGrow: 1, p: 2.5, pb: 1 }}>
        <Box
          sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
            {/* 插件图标 */}
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 1,
                overflow: 'hidden',
                flexShrink: 0,
                border: '1px solid',
                borderColor: 'divider',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: theme =>
                  theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
              }}
            >
              {plugin.icon && !iconError ? (
                <img
                  src={plugin.icon}
                  alt={`${plugin.name} 图标`}
                  onError={() => setIconError(true)}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : (
                <ExtensionIcon
                  sx={{
                    fontSize: 28,
                    opacity: 0.7,
                    color: theme => theme.palette.primary.main,
                  }}
                />
              )}
            </Box>

            <Box sx={{ overflow: 'hidden', flex: 1 }}>
              <Typography
                variant="h6"
                component="h2"
                sx={{
                  fontSize: '1rem',
                  fontWeight: 600,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {plugin.name}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  fontSize: '0.8rem',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {t('pluginsMarket.author')}: {plugin.author}
              </Typography>
            </Box>
          </Box>
        </Box>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            mb: 2,
            minHeight: '2.5em',
            fontSize: '0.85rem',
          }}
        >
          {plugin.description}
        </Typography>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
          <Chip
            label={plugin.moduleName}
            size="small"
            sx={{
              height: 24,
              fontSize: '0.75rem',
              bgcolor: theme =>
                theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
            }}
          />
        </Box>
      </CardContent>

      <CardActions
        sx={{
          justifyContent: 'space-between',
          p: 1.5,
          bgcolor: UI_STYLES.SELECTED,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <Button size="small" variant="text" startIcon={<InfoIcon />} onClick={onShowDetail}>
            {t('pluginsMarket.details')}
          </Button>

          {isMobile ? (
            <>
              <IconButton size="small" onClick={handleMoreClick} color="inherit" sx={{ ml: 0.5 }}>
                <MoreVertIcon />
              </IconButton>

              <Menu
                anchorEl={moreMenuAnchor}
                open={isMoreMenuOpen}
                onClose={handleMoreClose}
                anchorOrigin={{
                  vertical: 'bottom',
                  horizontal: 'left',
                }}
              >
                {onUnpublish && (
                  <MenuItem
                    onClick={() => {
                      handleMoreClose()
                      onUnpublish()
                    }}
                    sx={{ color: 'error.main' }}
                  >
                    <ListItemIcon sx={{ color: 'error.main' }}>
                      <RemoveCircleIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={t('pluginsMarket.delist')} />
                  </MenuItem>
                )}

                <MenuItem
                  onClick={() => {
                    handleMoreClose()
                    handleReport(new MouseEvent('click') as unknown as React.MouseEvent)
                  }}
                  sx={{ color: 'warning.main' }}
                >
                  <ListItemIcon sx={{ color: 'warning.main' }}>
                    <FlagIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText primary={t('pluginsMarket.report')} />
                </MenuItem>
              </Menu>
            </>
          ) : (
            <>
              {onUnpublish && (
                <Button
                  size="small"
                  variant="text"
                  startIcon={<RemoveCircleIcon />}
                  onClick={onUnpublish}
                  color="error"
                >
                  {t('pluginsMarket.delist')}
                </Button>
              )}

              <Button
                size="small"
                variant="text"
                color="warning"
                onClick={handleReport}
                title={t('pluginsMarket.reportTitle')}
              >
                {t('pluginsMarket.report')}
              </Button>
            </>
          )}
        </Box>

        {plugin.is_local ? (
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {isMobile ? (
              <Button
                size="small"
                variant="contained"
                startIcon={<UpdateIcon />}
                onClick={onUpdate}
                color="primary"
                sx={{ mr: 1 }}
              >
                {t('pluginsMarket.update')}
              </Button>
            ) : (
              <Button
                size="small"
                variant="contained"
                startIcon={<UpdateIcon />}
                onClick={onUpdate}
                color="primary"
              >
                {t('pluginsMarket.update')}
              </Button>
            )}

            {!isMobile && (
              <Button size="small" variant="outlined" color="error" onClick={onRemove}>
                {t('pluginsMarket.remove')}
              </Button>
            )}
          </Box>
        ) : (
          <Button
            size="small"
            variant="contained"
            startIcon={<CloudDownloadIcon />}
            onClick={onDownload}
            color="primary"
          >
            {t('pluginsMarket.obtain')}
          </Button>
        )}
      </CardActions>
    </Card>
  )
}

// 详情对话框组件
const PluginDetailDialog = ({
  open,
  onClose,
  plugin,
  onUnpublish,
  onDownload,
  onUpdate,
  onRemove,
  onEdit,
  t,
}: {
  open: boolean
  onClose: () => void
  plugin: CloudPlugin | null
  onUnpublish?: () => void
  onDownload?: () => void
  onUpdate?: () => void
  onRemove?: () => void
  onEdit?: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}) => {
  const theme = useTheme()
  // 移除 isDark 判断
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const [iconError, setIconError] = useState(false)
  const [repoInfo, setRepoInfo] = useState<PluginRepoInfo | null>(null)
  const [loadingRepo, setLoadingRepo] = useState(false)

  // 更多菜单状态
  const [moreMenuAnchor, setMoreMenuAnchor] = useState<null | HTMLElement>(null)
  const isMoreMenuOpen = Boolean(moreMenuAnchor)

  const handleMoreClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setMoreMenuAnchor(event.currentTarget)
  }

  const handleMoreClose = () => {
    setMoreMenuAnchor(null)
  }

  // 举报功能
  const handleReport = () => {
    if (!plugin) return
    // 打开GitHub插件举报页面
    const reportUrl = `https://github.com/KroMiose/nekro-agent/issues/new?template=plugin_report.yml&plugin_name=${encodeURIComponent(plugin.name)}&module_name=${encodeURIComponent(plugin.moduleName)}&repo_url=${encodeURIComponent(plugin.githubUrl || plugin.cloneUrl || '')}`
    window.open(reportUrl, '_blank')
  }

  // 获取仓库信息
  useEffect(() => {
    if (open && plugin) {
      setRepoInfo(null)
      setLoadingRepo(true)
      pluginsMarketApi
        .getPluginRepoInfo(plugin.moduleName)
        .then(info => {
          setRepoInfo(info)
        })
        .catch(err => {
          console.error('Failed to fetch repo info:', err)
        })
        .finally(() => {
          setLoadingRepo(false)
        })
    }
  }, [open, plugin])

  if (!plugin) return null

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      scroll="paper"
      PaperProps={{
        sx: {
          ...CARD_VARIANTS.default.styles,
          overflow: 'hidden',
        },
      }}
    >
      <DialogTitle
        sx={{
          px: 3,
          py: 2,
          background: UI_STYLES.SELECTED,
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Typography variant="h6">
          {t('pluginsMarket.pluginDetail')}: {plugin.name}
        </Typography>
        <IconButton
          color="default"
          onClick={onClose}
          size="small"
          sx={{
            position: 'absolute',
            right: 8,
            top: 8,
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers sx={{ p: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={4} md={3}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2.5 }}>
              {/* 插件图标 */}
              <Box
                sx={{
                  width: '100%',
                  aspectRatio: '1',
                  borderRadius: 2,
                  overflow: 'hidden',
                  border: '1px solid',
                  borderColor: 'divider',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: theme =>
                    theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                }}
              >
                {plugin.icon && !iconError ? (
                  <img
                    src={plugin.icon}
                    alt={`${plugin.name} 图标`}
                    onError={() => setIconError(true)}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <ExtensionIcon
                    sx={{
                      fontSize: 64,
                      opacity: 0.7,
                      color: theme => theme.palette.primary.main,
                    }}
                  />
                )}
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12} sm={8} md={9}>
            <Typography variant="h5" gutterBottom fontWeight={600}>
              {plugin.name}{' '}
              <Typography component="span" color="text.secondary">
                ({plugin.moduleName})
              </Typography>
            </Typography>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" color="text.secondary" gutterBottom>
                {t('pluginsMarket.author')}: {plugin.author || t('pluginsMarket.unknownAuthor')}
                {plugin.version && (
                  <Typography component="span" ml={2} color="primary.main">
                    {t('pluginsMarket.version')}: {plugin.version}
                  </Typography>
                )}
              </Typography>
              <Typography
                variant="body1"
                paragraph
                sx={{
                  backgroundColor: UI_STYLES.GRADIENTS.CARD.DEFAULT,
                  p: 2,
                  borderRadius: BORDER_RADIUS.SMALL,
                  borderLeft: '4px solid',
                  borderColor: 'primary.main',
                  mt: 1,
                }}
              >
                {plugin.description || t('pluginsMarket.noDescription')}
              </Typography>

              {/* 仓库统计信息 - 始终显示，使用占位符 */}
              <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <Chip
                  icon={<StarIcon sx={{ color: '#e3b341 !important' }} />}
                  label={repoInfo ? `${repoInfo.stargazersCount} Stars` : '- Stars'}
                  size="small"
                  variant="outlined"
                  onClick={
                    repoInfo ? () => window.open(repoInfo.stargazersUrl, '_blank') : undefined
                  }
                  sx={{ cursor: repoInfo ? 'pointer' : 'default' }}
                />
                <Chip
                  icon={<ForkIcon />}
                  label={repoInfo ? `${repoInfo.forksCount} Forks` : '- Forks'}
                  size="small"
                  variant="outlined"
                  onClick={repoInfo ? () => window.open(repoInfo.forksUrl, '_blank') : undefined}
                  sx={{ cursor: repoInfo ? 'pointer' : 'default' }}
                />
                <Chip
                  icon={<VisibilityIcon />}
                  label={repoInfo ? `${repoInfo.watchersCount} Watchers` : '- Watchers'}
                  size="small"
                  variant="outlined"
                />
                <Chip
                  icon={
                    <IssueIcon
                      color={repoInfo && repoInfo.openIssuesCount > 0 ? 'warning' : 'success'}
                    />
                  }
                  label={repoInfo ? `${repoInfo.openIssuesCount} Issues` : '- Issues'}
                  size="small"
                  variant="outlined"
                  onClick={repoInfo ? () => window.open(repoInfo.issuesUrl, '_blank') : undefined}
                  sx={{ cursor: repoInfo ? 'pointer' : 'default' }}
                />
              </Box>

              <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 2, mt: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    {t('presetsMarket.createdAt')}:
                  </Typography>
                  <Typography variant="body2">
                    {formatLastActiveTime(new Date(plugin.createdAt).getTime() / 1000)}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    {t('presetsMarket.updatedAt')}:
                  </Typography>
                  <Typography variant="body2">
                    {formatLastActiveTime(new Date(plugin.updatedAt).getTime() / 1000)}
                  </Typography>
                </Box>
              </Box>
            </Box>

            <Divider sx={{ mb: 2.5 }} />

            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                {t('pluginsMarket.linksAndInfo')}
              </Typography>
              <Grid container spacing={2}>
                {plugin.homepageUrl && (
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={<LinkIcon />}
                      onClick={() => window.open(plugin.homepageUrl, '_blank')}
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      {t('pluginsMarket.pluginHomepage')}
                    </Button>
                  </Grid>
                )}
                {plugin.githubUrl && (
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={<GitHubIcon />}
                      onClick={() => window.open(plugin.githubUrl, '_blank')}
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      {t('pluginsMarket.githubRepo')}
                    </Button>
                  </Grid>
                )}
                {plugin.cloneUrl && (
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={<CodeIcon />}
                      onClick={() => navigator.clipboard.writeText(plugin.cloneUrl)}
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      {t('pluginsMarket.copyCloneLink')}
                    </Button>
                  </Grid>
                )}
                {plugin.licenseType && (
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      disabled
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      {t('pluginsMarket.licenseType')}: {plugin.licenseType}
                    </Button>
                  </Grid>
                )}
              </Grid>
            </Box>
          </Grid>

          {/* 仓库动态 - 平铺展示 */}
          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Typography variant="h6" gutterBottom>
              仓库动态
            </Typography>
            {loadingRepo ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress size={24} />
              </Box>
            ) : repoInfo && repoInfo.recentIssues && repoInfo.recentIssues.length > 0 ? (
              <List>
                {repoInfo.recentIssues.map(issue => (
                  <ListItem
                    key={issue.number}
                    disablePadding
                    sx={{
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 1,
                      mb: 1,
                    }}
                  >
                    <ListItemButton
                      alignItems="flex-start"
                      onClick={() => window.open(issue.htmlUrl, '_blank')}
                    >
                      <ListItemAvatar>
                        <Avatar alt={issue.user.login} src={issue.user.avatarUrl} />
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Box
                            sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}
                          >
                            <Typography variant="subtitle1" component="span">
                              #{issue.number} {issue.title}
                            </Typography>
                            <Chip
                              label={issue.state === 'open' ? '进行中' : '已关闭'}
                              size="small"
                              color={issue.state === 'open' ? 'success' : 'default'}
                              variant="outlined"
                              sx={{ height: 20, fontSize: '0.7rem' }}
                            />
                          </Box>
                        }
                        secondary={
                          <Box
                            component="span"
                            sx={{ display: 'flex', flexDirection: 'column', mt: 0.5 }}
                          >
                            <Typography component="span" variant="body2" color="text.primary">
                              {issue.user.login}
                            </Typography>
                            <Box
                              component="span"
                              sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}
                            >
                              <Typography variant="caption" color="text.secondary">
                                更新于{' '}
                                {formatLastActiveTime(new Date(issue.updatedAt).getTime() / 1000)}
                              </Typography>
                              {issue.comments > 0 && (
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  <CommentIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                                  <Typography variant="caption" color="text.secondary">
                                    {issue.comments}
                                  </Typography>
                                </Box>
                              )}
                            </Box>
                            {issue.labels.length > 0 && (
                              <Box sx={{ display: 'flex', gap: 0.5, mt: 1, flexWrap: 'wrap' }}>
                                {issue.labels.map(label => (
                                  <Chip
                                    key={label.name}
                                    label={label.name}
                                    size="small"
                                    sx={{
                                      height: 20,
                                      fontSize: '0.7rem',
                                      backgroundColor: `#${label.color}`,
                                      color:
                                        parseInt(label.color, 16) > 0xffffff / 2 ? '#000' : '#fff',
                                    }}
                                  />
                                ))}
                              </Box>
                            )}
                          </Box>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            ) : !loadingRepo && repoInfo ? (
              <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
                暂无最近动态
              </Typography>
            ) : (
              <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
                无法获取仓库信息
              </Typography>
            )}
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions
        sx={{
          px: 3,
          py: 2,
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'space-between',
          gap: isMobile ? 2 : 0,
        }}
      >
        {isMobile ? (
          // 移动端布局 - 全部操作放入两个按钮组
          <>
            <Box sx={{ display: 'flex', width: '100%', gap: 1 }}>
              {plugin.is_local ? (
                <>
                  <Button
                    variant="contained"
                    startIcon={<UpdateIcon />}
                    color="primary"
                    onClick={onUpdate}
                    fullWidth
                  >
                    更新
                  </Button>
                  <Button variant="outlined" color="error" onClick={onRemove} fullWidth>
                    移除
                  </Button>
                </>
              ) : (
                <Button
                  variant="contained"
                  startIcon={<CloudDownloadIcon />}
                  color="primary"
                  onClick={onDownload}
                  fullWidth
                >
                  获取插件
                </Button>
              )}
            </Box>

            <Box sx={{ display: 'flex', width: '100%' }}>
              <Button
                variant="outlined"
                color="inherit"
                startIcon={<MoreVertIcon />}
                onClick={handleMoreClick}
                fullWidth
              >
                更多操作
              </Button>

              <Menu
                anchorEl={moreMenuAnchor}
                open={isMoreMenuOpen}
                onClose={handleMoreClose}
                anchorOrigin={{
                  vertical: 'top',
                  horizontal: 'center',
                }}
              >
                <MenuItem
                  onClick={() => {
                    handleMoreClose()
                    handleReport()
                  }}
                >
                  <ListItemIcon>
                    <FlagIcon fontSize="small" color="warning" />
                  </ListItemIcon>
                  <ListItemText primary="举报插件" />
                </MenuItem>

                {plugin.isOwner && (
                  <>
                    <MenuItem
                      onClick={() => {
                        handleMoreClose()
                        onUnpublish?.()
                      }}
                    >
                      <ListItemIcon>
                        <RemoveCircleIcon fontSize="small" color="error" />
                      </ListItemIcon>
                      <ListItemText primary="下架插件" />
                    </MenuItem>
                    <MenuItem
                      onClick={() => {
                        handleMoreClose()
                        onEdit?.()
                      }}
                    >
                      <ListItemIcon>
                        <EditIcon fontSize="small" color="primary" />
                      </ListItemIcon>
                      <ListItemText primary="编辑信息" />
                    </MenuItem>
                  </>
                )}
              </Menu>
            </Box>
          </>
        ) : (
          // 桌面端布局 - 保持原有左右排列
          <>
            <Box>
              <Button variant="outlined" color="warning" onClick={handleReport} sx={{ mr: 1 }}>
                举报插件
              </Button>
              {plugin.isOwner && (
                <>
                  <Button variant="outlined" color="error" onClick={onUnpublish} sx={{ mr: 1 }}>
                    下架插件
                  </Button>
                  <Button variant="outlined" color="primary" onClick={onEdit} sx={{ mr: 1 }}>
                    编辑信息
                  </Button>
                </>
              )}
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              {plugin.is_local ? (
                <>
                  <Button
                    variant="contained"
                    startIcon={<UpdateIcon />}
                    color="primary"
                    onClick={onUpdate}
                  >
                    同步最新
                  </Button>
                  <Button variant="outlined" color="error" onClick={onRemove}>
                    移除插件
                  </Button>
                </>
              ) : (
                <Button
                  variant="contained"
                  startIcon={<CloudDownloadIcon />}
                  color="primary"
                  onClick={onDownload}
                >
                  获取插件
                </Button>
              )}
            </Box>
          </>
        )}
      </DialogActions>
    </Dialog>
  )
}

// 创建插件表单对话框
const CreatePluginDialog = ({
  open,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (data: PluginCreateRequest) => void
  isSubmitting: boolean
}) => {
  const [formData, setFormData] = useState<PluginCreateRequest>({
    name: '',
    moduleName: '',
    description: '',
    author: '',
    hasWebhook: false,
    homepageUrl: '',
    githubUrl: '',
    cloneUrl: '',
    licenseType: 'MIT',
    isSfw: true,
    icon: '', // 添加图标字段
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [iconPreview, setIconPreview] = useState<string | null>(null)
  const [agreeToTerms, setAgreeToTerms] = useState(false)
  const [confirmSafeContent, setConfirmSafeContent] = useState(false)

  // 重置表单
  useEffect(() => {
    if (open) {
      setFormData({
        name: '',
        moduleName: '',
        description: '',
        author: '',
        hasWebhook: false,
        homepageUrl: '',
        githubUrl: '',
        cloneUrl: '',
        licenseType: 'MIT',
        isSfw: true,
        icon: '',
      })
      setErrors({})
      setIconPreview(null)
      setAgreeToTerms(false)
      setConfirmSafeContent(false)
    }
  }, [open])

  // 处理输入变化
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | { name?: string; value: unknown }>
  ) => {
    const { name, value } = e.target
    if (name) {
      setFormData(prev => ({ ...prev, [name]: value }))

      // GitHub URL自动填充Git克隆URL的逻辑
      if (name === 'githubUrl' && typeof value === 'string') {
        const githubUrl = value.trim()
        // 如果Git克隆URL为空或等于旧的GitHub URL + .git，则自动填充
        if (!formData.cloneUrl || formData.cloneUrl === formData.githubUrl + '.git') {
          if (githubUrl) {
            setFormData(prev => ({ ...prev, cloneUrl: githubUrl + '.git' }))

            // 当自动填充克隆URL时，同时清除克隆URL的错误
            if (errors.cloneUrl) {
              setErrors(prev => {
                const newErrors = { ...prev }
                delete newErrors.cloneUrl
                return newErrors
              })
            }
          } else {
            setFormData(prev => ({ ...prev, cloneUrl: '' }))
          }
        }
      }

      // 清除错误
      if (errors[name]) {
        setErrors(prev => {
          const newErrors = { ...prev }
          delete newErrors[name]
          return newErrors
        })
      }
    }
  }

  // 处理SFW确认变更
  const handleSfwChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setConfirmSafeContent(e.target.checked)
    // 同时更新formData中的isSfw值
    setFormData(prev => ({ ...prev, isSfw: e.target.checked }))
  }

  // 验证表单
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name?.trim()) {
      newErrors.name = '插件名称不能为空'
    }

    if (!formData.moduleName.trim()) {
      newErrors.moduleName = '模块名不能为空'
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.moduleName)) {
      newErrors.moduleName = '模块名只能包含英文、数字和下划线，并且在插件市场唯一'
    }

    if (!formData.description?.trim()) {
      newErrors.description = '插件描述不能为空'
    }

    if (!formData.author?.trim()) {
      newErrors.author = '作者不能为空'
    }

    if (!formData.githubUrl) {
      newErrors.githubUrl = 'GitHub 仓库 URL 不能为空'
    } else if (!/^https?:\/\/github\.com\//.test(formData.githubUrl)) {
      newErrors.githubUrl = 'GitHub URL 格式不正确'
    }

    if (!formData.cloneUrl) {
      newErrors.cloneUrl = 'Git 克隆 URL 不能为空'
    } else if (!/\.git$/.test(formData.cloneUrl)) {
      newErrors.cloneUrl = '克隆URL格式不正确，应以.git结尾'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // 处理提交
  const handleSubmit = () => {
    if (validateForm()) {
      onSubmit(formData)
    }
  }

  // 处理图标上传
  const handleIconUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 10 * 1024 * 1024) {
      setErrors(prev => ({
        ...prev,
        icon: '图片太大啦，最大支持10MB～',
      }))
      return
    }

    try {
      const base64Icon = await imageToBase64(file)
      setFormData(prev => ({ ...prev, icon: base64Icon }))
      setIconPreview(base64Icon)

      // 清除错误
      if (errors.icon) {
        setErrors(prev => {
          const newErrors = { ...prev }
          delete newErrors.icon
          return newErrors
        })
      }
    } catch (error) {
      console.error('图标转换失败:', error)
      setErrors(prev => ({
        ...prev,
        icon: '图标处理失败，请重试',
      }))
    }
  }

  // 图片转Base64函数
  const imageToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = error => reject(error)
    })
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          ...CARD_VARIANTS.default.styles,
          overflow: 'hidden',
        },
      }}
    >
      <DialogTitle sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
        发布新插件
      </DialogTitle>
      <DialogContent sx={{ pt: 3, mt: 3 }}>
        <Grid container spacing={3}>
          {/* 基本信息（左）和图标上传（右）并排布局 */}
          <Grid item xs={12} sm={6}>
            <Typography variant="subtitle1" gutterBottom fontWeight={500} sx={{ mb: 2 }}>
              基本信息
            </Typography>

            <TextField
              name="name"
              label="插件名称"
              value={formData.name}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.name}
              helperText={errors.name}
              disabled={isSubmitting}
              sx={{ mb: 2 }}
            />

            <TextField
              name="moduleName"
              label="模块名"
              value={formData.moduleName}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.moduleName}
              helperText={
                errors.moduleName || '模块名只能包含英文、数字和下划线，并且在插件市场唯一'
              }
              disabled={isSubmitting}
            />
          </Grid>

          {/* 插件图标上传 */}
          <Grid item xs={12} sm={6}>
            <Typography variant="subtitle1" gutterBottom fontWeight={500} sx={{ mb: 2 }}>
              插件图标
            </Typography>

            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 2,
              }}
            >
              <Box
                sx={{
                  width: 100,
                  height: 100,
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: theme =>
                    theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                }}
              >
                {iconPreview ? (
                  <img
                    src={iconPreview}
                    alt="插件图标预览"
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <ExtensionIcon
                    sx={{
                      fontSize: 48,
                      opacity: 0.7,
                      color: theme => theme.palette.primary.main,
                    }}
                  />
                )}
              </Box>
              <Box>
                <Button variant="outlined" component="label" disabled={isSubmitting} sx={{ mb: 1 }}>
                  选择图标
                  <input
                    type="file"
                    hidden
                    accept="image/*"
                    onChange={handleIconUpload}
                    disabled={isSubmitting}
                  />
                </Button>
                <Typography variant="caption" color="text.secondary" display="block">
                  建议尺寸: 128x128像素
                  <br />
                  支持格式: PNG, JPG, GIF
                  <br />
                  大小限制: 10MB (自动压缩至 500 KB)
                </Typography>
                {errors.icon && (
                  <Typography variant="caption" color="error" sx={{ mt: 1 }}>
                    {errors.icon}
                  </Typography>
                )}
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12}>
            <TextField
              name="description"
              label="插件描述"
              value={formData.description}
              onChange={handleChange}
              fullWidth
              required
              multiline
              rows={3}
              error={!!errors.description}
              helperText={errors.description}
              disabled={isSubmitting}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              name="author"
              label="作者"
              value={formData.author}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.author}
              helperText={errors.author}
              disabled={isSubmitting}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth disabled={isSubmitting}>
              <TextField
                select
                name="licenseType"
                label="许可证类型"
                value={formData.licenseType}
                onChange={handleChange}
                fullWidth
              >
                <MenuItem value="MIT">MIT</MenuItem>
                <MenuItem value="Apache-2.0">Apache-2.0</MenuItem>
                <MenuItem value="GPL-3.0">GPL-3.0</MenuItem>
                <MenuItem value="BSD-3-Clause">BSD-3-Clause</MenuItem>
                <MenuItem value="UNLICENSED">UNLICENSED</MenuItem>
                <MenuItem value="CUSTOM">自定义（参考描述）</MenuItem>
              </TextField>
            </FormControl>
          </Grid>
          <Grid item xs={12}>
            <TextField
              name="githubUrl"
              label="GitHub 仓库URL"
              value={formData.githubUrl}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.githubUrl}
              helperText={errors.githubUrl}
              placeholder="https://github.com/username/repo"
              disabled={isSubmitting}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              name="cloneUrl"
              label="Git 克隆URL"
              value={formData.cloneUrl}
              onChange={handleChange}
              fullWidth
              required
              error={!!errors.cloneUrl}
              helperText={errors.cloneUrl}
              placeholder="https://github.com/username/repo.git"
              disabled={isSubmitting}
            />
          </Grid>

          {/* 添加分割线和确认选项 */}
          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle1" color="text.secondary" gutterBottom>
              发布确认
            </Typography>
          </Grid>

          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={confirmSafeContent}
                  onChange={handleSfwChange}
                  disabled={isSubmitting}
                />
              }
              label="我确认这是符合社区内容规则的安全内容(SFW)"
            />
          </Grid>

          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={agreeToTerms}
                  onChange={e => setAgreeToTerms(e.target.checked)}
                  disabled={isSubmitting}
                />
              }
              label={
                <Box component="span" sx={{ display: 'flex', alignItems: 'center' }}>
                  我已阅读并接受{' '}
                  <Link
                    href="https://community.nekro.ai/terms"
                    target="_blank"
                    underline="hover"
                    sx={{ ml: 0.5 }}
                  >
                    《NekroAI 社区资源共享协议》
                  </Link>
                </Box>
              }
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Button onClick={onClose} disabled={isSubmitting}>
          取消
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          color="primary"
          disabled={isSubmitting || !agreeToTerms || !confirmSafeContent}
          startIcon={isSubmitting ? <CircularProgress size={20} /> : <AddIcon />}
        >
          {isSubmitting ? '提交中...' : '发布插件'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default function PluginsMarket() {
  const [plugins, setPlugins] = useState<CloudPlugin[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const debouncedSearchKeyword = useDebounce(searchKeyword, 800)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const [selectedPlugin, setSelectedPlugin] = useState<CloudPlugin | null>(null)
  const [processingId, setProcessingId] = useState<string | null>(null)
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean
    plugin: CloudPlugin | null
    action: 'download' | 'update' | 'unpublish' | 'remove'
  }>({
    open: false,
    plugin: null,
    action: 'download',
  })
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [editingPlugin, setEditingPlugin] = useState<CloudPlugin | null>(null)
  const pageSize = 12
  const notification = useNotification()
  const { t } = useTranslation('cloud')

  const fetchPlugins = useCallback(
    async (page: number, keyword: string = '') => {
      try {
        setLoading(true)
        setError(null)

        const data = await pluginsMarketApi.getList({
          page,
          page_size: pageSize,
          keyword: keyword || undefined,
        })

        setPlugins(data.items)
        setTotalPages(data.totalPages)

        if (data.items.length === 0 && data.total > 0 && page > 1) {
          // 如果当前页没有数据但总数大于0，说明可能是删除后的页码问题，回到第一页
          setCurrentPage(1)
          fetchPlugins(1, keyword)
        }
      } catch (error) {
        console.error('Failed to fetch plugins', error)
        setError(t('pluginsMarket.fetchFailed'))
      } finally {
        setLoading(false)
      }
    },
    [pageSize, setCurrentPage, setLoading, setError, setPlugins, setTotalPages, t]
  )

  useEffect(() => {
    fetchPlugins(currentPage, debouncedSearchKeyword)
  }, [fetchPlugins, currentPage, debouncedSearchKeyword])

  // 监听防抖后的搜索关键词变化，重置到第一页
  useEffect(() => {
    // 当搜索关键词变化时重置页码到第一页
    setCurrentPage(1)
  }, [debouncedSearchKeyword])

  const handlePageChange = (_event: React.ChangeEvent<unknown>, page: number) => {
    if (loading) return // 加载中禁止翻页
    setCurrentPage(page)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (loading) return // 加载中禁止搜索
    setCurrentPage(1)
    fetchPlugins(1, searchKeyword)
  }

  const handleSearchInputClear = () => {
    if (loading) return // 加载中禁止清空
    setSearchKeyword('')
    setCurrentPage(1)
    fetchPlugins(1, '')
  }

  const handleShowDetail = (plugin: CloudPlugin) => {
    setSelectedPlugin(plugin)
  }

  const handleDownloadClick = (plugin: CloudPlugin) => {
    setConfirmDialog({ open: true, plugin, action: 'download' })
  }

  const handleUpdateClick = (plugin: CloudPlugin) => {
    setConfirmDialog({ open: true, plugin, action: 'update' })
  }

  const handleUnpublishClick = (plugin: CloudPlugin) => {
    setConfirmDialog({ open: true, plugin, action: 'unpublish' })
  }

  const handleRemoveClick = (plugin: CloudPlugin) => {
    setConfirmDialog({ open: true, plugin, action: 'remove' })
  }

  const handleConfirm = async () => {
    if (!confirmDialog.plugin) return

    try {
      setProcessingId(confirmDialog.plugin.id)

      let response: { code: number; msg: string; data: null } | undefined

      if (confirmDialog.action === 'download') {
        response = await pluginsMarketApi.downloadPlugin(confirmDialog.plugin.moduleName)
      } else if (confirmDialog.action === 'update') {
        const updateResult = await updatePackage(confirmDialog.plugin.moduleName)
        response = {
          code: updateResult.success ? 200 : 500,
          msg: updateResult.success ? '成功' : updateResult.errorMsg || '失败',
          data: null,
        }
      } else if (confirmDialog.action === 'unpublish') {
        response = await pluginsMarketApi.deleteUserPlugin(confirmDialog.plugin.moduleName)
      } else if (confirmDialog.action === 'remove') {
        // 调用插件管理的移除插件接口
        const success = await removePackage(confirmDialog.plugin.moduleName)
        response = { code: success ? 200 : 500, msg: success ? '成功' : '失败', data: null }
      }

      if (response && response.code === 200) {
        let successMessage = '操作成功'
        if (confirmDialog.action === 'download') {
          successMessage = '插件获取成功'
        } else if (confirmDialog.action === 'update') {
          successMessage = '插件同步成功，已更新至最新版本'
        } else if (confirmDialog.action === 'unpublish') {
          successMessage = '插件下架成功'
          // 下架成功后从列表中移除
          setPlugins(prev => prev.filter(p => p.id !== confirmDialog.plugin?.id))
          if (selectedPlugin?.id === confirmDialog.plugin.id) {
            setSelectedPlugin(null)
          }
        } else if (confirmDialog.action === 'remove') {
          successMessage = '插件移除成功'
          // 更新状态，标记为未安装
          setPlugins(prev =>
            prev.map(p => (p.id === confirmDialog.plugin?.id ? { ...p, is_local: false } : p))
          )
          if (selectedPlugin?.id === confirmDialog.plugin.id) {
            setSelectedPlugin({
              ...selectedPlugin,
              is_local: false,
            })
          }
        }

        // 更新本地状态（下载、更新）
        if (confirmDialog.action === 'download' || confirmDialog.action === 'update') {
          setPlugins(prev =>
            prev.map(p => (p.id === confirmDialog.plugin?.id ? { ...p, is_local: true } : p))
          )
          if (selectedPlugin?.id === confirmDialog.plugin.id) {
            setSelectedPlugin({
              ...selectedPlugin,
              is_local: true,
            })
          }
        }

        notification.success(successMessage)
        // 重新获取插件列表以更新状态
        fetchPlugins(currentPage, debouncedSearchKeyword)
      } else if (response) {
        notification.error(`${t('pluginsMarket.operationFailed')}: ${response.msg}`)
      } else {
        notification.error(t('pluginsMarket.operationFailedUnknown'))
      }
    } catch (error) {
      console.error('操作失败', error)
      notification.error(t('pluginsMarket.operationFailedRetry'))
    } finally {
      setProcessingId(null)
      setConfirmDialog({ open: false, plugin: null, action: 'download' })
    }
  }

  // 处理创建插件
  const handleCreatePlugin = async (data: PluginCreateRequest) => {
    try {
      setIsSubmitting(true)
      const response = await pluginsMarketApi.createPlugin(data)

      if (response.code === 200) {
        // 成功创建
        notification.success(t('pluginsMarket.publishSuccess'))
        setCreateDialogOpen(false)
        // 刷新插件列表
        fetchPlugins(1, debouncedSearchKeyword)
      } else {
        // 处理不同的错误情况
        const errorMsg = response.msg || '未知错误'
        notification.error(errorMsg)
      }
    } catch (error) {
      console.error('创建插件失败', error)

      // 网络错误或其他未处理的错误
      const errorMessage = error instanceof Error ? error.message : String(error)
      notification.error(`发布失败: ${errorMessage}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  // 添加处理编辑的方法
  const handleEditPlugin = (plugin: CloudPlugin) => {
    setEditingPlugin(plugin)
  }

  // 在主组件中添加处理更新插件信息的方法
  const handleUpdatePluginInfo = async (data: PluginUpdateRequest, moduleName: string) => {
    try {
      setIsSubmitting(true)
      const response = await pluginsMarketApi.updateUserPlugin(moduleName, data)

      if (response.code === 200) {
        notification.success(t('pluginsMarket.updateInfoSuccess'))
        setEditingPlugin(null)

        // 刷新插件列表
        fetchPlugins(currentPage, debouncedSearchKeyword)

        // 如果当前有选中的插件，更新选中插件的信息
        if (selectedPlugin && selectedPlugin.moduleName === moduleName) {
          const updatedPlugin = await pluginsMarketApi.getPluginDetail(moduleName)
          setSelectedPlugin({
            ...updatedPlugin,
            isOwner: selectedPlugin.isOwner,
            is_local: selectedPlugin.is_local,
          })
        }
      } else {
        notification.error(response.msg || '更新失败')
      }
    } catch (error) {
      console.error('更新插件信息失败', error)
      notification.error(`更新失败: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  // 编辑插件对话框组件
  const EditPluginDialog = ({
    open,
    onClose,
    plugin,
    onSubmit,
    isSubmitting,
  }: {
    open: boolean
    onClose: () => void
    plugin: CloudPlugin | null
    onSubmit: (data: PluginUpdateRequest, moduleName: string) => void
    isSubmitting: boolean
  }) => {
    const [formData, setFormData] = useState<PluginUpdateRequest>({
      name: '',
      description: '',
      author: '',
      hasWebhook: false,
      homepageUrl: '',
      githubUrl: '',
      cloneUrl: '',
      licenseType: 'MIT',
      isSfw: true,
      icon: '',
    })
    const [errors, setErrors] = useState<Record<string, string>>({})
    const [iconPreview, setIconPreview] = useState<string | null>(null)
    // 添加确认选择框状态
    const [confirmSafeContent, setConfirmSafeContent] = useState(false)
    const [agreeToTerms, setAgreeToTerms] = useState(false)

    // 初始化表单数据
    useEffect(() => {
      if (open && plugin) {
        setFormData({
          name: plugin.name || '',
          description: plugin.description || '',
          author: plugin.author || '',
          hasWebhook: plugin.hasWebhook || false,
          homepageUrl: plugin.homepageUrl || '',
          githubUrl: plugin.githubUrl || '',
          cloneUrl: plugin.cloneUrl || '',
          licenseType: plugin.licenseType || 'MIT',
          isSfw: true,
          icon: plugin.icon || '',
        })
        setIconPreview(plugin.icon || null)
        setErrors({})
        // 重置确认状态
        setConfirmSafeContent(false)
        setAgreeToTerms(false)
      }
    }, [open, plugin])

    // 处理输入变化
    const handleChange = (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLTextAreaElement | { name?: string; value: unknown }
      >
    ) => {
      const { name, value } = e.target
      if (name) {
        setFormData(prev => ({ ...prev, [name]: value }))

        // GitHub URL自动填充Git克隆URL的逻辑
        if (name === 'githubUrl' && typeof value === 'string') {
          const githubUrl = value.trim()
          // 如果Git克隆URL为空或等于旧的GitHub URL + .git，则自动填充
          if (!formData.cloneUrl || formData.cloneUrl === formData.githubUrl + '.git') {
            if (githubUrl) {
              setFormData(prev => ({ ...prev, cloneUrl: githubUrl + '.git' }))

              // 当自动填充克隆URL时，同时清除克隆URL的错误
              if (errors.cloneUrl) {
                setErrors(prev => {
                  const newErrors = { ...prev }
                  delete newErrors.cloneUrl
                  return newErrors
                })
              }
            } else {
              setFormData(prev => ({ ...prev, cloneUrl: '' }))
            }
          }
        }

        // 清除错误
        if (errors[name]) {
          setErrors(prev => {
            const newErrors = { ...prev }
            delete newErrors[name]
            return newErrors
          })
        }
      }
    }

    // 处理SFW确认变更
    const handleSfwChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setConfirmSafeContent(e.target.checked)
      // 同时更新formData中的isSfw值
      setFormData(prev => ({ ...prev, isSfw: e.target.checked }))
    }

    // 验证表单
    const validateForm = (): boolean => {
      const newErrors: Record<string, string> = {}

      if (!formData.name?.trim()) {
        newErrors.name = '插件名称不能为空'
      }

      if (!formData.description?.trim()) {
        newErrors.description = '插件描述不能为空'
      }

      if (!formData.author?.trim()) {
        newErrors.author = '作者不能为空'
      }

      if (formData.githubUrl && !/^https?:\/\/github\.com\//.test(formData.githubUrl)) {
        newErrors.githubUrl = 'GitHub URL 格式不正确'
      }

      if (formData.cloneUrl && !/\.git$/.test(formData.cloneUrl)) {
        newErrors.cloneUrl = '克隆URL格式不正确，应以.git结尾'
      }

      setErrors(newErrors)
      return Object.keys(newErrors).length === 0
    }

    // 处理提交
    const handleSubmit = () => {
      if (!plugin) return
      if (validateForm()) {
        onSubmit(formData, plugin.moduleName)
      }
    }

    // 处理图标上传
    const handleIconUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return

      if (file.size > 10 * 1024 * 1024) {
        setErrors(prev => ({
          ...prev,
          icon: '图片太大啦，最大支持10MB～',
        }))
        return
      }

      try {
        const base64Icon = await imageToBase64(file)
        setFormData(prev => ({ ...prev, icon: base64Icon }))
        setIconPreview(base64Icon)

        // 清除错误
        if (errors.icon) {
          setErrors(prev => {
            const newErrors = { ...prev }
            delete newErrors.icon
            return newErrors
          })
        }
      } catch (error) {
        console.error('图标转换失败:', error)
        setErrors(prev => ({
          ...prev,
          icon: '图标处理失败，请重试',
        }))
      }
    }

    // 图片转Base64函数
    const imageToBase64 = (file: File): Promise<string> => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.readAsDataURL(file)
        reader.onload = () => resolve(reader.result as string)
        reader.onerror = error => reject(error)
      })
    }

    if (!plugin) return null

    return (
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 2,
            overflow: 'hidden',
          },
        }}
      >
        <DialogTitle sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
          编辑插件信息
          <IconButton
            aria-label="close"
            onClick={onClose}
            sx={{
              position: 'absolute',
              right: 8,
              top: 8,
            }}
            size="small"
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ pt: 3, mt: 3 }}>
          <Grid container spacing={3}>
            {/* 基本信息（左）和图标上传（右）并排布局 */}
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle1" gutterBottom fontWeight={500} sx={{ mb: 2 }}>
                基本信息
              </Typography>

              <TextField
                name="name"
                label="插件名称"
                value={formData.name}
                onChange={handleChange}
                fullWidth
                required
                error={!!errors.name}
                helperText={errors.name}
                disabled={isSubmitting}
                sx={{ mb: 2 }}
              />

              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                模块名: <b>{plugin.moduleName}</b> (不可修改)
              </Typography>
            </Grid>

            {/* 插件图标上传 */}
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle1" gutterBottom fontWeight={500} sx={{ mb: 2 }}>
                插件图标
              </Typography>

              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 2,
                }}
              >
                <Box
                  sx={{
                    width: 100,
                    height: 100,
                    borderRadius: 2,
                    border: '1px solid',
                    borderColor: 'divider',
                    overflow: 'hidden',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: theme =>
                      theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                  }}
                >
                  {iconPreview ? (
                    <img
                      src={iconPreview}
                      alt="插件图标预览"
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  ) : (
                    <ExtensionIcon
                      sx={{
                        fontSize: 48,
                        opacity: 0.7,
                        color: theme => theme.palette.primary.main,
                      }}
                    />
                  )}
                </Box>
                <Box>
                  <Button
                    variant="outlined"
                    component="label"
                    disabled={isSubmitting}
                    sx={{ mb: 1 }}
                  >
                    选择图标
                    <input
                      type="file"
                      hidden
                      accept="image/*"
                      onChange={handleIconUpload}
                      disabled={isSubmitting}
                    />
                  </Button>
                  <Typography variant="caption" color="text.secondary" display="block">
                    建议尺寸: 128x128像素
                    <br />
                    支持格式: PNG, JPG, GIF
                    <br />
                    大小限制: 10MB (自动压缩至 500 KB)
                  </Typography>
                  {errors.icon && (
                    <Typography variant="caption" color="error" sx={{ mt: 1 }}>
                      {errors.icon}
                    </Typography>
                  )}
                </Box>
              </Box>
            </Grid>

            <Grid item xs={12}>
              <TextField
                name="description"
                label="插件描述"
                value={formData.description}
                onChange={handleChange}
                fullWidth
                required
                multiline
                rows={3}
                error={!!errors.description}
                helperText={errors.description}
                disabled={isSubmitting}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                name="author"
                label="作者"
                value={formData.author}
                onChange={handleChange}
                fullWidth
                required
                error={!!errors.author}
                helperText={errors.author}
                disabled={isSubmitting}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth disabled={isSubmitting}>
                <TextField
                  select
                  name="licenseType"
                  label="许可证类型"
                  value={formData.licenseType}
                  onChange={handleChange}
                  fullWidth
                >
                  <MenuItem value="MIT">MIT</MenuItem>
                  <MenuItem value="Apache-2.0">Apache-2.0</MenuItem>
                  <MenuItem value="GPL-3.0">GPL-3.0</MenuItem>
                  <MenuItem value="BSD-3-Clause">BSD-3-Clause</MenuItem>
                  <MenuItem value="UNLICENSED">UNLICENSED</MenuItem>
                  <MenuItem value="CUSTOM">自定义（参考描述）</MenuItem>
                </TextField>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                name="githubUrl"
                label="GitHub 仓库URL"
                value={formData.githubUrl}
                onChange={handleChange}
                fullWidth
                error={!!errors.githubUrl}
                helperText={errors.githubUrl}
                placeholder="https://github.com/username/repo"
                disabled={isSubmitting}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                name="cloneUrl"
                label="Git 克隆URL"
                value={formData.cloneUrl}
                onChange={handleChange}
                fullWidth
                error={!!errors.cloneUrl}
                helperText={errors.cloneUrl}
                placeholder="https://github.com/username/repo.git"
                disabled={isSubmitting}
              />
            </Grid>

            {/* 添加分割线和确认选项 */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" color="text.secondary" gutterBottom>
                发布确认
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={confirmSafeContent}
                    onChange={handleSfwChange}
                    disabled={isSubmitting}
                  />
                }
                label="我确认这是符合社区内容规则的安全内容(SFW)"
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={agreeToTerms}
                    onChange={e => setAgreeToTerms(e.target.checked)}
                    disabled={isSubmitting}
                  />
                }
                label={
                  <Box component="span" sx={{ display: 'flex', alignItems: 'center' }}>
                    我已阅读并接受{' '}
                    <Link
                      href="https://community.nekro.ai/terms"
                      target="_blank"
                      underline="hover"
                      sx={{ ml: 0.5 }}
                    >
                      《NekroAI 社区资源共享协议》
                    </Link>
                  </Box>
                }
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2, borderTop: '1px solid', borderColor: 'divider' }}>
          <Button onClick={onClose} disabled={isSubmitting}>
            取消
          </Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            color="primary"
            disabled={isSubmitting || !agreeToTerms || !confirmSafeContent}
            startIcon={isSubmitting ? <CircularProgress size={20} /> : <EditIcon />}
          >
            {isSubmitting ? '提交中...' : '更新信息'}
          </Button>
        </DialogActions>
      </Dialog>
    )
  }

  if (error && plugins.length === 0) {
    return (
      <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      <Box
        sx={{
          mb: 4,
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 2,
          alignItems: 'center',
        }}
      >
        <Box
          component="form"
          onSubmit={handleSearch}
          sx={{
            display: 'flex',
            boxShadow: theme =>
              theme.palette.mode === 'dark'
                ? '0 0 10px rgba(0,0,0,0.2)'
                : '0 0 15px rgba(0,0,0,0.07)',
            overflow: 'hidden',
          }}
        >
          <TextField
            size="small"
            placeholder="搜索插件"
            value={searchKeyword}
            onChange={e => setSearchKeyword(e.target.value)}
            sx={{
              minWidth: 220,
              '& .MuiOutlinedInput-root': {
                borderRadius: '8px 0 0 8px',
              },
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: searchKeyword && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={handleSearchInputClear}>
                    &times;
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          <Button
            type="submit"
            disabled={loading}
            sx={{
              borderRadius: '0 8px 8px 0',
              px: 2,
              background: theme => theme.palette.primary.main,
              '&:hover': {
                background: theme => theme.palette.primary.dark,
              },
            }}
            variant="contained"
          >
            {loading ? '搜索中...' : '搜索'}
          </Button>
        </Box>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            发布插件
          </Button>
        </Box>
      </Box>

      {/* 插件内容区域 */}
      <Box position="relative" minHeight={plugins.length === 0 ? '300px' : 'auto'}>
        {/* 加载状态覆盖层 */}
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              justifyContent: 'center',
              alignItems: plugins.length === 0 ? 'center' : 'flex-start',
              backgroundColor: 'transparent',
              zIndex: 10,
              borderRadius: 2,
              backdropFilter: 'blur(2px)',
              pt: plugins.length === 0 ? 0 : 3,
            }}
          >
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 1,
                backgroundColor: theme =>
                  theme.palette.mode === 'dark'
                    ? 'rgba(30, 30, 30, 0.8)'
                    : 'rgba(255, 255, 255, 0.9)',
                boxShadow: theme =>
                  theme.palette.mode === 'dark'
                    ? '0 4px 20px rgba(0, 0, 0, 0.5)'
                    : '0 4px 20px rgba(0, 0, 0, 0.1)',
                borderRadius: 2,
                padding: '12px 24px',
              }}
            >
              <CircularProgress size={28} thickness={4} />
              <Typography variant="body2" sx={{ opacity: 0.8 }}>
                加载中...
              </Typography>
            </Box>
          </Box>
        )}

        {plugins.length > 0 ? (
          <>
            <Grid container spacing={3}>
              {plugins.map(plugin => (
                <Grid item xs={12} sm={6} md={4} key={plugin.id}>
                  <PluginCard
                    plugin={plugin}
                    onDownload={() => handleDownloadClick(plugin)}
                    onUpdate={() => handleUpdateClick(plugin)}
                    onRemove={() => handleRemoveClick(plugin)}
                    onUnpublish={plugin.isOwner ? () => handleUnpublishClick(plugin) : undefined}
                    onShowDetail={() => handleShowDetail(plugin)}
                    t={t}
                  />
                </Grid>
              ))}
            </Grid>

            <PaginationStyled
              totalPages={totalPages}
              currentPage={currentPage}
              onPageChange={handlePageChange}
              loading={loading}
            />
          </>
        ) : (
          !loading && (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                py: 8,
                px: 2,
                minHeight: 300,
                textAlign: 'center',
                bgcolor: theme =>
                  theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
                borderRadius: 2,
                border: '1px dashed',
                borderColor: 'divider',
              }}
            >
              <Typography variant="h6" color="text.secondary" sx={{ mb: 1, fontWeight: 'normal' }}>
                没有找到符合条件的插件
              </Typography>
              <Typography variant="body2" color="text.disabled" sx={{ maxWidth: 400 }}>
                尝试使用其他关键词搜索，或取消筛选条件后再次尝试。
                <br />
                新上传的插件可能需要一些时间才能被检索到。
              </Typography>
            </Box>
          )
        )}
      </Box>

      {/* 详情对话框 */}
      <PluginDetailDialog
        open={!!selectedPlugin}
        onClose={() => setSelectedPlugin(null)}
        plugin={selectedPlugin}
        onUnpublish={
          selectedPlugin?.isOwner ? () => handleUnpublishClick(selectedPlugin) : undefined
        }
        onDownload={
          selectedPlugin && !selectedPlugin.is_local
            ? () => handleDownloadClick(selectedPlugin)
            : undefined
        }
        onUpdate={selectedPlugin?.is_local ? () => handleUpdateClick(selectedPlugin) : undefined}
        onRemove={selectedPlugin?.is_local ? () => handleRemoveClick(selectedPlugin) : undefined}
        onEdit={selectedPlugin?.isOwner ? () => handleEditPlugin(selectedPlugin) : undefined}
        t={t}
      />

      {/* 确认下载/更新/下架/移除对话框 */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog({ open: false, plugin: null, action: 'download' })}
        maxWidth="md"
      >
        <DialogTitle>
          {confirmDialog.action === 'download'
            ? '确认获取'
            : confirmDialog.action === 'update'
              ? '确认同步'
              : confirmDialog.action === 'unpublish'
                ? '确认下架'
                : '确认移除'}
        </DialogTitle>
        <DialogContent>
          {(confirmDialog.action === 'download' || confirmDialog.action === 'update') && (
            <Box sx={{ mb: 2 }}>
              <Alert severity="warning" sx={{ mb: 2 }}>
                <Typography variant="body2" component="div">
                  <strong>安全提示：</strong>{' '}
                  NekroAI社区仅作为插件分享平台，不具备对第三方平台托管的插件内容负责的能力。
                  使用任何第三方插件都存在潜在风险，请自行评估插件的安全性，特别是高权限插件。
                </Typography>
              </Alert>

              {confirmDialog.plugin?.cloneUrl && (
                <Box sx={{ mt: 2, mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    插件仓库地址:
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                    <Typography
                      variant="body2"
                      component="code"
                      sx={{
                        display: 'inline-block',
                        p: 1,
                        bgcolor: theme =>
                          theme.palette.mode === 'dark'
                            ? 'rgba(255,255,255,0.05)'
                            : 'rgba(0,0,0,0.03)',
                        borderRadius: 1,
                        fontFamily: 'monospace',
                        overflow: 'auto',
                        maxWidth: '100%',
                        wordBreak: 'break-all',
                      }}
                    >
                      {confirmDialog.plugin.cloneUrl}
                    </Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<GitHubIcon />}
                      onClick={() => {
                        // 移除.git后缀并打开链接
                        const repoUrl = confirmDialog.plugin?.cloneUrl?.replace(/\.git$/, '')
                        if (repoUrl) window.open(repoUrl, '_blank')
                      }}
                    >
                      查看仓库
                    </Button>
                  </Box>
                </Box>
              )}
            </Box>
          )}

          <Typography>
            {confirmDialog.action === 'download' &&
              `确定要获取插件 "${confirmDialog.plugin?.name}" 到本地库吗？`}
            {confirmDialog.action === 'update' &&
              `确定要同步插件 "${confirmDialog.plugin?.name}" 到最新版本吗？将会执行 git pull 操作。`}
            {confirmDialog.action === 'unpublish' && (
              <>
                <Alert severity="warning" sx={{ mb: 2 }}>
                  下架后此插件将从云端市场移除，其他用户将无法再下载。此操作不可恢复。
                </Alert>
                确定要从云端市场下架插件 "{confirmDialog.plugin?.name}" 吗？
              </>
            )}
            {confirmDialog.action === 'remove' && (
              <>
                <Alert severity="warning" sx={{ mb: 2 }}>
                  移除后此插件将从本地删除，所有相关功能将无法使用。您可以随时从插件市场重新获取。
                </Alert>
                确定要从本地移除插件 "{confirmDialog.plugin?.name}" 吗？
              </>
            )}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmDialog({ open: false, plugin: null, action: 'download' })}
            disabled={!!processingId}
          >
            取消
          </Button>
          <Button
            onClick={handleConfirm}
            color={
              confirmDialog.action === 'unpublish' || confirmDialog.action === 'remove'
                ? 'error'
                : 'primary'
            }
            disabled={!!processingId}
          >
            {processingId ? <CircularProgress size={24} /> : '确认'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 创建插件对话框 */}
      <CreatePluginDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSubmit={handleCreatePlugin}
        isSubmitting={isSubmitting}
      />

      {/* 编辑插件对话框 */}
      <EditPluginDialog
        open={!!editingPlugin}
        onClose={() => setEditingPlugin(null)}
        plugin={editingPlugin}
        onSubmit={handleUpdatePluginInfo}
        isSubmitting={isSubmitting}
      />
    </Box>
  )
}
