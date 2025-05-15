/**
 * 统一的消息通知组件
 * 提供毛玻璃效果和主题系统集成的通知
 */
import { forwardRef, ReactElement, useEffect, useState } from 'react'
import { SnackbarContent, CustomContentProps, SnackbarKey } from 'notistack'
import {
  Box,
  Paper,
  Typography,
  IconButton,
  useTheme,
  Collapse,
  alpha
} from '@mui/material'
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  Close as CloseIcon
} from '@mui/icons-material'
import { getAlphaColor } from '../../theme/themeApi'

// 自定义接口
interface NekroNotificationProps extends Omit<CustomContentProps, 'style'> {
  message: string | ReactElement
  style?: React.CSSProperties
  onClose?: (event: React.SyntheticEvent<Element, Event> | null, reason: string | undefined, key: SnackbarKey) => void
}

// 图标映射
const iconMap = {
  success: <CheckCircleIcon />,
  error: <ErrorIcon />,
  warning: <WarningIcon />,
  info: <InfoIcon />,
  default: <InfoIcon />
}

// 自定义通知组件
const NekroNotification = forwardRef<HTMLDivElement, NekroNotificationProps>((props, ref) => {
  const { id, message, variant = 'default', onClose, style } = props
  const theme = useTheme()
  const [open, setOpen] = useState(false)
  
  // 获取颜色
  const getColor = () => {
    const palette = theme.palette
    
    switch (variant) {
      case 'success':
        return palette.success.main
      case 'error':
        return palette.error.main
      case 'warning':
        return palette.warning.main
      case 'info':
        return palette.info.main
      default:
        return palette.primary.main
    }
  }
  
  // 进入动画
  useEffect(() => {
    const timer = setTimeout(() => setOpen(true), 50)
    return () => clearTimeout(timer)
  }, [])
  
  // 关闭处理
  const handleClose = () => {
    setOpen(false)
    // 延迟一下，让动画完成后再真正关闭
    setTimeout(() => {
      if (onClose) {
        onClose(null, 'timeout', id)
      }
    }, 300)
  }
  
  const color = getColor()
  
  return (
    <SnackbarContent ref={ref} style={style} className="nekro-notification">
      <Collapse in={open} timeout={300}>
        <Paper
          elevation={2}
          sx={{
            overflow: 'hidden',
            position: 'relative',
            display: 'flex',
            minWidth: 280,
            maxWidth: { xs: 'calc(100vw - 32px)', sm: 440 },
            backdropFilter: 'blur(8px)',
            borderRadius: '8px',
            border: `1px solid ${getAlphaColor(color, 0.2)}`,
            backgroundColor: alpha(theme.palette.background.paper, theme.palette.mode === 'dark' ? 0.85 : 0.9),
            boxShadow: theme.palette.mode === 'dark' 
              ? `0 6px 16px 0 ${alpha(color, 0.25)}`
              : `0 6px 16px 0 ${alpha(color, 0.15)}`,
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              width: '4px',
              height: '100%',
              backgroundColor: color,
            },
            transition: 'all 0.3s ease'
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              padding: theme.spacing(1.5, 2),
              width: '100%'
            }}
          >
            <Box 
              sx={{ 
                color: color,
                display: 'flex',
                alignItems: 'center',
                marginRight: 1.5,
                '& svg': {
                  fontSize: 22
                }
              }}
            >
              {iconMap[variant] || iconMap.default}
            </Box>
            
            <Typography 
              variant="body2" 
              sx={{ 
                flexGrow: 1,
                fontWeight: 500,
                mr: 1
              }}
            >
              {message}
            </Typography>
            
            <IconButton 
              size="small" 
              onClick={handleClose}
              sx={{
                marginLeft: 0.5,
                padding: 0.5,
                color: theme.palette.text.secondary,
                '&:hover': {
                  backgroundColor: alpha(theme.palette.text.primary, 0.08)
                }
              }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </Paper>
      </Collapse>
    </SnackbarContent>
  )
})

NekroNotification.displayName = 'NekroNotification'

export default NekroNotification 