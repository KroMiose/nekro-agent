import { useState, useMemo } from 'react'
import {
  Box,
  Typography,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  CircularProgress,
  Chip,
  Stack,
  SelectChangeEvent,
  List,
  ListItemButton,
  ListItemText,
  Divider,
  useTheme,
  alpha,
} from '@mui/material'
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Storage as StorageIcon,
  Person as PersonIcon,
  Public as PublicIcon,
  Extension as ExtensionIcon,
  VpnKey as KeyIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatChannelApi, type ChatPluginData } from '../../../../services/api/chat-channel'
import { useSnackbar } from 'notistack'
import { useTranslation } from 'react-i18next'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useColorMode } from '../../../../stores/theme'
import { Editor } from '@monaco-editor/react'

interface PluginDataProps {
  chatKey: string
}

/** Try to parse and pretty-print JSON; return null if not valid JSON */
function tryFormatJson(value: string): string | null {
  try {
    const parsed = JSON.parse(value)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return null
  }
}

export default function PluginData({ chatKey }: PluginDataProps) {
  const [pluginFilter, setPluginFilter] = useState<string>('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [editValue, setEditValue] = useState('')

  const theme = useTheme()
  const { mode } = useColorMode()
  const { enqueueSnackbar } = useSnackbar()
  const queryClient = useQueryClient()
  const { t } = useTranslation('chat-channel')

  const queryKey = ['chat-plugin-data', chatKey, pluginFilter]

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () =>
      chatChannelApi.getPluginData(chatKey, {
        plugin_key: pluginFilter || undefined,
        page: 1,
        page_size: 500,
      }),
  })

  const pluginNames = data?.plugin_names ?? {}
  const getPluginName = (key: string) => pluginNames[key] || key

  const selectedItem = useMemo(
    () => data?.items.find((item) => item.id === selectedId) ?? null,
    [data, selectedId],
  )

  const formattedValue = useMemo(() => {
    if (!selectedItem) return null
    return tryFormatJson(selectedItem.data_value)
  }, [selectedItem])

  const { mutate: updateData, isPending: isUpdating } = useMutation({
    mutationFn: ({ dataId, value }: { dataId: number; value: string }) =>
      chatChannelApi.updatePluginData(chatKey, dataId, value),
    onSuccess: () => {
      enqueueSnackbar(t('pluginData.saveSuccess'), { variant: 'success' })
      queryClient.invalidateQueries({ queryKey })
      setEditDialogOpen(false)
    },
    onError: () => {
      enqueueSnackbar(t('pluginData.saveFailed'), { variant: 'error' })
    },
  })

  const { mutate: deleteData, isPending: isDeleting } = useMutation({
    mutationFn: (dataId: number) => chatChannelApi.deletePluginData(chatKey, dataId),
    onSuccess: () => {
      enqueueSnackbar(t('pluginData.deleteSuccess'), { variant: 'success' })
      if (selectedId === deleteDialogTarget) setSelectedId(null)
      queryClient.invalidateQueries({ queryKey })
      setDeleteDialogOpen(false)
    },
    onError: () => {
      enqueueSnackbar(t('pluginData.deleteFailed'), { variant: 'error' })
    },
  })

  const [deleteDialogTarget, setDeleteDialogTarget] = useState<number | null>(null)

  const handleOpenEdit = (item: ChatPluginData) => {
    const formatted = tryFormatJson(item.data_value)
    setEditValue(formatted ?? item.data_value)
    setEditDialogOpen(true)
  }

  const handleSave = () => {
    if (!selectedItem) return
    updateData({ dataId: selectedItem.id, value: editValue })
  }

  const handleOpenDelete = (item: ChatPluginData) => {
    setDeleteDialogTarget(item.id)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = () => {
    if (deleteDialogTarget == null) return
    deleteData(deleteDialogTarget)
  }

  const handlePluginFilterChange = (event: SelectChangeEvent) => {
    setPluginFilter(event.target.value)
    setSelectedId(null)
  }

  // JSON recursive renderer
  const renderJsonValue = (value: unknown, depth: number = 0): React.ReactNode => {
    if (value === null) return <span style={{ color: theme.palette.text.disabled }}>null</span>
    if (typeof value === 'boolean')
      return (
        <Chip
          label={value ? 'true' : 'false'}
          size="small"
          color={value ? 'success' : 'default'}
          variant="outlined"
          sx={{ height: 20, fontSize: '0.75rem' }}
        />
      )
    if (typeof value === 'number')
      return <span style={{ color: theme.palette.info.main, fontFamily: 'monospace' }}>{value}</span>
    if (typeof value === 'string') {
      if (value.length > 200) {
        return (
          <Typography
            variant="body2"
            sx={{
              fontFamily: 'monospace',
              fontSize: '0.8rem',
              color: theme.palette.success.main,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}
          >
            &quot;{value}&quot;
          </Typography>
        )
      }
      return (
        <span style={{ color: theme.palette.success.main, fontFamily: 'monospace', fontSize: '0.8rem' }}>
          &quot;{value}&quot;
        </span>
      )
    }
    if (Array.isArray(value)) {
      if (value.length === 0)
        return <span style={{ color: theme.palette.text.secondary, fontFamily: 'monospace' }}>[]</span>
      return (
        <Box sx={{ pl: depth > 0 ? 2 : 0 }}>
          {value.map((item, index) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1,
                py: 0.3,
                borderLeft: depth > 0 ? `2px solid ${alpha(theme.palette.primary.main, 0.2)}` : 'none',
                pl: depth > 0 ? 1.5 : 0,
              }}
            >
              <Chip
                label={index}
                size="small"
                sx={{
                  height: 18,
                  fontSize: '0.65rem',
                  minWidth: 24,
                  bgcolor: alpha(theme.palette.primary.main, 0.1),
                  color: theme.palette.primary.main,
                  flexShrink: 0,
                  mt: 0.2,
                }}
              />
              <Box sx={{ flex: 1, minWidth: 0 }}>{renderJsonValue(item, depth + 1)}</Box>
            </Box>
          ))}
        </Box>
      )
    }
    if (typeof value === 'object') {
      const entries = Object.entries(value as Record<string, unknown>)
      if (entries.length === 0)
        return <span style={{ color: theme.palette.text.secondary, fontFamily: 'monospace' }}>{'{}'}</span>
      return (
        <Box sx={{ pl: depth > 0 ? 2 : 0 }}>
          {entries.map(([key, val]) => (
            <Box
              key={key}
              sx={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1,
                py: 0.5,
                borderLeft: depth > 0 ? `2px solid ${alpha(theme.palette.divider, 0.5)}` : 'none',
                pl: depth > 0 ? 1.5 : 0,
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  fontFamily: 'monospace',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: theme.palette.warning.main,
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  mt: 0.1,
                }}
              >
                {key}:
              </Typography>
              <Box sx={{ flex: 1, minWidth: 0 }}>{renderJsonValue(val, depth + 1)}</Box>
            </Box>
          ))}
        </Box>
      )
    }
    return <span>{String(value)}</span>
  }

  const renderDetailPanel = () => {
    if (!selectedItem) {
      return (
        <Box
          sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'text.secondary',
            gap: 1,
          }}
        >
          <StorageIcon sx={{ fontSize: 48, opacity: 0.3 }} />
          <Typography variant="body2">{t('pluginData.selectItem')}</Typography>
        </Box>
      )
    }

    const parsed = tryFormatJson(selectedItem.data_value)
    const isJson = parsed !== null

    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header info */}
        <Box sx={{ p: 2, flexShrink: 0, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack spacing={0.5}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {getPluginName(selectedItem.plugin_key)}
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <KeyIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                <Typography variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                  {selectedItem.data_key}
                </Typography>
              </Stack>
              <Stack direction="row" spacing={1} alignItems="center">
                {selectedItem.target_user_id ? (
                  <>
                    <PersonIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {selectedItem.target_user_id}
                    </Typography>
                  </>
                ) : (
                  <>
                    <PublicIcon sx={{ fontSize: 16, color: 'info.main' }} />
                    <Chip
                      label={t('pluginData.globalScope')}
                      size="small"
                      color="info"
                      variant="outlined"
                      sx={{ height: 20, fontSize: '0.7rem' }}
                    />
                  </>
                )}
              </Stack>
            </Stack>
            <Stack direction="row" spacing={0.5}>
              <Tooltip title={t('pluginData.edit')}>
                <IconButton size="small" onClick={() => handleOpenEdit(selectedItem)}>
                  <EditIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={t('pluginData.delete')}>
                <IconButton size="small" color="error" onClick={() => handleOpenDelete(selectedItem)}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Stack>
          </Stack>
        </Box>

        {/* JSON rendered view */}
        <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
          {isJson ? (
            <Box>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
                <Chip label="JSON" size="small" color="primary" sx={{ height: 20, fontSize: '0.7rem' }} />
                <Typography variant="caption" color="text.secondary">
                  {selectedItem.update_time}
                </Typography>
              </Stack>
              {renderJsonValue(JSON.parse(selectedItem.data_value))}
            </Box>
          ) : (
            <Box>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
                <Chip label="Text" size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
                <Typography variant="caption" color="text.secondary">
                  {selectedItem.update_time}
                </Typography>
              </Stack>
              <SyntaxHighlighter
                language="text"
                style={mode === 'dark' ? vscDarkPlus : oneLight}
                customStyle={{
                  background: 'transparent',
                  margin: 0,
                  padding: 0,
                  fontSize: '0.85rem',
                }}
                wrapLongLines
              >
                {selectedItem.data_value}
              </SyntaxHighlighter>
            </Box>
          )}
        </Box>
      </Box>
    )
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', overflow: 'hidden' }}>
      {/* Left panel - list */}
      <Box
        sx={{
          width: 300,
          flexShrink: 0,
          borderRight: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Plugin filter */}
        <Box sx={{ p: 1.5, flexShrink: 0 }}>
          <FormControl size="small" fullWidth>
            <InputLabel>{t('pluginData.filterByPlugin')}</InputLabel>
            <Select
              value={pluginFilter}
              label={t('pluginData.filterByPlugin')}
              onChange={handlePluginFilterChange}
            >
              <MenuItem value="">{t('pluginData.allPlugins')}</MenuItem>
              {(data?.plugin_keys || []).map((key) => (
                <MenuItem key={key} value={key}>
                  {getPluginName(key)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        <Divider />

        {/* Items list */}
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress size={24} />
            </Box>
          ) : !data?.items.length ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4, gap: 1 }}>
              <InfoIcon sx={{ fontSize: 36, opacity: 0.3, color: 'text.secondary' }} />
              <Typography variant="body2" color="text.secondary">
                {t('pluginData.noData')}
              </Typography>
            </Box>
          ) : (
            <List disablePadding dense>
              {data.items.map((item) => (
                <ListItemButton
                  key={item.id}
                  selected={selectedId === item.id}
                  onClick={() => setSelectedId(item.id)}
                  sx={{
                    py: 1,
                    px: 1.5,
                    borderBottom: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
                    '&.Mui-selected': {
                      bgcolor: alpha(theme.palette.primary.main, 0.08),
                      borderRight: `3px solid ${theme.palette.primary.main}`,
                    },
                  }}
                >
                  <ListItemText
                    primary={
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: selectedId === item.id ? 600 : 500,
                          fontSize: '0.85rem',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {getPluginName(item.plugin_key)}
                      </Typography>
                    }
                    secondary={
                      <Stack spacing={0.3} sx={{ mt: 0.3 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: 'monospace',
                            fontSize: '0.75rem',
                            color: 'text.secondary',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {item.data_key}
                        </Typography>
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          {item.target_user_id ? (
                            <Chip
                              icon={<PersonIcon sx={{ fontSize: '0.6rem !important' }} />}
                              label={item.target_user_id}
                              size="small"
                              sx={{
                                height: 16,
                                fontSize: '0.6rem',
                                maxWidth: 120,
                                '& .MuiChip-label': { overflow: 'hidden', textOverflow: 'ellipsis' },
                              }}
                            />
                          ) : (
                            <Chip
                              icon={<PublicIcon sx={{ fontSize: '0.6rem !important' }} />}
                              label={t('pluginData.globalScope')}
                              size="small"
                              color="info"
                              variant="outlined"
                              sx={{ height: 16, fontSize: '0.6rem' }}
                            />
                          )}
                        </Stack>
                      </Stack>
                    }
                  />
                </ListItemButton>
              ))}
            </List>
          )}
        </Box>

      </Box>

      {/* Right panel - detail */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>{renderDetailPanel()}</Box>

      {/* Edit Dialog with Monaco */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{t('pluginData.editTitle')}</DialogTitle>
        <DialogContent sx={{ p: 0, overflow: 'hidden' }}>
          <Stack spacing={0} sx={{ height: 500 }}>
            {/* Meta info bar */}
            {selectedItem && (
              <Stack direction="row" spacing={2} sx={{ px: 2, py: 1, borderBottom: `1px solid ${theme.palette.divider}` }}>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <ExtensionIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary">
                    {getPluginName(selectedItem.plugin_key)}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <KeyIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                  <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                    {selectedItem.data_key}
                  </Typography>
                </Stack>
                {selectedItem.target_user_id && (
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <PersonIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                    <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                      {selectedItem.target_user_id}
                    </Typography>
                  </Stack>
                )}
              </Stack>
            )}
            {/* Monaco editor */}
            <Box sx={{ flex: 1, overflow: 'hidden' }}>
              <Editor
                language={formattedValue !== null ? 'json' : 'plaintext'}
                theme={mode === 'dark' ? 'vs-dark' : 'light'}
                value={editValue}
                onChange={(v) => setEditValue(v ?? '')}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  automaticLayout: true,
                  tabSize: 2,
                }}
              />
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>{t('pluginData.cancel')}</Button>
          <Button onClick={handleSave} variant="contained" disabled={isUpdating}>
            {isUpdating ? <CircularProgress size={20} /> : t('pluginData.save')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>{t('pluginData.deleteConfirmTitle')}</DialogTitle>
        <DialogContent>
          <Typography>{t('pluginData.deleteConfirmContent')}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>{t('pluginData.cancel')}</Button>
          <Button onClick={handleConfirmDelete} color="error" disabled={isDeleting}>
            {isDeleting ? <CircularProgress size={20} /> : t('pluginData.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
