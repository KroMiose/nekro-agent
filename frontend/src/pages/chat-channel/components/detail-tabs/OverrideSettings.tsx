import { useState } from 'react'
import { Box, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import ConfigTable from '../../../../components/common/ConfigTable'
import { createConfigService } from '../../../../services/api/unified-config'

interface OverrideSettingsProps {
  chatKey: string
}

export default function OverrideSettings({ chatKey }: OverrideSettingsProps) {
  const [searchText, setSearchText] = useState<string>('')

  // 创建会话覆盖配置服务
  const configKey = `channel_config_${chatKey}`
  const configService = createConfigService(configKey)

  // 获取会话覆盖配置列表
  const {
    data: configs = [],
    refetch,
    isLoading,
  } = useQuery({
    queryKey: ['channel-override-configs', chatKey],
    queryFn: () => configService.getConfigList(configKey),
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
        configKey={configKey}
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
            此处的配置将仅对当前会话生效。
            <br />
            它的优先级最高，将覆盖所有来自适配器和系统的同名配置。
          </Typography>
        }
        emptyMessage="该会话暂无可覆盖的配置项"
        isOverridePage={true}
      />
    </Box>
  )
}
