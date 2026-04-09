import {
  Box,
  Typography,
} from '@mui/material'
import DoneAllIcon from '@mui/icons-material/DoneAll'
import BackspaceIcon from '@mui/icons-material/Backspace'
import { useTranslation } from 'react-i18next'
import SearchField from '../../../../components/common/SearchField'
import FilterSelect from '../../../../components/common/FilterSelect'
import ActionButton from '../../../../components/common/ActionButton'

interface ChannelSelectorToolbarProps {
  search: string
  chatType: string
  status: string
  selectedCount: number
  visibleCount: number
  onSearchChange: (value: string) => void
  onChatTypeChange: (value: string) => void
  onStatusChange: (value: string) => void
  onSelectVisible: () => void
  onClearSelection: () => void
}

export default function ChannelSelectorToolbar({
  search,
  chatType,
  status,
  selectedCount,
  visibleCount,
  onSearchChange,
  onChatTypeChange,
  onStatusChange,
  onSelectVisible,
  onClearSelection,
}: ChannelSelectorToolbarProps) {
  const { t } = useTranslation('chat-announcement')

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <SearchField
        fullWidth
        value={search}
        onChange={onSearchChange}
        placeholder={t('search.placeholder')}
      />

      <Box
        sx={{
          display: 'grid',
          gap: 1,
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, minmax(0, 1fr))',
          },
        }}
      >
        <FilterSelect
          label={t('filters.type')}
          value={chatType}
          onChange={onChatTypeChange}
          options={[
            { value: '', label: t('filters.all') },
            { value: 'group', label: t('filters.group') },
            { value: 'private', label: t('filters.private') },
          ]}
        />

        <FilterSelect
          label={t('filters.status')}
          value={status}
          onChange={onStatusChange}
          options={[
            { value: '', label: t('filters.all') },
            { value: 'active', label: t('filters.active') },
            { value: 'observe', label: t('filters.observe') },
            { value: 'disabled', label: t('filters.inactive') },
          ]}
        />
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 1,
          justifyContent: 'space-between',
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {t('selector.selectedCount', { count: selectedCount })}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t('selector.visibleCount', { count: visibleCount })}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          <ActionButton
            tone="secondary"
            size="small"
            startIcon={<DoneAllIcon />}
            onClick={onSelectVisible}
            disabled={visibleCount === 0}
          >
            {t('selector.selectVisible')}
          </ActionButton>
          <ActionButton
            tone="ghost"
            size="small"
            startIcon={<BackspaceIcon />}
            onClick={onClearSelection}
            disabled={selectedCount === 0}
          >
            {t('selector.clearSelection')}
          </ActionButton>
        </Box>
      </Box>
    </Box>
  )
}
