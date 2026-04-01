import { useState } from 'react'
import {
  Box,
  Dialog,
  DialogContent,
  Link,
  Stack,
  Typography,
} from '@mui/material'
import { useTranslation } from 'react-i18next'
import type { CommandOutputSegment } from '../../services/api/commands'

interface CommandOutputSegmentsProps {
  segments?: CommandOutputSegment[] | null
  compact?: boolean
  textColor?: string
}

export default function CommandOutputSegments({
  segments,
  compact = false,
  textColor = 'text.primary',
}: CommandOutputSegmentsProps) {
  const { t } = useTranslation(['chat-channel', 'common'])
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)

  if (!segments?.length) {
    return null
  }

  const imageSize = compact ? 72 : 144
  const fileNameFontSize = compact ? '0.68rem' : '0.75rem'
  const textFontSize = compact ? '0.72rem' : '0.78rem'

  return (
    <>
      <Stack spacing={0.75} sx={{ mt: 0.75, width: '100%' }}>
        {segments.map((segment, index) => {
          if (segment.type === 'text') {
            if (!segment.text?.trim()) return null
            return (
              <Typography
                key={`${segment.type}-${index}`}
                component="div"
                sx={{
                  fontSize: textFontSize,
                  color: textColor,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {segment.text}
              </Typography>
            )
          }

          if (segment.type === 'image') {
            return segment.web_url ? (
              <Box
                key={`${segment.type}-${index}`}
                component="button"
                type="button"
                onClick={() => setPreviewSrc(segment.web_url || null)}
                sx={{
                  width: imageSize,
                  height: imageSize,
                  p: 0,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  overflow: 'hidden',
                  background: 'transparent',
                  cursor: 'zoom-in',
                  alignSelf: 'flex-start',
                }}
              >
                <Box
                  component="img"
                  src={segment.web_url}
                  alt={segment.file_name || t('commandSidebar.previewImage', { ns: 'chat-channel' })}
                  sx={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    display: 'block',
                  }}
                />
              </Box>
            ) : (
              <Typography
                key={`${segment.type}-${index}`}
                variant="caption"
                color="text.secondary"
              >
                {t('commandSidebar.imageUnavailable', { ns: 'chat-channel' })}
              </Typography>
            )
          }

          return (
            <Box
              key={`${segment.type}-${index}`}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                flexWrap: 'wrap',
                px: compact ? 0.75 : 1,
                py: compact ? 0.5 : 0.75,
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                bgcolor: 'background.paper',
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  fontSize: fileNameFontSize,
                  fontFamily: 'monospace',
                  wordBreak: 'break-all',
                }}
              >
                {segment.file_name || t('commandSidebar.fileUnavailable', { ns: 'chat-channel' })}
              </Typography>
              {segment.web_url ? (
                <Link
                  href={segment.web_url}
                  target="_blank"
                  rel="noreferrer"
                  underline="hover"
                  sx={{ fontSize: fileNameFontSize }}
                >
                  {t('actions.download', { ns: 'common' })}
                </Link>
              ) : (
                <Typography variant="caption" color="text.secondary">
                  {t('commandSidebar.fileUnavailable', { ns: 'chat-channel' })}
                </Typography>
              )}
            </Box>
          )
        })}
      </Stack>

      <Dialog
        open={!!previewSrc}
        onClose={() => setPreviewSrc(null)}
        maxWidth="lg"
        fullWidth
      >
        <DialogContent sx={{ p: 1.5, bgcolor: 'black' }}>
          {previewSrc && (
            <Box
              component="img"
              src={previewSrc}
              alt={t('commandSidebar.previewImage', { ns: 'chat-channel' })}
              sx={{
                width: '100%',
                maxHeight: '80vh',
                objectFit: 'contain',
                display: 'block',
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
