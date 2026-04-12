import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Tab,
  Card,
  Grid,
  Avatar,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from '@mui/material'
import {
  Person as PersonIcon,
  Extension as ExtensionIcon,
  Favorite as FavoriteIcon,
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
import ProfileSection from '../../components/cloud/profile/ProfileSection'
import CommunityApiKeyRequiredContent from '../../components/common/CommunityApiKeyRequiredContent'
import { useCommunityUserStore } from '../../stores/communityUser'

type TabValue = 'published' | 'favorites'
type PresetDetailSource = 'published' | 'favorites'

export default function CloudProfile() {
  const navigate = useNavigate()
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

  const pluginFavorites = favorites.filter(f => f.targetType === 'plugin')
  const presetFavorites = favorites.filter(f => f.targetType === 'preset')

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
      const data = await favoritesApi.getFavorites({ page: 1, page_size: 32 })
      setFavorites(data.data.items)
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
          moduleName: favorite.targetId,
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

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* 用户信息卡片 */}
      <Card
        sx={{
          ...CARD_VARIANTS.default.styles,
          mb: 3,
          p: { xs: 2.25, md: 2.75 },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            src={userProfile?.avatarUrl}
            alt={userProfile?.username}
            sx={{
              width: 72,
              height: 72,
              bgcolor: 'primary.main',
              fontSize: '2rem',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            {userProfile?.username?.[0]?.toUpperCase() || <PersonIcon />}
          </Avatar>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: '0.08em' }}>
              {t('cloud:profile.title')}
            </Typography>
            <Typography variant="h5" sx={{ fontWeight: 700, mt: 0.2 }}>
              {userProfile?.username || t('cloud:profile.loading')}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
              {activeTab === 'published'
                ? t('cloud:profile.myPublished')
                : t('cloud:profile.myFavorites')}
            </Typography>
          </Box>
        </Box>
      </Card>

      {/* 标签页 */}
      <Box sx={{ mb: 3 }}>
        <PageTabs
          value={activeTab}
          onChange={handleTabChange}
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
      </Box>

      {/* 我的发布 */}
      {activeTab === 'published' && (
        <Box sx={{ display: 'grid', gap: 3 }}>
          <ProfileSection title={t('cloud:profile.plugins')} count={userPlugins.length}>
            {pluginsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : userPlugins.length > 0 ? (
              <Grid container spacing={3}>
                {userPlugins.map(plugin => (
                  <Grid item xs={12} sm={6} md={4} key={plugin.id}>
                    <UserPluginCard
                      plugin={plugin}
                      onUnpublish={() => setPluginDelistDialog(plugin)}
                      onEdit={() => openEditDialog(plugin)}
                      t={t}
                    />
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Alert severity="info">{t('cloud:profile.noPublishedPlugins')}</Alert>
            )}
          </ProfileSection>

          <ProfileSection title={t('cloud:profile.presets')} count={userPresets.length}>
            {presetsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : userPresets.length > 0 ? (
              <Grid container spacing={3}>
                {userPresets.map(preset => (
                  <Grid item xs={12} sm={6} md={4} key={preset.id}>
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
            ) : (
              <Alert severity="info">{t('cloud:profile.noPublishedPresets')}</Alert>
            )}
          </ProfileSection>
        </Box>
      )}

      {/* 我的收藏 */}
      {activeTab === 'favorites' && (
        <Box sx={{ display: 'grid', gap: 3 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {loading && favorites.length === 0 ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : favorites.length > 0 ? (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <ProfileSection title={t('cloud:profile.plugins')} count={pluginFavorites.length}>
                  {pluginFavorites.length > 0 ? (
                    <Grid container spacing={2}>
                      {pluginFavorites.map(favorite => (
                        <Grid item xs={12} key={favorite.id}>
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
                    <Alert severity="info">{t('cloud:profile.noPluginFavorites') || '暂无插件收藏'}</Alert>
                  )}
                </ProfileSection>
              </Grid>

              <Grid item xs={12} md={6}>
                <ProfileSection title={t('cloud:profile.presets')} count={presetFavorites.length}>
                  {presetFavorites.length > 0 ? (
                    <Grid container spacing={2}>
                      {presetFavorites.map(favorite => (
                        <Grid item xs={12} key={favorite.id}>
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
                    <Alert severity="info">{t('cloud:profile.noPresetFavorites') || '暂无人设收藏'}</Alert>
                  )}
                </ProfileSection>
              </Grid>
            </Grid>
          ) : (
            <Alert severity="info">{t('cloud:profile.noFavorites')}</Alert>
          )}
        </Box>
      )}

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
          selectedPlugin && !selectedPlugin.is_local
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
