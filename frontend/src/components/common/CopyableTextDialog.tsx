import React, { useEffect, useRef } from 'react'
import { TextField, Button, Box, Stack } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { useNotification } from '../../hooks/useNotification'
import { copyText } from '../../utils/clipboard'
import NekroDialog from './NekroDialog'

export interface CopyableTextDialogProps {
  open: boolean
  onClose: () => void
  text: string
  title?: string
}

const CopyableTextDialog: React.FC<CopyableTextDialogProps> = ({
  open,
  onClose,
  text,
  title,
}) => {
  const { t } = useTranslation('common')
  const notification = useNotification()
  const dialogContentRef = useRef<HTMLDivElement>(null)

  // 自动选中文本
  useEffect(() => {
    if (open && dialogContentRef.current) {
      setTimeout(() => {
        const textarea = dialogContentRef.current?.querySelector('textarea') as HTMLTextAreaElement | null
        if (textarea) {
          textarea.select()
          textarea.focus()
        }
      }, 300)
    }
  }, [open])

  const handleCopy = async () => {
    const success = await copyText(text)
    if (success) {
      notification.success(t('clipboard.copied'))
      onClose()
    } else {
      notification.error(t('messages.operationFailed'))
    }
  }

  const finalTitle = title ?? t('clipboard.dialogTitle')

  return (
    <NekroDialog
      open={open}
      onClose={onClose}
      title={finalTitle}
      maxWidth="sm"
      showCloseButton={true}
      dividers={true}
      actions={
        <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ px: 2, py: 1.5 }}>
          <Button variant="outlined" onClick={onClose}>
            {t('actions.close')}
          </Button>
          <Button variant="contained" onClick={handleCopy}>
            {t('actions.copy')}
          </Button>
        </Stack>
      }
    >
      <Box ref={dialogContentRef} sx={{ p: 2 }}>
        <Box sx={{ mb: 2, fontSize: '0.875rem', color: 'text.secondary' }}>
          {t('clipboard.dialogDescription')}
        </Box>
        <TextField
          fullWidth
          multiline
          rows={6}
          value={text}
          variant="outlined"
          label={t('clipboard.textareaLabel')}
          slotProps={{
            input: {
              readOnly: true,
              style: {
                fontFamily: 'monospace',
                fontSize: '0.875rem',
              },
            },
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              fontFamily: 'monospace',
            },
          }}
        />
      </Box>
    </NekroDialog>
  )
}

export default CopyableTextDialog
