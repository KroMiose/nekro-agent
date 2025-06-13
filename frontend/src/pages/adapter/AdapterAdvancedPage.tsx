import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Alert,
  Paper,
  Divider,
  useTheme,
  Chip,
  Stack,
  Grid2,
} from '@mui/material'
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Code as CodeIcon,
  Security as SecurityIcon,
  BugReport as BugReportIcon,
  Architecture as ArchitectureIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { useOutletContext, useParams } from 'react-router-dom'
import { adaptersApi, AdapterDetailInfo, AdapterStatus } from '../../services/api/adapters'
import { CARD_VARIANTS } from '../../theme/variants'

interface AdapterContextType {
  adapterInfo: AdapterDetailInfo
}

// 信息行组件
const InfoRow = ({ label, value, monospace = false }: { 
  label: string
  value: string | React.ReactNode
  monospace?: boolean 
}) => (
  <Box sx={{ py: 1.5 }}>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
      {label}
    </Typography>
    {typeof value === 'string' ? (
      <Typography 
        variant="body1" 
        sx={{ 
          fontFamily: monospace ? 'monospace' : 'inherit',
          fontSize: monospace ? '0.875rem' : 'inherit',
          wordBreak: 'break-all',
          lineHeight: 1.4,
        }}
      >
        {value}
      </Typography>
    ) : (
      value
    )}
  </Box>
)

export default function AdapterAdvancedPage() {
  const { adapterKey } = useParams<{ adapterKey: string }>()
  const { adapterInfo } = useOutletContext<AdapterContextType>()
  const theme = useTheme()

  // 获取适配器状态
  const { data: status } = useQuery<AdapterStatus>({
    queryKey: ['adapter-status', adapterKey],
    queryFn: () => adaptersApi.getAdapterStatus(adapterKey!),
    enabled: !!adapterKey,
    refetchInterval: 5000,
  })

  // 获取状态信息
  const getStatusInfo = (statusValue: string) => {
    switch (statusValue) {
      case 'loaded':
        return { icon: <CheckCircleIcon />, text: '正常运行', color: theme.palette.success.main }
      case 'failed':
        return { icon: <ErrorIcon />, text: '加载失败', color: theme.palette.error.main }
      case 'disabled':
        return { icon: <WarningIcon />, text: '已禁用', color: theme.palette.warning.main }
      default:
        return { icon: <InfoIcon />, text: '未知状态', color: theme.palette.info.main }
    }
  }

  const statusInfo = getStatusInfo(adapterInfo.status)

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        p: 2,
        '&::-webkit-scrollbar': { width: '6px' },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: theme.palette.divider,
          borderRadius: '3px',
        },
      }}
    >
      <Stack spacing={3}>
        {/* 运行状态 */}
        <Card sx={CARD_VARIANTS.default.styles}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <ArchitectureIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                运行状态
              </Typography>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
              {statusInfo.icon}
              <Box>
                <Typography variant="h6" sx={{ color: statusInfo.color, fontWeight: 600 }}>
                  {statusInfo.text}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  适配器: {adapterInfo.name} v{adapterInfo.version || '未知'}
                </Typography>
              </Box>
            </Box>

            {status && (
              <Grid container spacing={3}>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h6" color={status.loaded ? 'success.main' : 'error.main'}>
                      {status.loaded ? '✓' : '✗'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      已加载
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h6" color={status.initialized ? 'success.main' : 'warning.main'}>
                      {status.initialized ? '✓' : '◯'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      已初始化
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h6" color={adapterInfo.has_config ? 'info.main' : 'text.disabled'}>
                      {adapterInfo.has_config ? '⚙' : '—'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      支持配置
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h6" color={status.config_file_exists ? 'success.main' : 'warning.main'}>
                      {status.config_file_exists ? '✓' : '!'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      配置文件
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            )}
          </CardContent>
        </Card>

        <Grid2 container spacing={3}>
          {/* 技术规格 */}
          <Grid2 size={{ xs: 12, lg: 6 }}>
            <Card sx={{ ...CARD_VARIANTS.default.styles, height: 'fit-content' }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <CodeIcon color="primary" />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    技术规格
                  </Typography>
                </Box>

                <Stack divider={<Divider />}>
                  <InfoRow 
                    label="适配器 ID" 
                    value={adapterInfo.key} 
                    monospace 
                  />
                  <InfoRow 
                    label="实现类" 
                    value={adapterInfo.config_class} 
                    monospace 
                  />
                  <InfoRow 
                    label="版本信息" 
                    value={
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                        <Chip 
                          label={`v${adapterInfo.version || '未知'}`} 
                          size="small" 
                          color="primary" 
                          variant="outlined"
                        />
                        {adapterInfo.author && (
                          <Chip 
                            label={adapterInfo.author} 
                            size="small" 
                            variant="outlined"
                          />
                        )}
                      </Box>
                    } 
                  />
                  <InfoRow 
                    label="标签" 
                    value={
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {adapterInfo.tags.length > 0 ? adapterInfo.tags.map((tag, index) => (
                          <Chip
                            key={index}
                            label={tag}
                            size="small"
                            sx={{
                              backgroundColor: theme.palette.primary.main + '15',
                              color: theme.palette.primary.main,
                              fontSize: '0.75rem',
                            }}
                          />
                        )) : (
                          <Typography variant="body2" color="text.disabled">
                            无标签
                          </Typography>
                        )}
                      </Box>
                    } 
                  />
                </Stack>
              </CardContent>
            </Card>
          </Grid2>

          {/* 路径配置 */}
          <Grid2 size={{ xs: 12, lg: 6 }}>
            <Card sx={{ ...CARD_VARIANTS.default.styles, height: 'fit-content' }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <BugReportIcon color="primary" />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    路径配置
                  </Typography>
                </Box>

                <Stack divider={<Divider />}>
                  <InfoRow 
                    label="配置文件" 
                    value={adapterInfo.config_path} 
                    monospace 
                  />
                  {adapterInfo.has_router && (
                    <InfoRow 
                      label="API 路由" 
                      value={adapterInfo.router_prefix} 
                      monospace 
                    />
                  )}
                  <InfoRow 
                    label="适配器目录" 
                    value={`/nekro_agent/adapters/${adapterInfo.key}/`} 
                    monospace 
                  />
                  <InfoRow 
                    label="文档路径" 
                    value={`/nekro_agent/adapters/${adapterInfo.key}/README.md`} 
                    monospace 
                  />
                </Stack>
              </CardContent>
            </Card>
          </Grid2>
        </Grid2>

        {/* 聊天标识规则 */}
        {adapterInfo.chat_key_rules.length > 0 && (
          <Card sx={CARD_VARIANTS.default.styles}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                <SecurityIcon color="primary" />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  聊天标识规则
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                该适配器使用以下格式来标识不同的聊天频道：
              </Typography>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: 2,
                }}
              >
                {adapterInfo.chat_key_rules.map((rule, index) => (
                  <Typography
                    key={index}
                    variant="body2"
                    component="pre"
                    sx={{
                      fontFamily: 'monospace',
                      whiteSpace: 'pre-wrap',
                      margin: 0,
                      mb: index < adapterInfo.chat_key_rules.length - 1 ? 1 : 0,
                      lineHeight: 1.5,
                      fontSize: '0.875rem',
                    }}
                  >
                    {rule}
                  </Typography>
                ))}
              </Paper>
            </CardContent>
          </Card>
        )}

        {/* 错误信息 */}
        {status?.error_message && (
          <Alert
            severity="error"
            sx={{
              ...CARD_VARIANTS.default.styles,
              border: `1px solid ${theme.palette.error.main}`,
            }}
          >
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
              错误信息
            </Typography>
            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
              {status.error_message}
            </Typography>
          </Alert>
        )}
      </Stack>
    </Box>
  )
}
