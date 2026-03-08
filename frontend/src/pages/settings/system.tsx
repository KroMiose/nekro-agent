import { useState, useEffect, useMemo } from 'react'
import { Box, Tabs, Tab } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import ConfigTable from '../../components/common/ConfigTable'
import { createConfigService } from '../../services/api/unified-config'
import { useTranslation } from 'react-i18next'
import { getLocalizedText } from '../../services/api/types'
import type { ConfigItem } from '../../components/common/ConfigTable'

export default function SettingsPage() {
  const location = useLocation()
  const [searchText, setSearchText] = useState<string>('')
  const { t } = useTranslation('settings')
  const { i18n } = useTranslation()

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

  // 从配置项中提取本地化的分类名称，无分类时 fallback 到"其他"
  const resolveCategory = (config: ConfigItem): string => {
    if (config.i18n_category && typeof config.i18n_category === 'object') {
      return (
        getLocalizedText(config.i18n_category, config.category || '', i18n.language) ||
        t('system.otherCategory', '其他')
      )
    }
    if (typeof config.i18n_category === 'string' && config.i18n_category) {
      return config.i18n_category
    }
    return config.category || t('system.otherCategory', '其他')
  }

  // 按分类组织配置，同时提取分类列表
  const { categories, configsByCategory } = useMemo(() => {
    const seen = new Set<string>()
    const cats: string[] = []
    const grouped: Record<string, ConfigItem[]> = {}

    const otherLabel = t('system.otherCategory', '其他')

    configs.forEach((config: ConfigItem) => {
      const category = resolveCategory(config)
      if (!seen.has(category)) {
        seen.add(category)
        // "其他"分类放到最后
        if (category !== otherLabel) {
          cats.push(category)
        }
      }
      if (!grouped[category]) {
        grouped[category] = []
      }
      grouped[category].push(config)
    })

    // "其他"分类有内容时才追加到末尾
    if (grouped[otherLabel]?.length) {
      cats.push(otherLabel)
    }

    return { categories: cats, configsByCategory: grouped }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configs, i18n.language])

  // 初始化 activeTab，默认为第一个分类
  const [activeTab, setActiveTab] = useState<string>(() => {
    return categories[0] || ''
  })

  // 当分类列表更新时，确保 activeTab 有效
  useEffect(() => {
    if (categories.length > 0 && (!activeTab || !categories.includes(activeTab))) {
      setActiveTab(categories[0])
    }
  }, [categories, activeTab])

  // 从URL中获取搜索参数
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search)
    const searchParamValue = searchParams.get('search')
    if (searchParamValue) {
      setSearchText(searchParamValue)
    }
  }, [location.search])

  // 根据当前选中的分类过滤配置
  const displayConfigs = useMemo(() => {
    if (searchText.trim()) {
      return configs
    }
    return configsByCategory[activeTab] || []
  }, [activeTab, configs, configsByCategory, searchText])

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
      {/* 分类选项卡 */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2, flexShrink: 0 }}>
        <Tabs
          value={categories.length > 0 ? activeTab : false}
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            '& .MuiTab-root': {
              textTransform: 'none',
              minWidth: 100,
              fontSize: '0.95rem',
            },
          }}
        >
          {categories.map((category) => (
            <Tab key={category} label={category} value={category} />
          ))}
        </Tabs>
      </Box>

      <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <ConfigTable
          configKey="system"
          configService={configService}
          configs={displayConfigs}
          loading={isLoading}
          searchText={searchText}
          onSearchChange={handleSearchChange}
          onRefresh={handleRefresh}
          showSearchBar={true}
          showToolbar={true}
          showCategoryColumn={Boolean(searchText.trim())}
          emptyMessage={t('system.emptyMessage')}
        />
      </Box>
    </Box>
  )
}
