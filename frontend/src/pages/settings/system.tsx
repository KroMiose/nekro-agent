import { useEffect, useMemo, useState, useDeferredValue } from 'react'
import { Box, Tab } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import ConfigTable from '../../components/common/ConfigTable'
import { createConfigService } from '../../services/api/unified-config'
import { useTranslation } from 'react-i18next'
import { getLocalizedText } from '../../services/api/types'
import type { ConfigItem } from '../../components/common/ConfigTable'
import { useLocaleStore } from '../../stores/locale'
import type { SupportedLocale } from '../../config/i18n'
import { PanelTabs, PanelTabsContainer } from '../../components/common/NekroTabs'

export default function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { t } = useTranslation('settings')
  const { i18n } = useTranslation()
  const { setLocaleLocal } = useLocaleStore()
  const urlSearchText = searchParams.get('search') ?? ''
  const requestedCategory = searchParams.get('category') ?? ''
  const [searchInput, setSearchInput] = useState<string>(urlSearchText)
  const deferredSearchInput = useDeferredValue(searchInput)

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

  const activeTab = useMemo(() => {
    if (categories.length === 0) {
      return ''
    }
    if (requestedCategory && categories.includes(requestedCategory)) {
      return requestedCategory
    }
    return categories[0]
  }, [categories, requestedCategory])

  useEffect(() => {
    setSearchInput(urlSearchText)
  }, [urlSearchText])

  useEffect(() => {
    if (categories.length === 0 || !activeTab) {
      return
    }
    if (requestedCategory === activeTab) {
      return
    }
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('category', activeTab)
    setSearchParams(nextParams, { replace: true })
  }, [activeTab, categories.length, requestedCategory, searchParams, setSearchParams])

  useEffect(() => {
    const normalizedSearch = deferredSearchInput.trim()
    const currentSearch = searchParams.get('search') ?? ''
    const currentCategory = searchParams.get('category') ?? ''
    const normalizedCurrentSearch = currentSearch.trim()
    if (normalizedSearch === normalizedCurrentSearch && currentCategory === activeTab) {
      return
    }

    const nextParams = new URLSearchParams(searchParams)
    if (normalizedSearch) {
      nextParams.set('search', deferredSearchInput)
    } else {
      nextParams.delete('search')
    }
    if (activeTab) {
      nextParams.set('category', activeTab)
    }
    setSearchParams(nextParams, { replace: true })
  }, [activeTab, deferredSearchInput, searchParams, setSearchParams])

  // 当系统配置刷新后，同步 SYSTEM_LANG 到前端 locale
  useEffect(() => {
    const langConfig = configs.find((c: ConfigItem) => c.key === 'SYSTEM_LANG')
    if (langConfig) {
      const backendLang = langConfig.value as string
      if (backendLang === 'zh-CN' || backendLang === 'en-US') {
        setLocaleLocal(backendLang as SupportedLocale)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configs])

  // 根据当前选中的分类过滤配置
  const displayConfigs = useMemo(() => {
    if (searchInput.trim()) {
      return configs
    }
    return configsByCategory[activeTab] || []
  }, [activeTab, configs, configsByCategory, searchInput])

  const handleSearchChange = (text: string) => {
    setSearchInput(text)
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
      <PanelTabsContainer
        sx={{
          mb: 2,
          flexShrink: 0,
        }}
      >
        <PanelTabs
          value={categories.length > 0 ? activeTab : false}
          onChange={(_, newValue) => {
            const nextParams = new URLSearchParams(searchParams)
            nextParams.set('category', newValue)
            setSearchParams(nextParams, { replace: true })
          }}
          variant="scrollable"
          scrollButtons="auto"
        >
          {categories.map((category) => (
            <Tab key={category} label={category} value={category} />
          ))}
        </PanelTabs>
      </PanelTabsContainer>

      <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <ConfigTable
          configKey="system"
          configService={configService}
          configs={displayConfigs}
          loading={isLoading}
          searchText={searchInput}
          onSearchChange={handleSearchChange}
          onRefresh={handleRefresh}
          showSearchBar={true}
          showToolbar={true}
          showCategoryColumn={Boolean(searchInput.trim())}
          emptyMessage={t('system.emptyMessage')}
        />
      </Box>
    </Box>
  )
}
