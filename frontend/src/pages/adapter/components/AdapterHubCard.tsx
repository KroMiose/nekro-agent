import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import { Box, Button, Card, CardActions, CardContent, Chip, Typography, useTheme } from '@mui/material'
import { alpha } from '@mui/material/styles'
import { useTranslation } from 'react-i18next'
import { createAdapterIcon, getAdapterStatusDisplay } from '../../../config/adapters'
import type { AdapterInfo } from '../../../services/api/adapters'
import { CARD_VARIANTS } from '../../../theme/variants'
import { UI_STYLES } from '../../../theme/themeConfig'

const getStatusColor = (status: AdapterInfo['status'], success: string, error: string, warning: string) => {
  switch (status) {
    case 'enabled':
      return success
    case 'failed':
      return error
    default:
      return warning
  }
}

function StatusDot({ color }: { color: string }) {
  return (
    <Box
      sx={{
        width: 8,
        height: 8,
        borderRadius: '999px',
        bgcolor: color,
        boxShadow: `0 0 0 3px ${alpha(color, 0.16)}`,
        flexShrink: 0,
      }}
    />
  )
}

interface AdapterHubCardProps {
  adapter: AdapterInfo
  onOpen: (adapterKey: string) => void
}

export default function AdapterHubCard({ adapter, onOpen }: AdapterHubCardProps) {
  const theme = useTheme()
  const { t } = useTranslation('adapter')
  const statusDisplay = getAdapterStatusDisplay(adapter.status)
  const statusColor = getStatusColor(
    adapter.status,
    theme.palette.success.main,
    theme.palette.error.main,
    theme.palette.warning.main
  )

  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        minHeight: 210,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <CardContent
        sx={{
          flexGrow: 1,
          p: 2,
          pb: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          gap: 1.25,
        }}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.25 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
              {createAdapterIcon(adapter.key, theme, 48)}

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
                  {adapter.name}
                </Typography>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.75,
                    mt: 0.25,
                  }}
                >
                  <StatusDot color={statusColor} />
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
                    {t(statusDisplay.text)}
                  </Typography>
                  {adapter.version ? (
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                      · v{adapter.version}
                    </Typography>
                  ) : null}
                </Box>
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
              minHeight: '2.7em',
              fontSize: '0.85rem',
            }}
          >
            {adapter.description || t('hub.noDescription')}
          </Typography>

          <Box
            sx={{
              display: 'flex',
              flexWrap: 'nowrap',
              gap: 0.75,
              minHeight: 24,
              overflow: 'hidden',
            }}
          >
            <Chip
              label={adapter.config_class}
              size="small"
              sx={{
                height: 24,
                fontSize: '0.75rem',
                bgcolor: alpha(statusColor, 0.1),
                color: statusColor,
                flexShrink: 0,
              }}
            />
            {adapter.tags.slice(0, 2).map(tag => (
              <Chip
                key={`${adapter.key}-${tag}`}
                label={tag}
                size="small"
                sx={{
                  height: 24,
                  fontSize: '0.75rem',
                  bgcolor: alpha(theme.palette.text.primary, 0.06),
                  flexShrink: 0,
                }}
              />
            ))}
          </Box>
        </Box>
      </CardContent>

      <CardActions
        sx={{
          justifyContent: 'space-between',
          px: 1.25,
          py: 1,
          minHeight: 46,
          bgcolor: UI_STYLES.SELECTED,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <StatusDot color={statusColor} />
          <Typography variant="caption" color="text.secondary">
            {t(statusDisplay.text)}
          </Typography>
        </Box>

        <Button
          size="small"
          variant="contained"
          endIcon={<ArrowForwardRoundedIcon />}
          onClick={() => onOpen(adapter.key)}
          sx={{
            minWidth: 'fit-content',
            px: 1.5,
            minHeight: 28,
            borderRadius: '999px',
            boxShadow: 'none',
            backgroundColor: theme.palette.primary.main,
            color: '#fff',
            whiteSpace: 'nowrap',
            fontSize: '0.75rem',
            fontWeight: 700,
            '& .MuiButton-endIcon': {
              ml: 0.5,
              '& svg': {
                fontSize: '0.95rem',
              },
            },
            '&:hover': {
              backgroundColor: theme.palette.primary.dark,
              boxShadow: 'none',
            },
          }}
        >
          {t('hub.open')}
        </Button>
      </CardActions>
    </Card>
  )
}
