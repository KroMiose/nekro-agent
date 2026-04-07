import { SyntheticEvent } from 'react'
import {
  Box,
  Tab,
  Tabs,
} from '@mui/material'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ModelGroupsPage from './model_group'
import CCModelsPage from '../workspace/cc-models'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'

type ModelsTab = 'basic' | 'cc'

export default function ModelsPage() {
  const { t } = useTranslation('settings')
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get('tab')
  const currentTab: ModelsTab = rawTab === 'cc' ? 'cc' : 'basic'

  const handleTabChange = (_event: SyntheticEvent, nextTab: ModelsTab) => {
    setSearchParams({ tab: nextTab })
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
      <Box
        sx={{
          mb: 2,
          flexShrink: 0,
          ...(UNIFIED_TABLE_STYLES.pageTabContainer as object),
        }}
      >
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            minHeight: 44,
            '& .MuiTabs-flexContainer': {
              gap: 0.5,
            },
            '& .MuiTab-root': {
              textTransform: 'none',
              minWidth: 100,
              minHeight: 36,
              fontSize: '0.95rem',
              borderRadius: 1.5,
              color: 'text.secondary',
            },
            '& .MuiTab-root.Mui-selected': {
              color: 'text.primary',
              bgcolor: theme => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'common.white',
            },
            '& .MuiTabs-indicator': {
              height: 3,
              borderRadius: 999,
            },
          }}
        >
          <Tab value="basic" label={t('models.tabs.basic')} />
          <Tab value="cc" label={t('models.tabs.cc')} />
        </Tabs>
      </Box>

      <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {currentTab === 'basic' ? <ModelGroupsPage /> : <CCModelsPage />}
      </Box>
    </Box>
  )
}
