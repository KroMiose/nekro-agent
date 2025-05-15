import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Stack,
  Button,
  TextField,
  Tooltip,
  useTheme,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  useMediaQuery,
  Tabs,
  Tab,
  CardMedia,
  CardActions,
  Slider,
  RadioGroup,
  FormControlLabel,
  Radio,
  CircularProgress,
} from '@mui/material'
import {
  Check as CheckIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  LightMode as LightModeIcon,
  DarkMode as DarkModeIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  Tune as TuneIcon,
  Save as SaveIcon,
  Add as AddIcon,
  Image as ImageIcon,
  PhotoSizeSelectActual as PhotoSizeSelectActualIcon,
  PhotoSizeSelectLarge as PhotoSizeSelectLargeIcon,
  Pages as PagesIcon,
  Wallpaper as WallpaperIcon,
  Palette as PaletteIcon,
  FormatColorFill as FormatColorFillIcon,
  Computer as ComputerIcon,
} from '@mui/icons-material'
import { useColorMode } from '../../stores/theme'
import {
  themePresets,
  updateTheme,
  customizeTheme,
  currentThemePresetId,
  MinimalPaletteConfig,
  getLighterColor,
  getDarkerColor,
} from '../../theme/themeApi'
import { HexColorPicker } from 'react-colorful'
import { useNotification } from '../../hooks/useNotification'
import { useWallpaperStore } from '../../stores/wallpaper'
import { commonApi, Wallpaper } from '../../services/api/common'
import WallpaperBackground from '../../components/common/WallpaperBackground'
import { BUTTON_VARIANTS } from '../../theme/variants'
import GitHubStarWarning from '../../components/common/GitHubStarWarning'
import { useGitHubStarStore } from '../../stores/githubStar'

// 颜色预览组件
const ColorPreview = ({
  color,
  onClick,
  active = false,
  size = 36,
}: {
  color: string
  onClick?: () => void
  active?: boolean
  size?: number
}) => (
  <Tooltip title={color} arrow>
    <Box
      sx={{
        width: size,
        height: size,
        borderRadius: '50%',
        bgcolor: color,
        cursor: 'pointer',
        border: theme => `2px solid ${active ? theme.palette.primary.main : 'transparent'}`,
        boxShadow: active ? '0 0 0 2px rgba(0, 0, 0, 0.1)' : 'none',
        transition: 'all 0.2s ease',
        position: 'relative',
        '&:hover': {
          transform: 'scale(1.05)',
          boxShadow: '0 0 0 2px rgba(0, 0, 0, 0.1)',
        },
      }}
      onClick={onClick}
    >
      {active && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: theme => theme.palette.getContrastText(color),
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <CheckIcon fontSize="small" />
        </Box>
      )}
    </Box>
  </Tooltip>
)

// 颜色选择对话框
const ColorPickerDialog = ({
  open,
  onClose,
  color,
  onChange,
  title,
}: {
  open: boolean
  onClose: () => void
  color: string
  onChange: (color: string) => void
  title: string
}) => {
  const [tempColor, setTempColor] = useState(color)

  // 当对话框打开或颜色变更时同步状态
  useEffect(() => {
    if (open) {
      setTempColor(color)
    }
  }, [color, open])

  const handleSave = () => {
    // 验证颜色格式
    const isValidColor = /^#([0-9A-F]{3}){1,2}$/i.test(tempColor)
    if (isValidColor) {
      onChange(tempColor)
      onClose()
    }
  }

  // 在用户输入时更新颜色
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value
    // 自动添加 # 前缀
    if (value && !value.startsWith('#')) {
      value = '#' + value
    }
    setTempColor(value)
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <HexColorPicker color={tempColor} onChange={setTempColor} style={{ width: '100%' }} />
          <TextField
            fullWidth
            label="十六进制颜色值"
            value={tempColor}
            onChange={handleInputChange}
            error={!/^#([0-9A-F]{3}){1,2}$/i.test(tempColor)}
            helperText={
              !/^#([0-9A-F]{3}){1,2}$/i.test(tempColor) ? '请输入有效的十六进制颜色值' : ''
            }
            InputProps={{
              startAdornment: (
                <Box
                  sx={{
                    width: 24,
                    height: 24,
                    borderRadius: 1,
                    bgcolor: /^#([0-9A-F]{3}){1,2}$/i.test(tempColor) ? tempColor : '#cccccc',
                    mr: 1,
                    border: '1px solid rgba(0,0,0,0.1)',
                  }}
                />
              ),
            }}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>取消</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={!/^#([0-9A-F]{3}){1,2}$/i.test(tempColor)}
        >
          应用
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// 壁纸模式选项
const WALLPAPER_MODES = [
  { value: 'cover', label: '填充', icon: <PhotoSizeSelectLargeIcon /> },
  { value: 'contain', label: '适应', icon: <PhotoSizeSelectActualIcon /> },
  { value: 'center', label: '居中', icon: <ImageIcon /> },
  { value: 'repeat', label: '平铺', icon: <PagesIcon /> },
]

// 主题预览卡片
const ThemePreviewCard = ({
  preset,
  active,
  onClick,
  onCustomizeClick,
  isCustom = false,
}: {
  preset: {
    id: string
    name: string
    description: string
    light: MinimalPaletteConfig
    dark: MinimalPaletteConfig
  }
  active: boolean
  onClick: () => void
  onCustomizeClick?: () => void
  isCustom?: boolean
}) => {
  const theme = useTheme()
  const { mode } = useColorMode()
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const currentMode =
    mode === 'system' ? (theme.palette.mode as 'light' | 'dark') : (mode as 'light' | 'dark')

  return (
    <Card
      sx={{
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        transform: active ? 'scale(1.02)' : 'scale(1)',
        border: active ? `2px solid ${theme.palette.primary.main}` : '2px solid transparent',
        '&:hover': {
          transform: active ? 'scale(1.02)' : 'scale(1.01)',
          boxShadow: theme => theme.shadows[4],
        },
        position: 'relative',
        overflow: 'visible',
      }}
      onClick={onClick}
    >
      {active && (
        <Box
          sx={{
            position: 'absolute',
            top: -10,
            right: -10,
            bgcolor: 'primary.main',
            color: 'white',
            width: 24,
            height: 24,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 2,
          }}
        >
          <CheckIcon fontSize="small" />
        </Box>
      )}
      <CardContent>
        <Stack spacing={2}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6" sx={{ fontSize: isSmall ? '1rem' : '1.25rem' }}>
              {preset.name}
            </Typography>
            {isCustom && onCustomizeClick && (
              <IconButton
                size="small"
                onClick={e => {
                  e.stopPropagation()
                  onCustomizeClick()
                }}
              >
                <EditIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mb: 2, fontSize: isSmall ? '0.75rem' : '0.875rem' }}
          >
            {preset.description}
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="caption" sx={{ fontSize: isSmall ? '0.65rem' : '0.75rem' }}>
                主色:
              </Typography>
              <ColorPreview color={preset[currentMode].brand} size={isSmall ? 24 : 30} />
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="caption" sx={{ fontSize: isSmall ? '0.65rem' : '0.75rem' }}>
                辅色:
              </Typography>
              <ColorPreview color={preset[currentMode].accent} size={isSmall ? 24 : 30} />
            </Stack>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  )
}

// 颜色对话框状态类型
interface ColorDialogState {
  open: boolean
  color: string
  title: string
  mode: 'light' | 'dark'
  type: 'brand' | 'accent'
}

// 主题配置页面
export default function ThemeConfigPage() {
  const { mode, setColorMode, setThemePreset, setCustomColors } = useColorMode()
  const theme = useTheme()
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const currentMode =
    mode === 'system' ? (theme.palette.mode as 'light' | 'dark') : (mode as 'light' | 'dark')
  const notification = useNotification()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const initializedRef = useRef(false)

  // 选中的主题
  const [selectedPresetId, setSelectedPresetId] = useState(currentThemePresetId)

  // 自定义主题
  const [customTheme, setCustomTheme] = useState({
    id: 'custom',
    name: '自定义主题',
    description: '自定义色彩搭配',
    light: {
      brand: '#7E57C2',
      accent: '#26A69A',
    },
    dark: {
      brand: '#9575CD',
      accent: '#4DB6AC',
    },
  })

  // 颜色选择对话框状态
  const [colorDialog, setColorDialog] = useState<ColorDialogState>({
    open: false,
    color: '',
    title: '',
    mode: 'light',
    type: 'brand',
  })

  // 壁纸相关状态
  const [wallpaperTab, setWallpaperTab] = useState(0)
  const [wallpapers, setWallpapers] = useState<Wallpaper[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [previewWallpaper, setPreviewWallpaper] = useState<Wallpaper | null>(null)

  // 壁纸store
  const {
    loginWallpaper,
    mainWallpaper,
    loginWallpaperMode,
    mainWallpaperMode,
    loginWallpaperBlur,
    mainWallpaperBlur,
    loginWallpaperDim,
    mainWallpaperDim,
    setLoginWallpaper,
    setMainWallpaper,
    setLoginWallpaperMode,
    setMainWallpaperMode,
    setLoginWallpaperBlur,
    setMainWallpaperBlur,
    setLoginWallpaperDim,
    setMainWallpaperDim,
    handleWallpaperInvalid,
  } = useWallpaperStore()

  // 壁纸设置面板状态
  const [editSettings, setEditSettings] = useState({
    wallpaperMode: wallpaperTab === 0 ? loginWallpaperMode : mainWallpaperMode,
    wallpaperBlur: wallpaperTab === 0 ? loginWallpaperBlur : mainWallpaperBlur,
    wallpaperDim: wallpaperTab === 0 ? loginWallpaperDim : mainWallpaperDim,
  })

  // 检查当前标签对应的壁纸是否设置
  const hasCurrentWallpaper = () => {
    return wallpaperTab === 0 ? !!loginWallpaper : !!mainWallpaper
  }

  // 获取当前壁纸URL
  const getCurrentWallpaperUrl = () => {
    return wallpaperTab === 0 ? loginWallpaper : mainWallpaper
  }

  // 移除当前壁纸
  const removeCurrentWallpaper = () => {
    if (wallpaperTab === 0) {
      setLoginWallpaper(null)
    } else {
      setMainWallpaper(null)
    }

    notification.info(`已移除${wallpaperTab === 0 ? '登录页' : '主页'}壁纸`)
  }

  // 获取壁纸列表
  const fetchWallpapers = async () => {
    try {
      setLoading(true)
      const response = await commonApi.getWallpapers()
      if (response.code === 200 && Array.isArray(response.data)) {
        setWallpapers(response.data)
      } else {
        notification.error('获取壁纸列表失败')
      }
    } catch (error) {
      console.error('获取壁纸列表失败:', error)
      notification.error('获取壁纸列表失败')
    } finally {
      setLoading(false)
    }
  }

  // 处理文件上传（包括拖放和点击上传）
  const handleFileUpload = async (file: File) => {
    // 检查文件类型
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if (!validTypes.includes(file.type)) {
      notification.error('不支持的文件类型，请上传 JPG, PNG, GIF 或 WebP 格式的图片')
      return
    }

    // 检查文件大小 (限制 24 MB)
    if (file.size > 24 * 1024 * 1024) {
      notification.error('文件大小不能超过10MB')
      return
    }

    try {
      setUploading(true)
      // 显示上传中通知
      notification.info(`正在上传壁纸 "${file.name}"...可能需要一段时间，请耐心等待`, {
        autoHideDuration: null, // 不自动隐藏
        key: 'upload-wallpaper-progress', // 使用固定key以便后续更新
      })

      const response = await commonApi.uploadWallpaper(file)

      if (response.code === 200 && response.data) {
        // 关闭上传中通知
        notification.close('upload-wallpaper-progress')
        notification.success('壁纸上传成功')

        // 获取壁纸列表并确保最新上传的壁纸被选中
        await fetchWallpapers()

        // 如果当前没有壁纸，自动应用最新上传的壁纸
        if (!hasCurrentWallpaper() && response.data && 'url' in response.data) {
          applyWallpaper(response.data as Wallpaper)
        }
      } else {
        // 关闭上传中通知并显示错误
        notification.close('upload-wallpaper-progress')
        notification.error(response.msg || '壁纸上传失败')
      }
    } catch (error) {
      console.error('壁纸上传失败:', error)
      // 关闭上传中通知并显示错误
      notification.close('upload-wallpaper-progress')

      // 提供更详细的错误信息
      if (error instanceof Error) {
        if (error.message.includes('timeout')) {
          notification.error('壁纸上传超时，请检查网络连接或尝试上传较小的图片')
        } else if (error.message.includes('Network Error')) {
          notification.error('网络连接失败，请检查网络设置后重试')
        } else {
          notification.error(`壁纸上传失败: ${error.message}`)
        }
      } else {
        notification.error('壁纸上传失败，请稍后重试')
      }
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  // 修改原有上传函数，复用文件处理逻辑
  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return
    await handleFileUpload(files[0])
  }

  // 应用壁纸
  const applyWallpaper = (wallpaper: Wallpaper) => {
    try {
      // 显示应用中通知
      notification.info(`正在应用壁纸...`, {
        autoHideDuration: 1500, // 短时间显示
      })

      // 根据壁纸类型设置不同的壁纸
      if (wallpaperTab === 0) {
        setLoginWallpaper(wallpaper.url)
      } else {
        setMainWallpaper(wallpaper.url)
      }

      // 预加载图片确保壁纸正确显示
      const img = new Image()
      img.src = wallpaper.url
      img.onload = () => {
        // 显示成功应用通知
        notification.success(`已成功设置为${wallpaperTab === 0 ? '登录页' : '主页'}壁纸`)

        // 更新设置标签页以反映新设置
        if (wallpaperTab === 0) {
          setEditSettings({
            ...editSettings,
            wallpaperMode: loginWallpaperMode,
            wallpaperBlur: loginWallpaperBlur,
            wallpaperDim: loginWallpaperDim,
          })
        } else {
          setEditSettings({
            ...editSettings,
            wallpaperMode: mainWallpaperMode,
            wallpaperBlur: mainWallpaperBlur,
            wallpaperDim: mainWallpaperDim,
          })
        }
      }
      img.onerror = () => {
        notification.error(`壁纸应用失败，无法加载图片: ${wallpaper.url}`)
        // 回滚设置
        if (wallpaperTab === 0) {
          setLoginWallpaper(null)
        } else {
          setMainWallpaper(null)
        }
      }
    } catch (error) {
      console.error('应用壁纸失败:', error)
      notification.error('应用壁纸失败')
    }
  }

  // 删除壁纸
  const handleDeleteWallpaper = async (wallpaperId: string) => {
    try {
      const response = await commonApi.deleteWallpaper(wallpaperId)

      if (response.code === 200) {
        notification.success('壁纸删除成功')

        // 找到被删除的壁纸
        const deletedWallpaper = wallpapers.find(wp => wp.id === wallpaperId)

        // 如果当前使用的壁纸被删除，则标记为无效
        if (deletedWallpaper?.url) {
          handleWallpaperInvalid(deletedWallpaper.url)
        }

        // 更新壁纸列表
        await fetchWallpapers()

        // 如果预览的壁纸被删除，关闭预览
        if (previewWallpaper?.id === wallpaperId) {
          setPreviewWallpaper(null)
        }
      } else {
        notification.error(response.msg || '壁纸删除失败')
      }
    } catch (error) {
      console.error('壁纸删除失败:', error)
      notification.error('壁纸删除失败')
    }
  }

  // 处理壁纸设置变更
  const handleWallpaperSettingChange = (
    setting: 'wallpaperMode' | 'wallpaperBlur' | 'wallpaperDim',
    value: string | number
  ) => {
    setEditSettings({
      ...editSettings,
      [setting]: value,
    })
  }

  // 应用壁纸设置
  const applyWallpaperSettings = () => {
    if (wallpaperTab === 0) {
      // 登录页壁纸设置
      const mode = editSettings.wallpaperMode as 'cover' | 'contain' | 'repeat' | 'center'
      setLoginWallpaperMode(mode)
      setLoginWallpaperBlur(editSettings.wallpaperBlur as number)
      setLoginWallpaperDim(editSettings.wallpaperDim as number)
    } else {
      // 主布局壁纸设置
      const mode = editSettings.wallpaperMode as 'cover' | 'contain' | 'repeat' | 'center'
      setMainWallpaperMode(mode)
      setMainWallpaperBlur(editSettings.wallpaperBlur as number)
      setMainWallpaperDim(editSettings.wallpaperDim as number)
    }

    setShowSettings(false)
    notification.success('壁纸设置已应用')
  }

  // 在页面加载时同步自定义主题
  useEffect(() => {
    // 只在首次渲染时执行初始化操作
    if (!initializedRef.current) {
      initializedRef.current = true

      // 从存储中加载当前主题颜色
      try {
        const storedData = JSON.parse(localStorage.getItem('color-mode') || '{}')

        if (storedData && storedData.state) {
          const { presetId, lightBrand, lightAccent, darkBrand, darkAccent } = storedData.state

          setSelectedPresetId(presetId || currentThemePresetId)

          // 如果是自定义主题，加载自定义颜色
          if (presetId === 'custom' && lightBrand && lightAccent && darkBrand && darkAccent) {
            setCustomTheme({
              id: 'custom',
              name: '自定义主题',
              description: '自定义色彩搭配',
              light: {
                brand: lightBrand,
                accent: lightAccent,
              },
              dark: {
                brand: darkBrand,
                accent: darkAccent,
              },
            })
          }
        }
      } catch (error) {
        console.error('加载主题数据失败:', error)
      }

      // 初始化壁纸功能
      fetchWallpapers()
    }

    // 添加主题变化事件监听
    const handleThemeChange = (event: Event) => {
      const customEvent = event as CustomEvent

      if (customEvent.detail && customEvent.detail.presetId) {
        setSelectedPresetId(customEvent.detail.presetId)
      }
    }

    window.addEventListener('nekro-theme-change', handleThemeChange)

    return () => {
      window.removeEventListener('nekro-theme-change', handleThemeChange)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 打开颜色选择器
  const openColorPicker = (type: 'brand' | 'accent', mode: 'light' | 'dark') => {
    // 如果未Star，显示提示
    if (!allStarred) {
      notification.warning('请先支持开源项目后再使用自定义主题功能')
      return
    }

    setColorDialog({
      open: true,
      color: customTheme[mode][type],
      title: `选择${mode === 'light' ? '浅色' : '深色'}主题的${type === 'brand' ? '主色' : '辅助色'}`,
      mode,
      type,
    })
  }

  // 处理颜色变更
  const handleColorChange = (color: string) => {
    const { mode, type } = colorDialog

    // 如果未Star，阻止修改
    if (!allStarred) {
      notification.warning('请先支持开源项目后再使用自定义主题功能')
      return
    }

    // 更新自定义主题状态
    setCustomTheme(prev => {
      const newTheme = {
        ...prev,
        [mode]: {
          ...prev[mode],
          [type]: color,
        },
      }

      // 如果当前选择的是自定义主题，立即应用改变
      if (selectedPresetId === 'custom') {
        customizeTheme(newTheme.light, newTheme.dark)

        // 更新状态管理
        const themeColors = {
          lightBrand: newTheme.light.brand,
          lightAccent: newTheme.light.accent,
          darkBrand: newTheme.dark.brand,
          darkAccent: newTheme.dark.accent,
        }
        setCustomColors(themeColors)
      }

      return newTheme
    })
  }

  // 应用主题
  const applyTheme = (presetId: string) => {
    // 如果未Star且不是默认主题，显示提示并使用默认主题
    if (!allStarred && presetId !== 'kolo' && presetId !== 'custom') {
      notification.warning('高级主题需要您支持开源项目后才能使用')
      setThemePreset('kolo')
      setSelectedPresetId('kolo')
      return
    }

    try {
      if (presetId === 'custom') {
        // 应用自定义主题
        customizeTheme(customTheme.light, customTheme.dark)

        // 更新状态管理
        const themeColors = {
          lightBrand: customTheme.light.brand,
          lightAccent: customTheme.light.accent,
          darkBrand: customTheme.dark.brand,
          darkAccent: customTheme.dark.accent,
        }
        setCustomColors(themeColors)

        notification.success('已应用自定义主题')
      } else {
        // 查找预设主题
        const preset = themePresets.find(p => p.id === presetId)
        if (!preset) {
          notification.error('找不到指定的预设主题')
          return
        }

        // 应用预设主题
        updateTheme(presetId)

        // 更新状态管理
        setThemePreset(presetId)

        notification.success(`已应用"${preset.name}"主题`)
      }

      // 更新选中状态
      setSelectedPresetId(presetId)
    } catch (error) {
      console.error('应用主题失败:', error)
      notification.error('应用主题失败，请重试')
    }
  }

  // 切换主题模式
  const handleThemeModeChange = (newMode: 'light' | 'dark' | 'system') => {
    setColorMode(newMode)
    notification.info(
      `已切换至${newMode === 'light' ? '浅色' : newMode === 'dark' ? '深色' : '跟随系统'}模式`
    )
  }

  // 重置自定义主题
  const resetCustomTheme = () => {
    const defaultCustom = {
      id: 'custom',
      name: '自定义主题',
      description: '自定义色彩搭配',
      light: {
        brand: '#7E57C2',
        accent: '#26A69A',
      },
      dark: {
        brand: '#9575CD',
        accent: '#4DB6AC',
      },
    }

    setCustomTheme(defaultCustom)

    if (selectedPresetId === 'custom') {
      customizeTheme(defaultCustom.light, defaultCustom.dark)

      // 更新状态管理
      const themeColors = {
        lightBrand: defaultCustom.light.brand,
        lightAccent: defaultCustom.light.accent,
        darkBrand: defaultCustom.dark.brand,
        darkAccent: defaultCustom.dark.accent,
      }
      setCustomColors(themeColors)

      notification.success('已重置自定义主题')
    }
  }

  // 打开自定义主题编辑器
  const openCustomizer = () => {
    // 根据当前主题模式打开相应的颜色选择器
    openColorPicker('brand', currentMode)
  }

  // 所有预设加上自定义主题
  const allPresets = [...themePresets, customTheme]

  // 在壁纸标签切换时，同步设置面板状态
  useEffect(() => {
    // 更新编辑设置以匹配当前选择的标签
    setEditSettings({
      wallpaperMode: wallpaperTab === 0 ? loginWallpaperMode : mainWallpaperMode,
      wallpaperBlur: wallpaperTab === 0 ? loginWallpaperBlur : mainWallpaperBlur,
      wallpaperDim: wallpaperTab === 0 ? loginWallpaperDim : mainWallpaperDim,
    })
  }, [
    wallpaperTab,
    loginWallpaperMode,
    mainWallpaperMode,
    loginWallpaperBlur,
    mainWallpaperBlur,
    loginWallpaperDim,
    mainWallpaperDim,
  ])

  // 添加重置壁纸设置方法
  const resetWallpaperSettings = () => {
    setEditSettings({
      wallpaperMode: 'cover',
      wallpaperBlur: 0,
      wallpaperDim: 30,
    })
    notification.info('已重置壁纸设置为默认值')
  }

  // GitHub Star状态
  const { allStarred } = useGitHubStarStore()

  return (
    <Box className="h-full flex flex-col overflow-auto p-4">
      {/* 主标题和内容容器 */}
      <Box sx={{ mb: 4 }}>
        {/* 主题模式控制 */}
        <Paper className="p-4 mb-4">
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <LightModeIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6" sx={{ fontSize: isSmall ? '1.1rem' : '1.25rem' }}>
              主题模式
            </Typography>
          </Box>

          <Stack direction="row" spacing={3} className="mb-2">
            <Button
              variant={mode === 'light' ? 'contained' : 'outlined'}
              startIcon={<LightModeIcon />}
              onClick={() => handleThemeModeChange('light')}
              size={isSmall ? 'small' : 'medium'}
            >
              浅色模式
            </Button>

            <Button
              variant={mode === 'dark' ? 'contained' : 'outlined'}
              startIcon={<DarkModeIcon />}
              onClick={() => handleThemeModeChange('dark')}
              size={isSmall ? 'small' : 'medium'}
            >
              深色模式
            </Button>

            <Button
              variant={mode === 'system' ? 'contained' : 'outlined'}
              startIcon={<ComputerIcon />}
              onClick={() => handleThemeModeChange('system')}
              size={isSmall ? 'small' : 'medium'}
            >
              跟随系统
            </Button>
          </Stack>

          <Typography variant="body2" color="text.secondary">
            当前模式: {mode === 'light' ? '浅色' : mode === 'dark' ? '深色' : '跟随系统'}
            {mode === 'system' && ` (${theme.palette.mode === 'light' ? '浅色' : '深色'})`}
          </Typography>
        </Paper>

        {/* 将GitHubStarWarning移到这里，包裹主题颜色和壁纸设置部分 */}
        <GitHubStarWarning
          title="解锁个性化设置"
          message="支持开源项目后即可使用自定义主题和壁纸功能，打造专属于您的个性化界面！"
          onStarred={() => {
            // 初始化操作
            fetchWallpapers()
          }}
          onNotStarred={() => {
            // 为未star用户应用默认主题
            setThemePreset('kolo')
          }}
          onError={error => {
            console.error('检查Star状态出错:', error)
            notification.error('功能授权检查失败，请稍后再试')
          }}
          searchParam="NEKRO_CLOUD"
        >
          {/* 主题预设选择 */}
          <Paper className="p-4 mb-4">
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <PaletteIcon sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6" sx={{ fontSize: isSmall ? '1.1rem' : '1.25rem' }}>
                主题颜色
              </Typography>
            </Box>

            <Grid container spacing={2}>
              {allPresets.map(preset => (
                <Grid item xs={12} sm={6} md={4} key={preset.id}>
                  <ThemePreviewCard
                    preset={preset}
                    active={selectedPresetId === preset.id}
                    onClick={() => applyTheme(preset.id)}
                    onCustomizeClick={preset.id === 'custom' ? openCustomizer : undefined}
                    isCustom={preset.id === 'custom'}
                  />
                </Grid>
              ))}
            </Grid>
          </Paper>

          {/* 自定义主题编辑 */}
          {selectedPresetId === 'custom' && allStarred && (
            <Paper className="p-4">
              <Box className="mb-3 flex justify-between items-center">
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <FormatColorFillIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6" sx={{ fontSize: isSmall ? '1.1rem' : '1.25rem' }}>
                    自定义主题编辑
                  </Typography>
                </Box>
                <Button
                  startIcon={<RefreshIcon />}
                  onClick={resetCustomTheme}
                  size={isSmall ? 'small' : 'medium'}
                >
                  重置
                </Button>
              </Box>

              <Grid container spacing={3}>
                {/* 浅色模式 */}
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography
                        variant="subtitle1"
                        gutterBottom
                        sx={{ fontSize: isSmall ? '0.9rem' : '1rem', fontWeight: 'bold' }}
                      >
                        浅色模式颜色
                      </Typography>
                      <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={6}>
                          <Stack spacing={1}>
                            <Typography
                              variant="caption"
                              sx={{ fontSize: isSmall ? '0.7rem' : '0.75rem' }}
                            >
                              主色调
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <ColorPreview
                                color={customTheme.light.brand}
                                onClick={() => openColorPicker('brand', 'light')}
                                size={isSmall ? 30 : 36}
                              />
                              <Typography
                                variant="body2"
                                sx={{
                                  fontSize: isSmall ? '0.75rem' : '0.875rem',
                                  textTransform: 'uppercase',
                                }}
                              >
                                {customTheme.light.brand}
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={() => openColorPicker('brand', 'light')}
                                sx={{ ml: 'auto' }}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </Box>
                          </Stack>
                        </Grid>
                        <Grid item xs={6}>
                          <Stack spacing={1}>
                            <Typography
                              variant="caption"
                              sx={{ fontSize: isSmall ? '0.7rem' : '0.75rem' }}
                            >
                              辅助色
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <ColorPreview
                                color={customTheme.light.accent}
                                onClick={() => openColorPicker('accent', 'light')}
                                size={isSmall ? 30 : 36}
                              />
                              <Typography
                                variant="body2"
                                sx={{
                                  fontSize: isSmall ? '0.75rem' : '0.875rem',
                                  textTransform: 'uppercase',
                                }}
                              >
                                {customTheme.light.accent}
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={() => openColorPicker('accent', 'light')}
                                sx={{ ml: 'auto' }}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </Box>
                          </Stack>
                        </Grid>
                      </Grid>

                      <Box sx={{ mt: 3 }}>
                        <Typography
                          variant="caption"
                          gutterBottom
                          sx={{ display: 'block', fontSize: isSmall ? '0.7rem' : '0.75rem' }}
                        >
                          派生色预览
                        </Typography>
                        <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          <ColorPreview
                            color={getLighterColor(customTheme.light.brand, 0.2)}
                            size={isSmall ? 24 : 28}
                          />
                          <ColorPreview color={customTheme.light.brand} size={isSmall ? 24 : 28} />
                          <ColorPreview
                            color={getDarkerColor(customTheme.light.brand, 0.2)}
                            size={isSmall ? 24 : 28}
                          />
                          <ColorPreview color={customTheme.light.accent} size={isSmall ? 24 : 28} />
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* 深色模式 */}
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography
                        variant="subtitle1"
                        gutterBottom
                        sx={{ fontSize: isSmall ? '0.9rem' : '1rem', fontWeight: 'bold' }}
                      >
                        深色模式颜色
                      </Typography>
                      <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={6}>
                          <Stack spacing={1}>
                            <Typography
                              variant="caption"
                              sx={{ fontSize: isSmall ? '0.7rem' : '0.75rem' }}
                            >
                              主色调
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <ColorPreview
                                color={customTheme.dark.brand}
                                onClick={() => openColorPicker('brand', 'dark')}
                                size={isSmall ? 30 : 36}
                              />
                              <Typography
                                variant="body2"
                                sx={{
                                  fontSize: isSmall ? '0.75rem' : '0.875rem',
                                  textTransform: 'uppercase',
                                }}
                              >
                                {customTheme.dark.brand}
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={() => openColorPicker('brand', 'dark')}
                                sx={{ ml: 'auto' }}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </Box>
                          </Stack>
                        </Grid>
                        <Grid item xs={6}>
                          <Stack spacing={1}>
                            <Typography
                              variant="caption"
                              sx={{ fontSize: isSmall ? '0.7rem' : '0.75rem' }}
                            >
                              辅助色
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <ColorPreview
                                color={customTheme.dark.accent}
                                onClick={() => openColorPicker('accent', 'dark')}
                                size={isSmall ? 30 : 36}
                              />
                              <Typography
                                variant="body2"
                                sx={{
                                  fontSize: isSmall ? '0.75rem' : '0.875rem',
                                  textTransform: 'uppercase',
                                }}
                              >
                                {customTheme.dark.accent}
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={() => openColorPicker('accent', 'dark')}
                                sx={{ ml: 'auto' }}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </Box>
                          </Stack>
                        </Grid>
                      </Grid>

                      <Box sx={{ mt: 3 }}>
                        <Typography
                          variant="caption"
                          gutterBottom
                          sx={{ display: 'block', fontSize: isSmall ? '0.7rem' : '0.75rem' }}
                        >
                          派生色预览
                        </Typography>
                        <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          <ColorPreview
                            color={getLighterColor(customTheme.dark.brand, 0.2)}
                            size={isSmall ? 24 : 28}
                          />
                          <ColorPreview color={customTheme.dark.brand} size={isSmall ? 24 : 28} />
                          <ColorPreview
                            color={getDarkerColor(customTheme.dark.brand, 0.2)}
                            size={isSmall ? 24 : 28}
                          />
                          <ColorPreview color={customTheme.dark.accent} size={isSmall ? 24 : 28} />
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Paper>
          )}

          {/* 壁纸设置 */}
          <Paper className="p-4 mt-4">
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <WallpaperIcon sx={{ mr: 1, verticalAlign: 'text-bottom', color: 'primary.main' }} />
              <Typography variant="h6" sx={{ fontSize: isSmall ? '1.1rem' : '1.25rem' }}>
                壁纸设置
              </Typography>
            </Box>

            {/* 壁纸设置内容 */}
            <Box
              sx={{
                display: 'flex',
                flexDirection: { xs: 'column', md: 'row' },
                gap: 2,
                position: 'relative',
                minHeight: '400px',
              }}
            >
              {/* 左侧标签和壁纸预览 */}
              <Box
                sx={{
                  width: { xs: '100%', md: '300px' },
                  display: 'flex',
                  flexDirection: 'column',
                  height: { xs: 'auto', md: '100%' },
                }}
              >
                <Box
                  sx={{
                    p: 2,
                    display: 'flex',
                    flexDirection: 'column',
                    position: 'relative',
                    overflow: 'hidden',
                    height: { xs: 'auto', md: '100%' },
                    bgcolor: 'background.paper',
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'divider',
                  }}
                >
                  <Tabs
                    value={wallpaperTab}
                    onChange={(_, newValue) => setWallpaperTab(newValue)}
                    indicatorColor="primary"
                    textColor="primary"
                    variant="fullWidth"
                    sx={{ mb: 2 }}
                  >
                    <Tab label="登录页壁纸" />
                    <Tab label="主布局壁纸" />
                  </Tabs>

                  {/* 预览区域 - 使用固定高度确保在所有设备上可见 */}
                  <div
                    style={{ position: 'relative', height: 250, marginBottom: 16, width: '100%' }}
                  >
                    {hasCurrentWallpaper() ? (
                      <div
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          right: 0,
                          bottom: 0,
                          overflow: 'hidden',
                          borderRadius: 4,
                          border: '1px solid rgba(0,0,0,0.12)',
                        }}
                      >
                        <WallpaperBackground
                          wallpaperUrl={getCurrentWallpaperUrl()}
                          mode={
                            (wallpaperTab === 0 ? loginWallpaperMode : mainWallpaperMode) as
                              | 'cover'
                              | 'contain'
                              | 'repeat'
                              | 'center'
                          }
                          blur={wallpaperTab === 0 ? loginWallpaperBlur : mainWallpaperBlur}
                          dim={wallpaperTab === 0 ? loginWallpaperDim : mainWallpaperDim}
                        />
                      </div>
                    ) : (
                      <div
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          right: 0,
                          bottom: 0,
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          backgroundColor: theme.palette.background.default,
                          borderRadius: 4,
                          border: '1px solid rgba(0,0,0,0.12)',
                        }}
                      >
                        <ImageIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
                        <Typography color="textSecondary" align="center">
                          未设置壁纸
                        </Typography>
                      </div>
                    )}
                  </div>

                  <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                    <Button
                      variant="outlined"
                      size="small"
                      color="primary"
                      startIcon={<TuneIcon />}
                      onClick={() => setShowSettings(true)}
                      disabled={!hasCurrentWallpaper()}
                    >
                      壁纸设置
                    </Button>

                    <Button
                      variant="outlined"
                      size="small"
                      color="error"
                      startIcon={<DeleteIcon />}
                      onClick={removeCurrentWallpaper}
                      disabled={!hasCurrentWallpaper()}
                    >
                      移除壁纸
                    </Button>
                  </Box>
                </Box>
              </Box>

              {/* 右侧壁纸列表 */}
              <Box
                sx={{
                  flex: 1,
                  p: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden',
                  position: 'relative',
                  height: { xs: 'auto', md: '100%' },
                  bgcolor: 'background.paper',
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    mb: 2,
                    height: 'auto',
                  }}
                >
                  <Typography variant="h6" sx={{ fontSize: { xs: '1rem', sm: '1.25rem' } }}>
                    选择壁纸
                  </Typography>

                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                      variant="outlined"
                      startIcon={<RefreshIcon />}
                      size="small"
                      onClick={fetchWallpapers}
                      disabled={loading}
                    >
                      刷新
                    </Button>

                    <Button
                      variant="contained"
                      startIcon={
                        uploading ? <CircularProgress size={20} color="inherit" /> : <UploadIcon />
                      }
                      size="small"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      sx={{
                        ...BUTTON_VARIANTS.primary.styles,
                        position: 'relative',
                        overflow: 'hidden',
                      }}
                    >
                      {uploading ? '上传中...' : '上传壁纸'}
                      {uploading && (
                        <Box
                          sx={{
                            position: 'absolute',
                            bottom: 0,
                            left: 0,
                            height: '3px',
                            backgroundColor: 'rgba(255, 255, 255, 0.5)',
                            animation: 'progress 2s infinite linear',
                            '@keyframes progress': {
                              '0%': {
                                width: '0%',
                                left: '0%',
                              },
                              '50%': {
                                width: '70%',
                                left: '15%',
                              },
                              '100%': {
                                width: '0%',
                                left: '100%',
                              },
                            },
                          }}
                        />
                      )}
                    </Button>
                    <input
                      type="file"
                      ref={fileInputRef}
                      style={{ display: 'none' }}
                      accept="image/jpeg,image/png,image/gif,image/webp"
                      onChange={handleUpload}
                    />
                  </Box>
                </Box>

                <Box
                  sx={{
                    flex: 1,
                    overflow: 'auto',
                    position: 'relative',
                    border: '2px dashed transparent',
                    borderRadius: 1,
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    height: 'calc(100% - 48px)', // 减去标题栏的高度
                    '&::before': {
                      content:
                        !uploading && wallpapers.length === 0 ? '"拖放图片到此处上传"' : '""',
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      color: 'text.secondary',
                      zIndex: 0,
                      pointerEvents: 'none',
                      opacity: 0.7,
                      fontSize: '1.2rem',
                      textAlign: 'center',
                      width: '100%',
                    },
                  }}
                  onDragOver={e => {
                    e.preventDefault()
                    e.stopPropagation()
                    if (!uploading) {
                      e.currentTarget.style.backgroundColor = theme.palette.action.hover
                      e.currentTarget.style.borderColor = theme.palette.primary.main
                    }
                  }}
                  onDragLeave={e => {
                    e.preventDefault()
                    e.stopPropagation()
                    e.currentTarget.style.backgroundColor = ''
                    e.currentTarget.style.borderColor = ''
                  }}
                  onDrop={e => {
                    e.preventDefault()
                    e.stopPropagation()
                    e.currentTarget.style.backgroundColor = ''
                    e.currentTarget.style.borderColor = ''

                    if (uploading) return

                    const files = e.dataTransfer.files
                    if (files && files.length > 0) {
                      const file = files[0]
                      handleFileUpload(file)
                    }
                  }}
                >
                  {loading ? (
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                      }}
                    >
                      <CircularProgress />
                    </Box>
                  ) : wallpapers.length === 0 ? (
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexDirection: 'column',
                        height: '100%',
                        padding: 2,
                        zIndex: 1,
                      }}
                    >
                      <ImageIcon sx={{ fontSize: 60, color: 'text.disabled', mb: 1 }} />
                      <Typography color="textSecondary" align="center" sx={{ mb: 1 }}>
                        暂无壁纸
                      </Typography>
                      <Button
                        variant="outlined"
                        startIcon={<AddIcon />}
                        size="small"
                        onClick={() => fileInputRef.current?.click()}
                      >
                        上传壁纸
                      </Button>
                      <Typography variant="caption" color="textSecondary" sx={{ mt: 2 }}>
                        支持拖放图片到此区域上传
                      </Typography>
                    </Box>
                  ) : (
                    <Grid container spacing={2}>
                      {wallpapers.map(wallpaper => (
                        <Grid item key={wallpaper.id} xs={12} sm={6} md={4} lg={3}>
                          <Card
                            sx={{
                              display: 'flex',
                              flexDirection: 'column',
                              height: '100%',
                              overflow: 'hidden',
                              transition: 'all 0.2s',
                              '&:hover': {
                                transform: 'translateY(-4px)',
                                boxShadow: theme.shadows[4],
                              },
                            }}
                          >
                            <CardMedia
                              component="div"
                              sx={{
                                height: 140,
                                backgroundSize: 'cover',
                                backgroundPosition: 'center',
                                backgroundImage: `url(${wallpaper.url})`,
                                position: 'relative',
                                '&::after': {
                                  content: '""',
                                  position: 'absolute',
                                  bottom: 0,
                                  left: 0,
                                  right: 0,
                                  height: '30%',
                                  background:
                                    'linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 100%)',
                                },
                                // 高亮当前选中的壁纸
                                outline:
                                  (wallpaperTab === 0 && loginWallpaper === wallpaper.url) ||
                                  (wallpaperTab === 1 && mainWallpaper === wallpaper.url)
                                    ? `2px solid ${theme.palette.primary.main}`
                                    : 'none',
                                boxShadow:
                                  (wallpaperTab === 0 && loginWallpaper === wallpaper.url) ||
                                  (wallpaperTab === 1 && mainWallpaper === wallpaper.url)
                                    ? `0 0 10px ${theme.palette.primary.main}`
                                    : 'none',
                              }}
                            />
                            <CardContent sx={{ p: 1.5, pb: 0, flex: 1 }}>
                              <Typography variant="body2" noWrap title={wallpaper.filename}>
                                {wallpaper.filename}
                              </Typography>
                            </CardContent>
                            <CardActions sx={{ p: 1 }}>
                              <IconButton
                                size="small"
                                onClick={() => setPreviewWallpaper(wallpaper)}
                                title="预览壁纸"
                              >
                                <VisibilityIcon fontSize="small" />
                              </IconButton>
                              <Button
                                size="small"
                                variant="outlined"
                                onClick={() => applyWallpaper(wallpaper)}
                                title="应用为当前选择的壁纸"
                                sx={{ ml: 'auto', minWidth: 0, px: 1 }}
                              >
                                应用
                              </Button>
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => handleDeleteWallpaper(wallpaper.id)}
                                title="删除壁纸"
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </CardActions>
                          </Card>
                        </Grid>
                      ))}
                    </Grid>
                  )}
                </Box>
              </Box>
            </Box>
          </Paper>
        </GitHubStarWarning>
      </Box>

      {/* 颜色选择对话框 */}
      <ColorPickerDialog
        open={colorDialog.open}
        onClose={() => setColorDialog({ ...colorDialog, open: false })}
        color={colorDialog.color}
        onChange={handleColorChange}
        title={colorDialog.title}
      />

      {/* 壁纸设置对话框 */}
      <Dialog open={showSettings} onClose={() => setShowSettings(false)} maxWidth="xs" fullWidth>
        <DialogTitle>壁纸设置</DialogTitle>
        <DialogContent>
          <Box sx={{ mb: 3, mt: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              显示模式
            </Typography>
            <RadioGroup
              row
              value={editSettings.wallpaperMode}
              onChange={e => handleWallpaperSettingChange('wallpaperMode', e.target.value)}
              sx={{ display: 'flex', justifyContent: 'space-between' }}
            >
              {WALLPAPER_MODES.map(mode => (
                <FormControlLabel
                  key={mode.value}
                  value={mode.value}
                  control={<Radio size="small" />}
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', flexDirection: 'column' }}>
                      {mode.icon}
                      <Typography variant="caption">{mode.label}</Typography>
                    </Box>
                  }
                  sx={{ mr: 0.5 }}
                />
              ))}
            </RadioGroup>
          </Box>

          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              模糊程度: {editSettings.wallpaperBlur}px
            </Typography>
            <Slider
              value={editSettings.wallpaperBlur}
              onChange={(_, value) =>
                handleWallpaperSettingChange('wallpaperBlur', value as number)
              }
              min={0}
              max={20}
              step={1}
              valueLabelDisplay="auto"
            />
          </Box>

          <Box sx={{ mb: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              暗度: {editSettings.wallpaperDim}%
            </Typography>
            <Slider
              value={editSettings.wallpaperDim}
              onChange={(_, value) => handleWallpaperSettingChange('wallpaperDim', value as number)}
              min={0}
              max={80}
              step={1}
              valueLabelDisplay="auto"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={resetWallpaperSettings} startIcon={<RefreshIcon />} color="inherit">
            重置
          </Button>
          <Button onClick={() => setShowSettings(false)}>取消</Button>
          <Button
            variant="contained"
            onClick={applyWallpaperSettings}
            startIcon={<SaveIcon />}
            sx={BUTTON_VARIANTS.primary.styles}
          >
            应用设置
          </Button>
        </DialogActions>
      </Dialog>

      {/* 壁纸预览对话框 */}
      <Dialog
        open={!!previewWallpaper}
        onClose={() => setPreviewWallpaper(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>壁纸预览</DialogTitle>
        <DialogContent sx={{ position: 'relative', minHeight: 400 }}>
          {previewWallpaper && (
            <Box
              component="img"
              src={previewWallpaper.url}
              alt={previewWallpaper.filename}
              sx={{
                width: '100%',
                objectFit: 'contain',
                maxHeight: '70vh',
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'divider',
              }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewWallpaper(null)}>关闭</Button>
          {previewWallpaper && (
            <>
              <Button
                color="error"
                onClick={() => {
                  handleDeleteWallpaper(previewWallpaper.id)
                  setPreviewWallpaper(null)
                }}
                startIcon={<DeleteIcon />}
              >
                删除
              </Button>
              <Button
                variant="contained"
                onClick={() => {
                  applyWallpaper(previewWallpaper)
                  setPreviewWallpaper(null)
                }}
                sx={BUTTON_VARIANTS.primary.styles}
              >
                应用到{wallpaperTab === 0 ? '登录页' : '主布局'}
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  )
}
