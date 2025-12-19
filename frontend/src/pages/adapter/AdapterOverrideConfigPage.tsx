import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Box, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import ConfigTable from '../../components/common/ConfigTable'
import { createConfigService } from '../../services/api/unified-config'
import { useTranslation } from 'react-i18next'

export default function AdapterOverrideConfigPage() {
  const { adapterKey } = useParams<{ adapterKey: string }>()
  const [searchText, setSearchText] = useState<string>('')
  const { t } = useTranslation('adapter')

  // 创建适配器覆盖配置服务
  const configService = createConfigService(`adapter_override_${adapterKey}`)

  // 获取适配器覆盖配置列表
  const {
    data: configs = [],
    refetch,
    isLoading,
  } = useQuery({
    queryKey: [`adapter-override-configs`, adapterKey],
    queryFn: () => configService.getConfigList(),
    enabled: !!adapterKey,
  })

  if (!adapterKey) {
    return <Box>{t('override.missingKey')}</Box>
  }

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
        configKey={`adapter_override_${adapterKey}`}
        configService={configService}
        configs={configs}
        loading={isLoading}
        searchText={searchText}
        onSearchChange={handleSearchChange}
        onRefresh={handleRefresh}
        showSearchBar={true}
        showToolbar={true}
        infoBox={
          <Typography variant="body2" color="text.secondary">
            {t('override.info')}
          </Typography>
        }
        emptyMessage={t('override.emptyMessage')}
        isOverridePage={true}
      />
    </Box>
  )
}
