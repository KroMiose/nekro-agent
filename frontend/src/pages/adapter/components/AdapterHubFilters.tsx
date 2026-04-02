import type { FormEvent } from 'react'
import SearchIcon from '@mui/icons-material/Search'
import CloseRoundedIcon from '@mui/icons-material/CloseRounded'
import { Box, Button, IconButton, InputAdornment, TextField, useTheme } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { BUTTON_VARIANTS } from '../../../theme/variants'

interface AdapterHubFiltersProps {
  search: string
  onSearchChange: (value: string) => void
  onSearchSubmit: () => void
  onSearchClear: () => void
}

export default function AdapterHubFilters({
  search,
  onSearchChange,
  onSearchSubmit,
  onSearchClear,
}: AdapterHubFiltersProps) {
  const theme = useTheme()
  const { t } = useTranslation('adapter')

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSearchSubmit()
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 1.5,
        alignItems: 'center',
      }}
    >
      <Box
        component="form"
        onSubmit={handleSubmit}
        sx={{
          display: 'flex',
          width: { xs: '100%', sm: 380, md: 420 },
          maxWidth: '100%',
          boxShadow:
            theme.palette.mode === 'dark'
              ? '0 0 10px rgba(0, 0, 0, 0.2)'
              : '0 0 15px rgba(0, 0, 0, 0.07)',
          overflow: 'hidden',
          borderRadius: 2,
        }}
      >
        <TextField
          fullWidth
          size="small"
          value={search}
          onChange={event => onSearchChange(event.target.value)}
          placeholder={t('hub.searchPlaceholder')}
          sx={{
            minWidth: 0,
            '& .MuiOutlinedInput-root': {
              borderRadius: '8px 0 0 8px',
            },
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: search ? (
              <InputAdornment position="end">
                <IconButton
                  type="button"
                  size="small"
                  onClick={onSearchClear}
                  aria-label={t('hub.clearSearch')}
                >
                  <CloseRoundedIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ) : undefined,
          }}
        />
        <Button
          type="submit"
          variant="contained"
          sx={{
            ...BUTTON_VARIANTS.primary.styles,
            borderRadius: '0 8px 8px 0',
            px: 1.75,
            minWidth: 82,
            boxShadow: 'none',
          }}
        >
          {t('hub.searchAction')}
        </Button>
      </Box>
    </Box>
  )
}
