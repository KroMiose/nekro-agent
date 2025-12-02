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
} from '@mui/material'
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
import { Suspense } from 'react'

export default function AdapterLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { adapterKey } = useParams<{ adapterKey: string }>()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))

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
          加载适配器信息中...
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
            加载失败
          </Typography>
          {error instanceof Error ? error.message : '加载适配器信息失败'}
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
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
            }}
          >
            {/* 适配器图标和状态 */}
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
            >
              {createAdapterIcon(adapterKey!, theme, 40)}
            </Badge>

            {/* 适配器信息 */}
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
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
                  label={statusDisplay.text}
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
              </Box>
            </Box>
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
              label={tab.label}
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
