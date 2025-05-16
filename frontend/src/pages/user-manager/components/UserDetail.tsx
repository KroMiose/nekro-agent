import React from 'react'
import {
  Drawer,
  Box,
  Typography,
  Divider,
  IconButton,
  CircularProgress,
  Chip,
  Grid,
  Paper,
  useTheme,
  useMediaQuery,
  Button
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { useQuery } from '@tanstack/react-query'
import { getUserDetail } from '../../../services/api/user-manager'
import { format } from 'date-fns'
import { CHIP_VARIANTS } from '../../../theme/variants'

interface UserDetailProps {
  userId: number
  open: boolean
  onClose: () => void
}

const UserDetail: React.FC<UserDetailProps> = ({ userId, open, onClose }) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  const { data, isLoading, error } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => getUserDetail(userId),
    enabled: open && !!userId,
  })

  const user = data?.data

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '无'
    try {
      return format(new Date(dateString), isMobile ? 'MM-dd HH:mm' : 'yyyy-MM-dd HH:mm:ss')
    } catch {
      return '无效日期'
    }
  }

  const getRoleLabel = (permLevel: number) => {
    switch (permLevel) {
      case 0:
        return '访客'
      case 1:
        return '用户'
      case 2:
        return '管理员'
      case 3:
        return '超级管理员'
      default:
        return `未知(${permLevel})`
    }
  }

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { 
          width: { xs: '100%', sm: 400, md: 450 },
          display: 'flex',
          flexDirection: 'column'
        },
      }}
    >
      <Box sx={{ 
        p: isSmall ? 1.5 : 2, 
        flexGrow: 1,
        overflow: 'auto'
      }}>
        <Box 
          sx={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            mb: isSmall ? 1 : 2,
            position: 'sticky',
            top: 0,
            backgroundColor: 'background.paper',
            zIndex: 10,
            pb: 1
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {isMobile && (
              <IconButton 
                onClick={onClose} 
                size={isSmall ? "small" : "medium"}
                sx={{ mr: 1 }}
              >
                <ArrowBackIcon />
              </IconButton>
            )}
            <Typography variant={isSmall ? "h6" : "h5"}>用户详情</Typography>
          </Box>
          <IconButton onClick={onClose} size={isSmall ? "small" : "medium"}>
            <CloseIcon />
          </IconButton>
        </Box>

        <Divider sx={{ mb: isSmall ? 1.5 : 2 }} />

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">加载失败: {String(error)}</Typography>
        ) : user ? (
          <Box sx={{ 
            '& .MuiPaper-root': { 
              p: isSmall ? 1.5 : 2,
              mb: isSmall ? 1.5 : 2 
            }
          }}>
            <Paper>
              <Typography 
                variant={isSmall ? "subtitle2" : "subtitle1"} 
                gutterBottom 
                fontWeight="bold"
                sx={{ mb: isSmall ? 1 : 1.5 }}
              >
                基本信息
              </Typography>

              <Grid container spacing={isSmall ? 0.5 : 1}>
                <Grid item xs={4}>
                  <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                    用户ID
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? "caption" : "body2"}>{user.id}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                    用户名
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? "caption" : "body2"}>{user.username}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                    QQ号
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? "caption" : "body2"}>{user.bind_qq}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                    权限等级
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Chip
                    label={getRoleLabel(user.perm_level)}
                    size="small"
                    sx={CHIP_VARIANTS.getRoleChip(user.perm_level, isSmall)}
                  />
                </Grid>
              </Grid>
            </Paper>

            <Paper>
              <Typography 
                variant={isSmall ? "subtitle2" : "subtitle1"} 
                gutterBottom 
                fontWeight="bold"
                sx={{ mb: isSmall ? 1 : 1.5 }}
              >
                状态信息
              </Typography>

              <Grid container spacing={isSmall ? 0.5 : 1}>
                <Grid item xs={4}>
                  <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                    账户状态
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  {!user.is_active ? (
                    <Chip 
                      label="已封禁" 
                      size="small" 
                      sx={CHIP_VARIANTS.getUserStatusChip('已封禁', isSmall)}
                    />
                  ) : (
                    <Chip 
                      label="正常" 
                      size="small" 
                      sx={CHIP_VARIANTS.getUserStatusChip('正常', isSmall)}
                    />
                  )}
                </Grid>

                {!user.is_active && (
                  <>
                    <Grid item xs={4}>
                      <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                        封禁截止
                      </Typography>
                    </Grid>
                    <Grid item xs={8}>
                      <Typography variant={isSmall ? "caption" : "body2"}>{formatDate(user.ban_until)}</Typography>
                    </Grid>
                  </>
                )}

                <Grid item xs={4}>
                  <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                    触发权限
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  {user.is_prevent_trigger ? (
                    <Chip 
                      label="禁止触发" 
                      size="small" 
                      sx={CHIP_VARIANTS.getUserStatusChip('禁止触发', isSmall)}
                    />
                  ) : (
                    <Chip 
                      label="允许触发" 
                      size="small" 
                      sx={CHIP_VARIANTS.getUserStatusChip('允许触发', isSmall)}
                    />
                  )}
                </Grid>

                {!user.is_prevent_trigger && (
                  <>
                    <Grid item xs={4}>
                      <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                        禁止触发截止
                      </Typography>
                    </Grid>
                    <Grid item xs={8}>
                      <Typography variant={isSmall ? "caption" : "body2"}>
                        {formatDate(user.prevent_trigger_until)}
                      </Typography>
                    </Grid>
                  </>
                )}
              </Grid>
            </Paper>

            <Paper>
              <Typography 
                variant={isSmall ? "subtitle2" : "subtitle1"} 
                gutterBottom 
                fontWeight="bold"
                sx={{ mb: isSmall ? 1 : 1.5 }}
              >
                其他信息
              </Typography>

              <Grid container spacing={isSmall ? 0.5 : 1}>
                <Grid item xs={4}>
                  <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                    创建时间
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? "caption" : "body2"}>{formatDate(user.create_time)}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? "caption" : "body2"} color="text.secondary">
                    更新时间
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? "caption" : "body2"}>{formatDate(user.update_time)}</Typography>
                </Grid>
              </Grid>
            </Paper>

            {user.ext_data && Object.keys(user.ext_data).length > 0 && (
              <Paper>
                <Typography 
                  variant={isSmall ? "subtitle2" : "subtitle1"} 
                  gutterBottom 
                  fontWeight="bold"
                  sx={{ mb: isSmall ? 1 : 1.5 }}
                >
                  扩展数据
                </Typography>

                <Box
                  component="pre"
                  sx={{
                    p: 1,
                    backgroundColor: 'background.default',
                    borderRadius: 1,
                    overflow: 'auto',
                    fontSize: isSmall ? '0.65rem' : '0.75rem',
                    maxHeight: isSmall ? '120px' : '200px',
                  }}
                >
                  {JSON.stringify(user.ext_data, null, 2)}
                </Box>
              </Paper>
            )}
          </Box>
        ) : (
          <Typography>未找到用户数据</Typography>
        )}
      </Box>
      
      {isMobile && (
        <Box sx={{ 
          p: 2, 
          borderTop: '1px solid', 
          borderColor: 'divider',
          mt: 'auto'
        }}>
          <Button 
            variant="contained" 
            fullWidth 
            onClick={onClose}
            startIcon={<ArrowBackIcon />}
          >
            返回
          </Button>
        </Box>
      )}
    </Drawer>
  )
}

export default UserDetail
