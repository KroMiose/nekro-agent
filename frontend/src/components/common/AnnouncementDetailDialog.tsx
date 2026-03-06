import { useCallback } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
  Typography,
  Chip,
  CircularProgress,
  alpha,
} from '@mui/material'
import { Close as CloseIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import type { AnnouncementDetail, AnnouncementType } from '../../services/api/cloud/announcement'
import { ANNOUNCEMENT_TYPE_COLORS, ANNOUNCEMENT_TYPE_LABELS, formatRelativeTime } from './AnnouncementConstants'
import { getCurrentThemeMode } from '../../theme/themeConfig'
import { BORDER_RADIUS } from '../../theme/variants'
import MarkdownRenderer from './MarkdownRenderer'

interface AnnouncementDetailDialogProps {
  open: boolean
  detail: AnnouncementDetail | null
  loading: boolean
  onClose: () => void
}

export default function AnnouncementDetailDialog({
  open,
  detail,
  loading,
  onClose,
}: AnnouncementDetailDialogProps) {
  const themeMode = getCurrentThemeMode()
  const { i18n } = useTranslation('layout-MainLayout')

  const getTypeLabel = useCallback(
    (type: AnnouncementType) => {
      const lang = i18n.language === 'en-US' ? 'en-US' : 'zh-CN'
      return ANNOUNCEMENT_TYPE_LABELS[lang]?.[type] ?? type
    },
    [i18n.language]
  )

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: BORDER_RADIUS.LARGE,
          backgroundColor:
            themeMode === 'dark' ? 'rgba(35, 35, 40, 0.98)' : 'rgba(255, 255, 255, 0.98)',
          backdropFilter: 'blur(20px)',
          maxHeight: '70vh',
        },
      }}
    >
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress size={32} />
        </Box>
      ) : detail ? (
        <>
          <DialogTitle sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, pr: 6 }}>
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.75 }}>
                <Chip
                  label={getTypeLabel(detail.type as AnnouncementType)}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    bgcolor: alpha(
                      ANNOUNCEMENT_TYPE_COLORS[detail.type as AnnouncementType] ?? '#999',
                      0.15
                    ),
                    color:
                      ANNOUNCEMENT_TYPE_COLORS[detail.type as AnnouncementType] ?? '#999',
                  }}
                />
                <Typography variant="caption" color="text.secondary">
                  {detail.authorName} · {formatRelativeTime(detail.createdAt)}
                </Typography>
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1.1rem', lineHeight: 1.4 }}>
                {detail.title}
              </Typography>
            </Box>
            <IconButton
              onClick={onClose}
              size="small"
              sx={{ position: 'absolute', right: 12, top: 12 }}
            >
              <CloseIcon sx={{ fontSize: 20 }} />
            </IconButton>
          </DialogTitle>
          <DialogContent dividers sx={{ py: 2 }}>
            <MarkdownRenderer>{detail.content}</MarkdownRenderer>
          </DialogContent>
        </>
      ) : null}
    </Dialog>
  )
}
