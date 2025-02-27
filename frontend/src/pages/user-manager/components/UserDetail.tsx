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
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { useQuery } from '@tanstack/react-query'
import { getUserDetail } from '../../../services/api/user-manager'
import { format } from 'date-fns'

interface UserDetailProps {
  userId: number
  open: boolean
  onClose: () => void
}

const UserDetail: React.FC<UserDetailProps> = ({ userId, open, onClose }) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => getUserDetail(userId),
    enabled: open && !!userId,
  })

  const user = data?.data

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '无'
    try {
      return format(new Date(dateString), 'yyyy-MM-dd HH:mm:ss')
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

  const getRoleColor = (permLevel: number) => {
    switch (permLevel) {
      case 0:
        return 'default'
      case 1:
        return 'primary'
      case 2:
        return 'secondary'
      case 3:
        return 'error'
      default:
        return 'default'
    }
  }

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { width: { xs: '100%', sm: 400 } },
      }}
    >
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">用户详情</Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        <Divider sx={{ mb: 2 }} />

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">加载失败: {String(error)}</Typography>
        ) : user ? (
          <Box>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                基本信息
              </Typography>

              <Grid container spacing={1}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">
                    用户ID
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant="body2">{user.id}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">
                    用户名
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant="body2">{user.username}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">
                    QQ号
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant="body2">{user.bind_qq}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">
                    权限等级
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Chip
                    label={getRoleLabel(user.perm_level)}
                    color={
                      getRoleColor(user.perm_level) as
                        | 'default'
                        | 'primary'
                        | 'secondary'
                        | 'error'
                        | 'info'
                        | 'success'
                        | 'warning'
                    }
                    size="small"
                  />
                </Grid>
              </Grid>
            </Paper>

            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                状态信息
              </Typography>

              <Grid container spacing={1}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">
                    账户状态
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  {!user.is_active ? (
                    <Chip label="已封禁" color="error" size="small" />
                  ) : (
                    <Chip label="正常" color="success" size="small" />
                  )}
                </Grid>

                {!user.is_active && (
                  <>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">
                        封禁截止
                      </Typography>
                    </Grid>
                    <Grid item xs={8}>
                      <Typography variant="body2">{formatDate(user.ban_until)}</Typography>
                    </Grid>
                  </>
                )}

                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">
                    触发权限
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  {user.is_prevent_trigger ? (
                    <Chip label="禁止触发" color="warning" size="small" />
                  ) : (
                    <Chip label="允许触发" color="success" size="small" />
                  )}
                </Grid>

                {!user.is_prevent_trigger && (
                  <>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">
                        禁止触发截止
                      </Typography>
                    </Grid>
                    <Grid item xs={8}>
                      <Typography variant="body2">
                        {formatDate(user.prevent_trigger_until)}
                      </Typography>
                    </Grid>
                  </>
                )}
              </Grid>
            </Paper>

            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                其他信息
              </Typography>

              <Grid container spacing={1}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">
                    创建时间
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant="body2">{formatDate(user.create_time)}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">
                    更新时间
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant="body2">{formatDate(user.update_time)}</Typography>
                </Grid>
              </Grid>
            </Paper>

            {user.ext_data && Object.keys(user.ext_data).length > 0 && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                  扩展数据
                </Typography>

                <Box
                  component="pre"
                  sx={{
                    p: 1,
                    backgroundColor: 'background.default',
                    borderRadius: 1,
                    overflow: 'auto',
                    fontSize: '0.75rem',
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
    </Drawer>
  )
}

export default UserDetail
