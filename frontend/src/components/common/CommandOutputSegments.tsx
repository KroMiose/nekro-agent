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

const SIZE_PRESETS = {
  compact: {
    imageSize: 72,
    fileNameFontSize: '0.68rem',
    textFontSize: '0.72rem',
    paddingX: 0.75,
    paddingY: 0.5,
  },
  regular: {
    imageSize: 144,
    fileNameFontSize: '0.75rem',
    textFontSize: '0.78rem',
    paddingX: 1,
    paddingY: 0.75,
  },
} as const

interface CommandOutputSegmentsProps {
  segments?: CommandOutputSegment[] | null
  compact?: boolean
  textColor?: string
}

interface SegmentSizes {
  imageSize: number
  fileNameFontSize: string
  textFontSize: string
  paddingX: number
  paddingY: number
}

interface SegmentLabels {
  download: string
  fileUnavailable: string
  imageUnavailable: string
  previewImage: string
}

function buildSegmentKeyBase(segment: CommandOutputSegment, index: number): string {
  const stablePart =
    segment.web_url ||
    segment.file_name ||
    (segment.type === 'text' ? segment.text?.trim() : undefined)

  if (!stablePart) {
    return `${segment.type}-${index}`
  }

  return `${segment.type}-${stablePart}`
}

function TextSegment({
  text,
  fontSize,
  textColor,
}: {
  text: string
  fontSize: string
  textColor: string
}) {
  if (!text.trim()) {
    return null
  }

  return (
    <Typography
      component="div"
      sx={{
        fontSize,
        color: textColor,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}
    >
      {text}
    </Typography>
  )
}

function ImageSegment({
  segment,
  imageSize,
  imageUnavailable,
  previewImage,
  onPreview,
}: {
  segment: CommandOutputSegment
  imageSize: number
  imageUnavailable: string
  previewImage: string
  onPreview: (src: string | null) => void
}) {
  if (!segment.web_url) {
    return (
      <Typography variant="caption" color="text.secondary">
        {imageUnavailable}
      </Typography>
    )
  }

  return (
    <Box
      component="button"
      type="button"
      onClick={() => onPreview(segment.web_url || null)}
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
        alt={segment.file_name || previewImage}
        sx={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          display: 'block',
        }}
      />
    </Box>
  )
}

function FileSegment({
  segment,
  sizes,
  labels,
}: {
  segment: CommandOutputSegment
  sizes: SegmentSizes
  labels: SegmentLabels
}) {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        flexWrap: 'wrap',
        px: sizes.paddingX,
        py: sizes.paddingY,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
        bgcolor: 'background.paper',
      }}
    >
      <Typography
        variant="body2"
        sx={{
          fontSize: sizes.fileNameFontSize,
          fontFamily: 'monospace',
          wordBreak: 'break-all',
        }}
      >
        {segment.file_name || labels.fileUnavailable}
      </Typography>
      {segment.web_url ? (
        <Link
          href={segment.web_url}
          target="_blank"
          rel="noreferrer"
          underline="hover"
          sx={{ fontSize: sizes.fileNameFontSize }}
        >
          {labels.download}
        </Link>
      ) : (
        <Typography variant="caption" color="text.secondary">
          {labels.fileUnavailable}
        </Typography>
      )}
    </Box>
  )
}

function ImagePreviewDialog({
  src,
  alt,
  onClose,
}: {
  src: string | null
  alt: string
  onClose: () => void
}) {
  return (
    <Dialog open={!!src} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogContent sx={{ p: 1.5, bgcolor: 'black' }}>
        {src && (
          <Box
            component="img"
            src={src}
            alt={alt}
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
  )
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

  const sizes = compact ? SIZE_PRESETS.compact : SIZE_PRESETS.regular
  const labels: SegmentLabels = {
    download: t('actions.download', { ns: 'common' }),
    fileUnavailable: t('commandSidebar.fileUnavailable', { ns: 'chat-channel' }),
    imageUnavailable: t('commandSidebar.imageUnavailable', { ns: 'chat-channel' }),
    previewImage: t('commandSidebar.previewImage', { ns: 'chat-channel' }),
  }
  const keyCounts = new Map<string, number>()

  return (
    <>
      <Stack spacing={0.75} sx={{ mt: 0.75, width: '100%' }}>
        {segments.map((segment, index) => {
          const baseKey = buildSegmentKeyBase(segment, index)
          const keyCount = keyCounts.get(baseKey) || 0
          keyCounts.set(baseKey, keyCount + 1)
          const key = keyCount > 0 ? `${baseKey}-${keyCount}` : baseKey

          if (segment.type === 'text') {
            return (
              <TextSegment
                key={key}
                text={segment.text || ''}
                fontSize={sizes.textFontSize}
                textColor={textColor}
              />
            )
          }

          if (segment.type === 'image') {
            return (
              <ImageSegment
                key={key}
                segment={segment}
                imageSize={sizes.imageSize}
                imageUnavailable={labels.imageUnavailable}
                previewImage={labels.previewImage}
                onPreview={setPreviewSrc}
              />
            )
          }

          return (
            <FileSegment
              key={key}
              segment={segment}
              sizes={sizes}
              labels={labels}
            />
          )
        })}
      </Stack>

      <ImagePreviewDialog
        src={previewSrc}
        alt={labels.previewImage}
        onClose={() => setPreviewSrc(null)}
      />
    </>
  )
}
