import type { ReactNode } from 'react'
import { Box, Card, CardContent, Typography } from '@mui/material'
import { CARD_VARIANTS } from '../../../theme/variants'
import { UI_STYLES } from '../../../theme/themeConfig'

interface ProfileResourceCardProps {
  media: ReactNode
  title: string
  subtitle?: string
  description?: string
  meta?: ReactNode
  actions: ReactNode
  trailingAction?: ReactNode
}

export default function ProfileResourceCard({
  media,
  title,
  subtitle,
  description,
  meta,
  actions,
  trailingAction,
}: ProfileResourceCardProps) {
  return (
    <Card
      sx={{
        ...CARD_VARIANTS.default.styles,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.2s ease',
        '&:hover': {
          transform: 'translateY(-2px)',
        },
      }}
    >
      <CardContent sx={{ flexGrow: 1, p: 2.5, pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 1.75 }}>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: 1.5,
              overflow: 'hidden',
              flexShrink: 0,
              border: '1px solid',
              borderColor: 'divider',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'action.hover',
            }}
          >
            {media}
          </Box>

          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography
              variant="h6"
              component="h2"
              sx={{
                fontSize: '1rem',
                fontWeight: 700,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {title}
            </Typography>
            {subtitle ? (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  mt: 0.4,
                  fontSize: '0.8rem',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {subtitle}
              </Typography>
            ) : null}
          </Box>
        </Box>

        {description ? (
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
            {description}
          </Typography>
        ) : null}

        {meta ? <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>{meta}</Box> : null}
      </CardContent>

      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 1.5,
          px: 1.5,
          py: 1.25,
          bgcolor: UI_STYLES.SELECTED,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>{actions}</Box>
        {trailingAction}
      </Box>
    </Card>
  )
}
