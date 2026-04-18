import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Tab,
  Card,
  CardContent,
  Grid,
  Avatar,
  Alert,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
  Button,
  useTheme,
} from '@mui/material'
import {
  Person as PersonIcon,
  Extension as ExtensionIcon,
  Favorite as FavoriteIcon,
  Face as FaceIcon,
} from '@mui/icons-material'
import { favoritesApi, FavoriteItem } from '../../services/api/cloud/favorites'
import {
  pluginsMarketApi,
  UserPlugin,
  PluginUpdateRequest,
  CloudPlugin,
} from '../../services/api/cloud/plugins_market'
import { presetsMarketApi, UserPreset } from '../../services/api/cloud/presets_market'
import { removePackage } from '../../services/api/plugins'
import { presetsApi } from '../../services/api/presets'
import { useNotification } from '../../hooks/useNotification'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { CARD_VARIANTS } from '../../theme/variants'
import { presetsPath } from '../../router/routes'
import type { CloudPreset } from '../../services/api/cloud/presets_market'

import FavoriteCard from '../../components/cloud/profile/FavoriteCard'
import UserPluginCard from '../../components/cloud/profile/UserPluginCard'
import UserPresetCard from '../../components/cloud/profile/UserPresetCard'
import PluginDetailDialog from '../../components/cloud/PluginDetailDialog'
import PluginEditDialog from '../../components/cloud/PluginEditDialog'
import PresetDetailDialog from '../../components/cloud/PresetDetailDialog'
import { PageTabs } from '../../components/common/NekroTabs'
import CommunityApiKeyRequiredContent from '../../components/common/CommunityApiKeyRequiredContent'
import StatCard from '../../components/common/StatCard'
import { useCommunityUserStore } from '../../stores/communityUser'

type TabValue = 'published' | 'favorites'
type PresetDetailSource = 'published' | 'favorites'

export default function CloudProfile() {
  const navigate = useNavigate()
  const theme = useTheme()
  const [activeTab, setActiveTab] = useState<TabValue>('published')
  const [favorites, setFavorites] = useState<FavoriteItem[]>([])
  const [userPlugins, setUserPlugins] = useState<UserPlugin[]>([])
  const [userPresets, setUserPresets] = useState<UserPreset[]>([])
  const [loading, setLoading] = useState(true)
  const [pluginsLoading, setPluginsLoading] = useState(false)
  const [presetsLoading, setPresetsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingPlugin, setEditingPlugin] = useState<CloudPlugin | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [pluginDelistDialog, setPluginDelistDialog] = useState<UserPlugin | null>(null)
  const [pluginDelistLoading, setPluginDelistLoading] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState<CloudPreset | null>(null)
  const [presetDetailOpen, setPresetDetailOpen] = useState(false)
  const [presetDetailSource, setPresetDetailSource] = useState<PresetDetailSource>('published')
  const [selectedPlugin, setSelectedPlugin] = useState<CloudPlugin | null>(null)
  const [pluginDetailOpen, setPluginDetailOpen] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean
    favorite: FavoriteItem | null
  }>({ open: false, favorite: null })
  const [downloading, setDownloading] = useState(false)
  const notification = useNotification()
  const { t } = useTranslation(['cloud', 'navigation', 'common'])
  const {
    userInfo: userProfile,
    loading: userProfileLoading,
    accessStatus: communityAccessStatus,
    fetchUserProfile,
  } = useCommunityUserStore()

  const hasSelectedPluginModuleName = Boolean(selectedPlugin?.moduleName)

  const setFavoriteLocalState = useCallback((targetType: string, targetId: string, isLocal: boolean) => {
    setFavorites(prev =>
      prev.map(favorite =>
        favorite.targetType === targetType && favorite.targetId === targetId
          ? {
              ...favorite,
              resource: {
                ...favorite.resource,
                isLocal,
              },
            }
          : favorite
      )
    )
  }, [])

  const fetchFavorites = useCallback(async () => {
    try {
      setLoading(true)
      const pageSize = 100
      let page = 1
      let totalPages = 1
      const allItems: FavoriteItem[] = []

      do {
        const data = await favoritesApi.getFavorites({ page, page_size: pageSize })
        allItems.push(...data.data.items)
        totalPages = data.data.totalPages || 1
        page += 1
      } while (page <= totalPages)

      setFavorites(allItems)
      setError(null)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      setError(`${t('cloud:profile.fetchFailed')}: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }, [t])

  const fetchUserPlugins = useCallback(async () => {
    setPluginsLoading(true)
    try {
      const plugins = await pluginsMarketApi.getUserPlugins()
      setUserPlugins(plugins)
    } catch (err) {
      console.error('Failed to fetch user plugins:', err)
    } finally {
      setPluginsLoading(false)
    }
  }, [])

  const fetchUserPresets = useCallback(async () => {
    setPresetsLoading(true)
    try {
      const data = await presetsMarketApi.getUserPresets()
      setUserPresets(data.items)
    } catch (err) {
      console.error('Failed to fetch user presets:', err)
    } finally {
      setPresetsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUserProfile(true)
  }, [fetchUserProfile])

  useEffect(() => {
    if (communityAccessStatus !== 'available') return
    fetchUserPlugins()
    fetchUserPresets()
  }, [communityAccessStatus, fetchUserPlugins, fetchUserPresets])

  useEffect(() => {
    if (communityAccessStatus !== 'available') return
    if (activeTab === 'favorites') {
      fetchFavorites()
    }
  }, [activeTab, communityAccessStatus, fetchFavorites])

  if (userProfileLoading && communityAccessStatus === 'unknown') {
    return (
      <Box sx={{ p: 3, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (communityAccessStatus === 'missing_api_key') {
    return (
      <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
        <Card
          sx={{
            ...CARD_VARIANTS.default.styles,
            maxWidth: 520,
            mx: 'auto',
            mt: { xs: 4, md: 8 },
          }}
        >
          <CommunityApiKeyRequiredContent />
        </Card>
      </Box>
    )
  }

  if (communityAccessStatus === 'error' && !userProfile) {
    return (
      <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
        <Alert severity="error">{t('cloud:profile.fetchFailed')}</Alert>
      </Box>
    )
  }

  const handleTabChange = (_event: React.SyntheticEvent, newValue: TabValue) => {
    setActiveTab(newValue)
  }

  const handleRemoveFavorite = async (favorite: FavoriteItem) => {
    try {
      await favoritesApi.removeFavorite(favorite.targetType, favorite.targetId)
      notification.success(t('cloud:profile.removeFavoriteSuccess') || '取消收藏成功')
      fetchFavorites()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      notification.error(`${t('cloud:profile.operationFailed') || '操作失败'}: ${errorMessage}`)
    }
  }

  const handleUnpublishPlugin = async (plugin: UserPlugin) => {
    try {
      setPluginDelistLoading(true)
      await pluginsMarketApi.deleteUserPlugin(plugin.moduleName)
      notification.success(t('cloud:pluginsMarket.delistSuccess') || '下架成功')
      setPluginDelistDialog(null)
      fetchUserPlugins()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      notification.error(`${t('cloud:pluginsMarket.delistFailed') || '下架失败'}: ${errorMessage}`)
    } finally {
      setPluginDelistLoading(false)
    }
  }

  const handleUnpublishPreset = async () => {
    notification.info(t('cloud:profile.featureNotAvailable') || '功能开发中')
  }

  const openPresetDetail = async (userPreset: UserPreset) => {
    setPresetDetailSource('published')
    try {
      const presetDetail = await presetsMarketApi.getPresetDetail(userPreset.id)
      setSelectedPreset(presetDetail)
    } catch {
      setSelectedPreset({
        remote_id: userPreset.id,
        is_local: false,
        name: userPreset.name,
        title: userPreset.title,
        avatar: userPreset.avatar || '',
        content: '',
        description: '',
        tags: '',
        author: '',
        create_time: new Date().toISOString(),
        update_time: new Date().toISOString(),
      })
    }
    setPresetDetailOpen(true)
  }

  const handleEditPlugin = async (data: PluginUpdateRequest, moduleName: string) => {
    setIsSubmitting(true)
    try {
      const response = await pluginsMarketApi.updateUserPlugin(moduleName, data)
      if (response.ok) {
        notification.success(t('cloud:pluginsMarket.updateInfoSuccess'))
        setEditingPlugin(null)
        fetchUserPlugins()
      } else {
        notification.error(t('cloud:pluginsMarket.operationFailed'))
      }
    } catch (error) {
      notification.error(`更新失败: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const fetchFullPluginForEdit = async (userPlugin: UserPlugin): Promise<CloudPlugin> => {
    try {
      const fullPlugin = await pluginsMarketApi.getPluginDetail(userPlugin.moduleName)
      return {
        id: userPlugin.id,
        name: fullPlugin.name ?? userPlugin.name,
        moduleName: fullPlugin.moduleName ?? userPlugin.moduleName,
        description: fullPlugin.description ?? '',
        author: fullPlugin.author ?? '',
        hasWebhook: fullPlugin.hasWebhook ?? false,
        homepageUrl: fullPlugin.homepageUrl ?? '',
        githubUrl: fullPlugin.githubUrl ?? '',
        cloneUrl: fullPlugin.cloneUrl ?? '',
        licenseType: fullPlugin.licenseType ?? 'MIT',
        is_local: false,
        icon: fullPlugin.icon ?? userPlugin.icon,
        version: fullPlugin.version ?? '',
        can_update: fullPlugin.can_update ?? false,
        isOwner: fullPlugin.isOwner ?? true,
        minNaVersion: fullPlugin.minNaVersion ?? null,
        maxNaVersion: fullPlugin.maxNaVersion ?? null,
        favoriteCount: fullPlugin.favoriteCount ?? 0,
        isFavorited: fullPlugin.isFavorited ?? false,
        createdAt: fullPlugin.createdAt ?? new Date().toISOString(),
        updatedAt: fullPlugin.updatedAt ?? new Date().toISOString(),
      }
    } catch {
      return {
        id: userPlugin.id,
        name: userPlugin.name,
        moduleName: userPlugin.moduleName,
        description: '',
        author: '',
        hasWebhook: false,
        homepageUrl: '',
        githubUrl: '',
        cloneUrl: '',
        licenseType: 'MIT',
        is_local: false,
        icon: userPlugin.icon,
        version: '',
        can_update: false,
        isOwner: true,
        minNaVersion: null,
        maxNaVersion: null,
        favoriteCount: 0,
        isFavorited: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
    }
  }

  const openEditDialog = async (plugin: UserPlugin) => {
    const fullPlugin = await fetchFullPluginForEdit(plugin)
    setEditingPlugin(fullPlugin)
  }

  const handleEditPreset = (preset: UserPreset) => {
    navigate(presetsPath({ editRemoteId: preset.id }))
  }

  const handleViewFavoriteDetail = async (favorite: FavoriteItem) => {
    if (favorite.targetType === 'preset') {
      setPresetDetailSource('favorites')
      try {
        const presetDetail = await presetsMarketApi.getPresetDetail(favorite.targetId)
        setSelectedPreset(presetDetail)
      } catch {
        setSelectedPreset({
          remote_id: favorite.targetId,
          is_local: false,
          name: favorite.resource.name,
          title: favorite.resource.title,
          avatar: favorite.resource.avatar || '',
          content: '',
          description: favorite.resource.description,
          tags: '',
          author: favorite.resource.author,
          create_time: new Date(favorite.createdAt).toISOString(),
          update_time: new Date(favorite.createdAt).toISOString(),
        })
      }
      setPresetDetailOpen(true)
    } else {
      const moduleName = favorite.resource.moduleName
      if (!moduleName) {
        setSelectedPlugin({
          id: favorite.targetId,
          name: favorite.resource.name,
          moduleName: '',
          description: favorite.resource.description,
          author: favorite.resource.author,
          hasWebhook: favorite.resource.hasWebhook || false,
          homepageUrl: '',
          githubUrl: '',
          cloneUrl: '',
          licenseType: '',
          createdAt: new Date(favorite.createdAt).toISOString(),
          updatedAt: new Date(favorite.createdAt).toISOString(),
          is_local: false,
        })
        setPluginDetailOpen(true)
        return
      }
      try {
        const pluginDetail = await pluginsMarketApi.getPluginDetail(moduleName)
        setSelectedPlugin({
          ...pluginDetail,
          is_local: favorite.resource.isLocal ?? pluginDetail.is_local,
        })
      } catch {
        setSelectedPlugin({
          id: favorite.targetId,
          name: favorite.resource.name,
          moduleName: favorite.resource.moduleName || favorite.targetId,
          description: favorite.resource.description,
          author: favorite.resource.author,
          hasWebhook: favorite.resource.hasWebhook || false,
          homepageUrl: '',
          githubUrl: '',
          cloneUrl: '',
          licenseType: '',
          createdAt: new Date(favorite.createdAt).toISOString(),
          updatedAt: new Date(favorite.createdAt).toISOString(),
          is_local: favorite.resource.isLocal ?? false,
        })
      }
      setPluginDetailOpen(true)
    }
  }

  const handleDownloadClick = (favorite: FavoriteItem) => {
    setConfirmDialog({ open: true, favorite })
  }

  const handleConfirmDownload = async () => {
    if (!confirmDialog.favorite) return

    const favorite = confirmDialog.favorite
    setDownloading(true)

    try {
      if (favorite.targetType === 'preset') {
        if (favorite.resource.isLocal) {
          const localPreset = await presetsApi.getDetailByRemoteId(favorite.targetId)
          const response = await presetsApi.delete(localPreset.id)
          if (!response.ok) {
            throw new Error(t('common:messages.deleteFailed') || '删除失败')
          }
          setFavoriteLocalState('preset', favorite.targetId, false)
          notification.success(t('common:messages.deleteSuccess') || '删除成功')
        } else {
          await presetsMarketApi.downloadPreset(favorite.targetId)
          setFavoriteLocalState('preset', favorite.targetId, true)
          notification.success(t('cloud:presetsMarket.obtainSuccess'))
        }
        await fetchFavorites()
      } else {
        const moduleName = favorite.resource.moduleName
        if (!moduleName) {
          notification.error(t('cloud:profile.moduleNameMissing') || '缺少模块名称')
          return
        }

        if (favorite.resource.isLocal) {
          const ok = await removePackage(moduleName)
          if (!ok) {
            throw new Error(t('cloud:pluginsMarket.removeFailed') || '移除失败')
          }
          setFavoriteLocalState('plugin', favorite.targetId, false)
          notification.success(t('cloud:pluginsMarket.removeSuccess'))
        } else {
          await pluginsMarketApi.downloadPlugin(moduleName)
          setFavoriteLocalState('plugin', favorite.targetId, true)
          notification.success(t('cloud:pluginsMarket.obtainSuccess'))
        }

        await fetchFavorites()
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      notification.error(`${t('cloud:profile.operationFailed') || '操作失败'}: ${errorMessage}`)
    } finally {
      setDownloading(false)
      setConfirmDialog({ open: false, favorite: null })
    }
  }

  const publishedLoading = pluginsLoading || presetsLoading
  const favoritesLoading = loading && favorites.length === 0
  const contentLoading = activeTab === 'published' ? publishedLoading : favoritesLoading

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* 头部统计栏 */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'stretch' }}>
        <Card
          sx={{
            ...CARD_VARIANTS.default.styles,
            flex: '1 1 0',
            minWidth: 160,
          }}
        >
          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Avatar
                src={userProfile?.avatarUrl}
                alt={userProfile?.username}
                sx={{
                  width: 40,
                  height: 40,
                  bgcolor: 'primary.main',
                  fontSize: '1.1rem',
                  border: '2px solid',
                  borderColor: 'divider',
                  flexShrink: 0,
                }}
              >
                {userProfile?.username?.[0]?.toUpperCase() || <PersonIcon />}
              </Avatar>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                  {userProfile?.username || t('cloud:profile.loading')}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.1 }}>
                  {t('cloud:profile.title')}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
        {communityAccessStatus === 'available' && (
          <>
            <StatCard
              icon={<ExtensionIcon sx={{ fontSize: 20 }} />}
              value={userPlugins.length}
              label={t('cloud:profile.plugins')}
              color={theme.palette.primary.main}
              loading={pluginsLoading}
            />
            <StatCard
              icon={<FaceIcon sx={{ fontSize: 20 }} />}
              value={userPresets.length}
              label={t('cloud:profile.presets')}
              color={theme.palette.secondary.main}
              loading={presetsLoading}
            />
            <StatCard
              icon={<FavoriteIcon sx={{ fontSize: 20 }} />}
              value={activeTab === 'favorites' && !loading ? favorites.length : '-'}
              label={t('cloud:profile.myFavorites')}
              color={theme.palette.error.main}
              loading={activeTab === 'favorites' && loading && favorites.length === 0}
            />
          </>
        )}
      </Box>

      {/* Tab 栏 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, mb: 3 }}>
        <PageTabs
          value={activeTab}
          onChange={handleTabChange}
          sx={{ px: { xs: 0.5, md: 2 } }}
        >
          <Tab
            label={t('cloud:profile.myPublished')}
            value="published"
            icon={<ExtensionIcon />}
            iconPosition="start"
          />
          <Tab
            label={t('cloud:profile.myFavorites')}
            value="favorites"
            icon={<FavoriteIcon />}
            iconPosition="start"
          />
        </PageTabs>
      </Card>

      {/* 内容区 — 统一加载覆盖层 */}
      <Box position="relative" minHeight={contentLoading ? '200px' : 'auto'}>
        {contentLoading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
              backdropFilter: 'blur(2px)',
            }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                bgcolor: 'background.paper',
                boxShadow: 2,
                borderRadius: 2,
                px: 3,
                py: 1.5,
              }}
            >
              <CircularProgress size={24} thickness={4} />
              <Typography variant="body2" color="text.secondary">
                {t('cloud:profile.loading')}
              </Typography>
            </Box>
          </Box>
        )}

        {/* 我的发布 */}
        {activeTab === 'published' && !publishedLoading && (
          <>
            {(userPlugins.length > 0 || userPresets.length > 0) ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {/* 插件区 */}
                {userPlugins.length > 0 && (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                      <ExtensionIcon sx={{ fontSize: 20, color: 'primary.main' }} />
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                        {t('cloud:profile.plugins')}
                      </Typography>
                      <Chip
                        label={userPlugins.length}
                        size="small"
                        color="primary"
                        sx={{ height: 22, fontSize: '0.75rem', fontWeight: 600 }}
                      />
                    </Box>
                    <Grid container spacing={3}>
                      {userPlugins.map(plugin => (
                        <Grid item xs={12} sm={6} md={4} key={`plugin-${plugin.id}`}>
                          <UserPluginCard
                            plugin={plugin}
                            onUnpublish={() => setPluginDelistDialog(plugin)}
                            onEdit={() => openEditDialog(plugin)}
                            t={t}
                          />
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                )}

                {/* 分隔线 */}
                {userPlugins.length > 0 && userPresets.length > 0 && (
                  <Divider />
                )}

                {/* 人设区 */}
                {userPresets.length > 0 && (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                      <FaceIcon sx={{ fontSize: 20, color: 'secondary.main' }} />
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                        {t('cloud:profile.presets')}
                      </Typography>
                      <Chip
                        label={userPresets.length}
                        size="small"
                        color="secondary"
                        sx={{ height: 22, fontSize: '0.75rem', fontWeight: 600 }}
                      />
                    </Box>
                    <Grid container spacing={3}>
                      {userPresets.map(preset => (
                        <Grid item xs={12} sm={6} md={4} key={`preset-${preset.id}`}>
                          <UserPresetCard
                            preset={preset}
                            onUnpublish={() => handleUnpublishPreset()}
                            onViewDetail={() => openPresetDetail(preset)}
                            onEdit={() => handleEditPreset(preset)}
                            t={t}
                          />
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                )}
              </Box>
            ) : (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  py: 8,
                  gap: 2,
                  minHeight: 300,
                  border: '1px dashed',
                  borderColor: 'divider',
                  borderRadius: 2,
                }}
              >
                <ExtensionIcon sx={{ fontSize: 56, opacity: 0.2 }} />
                <Typography variant="h6" color="text.secondary">
                  {t('cloud:profile.noPublishedPlugins')}
                </Typography>
              </Box>
            )}
          </>
        )}

        {/* 我的收藏 */}
        {activeTab === 'favorites' && (
          <>
            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            )}

            {!favoritesLoading && favorites.length > 0 ? (
              <Grid container spacing={3}>
                {favorites.map(favorite => (
                  <Grid item xs={12} sm={6} md={4} key={favorite.id}>
                    <FavoriteCard
                      favorite={favorite}
                      onRemove={() => handleRemoveFavorite(favorite)}
                      onViewDetail={() => handleViewFavoriteDetail(favorite)}
                      onDownload={() => handleDownloadClick(favorite)}
                      t={t}
                    />
                  </Grid>
                ))}
              </Grid>
            ) : (
              !favoritesLoading && (
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    py: 8,
                    gap: 2,
                    minHeight: 300,
                    border: '1px dashed',
                    borderColor: 'divider',
                    borderRadius: 2,
                  }}
                >
                  <FavoriteIcon sx={{ fontSize: 56, opacity: 0.2 }} />
                  <Typography variant="h6" color="text.secondary">{t('cloud:profile.noFavorites')}</Typography>
                </Box>
              )
            )}
          </>
        )}
      </Box>

      <PluginEditDialog
        open={!!editingPlugin}
        onClose={() => setEditingPlugin(null)}
        plugin={editingPlugin}
        onSubmit={handleEditPlugin}
        isSubmitting={isSubmitting}
      />

      <Dialog
        open={!!pluginDelistDialog}
        onClose={() => !pluginDelistLoading && setPluginDelistDialog(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t('cloud:pluginsMarket.delist')}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mt: 1 }}>
            {t('cloud:pluginsMarket.confirmDelistMessage', { name: pluginDelistDialog?.name ?? '' })}
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPluginDelistDialog(null)} disabled={pluginDelistLoading}>
            {t('cloud:presetsMarket.cancel')}
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => pluginDelistDialog && handleUnpublishPlugin(pluginDelistDialog)}
            disabled={pluginDelistLoading}
            startIcon={pluginDelistLoading ? <CircularProgress size={16} /> : undefined}
          >
            {t('cloud:pluginsMarket.delist')}
          </Button>
        </DialogActions>
      </Dialog>

      <PluginDetailDialog
        open={pluginDetailOpen}
        onClose={() => setPluginDetailOpen(false)}
        plugin={selectedPlugin}
        t={t}
        onDownload={
          selectedPlugin && !selectedPlugin.is_local && hasSelectedPluginModuleName
            ? async () => {
                try {
                  await pluginsMarketApi.downloadPlugin(selectedPlugin.moduleName)
                  notification.success(t('cloud:pluginsMarket.obtainSuccess'))
                  setSelectedPlugin(prev => (prev ? { ...prev, is_local: true } : prev))
                  await fetchFavorites()
                } catch (err) {
                  const errorMessage = err instanceof Error ? err.message : String(err)
                  notification.error(`${t('cloud:profile.downloadFailed') || '下载失败'}: ${errorMessage}`)
                }
              }
            : undefined
        }
        onFavoriteChange={(pluginId, isFavorited) => {
          if (!isFavorited) {
            setFavorites(prev => prev.filter(f => !(f.targetType === 'plugin' && f.targetId === pluginId)))
          }
        }}
        onRemove={
          selectedPlugin?.is_local
            ? async () => {
                try {
                  const ok = await removePackage(selectedPlugin.moduleName)
                  if (!ok) {
                    throw new Error(t('cloud:pluginsMarket.removeFailed') || '移除失败')
                  }
                  notification.success(t('cloud:pluginsMarket.removeSuccess'))
                  setSelectedPlugin(prev => (prev ? { ...prev, is_local: false } : prev))
                  await fetchFavorites()
                } catch (err) {
                  const errorMessage = err instanceof Error ? err.message : String(err)
                  notification.error(`${t('cloud:pluginsMarket.removeFailed') || '移除失败'}: ${errorMessage}`)
                }
              }
            : undefined
        }
      />

      <PresetDetailDialog
        open={presetDetailOpen}
        onClose={() => setPresetDetailOpen(false)}
        preset={selectedPreset}
        t={(key: string) => t(`cloud:${key}`)}
        showFavoriteAction={presetDetailSource === 'favorites'}
        onFavoriteChange={(remoteId, isFavorited) => {
          if (!isFavorited) {
            setFavorites(prev => prev.filter(f => !(f.targetType === 'preset' && f.targetId === remoteId)))
          }
        }}
      />

      {/* 确认下载对话框 */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => !downloading && setConfirmDialog({ open: false, favorite: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {(confirmDialog.favorite?.targetType === 'plugin' || confirmDialog.favorite?.targetType === 'preset') &&
            confirmDialog.favorite?.resource.isLocal
            ? t('common:actions.delete')
            : (confirmDialog.favorite?.targetType === 'preset'
              ? t('cloud:presetsMarket.confirmObtain')
              : t('cloud:pluginsMarket.confirmObtain'))}
        </DialogTitle>
        <DialogContent>
          {confirmDialog.favorite?.targetType === 'plugin' && !confirmDialog.favorite?.resource.isLocal && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, fontSize: '0.875rem' }}>
              <strong style={{ color: '#ed6c02' }}>{t('cloud:pluginsMarket.securityNoticeTitle')}</strong>{' '}
              {t('cloud:pluginsMarket.pluginSecurityNotice')}
            </Typography>
          )}

          {confirmDialog.favorite?.targetType === 'preset' && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {confirmDialog.favorite?.resource.isLocal
                ? `${t('common:messages.confirmDelete') || '确认删除？'}`
                : t('cloud:presetsMarket.confirmObtainMessage', {
                    name: confirmDialog.favorite?.resource.title || confirmDialog.favorite?.resource.name,
                  })}
            </Alert>
          )}

          {confirmDialog.favorite?.targetType === 'plugin' && (
            <Typography>
              {confirmDialog.favorite?.resource.isLocal
                ? t('cloud:pluginsMarket.confirmRemoveMessage', {
                    name: confirmDialog.favorite?.resource.title || confirmDialog.favorite?.resource.name,
                  })
                : t('cloud:pluginsMarket.confirmObtainMessage', {
                    name: confirmDialog.favorite?.resource.title || confirmDialog.favorite?.resource.name,
                  })}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmDialog({ open: false, favorite: null })}
            disabled={downloading}
          >
            {t('cloud:presetsMarket.cancel')}
          </Button>
          <Button
            onClick={handleConfirmDownload}
            color="primary"
            variant="contained"
            disabled={downloading}
            startIcon={downloading ? <CircularProgress size={16} /> : undefined}
          >
            {downloading
              ? ((confirmDialog.favorite?.targetType === 'plugin' || confirmDialog.favorite?.targetType === 'preset') &&
                  confirmDialog.favorite?.resource.isLocal
                ? t('cloud:pluginsMarket.loading') || '处理中...'
                : (confirmDialog.favorite?.targetType === 'preset'
                  ? t('cloud:presetsMarket.loading') || '获取中...'
                  : t('cloud:pluginsMarket.loading') || '获取中...'))
              : (((confirmDialog.favorite?.targetType === 'plugin' || confirmDialog.favorite?.targetType === 'preset') &&
                    confirmDialog.favorite?.resource.isLocal)
                ? t('common:actions.delete')
                : (confirmDialog.favorite?.targetType === 'preset'
                  ? t('cloud:presetsMarket.obtain')
                  : t('cloud:pluginsMarket.obtain')))}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
