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
  Avatar,
  Badge,
} from '@mui/material'
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  RadioButtonUnchecked as RadioButtonUncheckedIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { adaptersApi, AdapterDetailInfo } from '../services/api/adapters'
import { CARD_VARIANTS } from '../theme/variants'
import { getAdapterConfig, getAdapterTabPath } from '../config/adapters'

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

  // 获取适配器图标
  const getAdapterIcon = (key: string) => {
    const iconProps = {
      sx: {
        width: 48,
        height: 48,
        fontSize: '1.5rem',
        background:
          theme.palette.mode === 'dark'
            ? 'linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05))'
            : 'linear-gradient(135deg, rgba(0,0,0,0.08), rgba(0,0,0,0.02))',
        backdropFilter: 'blur(8px)',
        border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}`,
      },
    }

    // 根据适配器类型返回不同的图标字符
    const iconText = (() => {
      switch (key) {
        case 'onebot_v11':
          return 'QQ'
        case 'minecraft':
          return 'MC'
        case 'bilibili_live':
          return 'B站'
        case 'sse':
          return 'SSE'
        default:
          return key?.substring(0, 2).toUpperCase() || 'AD'
      }
    })()

    return <Avatar {...iconProps}>{iconText}</Avatar>
  }

  // 状态图标和颜色
  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'loaded':
        return {
          icon: <CheckCircleIcon color="success" fontSize="small" />,
          text: '已加载',
          color: 'success' as const,
          bgColor: theme.palette.success.main,
        }
      case 'failed':
        return {
          icon: <ErrorIcon color="error" fontSize="small" />,
          text: '加载失败',
          color: 'error' as const,
          bgColor: theme.palette.error.main,
        }
      case 'disabled':
        return {
          icon: <WarningIcon color="warning" fontSize="small" />,
          text: '已禁用',
          color: 'warning' as const,
          bgColor: theme.palette.warning.main,
        }
      default:
        return {
          icon: <RadioButtonUncheckedIcon color="disabled" fontSize="small" />,
          text: '未知',
          color: 'default' as const,
          bgColor: theme.palette.grey[500],
        }
    }
  }

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

  const statusDisplay = getStatusDisplay(adapterInfo.status)

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: { xs: 2, md: 3 },
        p: { xs: 0, md: 3 },
        overflow: 'hidden',
      }}
    >
      {/* 适配器头部信息 - 简化版本 */}
      <Card
        sx={{
          ...CARD_VARIANTS.default.styles,
        }}
      >
        <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            {/* 适配器图标和状态 */}
            <Badge
              overlap="circular"
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              badgeContent={
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor: statusDisplay.bgColor,
                    border: `2px solid ${theme.palette.background.paper}`,
                  }}
                />
              }
            >
              {getAdapterIcon(adapterKey!)}
            </Badge>

            {/* 适配器信息 */}
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Typography
                  variant="h5"
                  component="h1"
                  sx={{
                    fontWeight: 600,
                    fontSize: { xs: '1.25rem', md: '1.5rem' },
                  }}
                >
                  {adapterInfo.name}
                </Typography>
              </Box>

              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                <Chip
                  icon={statusDisplay.icon}
                  label={statusDisplay.text}
                  color={statusDisplay.color}
                  variant="filled"
                  size="small"
                  sx={{ fontWeight: 500 }}
                />
                <Chip
                  label={adapterInfo.config_class}
                  color="primary"
                  variant="outlined"
                  size="small"
                  sx={{ fontWeight: 400 }}
                />
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* 导航标签 - 使用默认透明效果 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <Tabs
          value={getActiveTab()}
          onChange={handleTabChange}
          variant={isMobile ? 'fullWidth' : 'standard'}
          indicatorColor="primary"
          textColor="primary"
          sx={{
            minHeight: 56,
            px: { xs: 1, md: 3 },
            '& .MuiTab-root': {
              minHeight: 56,
              fontSize: '0.875rem',
              fontWeight: 600,
              textTransform: 'none',
              transition: 'all 0.2s ease',
              borderRadius: '8px',
              mx: 0.5,
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
          <Outlet context={{ adapterInfo }} />
        </motion.div>
      </Box>
    </Box>
  )
}
