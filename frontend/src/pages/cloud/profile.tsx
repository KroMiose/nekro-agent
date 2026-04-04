import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Card,
  CardContent,
  Grid,
  Avatar,
  Chip,
  IconButton,
  Button,
  CircularProgress,
  Alert,
  Divider,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Link,
} from '@mui/material'
import {
  Person as PersonIcon,
  Extension as ExtensionIcon,
  Face as FaceIcon,
  Favorite as FavoriteIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material'
import { favoritesApi, FavoriteItem } from '../../services/api/cloud/favorites'
import {
  pluginsMarketApi,
  UserPlugin,
  PluginUpdateRequest,
  CloudPlugin,
} from '../../services/api/cloud/plugins_market'
import PluginEditDialog from '../../components/cloud/PluginEditDialog'
import PresetDetailDialog from '../../components/cloud/PresetDetailDialog'
import { CloudPreset } from '../../services/api/cloud/presets_market'
import { presetsMarketApi, UserPreset } from '../../services/api/cloud/presets_market'
import { authApi } from '../../services/api/cloud'
import { useNotification } from '../../hooks/useNotification'
import { useTranslation } from 'react-i18next'
import { UI_STYLES } from '../../theme/themeConfig'
import { CARD_VARIANTS } from '../../theme/variants'

// 从 auth.ts 导入 CommunityUserProfile 类型
import type { CommunityUserProfile } from '../../services/api/cloud/auth'

// Tab 类型
type TabValue = 'published' | 'favorites'

// 收藏资源卡片组件
const FavoriteCard = ({
  favorite,
  onRemove,
  onViewDetail,
  t,
}: {
  favorite: FavoriteItem
  onRemove: () => void
  onViewDetail: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}) => {
  const [iconError, setIconError] = useState(false)
  const isPlugin = favorite.targetType === 'plugin'

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
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
            {/* 图标 */}
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
              {(favorite.resource.icon || favorite.resource.avatar) && !iconError ? (
                <img
                  src={favorite.resource.icon || favorite.resource.avatar}
                  alt={`${favorite.resource.name} 图标`}
                  onError={() => setIconError(true)}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : isPlugin ? (
                <ExtensionIcon
                  sx={{
                    fontSize: 28,
                    opacity: 0.7,
                    color: theme => theme.palette.primary.main,
                  }}
                />
              ) : (
                <FaceIcon
                  sx={{
                    fontSize: 28,
                    opacity: 0.7,
                    color: theme => theme.palette.secondary.main,
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
                {favorite.resource.title || favorite.resource.name}
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
                {t('cloud:profile.author')}: {favorite.resource.author}
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
          {favorite.resource.description || t('cloud:profile.noDescription')}
        </Typography>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
          <Chip
            label={isPlugin ? t('cloud:profile.plugin') : t('cloud:profile.preset')}
            size="small"
            color={isPlugin ? 'primary' : 'secondary'}
            sx={{ height: 24, fontSize: '0.75rem' }}
          />
          <Chip
            label={`${t('cloud:profile.collectedAt')}: ${new Date(favorite.createdAt).toLocaleDateString()}`}
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

      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          p: 1.5,
          bgcolor: UI_STYLES.SELECTED,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Button
          size="small"
          variant="text"
          startIcon={<OpenInNewIcon />}
          onClick={onViewDetail}
        >
          {t('cloud:profile.viewDetail') || '查看详情'}
        </Button>
        <Tooltip title={t('cloud:profile.removeFavorite')}>
          <IconButton size="small" color="error" onClick={onRemove}>
            <FavoriteIcon />
          </IconButton>
        </Tooltip>
      </Box>
    </Card>
  )
}

// 用户发布的插件卡片
const UserPluginCard = ({
  plugin,
  onUnpublish,
  onEdit,
  t,
}: {
  plugin: UserPlugin
  onUnpublish: () => void
  onEdit: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}) => {
  const [iconError, setIconError] = useState(false)

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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
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
              {plugin.moduleName}
            </Typography>
          </Box>
        </Box>
        <Chip
          label={t('cloud:profile.plugin')}
          size="small"
          color="primary"
          sx={{ height: 24, fontSize: '0.75rem' }}
        />
      </CardContent>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          p: 1.5,
          bgcolor: UI_STYLES.SELECTED,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Button
          size="small"
          variant="text"
          startIcon={<EditIcon />}
          onClick={onEdit}
        >
          {t('cloud:pluginsMarket.edit') || '编辑'}
        </Button>
        <Button
          size="small"
          variant="text"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={onUnpublish}
        >
          {t('cloud:pluginsMarket.delist')}
        </Button>
      </Box>
    </Card>
  )
}

// 用户发布的人设卡片
const UserPresetCard = ({
  preset,
  onUnpublish,
  onViewDetail,
  t,
}: {
  preset: UserPreset
  onUnpublish: () => void
  onViewDetail: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}) => {
  const [avatarError, setAvatarError] = useState(false)

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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
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
            {preset.avatar && !avatarError ? (
              <img
                src={preset.avatar}
                alt={`${preset.name} 头像`}
                onError={() => setAvatarError(true)}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            ) : (
              <FaceIcon
                sx={{
                  fontSize: 28,
                  opacity: 0.7,
                  color: theme => theme.palette.secondary.main,
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
              {preset.title || preset.name}
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
              {preset.name}
            </Typography>
          </Box>
        </Box>
        <Chip
          label={t('cloud:profile.preset')}
          size="small"
          color="secondary"
          sx={{ height: 24, fontSize: '0.75rem' }}
        />
      </CardContent>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          p: 1.5,
          bgcolor: UI_STYLES.SELECTED,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Button
          size="small"
          variant="text"
          startIcon={<OpenInNewIcon />}
          onClick={onViewDetail}
        >
          {t('cloud:profile.viewDetail')}
        </Button>
        <Button
          size="small"
          variant="text"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={onUnpublish}
        >
          {t('cloud:pluginsMarket.delist')}
        </Button>
      </Box>
    </Card>
  )
}

export default function CloudProfile() {
  const [activeTab, setActiveTab] = useState<TabValue>('published')
  const [userProfile, setUserProfile] = useState<CommunityUserProfile | null>(null)
  const [favorites, setFavorites] = useState<FavoriteItem[]>([])
  const [userPlugins, setUserPlugins] = useState<UserPlugin[]>([])
  const [userPresets, setUserPresets] = useState<UserPreset[]>([])
  const [loading, setLoading] = useState(true)
  const [publishedLoading, setPublishedLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingPlugin, setEditingPlugin] = useState<CloudPlugin | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState<CloudPreset | null>(null)
  const [presetDetailOpen, setPresetDetailOpen] = useState(false)
  const [selectedPlugin, setSelectedPlugin] = useState<CloudPlugin | null>(null)
  const [pluginDetailOpen, setPluginDetailOpen] = useState(false)
  const notification = useNotification()
  const { t } = useTranslation(['cloud', 'navigation'])

  // 分类收藏
  const pluginFavorites = favorites.filter(f => f.targetType === 'plugin')
  const presetFavorites = favorites.filter(f => f.targetType === 'preset')

  // 获取用户资料
  const fetchUserProfile = useCallback(async () => {
    try {
      const profile = await authApi.getCommunityUserProfile()
      setUserProfile(profile)
    } catch (err) {
      console.error('Failed to fetch user profile:', err)
    }
  }, [])

  // 获取收藏列表（一次性获取所有）
  const fetchFavorites = useCallback(async () => {
    try {
      setLoading(true)
      const data = await favoritesApi.getFavorites({
        page: 1,
        page_size: 32, // 最大支持 32
      })
      setFavorites(data.data.items)
      setError(null)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      setError(`${t('cloud:profile.fetchFailed')}: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }, [t])

  // 获取用户发布的插件
  const fetchUserPlugins = useCallback(async () => {
    setPublishedLoading(true)
    try {
      const plugins = await pluginsMarketApi.getUserPlugins()
      setUserPlugins(plugins)
    } catch (err) {
      console.error('Failed to fetch user plugins:', err)
    } finally {
      setPublishedLoading(false)
    }
  }, [])

  // 获取用户发布的人设
  const fetchUserPresets = useCallback(async () => {
    setPublishedLoading(true)
    try {
      const data = await presetsMarketApi.getUserPresets()
      setUserPresets(data.items)
    } catch (err) {
      console.error('Failed to fetch user presets:', err)
    } finally {
      setPublishedLoading(false)
    }
  }, [])

  // 初始加载
  useEffect(() => {
    fetchUserProfile()
    fetchUserPlugins()
    fetchUserPresets()
  }, [fetchUserProfile, fetchUserPlugins, fetchUserPresets])

  // 收藏列表加载
  useEffect(() => {
    if (activeTab === 'favorites') {
      fetchFavorites()
    }
  }, [activeTab, fetchFavorites])

  // Tab 切换
  const handleTabChange = (_event: React.SyntheticEvent, newValue: TabValue) => {
    setActiveTab(newValue)
  }

  // 取消收藏
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

  // 下架插件
  const handleUnpublishPlugin = async (plugin: UserPlugin) => {
    try {
      await pluginsMarketApi.deleteUserPlugin(plugin.moduleName)
      notification.success(t('cloud:pluginsMarket.delistSuccess') || '下架成功')
      fetchUserPlugins()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      notification.error(`${t('cloud:pluginsMarket.delistFailed') || '下架失败'}: ${errorMessage}`)
    }
  }

  // 下架人设（需要后端接口）
  const handleUnpublishPreset = async (_preset: UserPreset) => {
    notification.info(t('cloud:profile.featureNotAvailable') || '功能开发中')
  }

  // 打开人设详情对话框
  const openPresetDetail = async (userPreset: UserPreset) => {
    try {
      // 尝试获取完整的人设详情
      const presetDetail = await presetsMarketApi.getPresetDetail(userPreset.id)
      setSelectedPreset(presetDetail)
      setPresetDetailOpen(true)
    } catch {
      // 如果获取失败，使用基本信息构造
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
      setPresetDetailOpen(true)
    }
  }

  // 编辑插件
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

  // 获取完整的插件信息用于编辑
  const fetchFullPluginForEdit = async (userPlugin: UserPlugin): Promise<CloudPlugin> => {
    try {
      const fullPlugin = await pluginsMarketApi.getPluginDetail(userPlugin.moduleName)
      console.log('Full plugin detail:', fullPlugin)
      // 明确映射字段，确保所有字段都有值
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
    } catch (err) {
      console.error('Failed to fetch full plugin detail:', err)
      // 如果获取详情失败，使用基本信息构造
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

  // 打开编辑对话框
  const openEditDialog = async (plugin: UserPlugin) => {
    const fullPlugin = await fetchFullPluginForEdit(plugin)
    setEditingPlugin(fullPlugin)
  }

  // 查看收藏详情
  const handleViewFavoriteDetail = async (favorite: FavoriteItem) => {
    if (favorite.targetType === 'preset') {
      // 获取完整的人设详情
      try {
        const presetDetail = await presetsMarketApi.getPresetDetail(favorite.targetId)
        setSelectedPreset(presetDetail)
        setPresetDetailOpen(true)
      } catch {
        // 如果获取失败，使用收藏中的基本信息构造
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
        setPresetDetailOpen(true)
      }
    } else {
      // 获取完整的插件详情，使用 moduleName
      const moduleName = favorite.resource.moduleName
      if (!moduleName) {
        // 如果没有 moduleName，使用收藏中的基本信息
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
        setSelectedPlugin(pluginDetail)
        setPluginDetailOpen(true)
      } catch {
        // 如果获取失败，使用收藏中的基本信息构造
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
          is_local: false,
        })
        setPluginDetailOpen(true)
      }
    }
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* 用户信息卡片 */}
      <Card
        sx={{
          ...CARD_VARIANTS.default.styles,
          mb: 3,
          p: 2.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            src={userProfile?.avatarUrl}
            alt={userProfile?.username}
            sx={{
              width: 64,
              height: 64,
              bgcolor: 'primary.main',
              fontSize: '1.75rem',
            }}
          >
            {userProfile?.username?.[0]?.toUpperCase() || <PersonIcon />}
          </Avatar>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" fontWeight={600}>
              {userProfile?.username || t('cloud:profile.loading')}
            </Typography>
          </Box>
        </Box>
      </Card>

      {/* 标签页 */}
      <Box sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          sx={{
            '& .MuiTab-root': {
              textTransform: 'none',
              borderRadius: 1.5,
              color: 'text.secondary',
              '&:hover': {
                color: 'text.primary',
                bgcolor: theme =>
                  theme.palette.mode === 'dark'
                    ? 'rgba(255,255,255,0.05)'
                    : 'rgba(0,0,0,0.05)',
              },
            },
            '& .MuiTab-root.Mui-selected': {
              color: 'text.primary',
              bgcolor: theme =>
                theme.palette.mode === 'dark'
                  ? 'rgba(255,255,255,0.08)'
                  : 'common.white',
            },
            '& .MuiTabs-indicator': {
              height: 3,
              borderRadius: 999,
            },
          }}
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
        </Tabs>
      </Box>

      {/* 我的发布 */}
      {activeTab === 'published' && (
        <Box>
          {/* 插件列表 */}
          <Typography variant="h6" gutterBottom>
            {t('cloud:profile.plugins')} ({userPlugins.length})
          </Typography>
          {publishedLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : userPlugins.length > 0 ? (
            <Grid container spacing={3} sx={{ mb: 4 }}>
              {userPlugins.map(plugin => (
                <Grid item xs={12} sm={6} md={4} key={plugin.id}>
                  <UserPluginCard
                    plugin={plugin}
                    onUnpublish={() => handleUnpublishPlugin(plugin)}
                    onEdit={() => openEditDialog(plugin)}
                    t={t}
                  />
                </Grid>
              ))}
            </Grid>
          ) : (
            <Alert severity="info" sx={{ mb: 4 }}>
              {t('cloud:profile.noPublishedPlugins')}
            </Alert>
          )}

          <Divider sx={{ my: 3 }} />

          {/* 人设列表 */}
          <Typography variant="h6" gutterBottom>
            {t('cloud:profile.presets')} ({userPresets.length})
          </Typography>
          {publishedLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : userPresets.length > 0 ? (
            <Grid container spacing={3}>
              {userPresets.map(preset => (
                <Grid item xs={12} sm={6} md={4} key={preset.id}>
                  <UserPresetCard
                    preset={preset}
                    onUnpublish={() => handleUnpublishPreset(preset)}
                    onViewDetail={() => openPresetDetail(preset)}
                    t={t}
                  />
                </Grid>
              ))}
            </Grid>
          ) : (
            <Alert severity="info">{t('cloud:profile.noPublishedPresets')}</Alert>
          )}
        </Box>
      )}

      {/* 我的收藏 */}
      {activeTab === 'favorites' && (
        <Box>
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
              {/* 左侧：插件收藏 */}
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  {t('cloud:profile.plugins')} ({pluginFavorites.length})
                </Typography>
                {pluginFavorites.length > 0 ? (
                  <Grid container spacing={2}>
                    {pluginFavorites.map(favorite => (
                      <Grid item xs={12} key={favorite.id}>
                        <FavoriteCard
                          favorite={favorite}
                          onRemove={() => handleRemoveFavorite(favorite)}
                          onViewDetail={() => handleViewFavoriteDetail(favorite)}
                          t={t}
                        />
                      </Grid>
                    ))}
                  </Grid>
                ) : (
                  <Alert severity="info">{t('cloud:profile.noPluginFavorites') || '暂无插件收藏'}</Alert>
                )}
              </Grid>

              {/* 右侧：人设收藏 */}
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  {t('cloud:profile.presets')} ({presetFavorites.length})
                </Typography>
                {presetFavorites.length > 0 ? (
                  <Grid container spacing={2}>
                    {presetFavorites.map(favorite => (
                      <Grid item xs={12} key={favorite.id}>
                        <FavoriteCard
                          favorite={favorite}
                          onRemove={() => handleRemoveFavorite(favorite)}
                          onViewDetail={() => handleViewFavoriteDetail(favorite)}
                          t={t}
                        />
                      </Grid>
                    ))}
                  </Grid>
                ) : (
                  <Alert severity="info">{t('cloud:profile.noPresetFavorites') || '暂无人设收藏'}</Alert>
                )}
              </Grid>
            </Grid>
          ) : (
            <Alert severity="info">{t('cloud:profile.noFavorites')}</Alert>
          )}
        </Box>
      )}

      {/* 插件编辑对话框 */}
      <PluginEditDialog
        open={!!editingPlugin}
        onClose={() => setEditingPlugin(null)}
        plugin={editingPlugin}
        onSubmit={handleEditPlugin}
        isSubmitting={isSubmitting}
      />

      {/* 插件详情对话框 */}
      <Dialog
        open={pluginDetailOpen}
        onClose={() => setPluginDetailOpen(false)}
        maxWidth="md"
        fullWidth
        scroll="paper"
      >
        <DialogTitle>
          {t('cloud:pluginsMarket.pluginDetail')}: {selectedPlugin?.name}
        </DialogTitle>
        <DialogContent dividers>
          {selectedPlugin && (
            <Grid container spacing={3}>
              <Grid item xs={12} sm={4}>
                {selectedPlugin.icon ? (
                  <Avatar
                    src={selectedPlugin.icon}
                    alt={selectedPlugin.name}
                    variant="rounded"
                    sx={{ width: '100%', height: 'auto', aspectRatio: '1/1' }}
                  />
                ) : (
                  <Avatar
                    variant="rounded"
                    sx={{
                      width: '100%',
                      height: 'auto',
                      aspectRatio: '1/1',
                      bgcolor: 'primary.main',
                    }}
                  >
                    <ExtensionIcon sx={{ fontSize: 64 }} />
                  </Avatar>
                )}
              </Grid>
              <Grid item xs={12} sm={8}>
                <Typography variant="h5" gutterBottom>
                  {selectedPlugin.name}
                </Typography>
                <Typography variant="body1" color="text.secondary" gutterBottom>
                  {t('cloud:pluginsMarket.moduleName')}: {selectedPlugin.moduleName}
                </Typography>
                <Typography variant="body2" paragraph>
                  {selectedPlugin.description}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                  {selectedPlugin.hasWebhook && (
                    <Chip
                      label={t('cloud:pluginsMarket.hasWebhook')}
                      size="small"
                      color="primary"
                    />
                  )}
                  {selectedPlugin.licenseType && (
                    <Chip
                      label={selectedPlugin.licenseType}
                      size="small"
                      variant="outlined"
                    />
                  )}
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {t('cloud:pluginsMarket.author')}: {selectedPlugin.author}
                </Typography>
                {(selectedPlugin.homepageUrl || selectedPlugin.githubUrl) && (
                  <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                    {selectedPlugin.homepageUrl && (
                      <Link
                        href={selectedPlugin.homepageUrl}
                        target="_blank"
                        rel="noopener"
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.5,
                          color: 'primary.main',
                          textDecoration: 'none',
                          '&:hover': {
                            textDecoration: 'underline',
                          },
                        }}
                      >
                        {t('cloud:pluginsMarket.homepage')}
                      </Link>
                    )}
                    {selectedPlugin.githubUrl && (
                      <Link
                        href={selectedPlugin.githubUrl}
                        target="_blank"
                        rel="noopener"
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.5,
                          color: 'primary.main',
                          textDecoration: 'none',
                          '&:hover': {
                            textDecoration: 'underline',
                          },
                        }}
                      >
                        GitHub
                      </Link>
                    )}
                  </Box>
                )}
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPluginDetailOpen(false)}>
            {t('cloud:presetsMarket.close')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 人设详情对话框（复用市场组件） */}
      <PresetDetailDialog
        open={presetDetailOpen}
        onClose={() => setPresetDetailOpen(false)}
        preset={selectedPreset}
        t={(key: string) => t(`cloud:${key}`)}
        onFavoriteChange={(remoteId, isFavorited) => {
          // 如果取消收藏，从列表中移除
          if (!isFavorited) {
            setFavorites(prev => prev.filter(f => !(f.targetType === 'preset' && f.targetId === remoteId)))
          }
        }}
      />
    </Box>
  )
}
