import { useEffect, useRef, useState } from 'react'
import {
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Fade,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemAvatar,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  CloudDownload as CloudDownloadIcon,
  GitHub as GitHubIcon,
  Link as LinkIcon,
  Code as CodeIcon,
  Extension as ExtensionIcon,
  RemoveCircle as RemoveCircleIcon,
  Close as CloseIcon,
  Edit as EditIcon,
  MoreVert as MoreVertIcon,
  Flag as FlagIcon,
  Star as StarIcon,
  CheckCircle as CheckCircleIcon,
  CallSplit as ForkIcon,
  Visibility as VisibilityIcon,
  BugReport as IssueIcon,
  ChatBubbleOutline as CommentIcon,
  Update as UpdateIcon,
} from '@mui/icons-material'
import { favoritesApi } from '../../services/api/cloud/favorites'
import { CloudPlugin, PluginRepoInfo, pluginsMarketApi } from '../../services/api/cloud/plugins_market'
import { formatLastActiveTimeFromInput } from '../../utils/time'
import { UI_STYLES, BORDER_RADIUS } from '../../theme/themeConfig'
import { CARD_VARIANTS } from '../../theme/variants'
import { copyText } from '../../utils/clipboard'
import ActionButton from '../common/ActionButton'
import IconActionButton from '../common/IconActionButton'
import { useNotification } from '../../hooks/useNotification'

interface PluginDetailDialogProps {
  open: boolean
  onClose: () => void
  plugin: CloudPlugin | null
  onUnpublish?: () => void
  onDownload?: () => void
  onUpdate?: () => void
  onRemove?: () => void
  onEdit?: () => void
  onFavoriteChange?: (pluginId: string, isFavorited: boolean) => void
  t: (key: string, options?: Record<string, unknown>) => string
  naVersion?: string | null
}

function compareVersions(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < 3; i += 1) {
    const x = pa[i] || 0
    const y = pb[i] || 0
    if (x < y) return -1
    if (x > y) return 1
  }
  return 0
}

function isPluginCompatible(
  plugin: CloudPlugin,
  naVersion: string | null
): { compatible: boolean; reasonKey?: string; reasonParams?: Record<string, string> } {
  if (!naVersion) return { compatible: true }
  if (plugin.minNaVersion && compareVersions(naVersion, plugin.minNaVersion) < 0) {
    return {
      compatible: false,
      reasonKey: 'pluginsMarket.requiresNaVersion',
      reasonParams: { version: plugin.minNaVersion },
    }
  }
  if (plugin.maxNaVersion && compareVersions(naVersion, plugin.maxNaVersion) >= 0) {
    return {
      compatible: false,
      reasonKey: 'pluginsMarket.maxNaVersionLimit',
      reasonParams: { version: plugin.maxNaVersion },
    }
  }
  return { compatible: true }
}

export default function PluginDetailDialog({
  open,
  onClose,
  plugin,
  onUnpublish,
  onDownload,
  onUpdate,
  onRemove,
  onEdit,
  onFavoriteChange,
  t,
  naVersion = null,
}: PluginDetailDialogProps) {
  const theme = useTheme()
  const notification = useNotification()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const [iconError, setIconError] = useState(false)
  const [repoInfo, setRepoInfo] = useState<PluginRepoInfo | null>(null)
  const [loadingRepo, setLoadingRepo] = useState(false)
  const [moreMenuAnchor, setMoreMenuAnchor] = useState<null | HTMLElement>(null)
  const [isFavorited, setIsFavorited] = useState(false)
  const [favoriteCount, setFavoriteCount] = useState(0)
  const [favoriteLoading, setFavoriteLoading] = useState(false)
  const [installFeedbackVisible, setInstallFeedbackVisible] = useState(false)

  const isMoreMenuOpen = Boolean(moreMenuAnchor)
  const pluginModuleName = plugin?.moduleName ?? null
  const previousLocalStateRef = useRef<boolean | null>(null)

  useEffect(() => {
    if (open && plugin) {
      setFavoriteCount(plugin.favoriteCount || 0)
      setIsFavorited(plugin.isFavorited || false)
      setIconError(false)
    }
  }, [open, plugin])

  useEffect(() => {
    if (!open || !plugin) {
      previousLocalStateRef.current = plugin?.is_local ?? null
      setInstallFeedbackVisible(false)
      return
    }

    const previousIsLocal = previousLocalStateRef.current
    previousLocalStateRef.current = plugin.is_local

    if (previousIsLocal === false && plugin.is_local) {
      setInstallFeedbackVisible(true)
      const timeout = window.setTimeout(() => {
        setInstallFeedbackVisible(false)
      }, 1600)

      return () => {
        window.clearTimeout(timeout)
      }
    }

    if (!plugin.is_local) {
      setInstallFeedbackVisible(false)
    }
  }, [open, plugin])

  useEffect(() => {
    if (open && pluginModuleName) {
      setRepoInfo(null)
      setLoadingRepo(true)
      pluginsMarketApi
        .getPluginRepoInfo(pluginModuleName)
        .then(info => {
          setRepoInfo(info)
        })
        .catch(err => {
          const errorMessage = err instanceof Error ? err.message : String(err)
          notification.error(`${t('pluginsMarket.unableToFetchRepo')}: ${errorMessage}`)
        })
        .finally(() => {
          setLoadingRepo(false)
        })
    }
    // 仅在弹窗打开且插件切换时重新请求，避免通知对象变更导致循环请求
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, pluginModuleName])

  if (!plugin) return null

  const compatibility = isPluginCompatible(plugin, naVersion)
  const createdAtDisplay = formatLastActiveTimeFromInput(repoInfo?.createdAt ?? plugin.createdAt)
  const updatedAtDisplay = formatLastActiveTimeFromInput(repoInfo?.updatedAt ?? plugin.updatedAt)

  const handleFavoriteToggle = async () => {
    if (favoriteLoading) return
    setFavoriteLoading(true)
    try {
      if (isFavorited) {
        await favoritesApi.removeFavorite('plugin', plugin.id)
        setIsFavorited(false)
        setFavoriteCount(prev => Math.max(0, prev - 1))
        onFavoriteChange?.(plugin.id, false)
      } else {
        await favoritesApi.addFavorite('plugin', plugin.id)
        setIsFavorited(true)
        setFavoriteCount(prev => prev + 1)
        onFavoriteChange?.(plugin.id, true)
      }
    } catch (err) {
      console.error('收藏操作失败:', err)
    } finally {
      setFavoriteLoading(false)
    }
  }

  const handleMoreClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setMoreMenuAnchor(event.currentTarget)
  }

  const handleMoreClose = () => {
    setMoreMenuAnchor(null)
  }

  const handleReport = () => {
    const reportUrl = `https://github.com/KroMiose/nekro-agent/issues/new?template=plugin_report.yml&plugin_name=${encodeURIComponent(plugin.name)}&module_name=${encodeURIComponent(plugin.moduleName)}&repo_url=${encodeURIComponent(plugin.githubUrl || plugin.cloneUrl || '')}`
    window.open(reportUrl, '_blank')
  }

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
        <Typography variant="h6" component="span">
          {t('pluginsMarket.pluginDetail')}: {plugin.name}
        </Typography>
        <IconActionButton
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
        </IconActionButton>
      </DialogTitle>
      <DialogContent dividers sx={{ p: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={4} md={3}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2.5 }}>
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
                  backgroundColor: 'action.hover',
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
                      color: 'primary.main',
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

              {(plugin.minNaVersion || plugin.maxNaVersion) && (
                <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                  {plugin.minNaVersion && (
                    <Chip
                      label={`NA ≥ ${plugin.minNaVersion}`}
                      size="small"
                      color={compatibility.compatible ? 'default' : 'error'}
                      variant="outlined"
                    />
                  )}
                  {plugin.maxNaVersion && (
                    <Chip
                      label={`NA < ${plugin.maxNaVersion}`}
                      size="small"
                      color={compatibility.compatible ? 'default' : 'error'}
                      variant="outlined"
                    />
                  )}
                  {!compatibility.compatible && compatibility.reasonKey && (
                    <Typography variant="caption" color="error.main">
                      {t(compatibility.reasonKey, compatibility.reasonParams)}
                    </Typography>
                  )}
                </Box>
              )}

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

              <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <Chip
                  icon={<StarIcon sx={{ color: '#e3b341 !important' }} />}
                  label={repoInfo ? `${repoInfo.stargazersCount} Stars` : '- Stars'}
                  size="small"
                  variant="outlined"
                  onClick={repoInfo ? () => window.open(repoInfo.stargazersUrl, '_blank') : undefined}
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
                  <Typography variant="body2">{createdAtDisplay}</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    {t('presetsMarket.updatedAt')}:
                  </Typography>
                  <Typography variant="body2">{updatedAtDisplay}</Typography>
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
                    <ActionButton
                      fullWidth
                      variant="outlined"
                      startIcon={<LinkIcon />}
                      onClick={() => window.open(plugin.homepageUrl, '_blank')}
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      {t('pluginsMarket.pluginHomepage')}
                    </ActionButton>
                  </Grid>
                )}
                {plugin.githubUrl && (
                  <Grid item xs={12} sm={6}>
                    <ActionButton
                      fullWidth
                      variant="outlined"
                      startIcon={<GitHubIcon />}
                      onClick={() => window.open(plugin.githubUrl, '_blank')}
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      {t('pluginsMarket.githubRepo')}
                    </ActionButton>
                  </Grid>
                )}
                {plugin.cloneUrl && (
                  <Grid item xs={12} sm={6}>
                    <ActionButton
                      fullWidth
                      variant="outlined"
                      startIcon={<CodeIcon />}
                      onClick={async () => {
                        try {
                          const success = await copyText(plugin.cloneUrl)
                          if (success) {
                            notification.success(t('pluginsMarket.cloneLinkCopied'))
                          } else {
                            notification.error(t('common:messages.operationFailed'))
                          }
                        } catch (err) {
                          const errorMessage = err instanceof Error ? err.message : String(err)
                          notification.error(`${t('pluginsMarket.operationFailed')}: ${errorMessage}`)
                        }
                      }}
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      {t('pluginsMarket.copyCloneLink')}
                    </ActionButton>
                  </Grid>
                )}
                {plugin.licenseType && (
                  <Grid item xs={12} sm={6}>
                    <ActionButton
                      fullWidth
                      variant="outlined"
                      disabled
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                    >
                      {t('pluginsMarket.licenseType')}: {plugin.licenseType}
                    </ActionButton>
                  </Grid>
                )}
              </Grid>
            </Box>
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Typography variant="h6" gutterBottom>
              {t('pluginsMarket.repoDynamics')}
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
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Typography variant="subtitle1" component="span">
                              #{issue.number} {issue.title}
                            </Typography>
                            <Chip
                              label={
                                issue.state === 'open'
                                  ? t('pluginsMarket.issueOpen')
                                  : t('pluginsMarket.issueClosed')
                              }
                              size="small"
                              color={issue.state === 'open' ? 'success' : 'default'}
                              variant="outlined"
                              sx={{ height: 20, fontSize: '0.7rem' }}
                            />
                          </Box>
                        }
                        secondary={
                          <Box component="span" sx={{ display: 'flex', flexDirection: 'column', mt: 0.5 }}>
                            <Typography component="span" variant="body2" color="text.primary">
                              {issue.user.login}
                            </Typography>
                            <Box component="span" sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                              <Typography variant="caption" color="text.secondary">
                                {t('pluginsMarket.updatedAt')} {formatLastActiveTimeFromInput(issue.updatedAt)}
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
                {t('pluginsMarket.noRecentActivity')}
              </Typography>
            ) : (
              <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
                {t('pluginsMarket.unableToFetchRepo')}
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
        <Fade in={installFeedbackVisible} timeout={{ enter: 220, exit: 180 }}>
          <Box
            sx={{
              position: isMobile ? 'static' : 'absolute',
              left: 24,
              display: 'flex',
              alignItems: 'center',
              gap: 0.75,
              px: 1.25,
              py: 0.75,
              borderRadius: 999,
              color: 'success.main',
              bgcolor: 'success.light',
              opacity: installFeedbackVisible ? 1 : 0,
              transform: installFeedbackVisible ? 'translateY(0)' : 'translateY(4px)',
              transition: 'all 0.2s ease',
              '& .MuiSvgIcon-root': {
                fontSize: 18,
              },
            }}
          >
            <CheckCircleIcon />
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'inherit' }}>
              {t('pluginsMarket.addedToLocal')}
            </Typography>
          </Box>
        </Fade>

        {isMobile ? (
          <>
            <Box sx={{ display: 'flex', width: '100%', gap: 1 }}>
              <Button
                variant={isFavorited ? 'contained' : 'outlined'}
                color={isFavorited ? 'error' : 'primary'}
                startIcon={<StarIcon />}
                onClick={handleFavoriteToggle}
                disabled={favoriteLoading}
                fullWidth
              >
                {isFavorited ? t('pluginsMarket.favorited') : t('pluginsMarket.favorite')}
              </Button>
              {plugin.is_local ? (
                <>
                  {onUpdate ? (
                    <ActionButton tone="primary" startIcon={<UpdateIcon />} onClick={onUpdate} fullWidth>
                      {t('pluginsMarket.update')}
                    </ActionButton>
                  ) : null}
                  {onRemove ? (
                    <ActionButton
                      tone="danger"
                      onClick={onRemove}
                      fullWidth
                      sx={
                        installFeedbackVisible
                          ? {
                              animation: 'pluginInstallSuccessPulse 0.7s ease',
                              '@keyframes pluginInstallSuccessPulse': {
                                '0%': {
                                  transform: 'scale(0.96)',
                                  boxShadow: '0 0 0 rgba(34, 197, 94, 0)',
                                },
                                '55%': {
                                  transform: 'scale(1.03)',
                                  boxShadow: '0 0 0 6px rgba(34, 197, 94, 0.14)',
                                },
                                '100%': {
                                  transform: 'scale(1)',
                                  boxShadow: '0 0 0 rgba(34, 197, 94, 0)',
                                },
                              },
                            }
                          : undefined
                      }
                    >
                      {t('pluginsMarket.remove')}
                    </ActionButton>
                  ) : null}
                </>
              ) : onDownload ? (
                <ActionButton
                  tone="primary"
                  startIcon={<CloudDownloadIcon />}
                  onClick={onDownload}
                  fullWidth
                  disabled={!compatibility.compatible}
                >
                  {!compatibility.compatible
                    ? t('pluginsMarket.incompatibleVersion')
                    : t('pluginsMarket.obtain')}
                </ActionButton>
              ) : null}
            </Box>

            <Box sx={{ display: 'flex', width: '100%' }}>
              <ActionButton
                tone="secondary"
                startIcon={<MoreVertIcon />}
                onClick={handleMoreClick}
                fullWidth
              >
                {t('pluginsMarket.moreActions')}
              </ActionButton>

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
                  <ListItemText primary={t('pluginsMarket.reportPlugin')} />
                </MenuItem>

                {plugin.isOwner && (
                  <>
                    {onUnpublish ? (
                      <MenuItem
                        onClick={() => {
                          handleMoreClose()
                          onUnpublish()
                        }}
                      >
                        <ListItemIcon>
                          <RemoveCircleIcon fontSize="small" color="error" />
                        </ListItemIcon>
                        <ListItemText primary={t('pluginsMarket.delistPlugin')} />
                      </MenuItem>
                    ) : null}
                    {onEdit ? (
                      <MenuItem
                        onClick={() => {
                          handleMoreClose()
                          onEdit()
                        }}
                      >
                        <ListItemIcon>
                          <EditIcon fontSize="small" color="primary" />
                        </ListItemIcon>
                        <ListItemText primary={t('pluginsMarket.editInfo')} />
                      </MenuItem>
                    ) : null}
                  </>
                )}
              </Menu>
            </Box>
          </>
        ) : (
          <>
            <Box>
              <ActionButton tone="secondary" onClick={handleReport} sx={{ mr: 1, color: 'warning.main', borderColor: 'warning.main' }}>
                {t('pluginsMarket.reportPlugin')}
              </ActionButton>
              {plugin.isOwner && onUnpublish ? (
                <ActionButton tone="danger" onClick={onUnpublish} sx={{ mr: 1 }}>
                  {t('pluginsMarket.delistPlugin')}
                </ActionButton>
              ) : null}
              {plugin.isOwner && onEdit ? (
                <ActionButton tone="secondary" onClick={onEdit} sx={{ mr: 1 }}>
                  {t('pluginsMarket.editInfo')}
                </ActionButton>
              ) : null}
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant={isFavorited ? 'contained' : 'outlined'}
                color={isFavorited ? 'error' : 'primary'}
                startIcon={<StarIcon />}
                onClick={handleFavoriteToggle}
                disabled={favoriteLoading}
              >
                {isFavorited ? t('pluginsMarket.favorited') : t('pluginsMarket.favorite')} ({favoriteCount})
              </Button>
              {plugin.is_local ? (
                <>
                  {onUpdate ? (
                    <ActionButton tone="primary" startIcon={<UpdateIcon />} onClick={onUpdate}>
                      {t('pluginsMarket.syncLatest')}
                    </ActionButton>
                  ) : null}
                  {onRemove ? (
                    <ActionButton
                      tone="danger"
                      onClick={onRemove}
                      sx={
                        installFeedbackVisible
                          ? {
                              animation: 'pluginInstallSuccessPulse 0.7s ease',
                              '@keyframes pluginInstallSuccessPulse': {
                                '0%': {
                                  transform: 'scale(0.96)',
                                  boxShadow: '0 0 0 rgba(34, 197, 94, 0)',
                                },
                                '55%': {
                                  transform: 'scale(1.03)',
                                  boxShadow: '0 0 0 6px rgba(34, 197, 94, 0.14)',
                                },
                                '100%': {
                                  transform: 'scale(1)',
                                  boxShadow: '0 0 0 rgba(34, 197, 94, 0)',
                                },
                              },
                            }
                          : undefined
                      }
                    >
                      {t('pluginsMarket.removePlugin')}
                    </ActionButton>
                  ) : null}
                </>
              ) : onDownload ? (
                <ActionButton
                  tone="primary"
                  startIcon={<CloudDownloadIcon />}
                  onClick={onDownload}
                  disabled={!compatibility.compatible}
                >
                  {!compatibility.compatible
                    ? t('pluginsMarket.incompatibleVersion')
                    : t('pluginsMarket.obtain')}
                </ActionButton>
              ) : null}
            </Box>
          </>
        )}
      </DialogActions>
    </Dialog>
  )
}
