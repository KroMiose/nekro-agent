import { SyntheticEvent } from 'react'
import {
  Box,
  Tab,
} from '@mui/material'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ModelGroupsPage from './model_group'
import CCModelsPage from '../workspace/cc-models'
import { PanelTabs, PanelTabsContainer } from '../../components/common/NekroTabs'

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
      <PanelTabsContainer
        sx={{
          mb: 2,
          flexShrink: 0,
        }}
      >
        <PanelTabs
          value={currentTab}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab value="basic" label={t('models.tabs.basic')} />
          <Tab value="cc" label={t('models.tabs.cc')} />
        </PanelTabs>
      </PanelTabsContainer>

      <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {currentTab === 'basic' ? <ModelGroupsPage /> : <CCModelsPage />}
      </Box>
    </Box>
  )
}
