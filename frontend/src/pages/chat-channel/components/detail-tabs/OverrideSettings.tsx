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

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
  // 创建聊天频道覆盖配置服务
  const configKey = `channel_config_${chatKey}`
  const configService = createConfigService(configKey)

  // 获取聊天频道覆盖配置列表
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
  // 创建会话覆盖配置服务
  const configKey = `channel_config_${chatKey}`
  const configService = createConfigService(configKey)

  // 获取会话覆盖配置列表
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
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
<<<<<<< HEAD
            此处的配置将仅对当前聊天频道生效。
=======
<<<<<<< HEAD
            此处的配置将仅对当前聊天频道生效。
=======
<<<<<<< HEAD
            此处的配置将仅对当前聊天频道生效。
=======
            此处的配置将仅对当前会话生效。
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
            <br />
            它的优先级最高，将覆盖所有来自适配器和系统的同名配置。
          </Typography>
        }
<<<<<<< HEAD
        emptyMessage="该聊天频道暂无可覆盖的配置项"
=======
<<<<<<< HEAD
        emptyMessage="该聊天频道暂无可覆盖的配置项"
=======
<<<<<<< HEAD
        emptyMessage="该聊天频道暂无可覆盖的配置项"
=======
        emptyMessage="该会话暂无可覆盖的配置项"
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
        isOverridePage={true}
      />
    </Box>
  )
}
