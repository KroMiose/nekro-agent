import type { FormEvent } from 'react'
import { Box, useTheme } from '@mui/material'
import { useTranslation } from 'react-i18next'
import SearchField from '../../../components/common/SearchField'
import ActionButton from '../../../components/common/ActionButton'

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
        <SearchField
          fullWidth
          value={search}
          onChange={onSearchChange}
          onClear={onSearchClear}
          clearAriaLabel={t('hub.clearSearch')}
          placeholder={t('hub.searchPlaceholder')}
          sx={{
            minWidth: 0,
            '& .MuiOutlinedInput-root': {
              borderRadius: '8px 0 0 8px',
            },
          }}
        />
        <ActionButton
          type="submit"
          tone="primary"
          sx={{
            borderRadius: '0 8px 8px 0',
            px: 1.75,
            minWidth: 82,
            boxShadow: 'none',
          }}
        >
          {t('hub.searchAction')}
        </ActionButton>
      </Box>
    </Box>
  )
}
