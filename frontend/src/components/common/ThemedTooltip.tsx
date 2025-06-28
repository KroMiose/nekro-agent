/**
 * 主题化的 Tooltip 组件
 * 统一管理所有悬浮提示的样式，确保在亮色/暗色主题下都有正确的文字颜色
 */
import { Tooltip, tooltipClasses, TooltipProps, styled } from '@mui/material'
import { getCurrentBackground } from '../../theme/themeConfig'
import { BORDER_RADIUS } from '../../theme/variants'
import { getAlphaColor } from '../../theme/palette'

/**
 * 支持富文本内容的主题化 Tooltip
 * 自动适配当前主题的颜色方案
 */
export const ThemedTooltip = styled(({ className, ...props }: TooltipProps) => (
  <Tooltip {...props} classes={{ popper: className }} />
))(({ theme }) => {
  const background = getCurrentBackground()
  const isLight = theme.palette.mode === 'light'
  
  return {
    [`& .${tooltipClasses.tooltip}`]: {
      backgroundColor: isLight 
        ? getAlphaColor('#ffffff', 0.95)
        : getAlphaColor(background.paper, 0.95),
      color: isLight 
        ? 'rgba(0, 0, 0, 0.87)'
        : 'rgba(255, 255, 255, 0.92)',
      maxWidth: 300,
      fontSize: theme.typography.pxToRem(12),
      border: `1px solid ${isLight 
        ? 'rgba(0, 0, 0, 0.08)'
        : getAlphaColor(theme.palette.primary.main, 0.15)}`,
      borderRadius: BORDER_RADIUS.DEFAULT,
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      boxShadow: isLight
        ? '0 4px 20px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04)'
        : '0 4px 20px rgba(0, 0, 0, 0.25), 0 2px 8px rgba(0, 0, 0, 0.15)',
      lineHeight: 1.4,
      padding: '8px 12px',
      '& a': {
        color: theme.palette.primary.main,
        textDecoration: 'none',
        fontWeight: 500,
        '&:hover': {
          textDecoration: 'underline',
        },
      },
      '& strong': {
        fontWeight: 600,
        color: isLight 
          ? 'rgba(0, 0, 0, 0.95)'
          : 'rgba(255, 255, 255, 0.95)',
      },
      '& code': {
        backgroundColor: isLight 
          ? 'rgba(0, 0, 0, 0.06)'
          : 'rgba(255, 255, 255, 0.1)',
        color: theme.palette.primary.main,
        padding: '2px 4px',
        borderRadius: '3px',
        fontSize: '0.85em',
        fontFamily: 'Monaco, Consolas, "Courier New", monospace',
      },
    },
    [`& .${tooltipClasses.arrow}`]: {
      color: isLight 
        ? getAlphaColor('#ffffff', 0.95)
        : getAlphaColor(background.paper, 0.95),
    },
  }
})

/**
 * 简单文本的主题化 Tooltip
 * 用于不需要富文本的场景
 */
export const SimpleTooltip = styled(Tooltip)(({ theme }) => {
  const isLight = theme.palette.mode === 'light'
  
  return {
    [`& .${tooltipClasses.tooltip}`]: {
      backgroundColor: isLight 
        ? 'rgba(97, 97, 97, 0.92)'
        : 'rgba(255, 255, 255, 0.92)',
      color: isLight 
        ? '#ffffff'
        : 'rgba(0, 0, 0, 0.87)',
      fontSize: theme.typography.pxToRem(11),
      borderRadius: BORDER_RADIUS.SMALL,
      padding: '6px 8px',
      fontWeight: 500,
      backdropFilter: 'blur(4px)',
      WebkitBackdropFilter: 'blur(4px)',
      maxWidth: 200,
    },
    [`& .${tooltipClasses.arrow}`]: {
      color: isLight 
        ? 'rgba(97, 97, 97, 0.92)'
        : 'rgba(255, 255, 255, 0.92)',
    },
  }
})

// 默认导出主题化 Tooltip
export default ThemedTooltip 