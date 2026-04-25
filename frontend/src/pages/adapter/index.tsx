import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, CircularProgress, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { adaptersApi, type AdapterInfo } from '../../services/api/adapters'
import AdapterHubCard from './components/AdapterHubCard'
import AdapterHubFilters from './components/AdapterHubFilters'
import AdapterHubStats from './components/AdapterHubStats'
import { useTranslation } from 'react-i18next'

export default function AdapterHubPage() {
  const navigate = useNavigate()
  const [searchInput, setSearchInput] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const { t } = useTranslation('adapter')

  const { data: adapters = [], isLoading } = useQuery({
    queryKey: ['adapter-list'],
    queryFn: () => adaptersApi.getAdaptersList(),
    staleTime: 30_000,
  })

  const stats = useMemo(
    () => ({
      total: adapters.length,
      enabled: adapters.filter(adapter => adapter.status === 'enabled').length,
      failed: adapters.filter(adapter => adapter.status === 'failed').length,
      disabled: adapters.filter(adapter => adapter.status === 'disabled').length,
    }),
    [adapters]
  )

  const filteredAdapters = useMemo(() => {
    const keyword = searchKeyword.trim().toLowerCase()
    const statusWeight: Record<string, number> = { enabled: 0, failed: 1, disabled: 2 }

    return adapters
      .filter(adapter => {
        if (!keyword) {
          return true
        }

        const haystacks = [
          adapter.key,
          adapter.name,
          adapter.description ?? '',
          adapter.config_class ?? '',
          ...adapter.tags,
        ]

        return haystacks.some(value => value.toLowerCase().includes(keyword))
      })
      .sort((left, right) => {
        const leftWeight = statusWeight[left.status] ?? 99
        const rightWeight = statusWeight[right.status] ?? 99
        if (leftWeight !== rightWeight) {
          return leftWeight - rightWeight
        }
        return left.name.localeCompare(right.name, 'zh-CN')
      })
  }, [adapters, searchKeyword])

  return (
    <Box
      sx={{
        p: { xs: 1.5, sm: 2, md: 3 },
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      <AdapterHubStats stats={stats} />
      <AdapterHubFilters
        search={searchInput}
        onSearchChange={setSearchInput}
        onSearchSubmit={() => setSearchKeyword(searchInput)}
        onSearchClear={() => {
          setSearchInput('')
          setSearchKeyword('')
        }}
      />
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, minmax(0, 1fr))',
            lg: 'repeat(3, minmax(0, 1fr))',
            xl: 'repeat(4, minmax(0, 1fr))',
          },
          gap: { xs: 1.25, sm: 2 },
          alignContent: 'start',
          overflow: 'auto',
        }}
      >
        {isLoading ? (
          <Box
            sx={{
              gridColumn: '1 / -1',
              minHeight: 240,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <CircularProgress />
          </Box>
        ) : filteredAdapters.length > 0 ? (
          filteredAdapters.map((adapter: AdapterInfo) => (
            <AdapterHubCard
              key={adapter.key}
              adapter={adapter}
              onOpen={adapterKey => navigate(`/adapters/${adapterKey}`)}
            />
          ))
        ) : (
          <Box
            sx={{
              gridColumn: '1 / -1',
              minHeight: 240,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 1,
            }}
          >
            <Typography variant="h6">{t('hub.emptyTitle')}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t('hub.emptyDescription')}
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  )
}
