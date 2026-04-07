import { Outlet, useNavigate, useLocation, useParams } from 'react-router-dom'
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  CircularProgress,
  useTheme,
  useMediaQuery,
  Badge,
  Button,
} from '@mui/material'
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded'
import ExpandLessRoundedIcon from '@mui/icons-material/ExpandLessRounded'
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { adaptersApi, AdapterDetailInfo } from '../services/api/adapters'
import { CARD_VARIANTS } from '../theme/variants'
import {
  getAdapterConfig,
  getAdapterTabPath,
  createAdapterIcon,
  getAdapterStatusDisplay,
} from '../config/adapters'
import { Suspense, useState } from 'react'
import { useTranslation } from 'react-i18next'

export default function AdapterLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { adapterKey } = useParams<{ adapterKey: string }>()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const { t } = useTranslation('adapter')
  const [headerExpanded, setHeaderExpanded] = useState(true)

  // 获取当前适配器的选项卡配置
  const adapterConfig = getAdapterConfig(adapterKey || '')
  const tabs = adapterConfig.tabs.map(tab => ({
    label: tab.label,
    value: tab.value,
    icon: tab.icon,
    path: getAdapterTabPath(adapterKey || '', tab.path),
  }))

  // 获取适配器信息
  const {
    data: adapterInfo,
    isLoading,
    error,
  } = useQuery<AdapterDetailInfo>({
    queryKey: ['adapter-info', adapterKey],
    queryFn: () => adaptersApi.getAdapterInfo(adapterKey!),
    enabled: !!adapterKey,
  })

  // 获取当前激活的标签
  const getActiveTab = () => {
    const path = location.pathname
    const currentTab = tabs.find(tab => tab.path === path)
    return currentTab?.value || 'home'
  }

  // 处理标签切换
  const handleTabChange = (_: React.SyntheticEvent, newValue: string) => {
    const tab = tabs.find(t => t.value === newValue)
    if (tab) {
      navigate(tab.path)
    }
  }

  // // 获取适配器图标
  // const getAdapterIcon = (key: string) => {
  //   return createAdapterIcon(key, theme, 48)
  // }

  if (isLoading) {
    return (
      <Box
        sx={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        <CircularProgress size={48} thickness={3.6} />
        <Typography variant="body2" color="text.secondary">
          {t('loading')}
        </Typography>
      </Box>
    )
  }

  if (error || !adapterInfo) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          sx={{
            ...CARD_VARIANTS.default.styles,
            border: `1px solid ${theme.palette.error.main}`,
          }}
        >
          <Typography variant="h6" gutterBottom>
            {t('loadFailed')}
          </Typography>
          {error instanceof Error ? error.message : t('loadAdapterFailed')}
        </Alert>
      </Box>
    )
  }

  const statusDisplay = getAdapterStatusDisplay(adapterInfo.status)

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: { xs: 2, md: 3 },
        p: { xs: 1, md: 2 },
        overflow: 'hidden',
      }}
    >
      {/* 适配器头部信息 - 紧凑版本 */}
      <Card
        sx={{
          ...CARD_VARIANTS.default.styles,
        }}
      >
        <CardContent sx={{ p: { xs: 1.5, md: 2 }, '&:last-child': { pb: { xs: 1.5, md: 2 } } }}>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'auto minmax(0, 1fr)',
              columnGap: 1.5,
              rowGap: headerExpanded ? 1.25 : 0,
              alignItems: 'start',
            }}
          >
            <Badge
              overlap="circular"
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              badgeContent={
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    backgroundColor: statusDisplay.getBgColor(theme),
                    border: `2px solid ${theme.palette.background.paper}`,
                  }}
                />
              }
              sx={{ gridColumn: '1 / 2', gridRow: '1 / 2' }}
            >
              {createAdapterIcon(adapterKey!, theme, 40)}
            </Badge>

            <Box
              sx={{
                gridColumn: '2 / 3',
                gridRow: '1 / 2',
                minWidth: 0,
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                flexWrap: 'wrap',
              }}
            >
              <Typography
                variant="h6"
                component="h1"
                sx={{
                  fontWeight: 600,
                  fontSize: { xs: '1.125rem', md: '1.25rem' },
                  lineHeight: 1.2,
                }}
              >
                {adapterInfo.name}
              </Typography>
              <Chip
                icon={statusDisplay.icon}
                label={t(statusDisplay.text)}
                color={statusDisplay.color}
                variant="filled"
                size="small"
                sx={{ height: 24, fontWeight: 500 }}
              />
              <Chip
                label={adapterInfo.config_class}
                color="primary"
                variant="outlined"
                size="small"
                sx={{ height: 24, fontWeight: 400 }}
              />
              <Box sx={{ flex: 1 }} />
              <Button
                size="small"
                variant="text"
                startIcon={headerExpanded ? <ExpandLessRoundedIcon fontSize="small" /> : <ExpandMoreRoundedIcon fontSize="small" />}
                onClick={() => setHeaderExpanded(prev => !prev)}
                sx={{
                  alignSelf: 'center',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  minHeight: 28,
                  px: 1,
                  borderRadius: '999px',
                  color: 'text.secondary',
                  backgroundColor: 'action.hover',
                  boxShadow: 'none',
                  '&:hover': {
                    color: 'primary.main',
                    backgroundColor: 'action.selected',
                    boxShadow: 'none',
                  },
                }}
              >
                {headerExpanded ? t('home.collapseSummary') : t('home.expandSummary')}
              </Button>
              <Button
                size="small"
                variant="outlined"
                startIcon={<ArrowBackRoundedIcon fontSize="small" />}
                onClick={() => navigate('/adapters')}
                sx={{
                  alignSelf: 'center',
                  whiteSpace: 'nowrap',
                  ml: 'auto',
                  flexShrink: 0,
                  minHeight: 28,
                  px: 1.25,
                  borderRadius: '999px',
                  borderColor: 'divider',
                  backgroundColor: 'background.paper',
                  boxShadow: 'none',
                  '&:hover': {
                    borderColor: 'primary.main',
                    backgroundColor: 'action.hover',
                    boxShadow: 'none',
                  },
                }}
              >
                {t('hub.backToHub')}
              </Button>
            </Box>
            {headerExpanded && (
              <Box
                sx={{
                  gridColumn: '1 / -1',
                  gridRow: '2 / 3',
                  minWidth: 0,
                }}
              >
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    lineHeight: 1.6,
                    wordBreak: 'break-word',
                  }}
                >
                  {adapterInfo.description}
                </Typography>
                {adapterInfo.version && (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.75, display: 'block' }}>
                    {t('home.version')}: {adapterInfo.version}
                    {adapterInfo.author && ` • ${t('home.author')}: ${adapterInfo.author}`}
                  </Typography>
                )}
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* 导航标签 - 紧凑版本 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <Tabs
          value={getActiveTab()}
          onChange={handleTabChange}
          variant={isMobile ? 'fullWidth' : 'standard'}
          indicatorColor="primary"
          textColor="primary"
          sx={{
            minHeight: { xs: 48, md: 52 },
            px: { xs: 0.5, md: 2 },
            '& .MuiTab-root': {
              minHeight: { xs: 48, md: 52 },
              fontSize: '0.875rem',
              fontWeight: 600,
              textTransform: 'none',
              transition: 'all 0.2s ease',
              borderRadius: '8px',
              mx: 0.5,
              py: { xs: 1, md: 1.5 },
              '&:hover': {
                backgroundColor: theme.palette.action.hover,
              },
              '&.Mui-selected': {
                color: theme.palette.primary.main,
                backgroundColor: theme.palette.primary.main + '10',
              },
            },
            '& .MuiTabs-indicator': {
              height: 3,
              borderRadius: '2px',
              boxShadow: `0 0 8px ${theme.palette.primary.main}`,
            },
          }}
        >
          {tabs.map(tab => (
            <Tab
              key={tab.value}
              label={t(tab.label)}
              value={tab.value}
              icon={tab.icon}
              iconPosition="start"
              sx={{
                flexDirection: 'row',
                gap: 1,
                '& .MuiTab-iconWrapper': {
                  marginBottom: 0,
                },
              }}
            />
          ))}
        </Tabs>
      </Card>

      {/* 页面内容 */}
      <Box sx={{ flex: 1, overflow: 'hidden', minHeight: 0, mt: { xs: -1.5, md: -2.5 } }}>
        <motion.div
          key={getActiveTab()}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.3,
            ease: [0.4, 0, 0.2, 1],
          }}
          style={{ height: '100%', overflow: 'auto' }}
        >
          <Suspense
            fallback={
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                }}
              >
                <CircularProgress />
              </Box>
            }
          >
            <Outlet context={{ adapterInfo }} />
          </Suspense>
        </motion.div>
      </Box>
    </Box>
  )
}
