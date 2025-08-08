import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Box, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import ConfigTable from '../../components/common/ConfigTable'
import { createConfigService } from '../../services/api/unified-config'

export default function AdapterOverrideConfigPage() {
  const { adapterKey } = useParams<{ adapterKey: string }>()
  const [searchText, setSearchText] = useState<string>('')

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
    return <Box>缺少适配器 KEY</Box>
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
            此处的配置将覆盖指定适配器的系统默认配置。
            <br />
            如果启用了某个配置项的覆盖，该适配器下的所有聊天都将默认使用此处设置的值，除非聊天自身再次覆盖了该配置。
          </Typography>
        }
        emptyMessage="该适配器暂无可覆盖的配置项"
        isOverridePage={true}
      />
    </Box>
  )
}
