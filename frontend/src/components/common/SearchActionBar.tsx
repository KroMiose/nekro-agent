import type { FormEventHandler } from 'react'
import { Box, BoxProps, SxProps, Theme } from '@mui/material'
import SearchField from './SearchField'
import ActionButton from './ActionButton'
import { BORDER_RADIUS } from '../../theme/variants'

interface SearchActionBarProps extends Omit<BoxProps<'form'>, 'onSubmit' | 'onChange'> {
  value: string
  onChange: (value: string) => void
  onSubmit?: FormEventHandler<HTMLFormElement>
  onClear?: () => void
  placeholder?: string
  actionLabel: string
  actionDisabled?: boolean
  searchWidth?: number | string | { xs?: number | string; sm?: number | string; md?: number | string }
}

export default function SearchActionBar({
  value,
  onChange,
  onSubmit,
  onClear,
  placeholder,
  actionLabel,
  actionDisabled,
  searchWidth = { xs: '100%', sm: 280, md: 320 },
  sx,
  ...props
}: SearchActionBarProps) {
  const responsiveSearchWidth =
    typeof searchWidth === 'object'
      ? searchWidth
      : { sm: searchWidth, md: searchWidth }

  const baseSx = {
    display: { xs: 'flex', sm: 'inline-grid' },
    width: { xs: '100%', sm: 'max-content' },
    gridTemplateColumns: { sm: 'max-content max-content' },
    justifyItems: 'start',
    alignItems: 'stretch',
    gap: { xs: 1, sm: 0 },
    flex: '0 0 auto',
    maxWidth: '100%',
  } satisfies SxProps<Theme>

  const mergedSx = (sx ? [baseSx, sx] : baseSx) as SxProps<Theme>

  return (
    <Box
      component="form"
      onSubmit={onSubmit}
      sx={mergedSx}
      {...props}
    >
      <Box
        sx={{
          width: { xs: '100%', sm: 'max-content' },
          maxWidth: '100%',
        }}
      >
        <SearchField
          size="small"
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          onClear={onClear}
          sx={{
            width: { xs: '100%', ...responsiveSearchWidth },
            minWidth: { xs: 0, sm: typeof searchWidth === 'object' ? searchWidth.sm ?? 280 : searchWidth },
            maxWidth: '100%',
            flexShrink: 0,
            flex: '0 0 auto',
            '& .MuiOutlinedInput-root': {
              borderRadius: `${BORDER_RADIUS.DEFAULT}px`,
              '@media (min-width:600px)': {
                borderTopRightRadius: '0 !important',
                borderBottomRightRadius: '0 !important',
              },
            },
            '& .MuiOutlinedInput-root fieldset': {
              '@media (min-width:600px)': {
                borderTopRightRadius: '0 !important',
                borderBottomRightRadius: '0 !important',
              },
            },
          }}
        />
      </Box>
      <Box
        sx={{
          width: { xs: '100%', sm: 'max-content' },
          display: 'flex',
          flex: '0 0 auto',
        }}
      >
        <ActionButton
          type="submit"
          tone="primary"
          disabled={actionDisabled}
          sx={{
            width: { xs: '100%', sm: 'auto !important' },
            maxWidth: { xs: '100%', sm: 'max-content' },
            alignSelf: { xs: 'stretch', sm: 'auto' },
            minWidth: { xs: '100%', sm: 88 },
            flex: '0 0 auto',
            marginLeft: { xs: 0, sm: '-1px' },
            borderRadius: `${BORDER_RADIUS.DEFAULT}px`,
            whiteSpace: 'nowrap',
            '@media (min-width:600px)': {
              borderTopLeftRadius: '0 !important',
              borderBottomLeftRadius: '0 !important',
            },
            px: 2,
          }}
        >
          {actionLabel}
        </ActionButton>
      </Box>
    </Box>
  )
}
