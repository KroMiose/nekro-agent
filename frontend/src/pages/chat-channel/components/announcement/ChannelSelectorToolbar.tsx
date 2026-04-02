import {
  Box,
  Button,
  FormControl,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import DoneAllIcon from '@mui/icons-material/DoneAll'
import BackspaceIcon from '@mui/icons-material/Backspace'
import { useTranslation } from 'react-i18next'
import { INPUT_VARIANTS } from '../../../../theme/variants'

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
      <TextField
        fullWidth
        size="small"
        value={search}
        onChange={event => onSearchChange(event.target.value)}
        placeholder={t('search.placeholder')}
        sx={INPUT_VARIANTS.default.styles}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
        }}
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
        <FormControl fullWidth size="small">
          <InputLabel>{t('filters.type')}</InputLabel>
          <Select
            value={chatType}
            label={t('filters.type')}
            onChange={event => onChatTypeChange(event.target.value)}
          >
            <MenuItem value="">{t('filters.all')}</MenuItem>
            <MenuItem value="group">{t('filters.group')}</MenuItem>
            <MenuItem value="private">{t('filters.private')}</MenuItem>
          </Select>
        </FormControl>

        <FormControl fullWidth size="small">
          <InputLabel>{t('filters.status')}</InputLabel>
          <Select
            value={status}
            label={t('filters.status')}
            onChange={event => onStatusChange(event.target.value)}
          >
            <MenuItem value="">{t('filters.all')}</MenuItem>
            <MenuItem value="active">{t('filters.active')}</MenuItem>
            <MenuItem value="observe">{t('filters.observe')}</MenuItem>
            <MenuItem value="disabled">{t('filters.inactive')}</MenuItem>
          </Select>
        </FormControl>
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
          <Button
            variant="outlined"
            size="small"
            startIcon={<DoneAllIcon />}
            onClick={onSelectVisible}
            disabled={visibleCount === 0}
          >
            {t('selector.selectVisible')}
          </Button>
          <Button
            variant="text"
            size="small"
            color="inherit"
            startIcon={<BackspaceIcon />}
            onClick={onClearSelection}
            disabled={selectedCount === 0}
          >
            {t('selector.clearSelection')}
          </Button>
        </Box>
      </Box>
    </Box>
  )
}
