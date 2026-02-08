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
  Button,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { useQuery } from '@tanstack/react-query'
import { getUserDetail } from '../../../services/api/user-manager'
import { format } from 'date-fns'
import { CHIP_VARIANTS } from '../../../theme/variants'
import { useTranslation } from 'react-i18next'

interface UserDetailProps {
  userId: number
  open: boolean
  onClose: () => void
}

const UserDetail: React.FC<UserDetailProps> = ({ userId, open, onClose }) => {
  const { t } = useTranslation('user-manager')
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  const { data, isLoading, error } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => getUserDetail(userId),
    enabled: open && !!userId,
  })

  const user = data

  const formatDate = (dateString: string | null) => {
    if (!dateString) return t('common.none', { ns: 'common' })
    try {
      return format(new Date(dateString), isMobile ? 'MM-dd HH:mm' : 'yyyy-MM-dd HH:mm:ss')
    } catch {
      return t('common.invalidDate', { ns: 'common' })
    }
  }

  const getRoleLabel = (permLevel: number) => {
    switch (permLevel) {
      case 0:
        return t('roles.guest', { ns: 'common' })
      case 1:
        return t('roles.user', { ns: 'common' })
      case 2:
        return t('roles.admin', { ns: 'common' })
      case 3:
        return t('roles.superAdmin', { ns: 'common' })
      default:
        return `${t('roles.unknown', { ns: 'common' })}(${permLevel})`
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
          flexDirection: 'column',
        },
      }}
    >
      <Box
        sx={{
          p: isSmall ? 1.5 : 2,
          flexGrow: 1,
          overflow: 'auto',
        }}
      >
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
            pb: 1,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {isMobile && (
              <IconButton onClick={onClose} size={isSmall ? 'small' : 'medium'} sx={{ mr: 1 }}>
                <ArrowBackIcon />
              </IconButton>
            )}
            <Typography variant={isSmall ? 'h6' : 'h5'}>{t('detail.title')}</Typography>
          </Box>
          <IconButton onClick={onClose} size={isSmall ? 'small' : 'medium'}>
            <CloseIcon />
          </IconButton>
        </Box>

        <Divider sx={{ mb: isSmall ? 1.5 : 2 }} />

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">
            {t('detail.loadingError', { error: String(error) })}
          </Typography>
        ) : user ? (
          <Box
            sx={{
              '& .MuiPaper-root': {
                p: isSmall ? 1.5 : 2,
                mb: isSmall ? 1.5 : 2,
              },
            }}
          >
            <Paper>
              <Typography
                variant={isSmall ? 'subtitle2' : 'subtitle1'}
                gutterBottom
                fontWeight="bold"
                sx={{ mb: isSmall ? 1 : 1.5 }}
              >
                {t('detail.basicInfo')}
              </Typography>

              <Grid container spacing={isSmall ? 0.5 : 1}>
                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('table.userId')}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? 'caption' : 'body2'}>{user.id}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('table.username')}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? 'caption' : 'body2'}>{user.username}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('table.adapterPlatform')}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? 'caption' : 'body2'}>
                    {user.adapter_key}
                  </Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('table.platformUserId')}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? 'caption' : 'body2'}>
                    {user.platform_userid}
                  </Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('detail.uniqueId')}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? 'caption' : 'body2'}>{user.unique_id}</Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('table.permission')}
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
                variant={isSmall ? 'subtitle2' : 'subtitle1'}
                gutterBottom
                fontWeight="bold"
                sx={{ mb: isSmall ? 1 : 1.5 }}
              >
                {t('detail.statusInfo')}
              </Typography>

              <Grid container spacing={isSmall ? 0.5 : 1}>
                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('detail.accountStatus')}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  {!user.is_active ? (
                    <Chip
                      label={t('status.banned')}
                      size="small"
                      sx={CHIP_VARIANTS.getUserStatusChip('banned', isSmall)}
                    />
                  ) : (
                    <Chip
                      label={t('status.normal')}
                      size="small"
                      sx={CHIP_VARIANTS.getUserStatusChip('normal', isSmall)}
                    />
                  )}
                </Grid>

                {!user.is_active && (
                  <>
                    <Grid item xs={4}>
                      <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                        {t('detail.banUntil')}
                      </Typography>
                    </Grid>
                    <Grid item xs={8}>
                      <Typography variant={isSmall ? 'caption' : 'body2'}>
                        {formatDate(user.ban_until)}
                      </Typography>
                    </Grid>
                  </>
                )}

                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('detail.triggerPermission')}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  {user.is_prevent_trigger ? (
                    <Chip
                      label={t('detail.preventTrigger')}
                      size="small"
                      sx={CHIP_VARIANTS.getUserStatusChip('passive', isSmall)}
                    />
                  ) : (
                    <Chip
                      label={t('detail.allowTrigger')}
                      size="small"
                      sx={CHIP_VARIANTS.getUserStatusChip('normal', isSmall)}
                    />
                  )}
                </Grid>

                {!user.is_prevent_trigger && (
                  <>
                    <Grid item xs={4}>
                      <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                        {t('detail.preventTriggerUntil')}
                      </Typography>
                    </Grid>
                    <Grid item xs={8}>
                      <Typography variant={isSmall ? 'caption' : 'body2'}>
                        {formatDate(user.prevent_trigger_until)}
                      </Typography>
                    </Grid>
                  </>
                )}
              </Grid>
            </Paper>

            <Paper>
              <Typography
                variant={isSmall ? 'subtitle2' : 'subtitle1'}
                gutterBottom
                fontWeight="bold"
                sx={{ mb: isSmall ? 1 : 1.5 }}
              >
                {t('detail.otherInfo')}
              </Typography>

              <Grid container spacing={isSmall ? 0.5 : 1}>
                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('table.createdAt')}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? 'caption' : 'body2'}>
                    {formatDate(user.create_time)}
                  </Typography>
                </Grid>

                <Grid item xs={4}>
                  <Typography variant={isSmall ? 'caption' : 'body2'} color="text.secondary">
                    {t('detail.updateTime')}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography variant={isSmall ? 'caption' : 'body2'}>
                    {formatDate(user.update_time)}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>

            {user.ext_data && Object.keys(user.ext_data).length > 0 && (
              <Paper>
                <Typography
                  variant={isSmall ? 'subtitle2' : 'subtitle1'}
                  gutterBottom
                  fontWeight="bold"
                  sx={{ mb: isSmall ? 1 : 1.5 }}
                >
                  {t('detail.extData')}
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
          <Typography>{t('detail.notFound')}</Typography>
        )}
      </Box>

      {isMobile && (
        <Box
          sx={{
            p: 2,
            borderTop: '1px solid',
            borderColor: 'divider',
            mt: 'auto',
          }}
        >
          <Button variant="contained" fullWidth onClick={onClose} startIcon={<ArrowBackIcon />}>
            {t('actions.back', { ns: 'common' })}
          </Button>
        </Box>
      )}
    </Drawer>
  )
}

export default UserDetail
