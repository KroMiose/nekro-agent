import React, { ReactNode } from 'react'
import {
  Dialog as MuiDialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogProps as MuiDialogProps,
  Typography,
  Divider,
  useTheme,
  useMediaQuery,
  Fade,
  Box,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { BORDER_RADIUS } from '../../theme/variants'
import { UI_STYLES } from '../../theme/themeApi'
import { useTranslation } from 'react-i18next'
import IconActionButton from './IconActionButton'

export interface NekroDialogProps extends Omit<MuiDialogProps, 'title'> {
  open: boolean
  onClose: () => void
  title?: ReactNode
  titleActions?: ReactNode
  titleStartIcon?: ReactNode
  actions?: ReactNode
  maxWidth?: MuiDialogProps['maxWidth']
  showCloseButton?: boolean
  fullWidth?: boolean
  dividers?: boolean
}

const NekroDialog: React.FC<NekroDialogProps> = ({
  open,
  onClose,
  title,
  titleActions,
  titleStartIcon,
  children,
  actions,
  maxWidth = 'md',
  showCloseButton = true,
  fullWidth = true,
  dividers = false,
  fullScreen = false,
  PaperProps: callerPaperProps,
  ...props
}) => {
  const theme = useTheme()
  const { t } = useTranslation('common')
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const generatedPaperSx = {
    borderRadius: BORDER_RADIUS.DEFAULT,
    background: UI_STYLES.GRADIENTS.CARD.DEFAULT,
    backdropFilter: UI_STYLES.CARD_LAYOUT.BACKDROP_FILTER,
    border: UI_STYLES.BORDERS.CARD.DEFAULT,
    overflow: 'hidden',
    width: fullScreen ? '100%' : isMobile ? `calc(100% - ${theme.spacing(2)})` : undefined,
    maxWidth: fullScreen ? '100%' : isMobile ? `calc(100% - ${theme.spacing(2)})` : '800px',
    maxHeight: fullScreen ? '100%' : isMobile ? 'calc(100dvh - 16px)' : '80vh',
    margin: fullScreen ? 0 : isMobile ? 1 : undefined,
  }
  const mergedPaperProps = {
    ...callerPaperProps,
    elevation: callerPaperProps?.elevation ?? 8,
    sx: [generatedPaperSx, callerPaperProps?.sx],
  }

  return (
    <MuiDialog
      open={open}
      onClose={onClose}
      maxWidth={maxWidth}
      fullWidth={fullWidth}
      fullScreen={fullScreen}
      TransitionComponent={Fade}
      transitionDuration={{ enter: 300, exit: 200 }}
      PaperProps={mergedPaperProps}
      {...props}
    >
      {title && (
        <>
          <DialogTitle 
            sx={{ 
              pb: 1,
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              borderBottom: dividers ? `1px solid ${theme.palette.divider}` : 'none'
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {titleStartIcon}
              {typeof title === 'string' ? (
                <Typography variant="h6">{title}</Typography>
              ) : (
                title
              )}
            </Box>
            <Box>
              {titleActions}
              {showCloseButton && (
                <IconActionButton
                  onClick={onClose}
                  size="small"
                  edge="end"
                  aria-label={t('actions.close')}
                >
                  <CloseIcon fontSize="small" />
                </IconActionButton>
              )}
            </Box>
          </DialogTitle>
          {dividers && <Divider />}
        </>
      )}
      <DialogContent sx={{ pt: title ? 2 : 0, minWidth: 0, overflowX: 'hidden', overflowWrap: 'anywhere' }}>
        {children}
      </DialogContent>
      {actions && (
        <>
          {!dividers && <Divider />}
          <DialogActions>{actions}</DialogActions>
        </>
      )}
    </MuiDialog>
  )
}

export default NekroDialog 
