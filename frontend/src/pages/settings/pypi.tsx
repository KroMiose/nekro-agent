import { useState, useEffect } from 'react'
import { Box, Alert, Switch, FormControlLabel, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import ConfigTable from '../../components/common/ConfigTable'
import { createConfigService } from '../../services/api/unified-config'
import { useNotification } from '../../hooks/useNotification'

export default function PyPISettingsPage() {
  const location = useLocation()
  const notification = useNotification()
  const [searchText, setSearchText] = useState<string>('')
  const [useSystemConfig, setUseSystemConfig] = useState<boolean>(false)

  // 从URL中获取搜索参数
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search)
    const searchParamValue = searchParams.get('search')
    if (searchParamValue) {
      setSearchText(searchParamValue)
    }
  }, [location.search])

  // 获取系统配置状态
  useEffect(() => {
    const loadSystemConfig = async () => {
      try {
        const configService = createConfigService('system')
        const configs = await configService.getConfigList('system')
        const systemConfig = configs.find(config => config.key === 'PYPI_USE_SYSTEM_CONFIG')
        if (systemConfig) {
          setUseSystemConfig(Boolean(systemConfig.value))
        }
      } catch (error) {
        console.error('加载系统配置失败:', error)
      }
    }
    loadSystemConfig()
  }, [])

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

  // 过滤PyPI相关的配置
  const pypiConfigs = configs.filter(config => 
    config.key.startsWith('PYPI_') || 
    config.key === 'PYPI_USE_SYSTEM_CONFIG'
  )

  const handleSearchChange = (text: string) => {
    setSearchText(text)
  }

  const handleRefresh = () => {
    refetch()
  }

  // 处理系统配置开关变化
  const handleSystemConfigChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.checked
    setUseSystemConfig(newValue)
    
    try {
      const configService = createConfigService('system')
      await configService.batchUpdateConfig('system', { PYPI_USE_SYSTEM_CONFIG: String(newValue) })
      await configService.saveConfig('system')
      notification.success(`已${newValue ? '启用' : '禁用'}系统pip配置`)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '保存失败'
      notification.error(`保存配置失败: ${errorMessage}`)
      // 恢复状态
      setUseSystemConfig(!newValue)
    }
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
      {/* 系统配置开关 */}
      <Alert 
        severity="info" 
        sx={{ mb: 2 }}
        action={
          <FormControlLabel
            control={
              <Switch
                checked={useSystemConfig}
                onChange={handleSystemConfigChange}
                color="primary"
              />
            }
            label="使用系统pip配置"
          />
        }
      >
        <Typography variant="body2">
          开启后将使用系统pip配置，关闭后可自定义PyPI源设置
        </Typography>
      </Alert>

      {/* 配置表格 */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <ConfigTable
          configKey="system"
          configService={configService}
          configs={pypiConfigs}
          loading={isLoading}
          searchText={searchText}
          onSearchChange={handleSearchChange}
          onRefresh={handleRefresh}
          showSearchBar={true}
          showToolbar={true}
          emptyMessage="暂无PyPI配置项"
          disabled={useSystemConfig}
        />
      </Box>
    </Box>
  )
}