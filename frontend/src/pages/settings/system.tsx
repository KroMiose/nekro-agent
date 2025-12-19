import { useState, useEffect } from 'react'
import { Box } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import ConfigTable from '../../components/common/ConfigTable'
import { createConfigService } from '../../services/api/unified-config'
import { useTranslation } from 'react-i18next'

export default function SettingsPage() {
  const location = useLocation()
  const [searchText, setSearchText] = useState<string>('')
  const { t } = useTranslation('settings')

  // 从URL中获取搜索参数
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search)
    const searchParamValue = searchParams.get('search')
    if (searchParamValue) {
      setSearchText(searchParamValue)
    }
  }, [location.search])

  // 创建系统配置服务
  const configService = createConfigService('system')

  // 获取系统配置列表
  const {
    data: configs = [],
    refetch,
    isLoading,
  } = useQuery({
    queryKey: ['system-configs'],
    queryFn: () => configService.getConfigList('system'),
  })

  const handleSearchChange = (text: string) => {
    setSearchText(text)
  }

  const handleRefresh = () => {
    refetch()
  }

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        p: 2,
      }}
    >
      <ConfigTable
        configKey="system"
        configService={configService}
        configs={configs}
        loading={isLoading}
        searchText={searchText}
        onSearchChange={handleSearchChange}
        onRefresh={handleRefresh}
        showSearchBar={true}
        showToolbar={true}
        emptyMessage={t('system.emptyMessage')}
      />
    </Box>
  )
}
