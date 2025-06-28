/**
 * 主题切换按钮组件
 * 用于在亮色模式和暗色模式之间切换
 */
import { IconButton, Tooltip, SxProps, Theme } from '@mui/material'
import { LightMode as LightIcon, DarkMode as DarkIcon } from '@mui/icons-material'
import { useColorMode } from '../stores/theme'
import { ThemeMode } from './palette'

/**
 * 主题切换按钮组件
 * 切换顺序为：浅色 -> 暗色 -> 浅色
 */
export default function ThemeToggleButton({
  size = 'medium',
  sx,
}: {
  size?: 'small' | 'medium' | 'large'
  sx?: SxProps<Theme>
}) {
  const { mode, toggleColorMode } = useColorMode()

  // 根据当前主题模式选择显示的图标
  const ThemeIcon = (() => {
    switch (mode) {
      case 'light':
        return LightIcon
      case 'dark':
        return DarkIcon
      default:
        return LightIcon
    }
  })()

  // 获取提示文本
  const getTooltipText = (mode: ThemeMode): string => {
    switch (mode) {
      case 'light':
        return '当前：浅色模式 (点击切换到暗色模式)'
      case 'dark':
        return '当前：暗色模式 (点击切换到浅色模式)'
      default:
        return '切换主题'
    }
  }

  return (
    <Tooltip title={getTooltipText(mode)} arrow>
      <IconButton
        onClick={toggleColorMode}
        color="inherit"
        size={size}
        sx={{
          transition: 'transform 0.3s ease, opacity 0.2s ease',
          '&:hover': {
            transform: 'rotate(12deg) scale(1.05)',
          },
          '&:active': {
            transform: 'scale(0.95)',
          },
          ...sx,
        }}
      >
        <ThemeIcon
          sx={{
            transition: 'all 0.3s ease',
          }}
        />
      </IconButton>
    </Tooltip>
  )
}
