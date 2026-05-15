import { Alert } from '@mui/material'
import type { SxProps, Theme } from '@mui/material/styles'

export function KbEmbeddingWarning({
  message,
  sx,
}: {
  message: string
  sx?: SxProps<Theme>
}) {
  return (
    <Alert severity="warning" sx={sx}>
      {message}
    </Alert>
  )
}
