import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { adaptersApi } from '../../services/api/adapters'
import AdapterHubContent from './components/AdapterHubContent'
import AdapterHubFilters from './components/AdapterHubFilters'
import AdapterHubStats from './components/AdapterHubStats'

export default function AdapterHubPage() {
  const navigate = useNavigate()
  const [searchInput, setSearchInput] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')

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
        p: 3,
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        overflow: 'hidden',
        boxSizing: 'border-box',
        bgcolor: 'background.default',
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
      <AdapterHubContent
        adapters={filteredAdapters}
        isLoading={isLoading}
        onOpen={adapterKey => navigate(`/adapters/${adapterKey}`)}
      />
    </Box>
  )
}
