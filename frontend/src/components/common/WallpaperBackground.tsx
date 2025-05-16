import React, { useState, useEffect } from 'react'
import { Box, styled } from '@mui/material'
import { motion, AnimatePresence } from 'framer-motion'
import { UI_STYLES, getAnimationDuration, getBlurValue } from '../../theme/themeApi'
import { useWallpaperStore } from '../../stores/wallpaper'
import { useColorMode } from '../../stores/theme'

// 背景壁纸容器
const BackgroundContainer = styled(Box)(() => ({
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  zIndex: 0,
  overflow: 'hidden',
}))

// 已加载壁纸缓存
const wallpaperCache: Record<string, HTMLImageElement> = {}

interface WallpaperBackgroundProps {
  wallpaperUrl: string | null
  mode?: 'cover' | 'contain' | 'repeat' | 'center'
  blur?: number
  dim?: number
  children?: React.ReactNode
  className?: string
  fallbackBackground?: string
  onError?: (url: string) => void // 可选的错误回调
}

const WallpaperBackground: React.FC<WallpaperBackgroundProps> = ({
  wallpaperUrl,
  mode = 'cover',
  blur = 0,
  dim = 30,
  children,
  className,
  fallbackBackground,
  onError,
}) => {
  const [currentWallpaper, setCurrentWallpaper] = useState<string | null>(wallpaperUrl)
  const [hasError, setHasError] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { performanceMode } = useColorMode()
  // 从全局store获取壁纸失效处理函数
  const { handleWallpaperInvalid } = useWallpaperStore()

  // 壁纸改变时预加载并平滑过渡
  useEffect(() => {
    // 无壁纸，直接设置为null
    if (!wallpaperUrl) {
      setCurrentWallpaper(null)
      setHasError(false)
      return
    }

    // 如果壁纸URL相同，无需重新加载
    if (wallpaperUrl === currentWallpaper) {
      return
    }

    // 检查缓存中是否已存在
    if (wallpaperCache[wallpaperUrl]) {
      console.log('使用缓存的壁纸:', wallpaperUrl)
      setCurrentWallpaper(wallpaperUrl)
      setHasError(false)
      return
    }

    // 开始加载新壁纸
    setIsLoading(true)
    setHasError(false)

    const img = new Image()
    img.crossOrigin = 'anonymous' // 尝试解决可能的跨域问题
    
    img.onload = () => {
      // 加载成功，更新当前壁纸
      wallpaperCache[wallpaperUrl] = img // 加入缓存
      setCurrentWallpaper(wallpaperUrl)
      setHasError(false)
      setIsLoading(false)
    }
    
    img.onerror = () => {
      // 加载失败，但如果之前已成功加载，保持当前壁纸
      console.error('壁纸加载失败:', wallpaperUrl)
      
      // 如果当前已有壁纸且非首次加载，保持使用当前壁纸
      if (currentWallpaper && currentWallpaper !== wallpaperUrl) {
        console.log('保持使用现有壁纸')
        setHasError(false)
      } else {
        setHasError(true)
        setCurrentWallpaper(null)
        
        // 第一次加载失败时，通知壁纸无效
        if (onError) {
          onError(wallpaperUrl)
        } else {
          // 使用全局处理函数
          handleWallpaperInvalid(wallpaperUrl)
        }
      }
      setIsLoading(false)
    }
    
    // 开始加载图片
    img.src = wallpaperUrl
  }, [wallpaperUrl, currentWallpaper, onError, handleWallpaperInvalid])

  // 获取背景样式
  const getBackgroundStyle = () => {
    if (currentWallpaper && !hasError) {
      // 根据性能模式调整模糊效果
      const effectiveBlur = getBlurValue(blur)
      
      return {
        backgroundImage: `url(${currentWallpaper})`,
        backgroundSize: mode,
        backgroundPosition: 'center',
        backgroundRepeat: mode === 'repeat' ? 'repeat' : 'no-repeat',
        filter: effectiveBlur > 0 ? `blur(${effectiveBlur}px)` : 'none',
      }
    }
    
    // 回退到默认背景
    return {
      background: fallbackBackground || UI_STYLES.BACKGROUND.PRIMARY,
    }
  }

  // 获取暗度覆盖层样式
  const getDimOverlayStyle = () => {
    if (!currentWallpaper || hasError) return {}
    
    return {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: `rgba(0, 0, 0, ${dim / 100})`,
      zIndex: 1,
    }
  }

  // 根据性能模式决定是否禁用动画
  const shouldEnableAnimation = () => {
    return performanceMode !== 'performance'
  }

  return (
    <BackgroundContainer className={className}>
      {/* 壁纸背景 */}
      <AnimatePresence>
        <motion.div
          key={currentWallpaper || 'fallback'}
          initial={shouldEnableAnimation() ? { opacity: 0 } : { opacity: 1 }}
          animate={{ opacity: 1 }}
          exit={shouldEnableAnimation() ? { opacity: 0 } : { opacity: 1 }}
          transition={{ duration: getAnimationDuration(0.5) }}
          style={{
            position: 'absolute',
            top: -10,
            left: -10,
            right: -10,
            bottom: -10,
            ...getBackgroundStyle(),
          }}
        />
      </AnimatePresence>

      {/* 暗度覆盖层 */}
      <Box sx={getDimOverlayStyle()} />

      {/* 加载指示器 */}
      {isLoading && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            zIndex: 2,
          }}
        >
          {/* 可以添加加载动画 */}
        </Box>
      )}

      {/* 子内容 */}
      {children}
    </BackgroundContainer>
  )
}

export default WallpaperBackground 