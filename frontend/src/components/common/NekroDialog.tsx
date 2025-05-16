import React, { ReactNode } from 'react'
import {
  Dialog as MuiDialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogProps as MuiDialogProps,
  IconButton,
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
  ...props
}) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))

  return (
    <MuiDialog
      open={open}
      onClose={onClose}
      maxWidth={maxWidth}
      fullWidth={fullWidth}
      TransitionComponent={Fade}
      transitionDuration={{ enter: 300, exit: 200 }}
      PaperProps={{
        elevation: 8,
        sx: {
          borderRadius: BORDER_RADIUS.DEFAULT,
          background: UI_STYLES.GRADIENTS.CARD.DEFAULT,
          backdropFilter: UI_STYLES.CARD_LAYOUT.BACKDROP_FILTER,
          border: UI_STYLES.BORDERS.CARD.DEFAULT,
          overflow: 'hidden',
          maxWidth: isMobile ? '95%' : '800px',
          maxHeight: '80vh',
        },
      }}
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
                <IconButton
                  onClick={onClose}
                  size="small"
                  edge="end"
                  aria-label="关闭"
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              )}
            </Box>
          </DialogTitle>
          {dividers && <Divider />}
        </>
      )}
      <DialogContent sx={{ pt: title ? 2 : 0 }}>
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