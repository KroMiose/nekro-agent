import { useState } from 'react'
import { useParams, useOutletContext } from 'react-router-dom'
import { Box, Typography, Alert } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import ConfigTable from '../../components/common/ConfigTable'
import { createConfigService } from '../../services/api/unified-config'
import { AdapterDetailInfo } from '../../services/api/adapters'

interface AdapterContextType {
  adapterInfo: AdapterDetailInfo
}

export default function AdapterConfigPage() {
  const { adapterKey } = useParams<{ adapterKey: string }>()
  const { adapterInfo } = useOutletContext<AdapterContextType>()
  const [searchText, setSearchText] = useState<string>('')

  // 创建适配器配置服务，使用 adapter_${adapterKey} 作为配置键
  const configKey = `adapter_${adapterKey}`
  const configService = createConfigService(configKey)

  // 获取适配器配置列表
  const {
    data: configs = [],
    refetch,
    isLoading,
  } = useQuery({
    queryKey: ['adapter-configs', adapterKey],
    queryFn: () => configService.getConfigList(configKey),
    enabled: adapterInfo.has_config, // 只有当适配器支持配置时才执行查询
  })

  // 如果适配器不支持配置，显示提示信息
  if (!adapterInfo.has_config) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">
          <Typography variant="h6" gutterBottom>
            该适配器不支持配置
          </Typography>
          该适配器没有可配置的参数，无需进行配置。
        </Alert>
      </Box>
    )
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
        configKey={configKey}
        configService={configService}
        configs={configs}
        loading={isLoading}
        searchText={searchText}
        onSearchChange={handleSearchChange}
        onRefresh={handleRefresh}
        showSearchBar={true}
        showToolbar={true}
        emptyMessage={`暂无 ${adapterInfo.name} 配置项`}
      />
    </Box>
  )
} 