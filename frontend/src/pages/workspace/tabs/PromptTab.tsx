import { useState, useEffect } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Collapse,
  IconButton,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Save as SaveIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { workspaceApi, WorkspaceDetail } from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { CARD_VARIANTS } from '../../../theme/variants'
import { useTranslation } from 'react-i18next'

export default function PromptTab({ workspace }: { workspace: WorkspaceDetail }) {
  const { t } = useTranslation('workspace')
  const notification = useNotification()
  const queryClient = useQueryClient()

  const [extraDraft, setExtraDraft] = useState('')
  const [previewExpanded, setPreviewExpanded] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['claude-md', workspace.id],
    queryFn: () => workspaceApi.getClaudeMd(workspace.id),
  })

  useEffect(() => {
    if (data) {
      setExtraDraft(data.extra)
    }
  }, [data])

  const saveMutation = useMutation({
    mutationFn: () => workspaceApi.updateClaudeMdExtra(workspace.id, extraDraft),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claude-md', workspace.id] })
      notification.success(t('detail.prompt.notifications.saveSuccess'))
    },
    onError: (err: Error) =>
      notification.error(t('detail.prompt.notifications.saveFailed', { message: err.message })),
  })

  const isDirty = data ? extraDraft !== data.extra : false

  return (
    <Stack spacing={2} sx={{ flex: 1 }}>
      {/* 系统提示词只读预览 */}
      <Card sx={CARD_VARIANTS.default.styles}>
        <CardContent sx={{ pb: '12px !important' }}>
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ mb: previewExpanded ? 1.5 : 0 }}
          >
            <Typography variant="subtitle1" fontWeight={600}>
              {t('detail.prompt.systemPromptTitle')}
            </Typography>
            <Tooltip
              title={
                previewExpanded
                  ? t('detail.prompt.collapseTooltip')
                  : t('detail.prompt.expandTooltip')
              }
            >
              <IconButton size="small" onClick={() => setPreviewExpanded(v => !v)}>
                {previewExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
          </Stack>

          <Collapse in={previewExpanded}>
            {isLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                <CircularProgress size={24} />
              </Box>
            ) : (
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 1.5,
                  borderRadius: 1,
                  bgcolor: 'background.default',
                  border: '1px solid',
                  borderColor: 'divider',
                  fontSize: '0.78rem',
                  fontFamily: 'monospace',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  maxHeight: 500,
                  overflowY: 'auto',
                  color: 'text.secondary',
                }}
              >
                {data?.content ?? ''}
              </Box>
            )}
          </Collapse>

          {!previewExpanded && (
            <Typography variant="caption" color="text.disabled">
              {t('detail.prompt.systemPromptHint')}
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* 自定义追加提示词 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', pb: '16px !important' }}>
          <Stack
            direction="row"
            alignItems="flex-start"
            justifyContent="space-between"
            sx={{ mb: 1.5 }}
          >
            <Box>
              <Typography variant="subtitle1" fontWeight={600}>
                {t('detail.prompt.extraTitle')}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t('detail.prompt.extraHint')}
              </Typography>
            </Box>
            <Button
              variant="contained"
              size="small"
              startIcon={
                saveMutation.isPending ? <CircularProgress size={14} color="inherit" /> : <SaveIcon />
              }
              onClick={() => saveMutation.mutate()}
              disabled={!isDirty || saveMutation.isPending}
              sx={{ flexShrink: 0, ml: 2 }}
            >
              {t('detail.prompt.saveBtn')}
            </Button>
          </Stack>

          <TextField
            multiline
            fullWidth
            minRows={10}
            value={extraDraft}
            onChange={e => setExtraDraft(e.target.value)}
            placeholder={t('detail.prompt.extraPlaceholder')}
            variant="outlined"
            sx={{
              flex: 1,
              '& .MuiInputBase-root': {
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                alignItems: 'flex-start',
              },
            }}
          />
        </CardContent>
      </Card>
    </Stack>
  )
}
