import React, { useEffect, useState } from 'react'
import {
  Box,
  Button,
  CircularProgress,
  Paper,
  Typography,
  styled,
  Stepper,
  Step,
  StepLabel,
  Divider,
} from '@mui/material'
import GitHubIcon from '@mui/icons-material/GitHub'
import RefreshIcon from '@mui/icons-material/Refresh'
import FavoriteIcon from '@mui/icons-material/Favorite'
import KeyIcon from '@mui/icons-material/Key'
import LoginIcon from '@mui/icons-material/Login'
import { useGitHubStarStore, StarCheckCallbacks, NotifyOptions } from '../../stores/githubStar'
import { BUTTON_VARIANTS } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'
import { useNavigate } from 'react-router-dom'

// 模糊容器
const BlurredContent = styled(Box)(() => ({
  position: 'relative',
  filter: 'blur(5px)',
  pointerEvents: 'none',
  opacity: 0.7,
  overflow: 'hidden',
}))

interface GitHubStarWarningProps {
  children: React.ReactNode
  title?: string
  message?: string
  onStarred?: () => void // 当用户已经Star时的回调
  onNotStarred?: () => void // 当用户未Star时的回调
  onError?: (error: unknown) => void // 发生错误时的回调
  resetDefaults?: boolean // 是否在未Star时重置默认设置
  lazyCheck?: boolean // 是否延迟检查（不在组件挂载时立即检查）
  searchParam?: string // 需要在系统设置中搜索的参数
}

/**
 * GitHub Star 提示组件
 * 邀请用户支持项目，并在用户未Star时显示模糊化内容
 */
const GitHubStarWarning: React.FC<GitHubStarWarningProps> = ({
  children,
  title = '欢迎支持开源项目',
  message = '通过Star开源仓库来支持我们，即可解锁高级自定义功能。您的支持是我们持续改进的动力！',
  onStarred,
  onNotStarred,
  onError,
  resetDefaults = true,
  lazyCheck = false, // 默认不懒加载，会在组件挂载时立即检查
  searchParam,
}) => {
  const { allStarred, checking, checkStarStatus } = useGitHubStarStore()
  const [hasCheckedOnce, setHasCheckedOnce] = useState(false)
  const notification = useNotification()
  const navigate = useNavigate()
  const [activeStep, setActiveStep] = useState(0)

  // 验证步骤
  const steps = [
    { label: 'Star项目', description: '前往GitHub给项目点Star' },
    { label: '获取API Key', description: '在NekroAI社区获取API Key' },
    { label: '配置验证', description: '填写API Key并验证Star状态' },
  ]

  // 创建通知回调对象
  const notifyCallbacks: NotifyOptions = {
    showSuccess: msg => notification.success(msg),
    showWarning: msg => notification.warning(msg),
    showError: msg => notification.error(msg),
  }

  // 检查Star状态的函数
  const handleCheckStatus = (
    force: boolean = false,
    clearCache: boolean = false,
    showNotification: boolean = false
  ) => {
    const callbacks: StarCheckCallbacks = {
      onStarred,
      onNotStarred,
      onError,
      resetDefaults,
      notify: showNotification ? notifyCallbacks : undefined,
    }

    checkStarStatus({ force, clearCache, showNotification }, callbacks)
    setHasCheckedOnce(true)
  }

  // 组件挂载时，如果不是懒加载，则检查一次状态
  useEffect(() => {
    // 如果不是懒加载且之前没有检查过，则进行检查
    if (!lazyCheck && !hasCheckedOnce && !checking) {
      handleCheckStatus(false, false, false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allStarred, checking, lazyCheck, hasCheckedOnce])

  // 前往配置页面
  const goToSettings = () => {
    // 导航到系统设置页并传递搜索参数
    navigate(`/settings/system${searchParam ? `?search=${searchParam}` : ''}`)
  }

  // 如果已检查且已Star，正常显示内容
  if (allStarred) {
    return <>{children}</>
  }

  return (
    <Box sx={{ position: 'relative' }}>
      {/* 模糊化的内容 */}
      <BlurredContent>{children}</BlurredContent>

      {/* Star 提示覆盖层 */}
      <Paper
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          p: 3,
          width: 'calc(100% - 64px)',
          maxWidth: 600,
          textAlign: 'center',
          boxShadow: 3,
          zIndex: 5,
          borderRadius: 2,
        }}
      >
        <FavoriteIcon color="primary" sx={{ mb: 1, fontSize: 28 }} />
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {message}
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontSize: '0.85rem' }}>
            Star是一种鼓励开发者的方式，它让我们知道这个项目对您有价值
          </Typography>
        </Typography>

        <Divider sx={{ my: 2 }} />

        {/* 步骤流程 */}
        <Box sx={{ maxWidth: 500, mx: 'auto', mb: 3 }}>
          <Stepper activeStep={activeStep} alternativeLabel>
            {steps.map(step => (
              <Step key={step.label}>
                <StepLabel>{step.label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
            <Typography variant="subtitle1" gutterBottom>
              {steps[activeStep].label}
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              {steps[activeStep].description}
            </Typography>

            {activeStep === 0 && (
              <Button
                variant="contained"
                color="primary"
                startIcon={<GitHubIcon />}
                onClick={() => {
                  window.open('https://github.com/KroMiose/nekro-agent', '_blank')
                  setActiveStep(1)
                }}
                sx={{ ...BUTTON_VARIANTS.primary.styles, mt: 1 }}
              >
                前往GitHub支持项目
              </Button>
            )}

            {activeStep === 1 && (
              <>
                <Typography variant="body2" paragraph sx={{ mt: 1 }}>
                  请使用GitHub账号登录NekroAI社区，在个人中心获取API Key
                </Typography>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<LoginIcon />}
                  onClick={() => {
                    window.open('https://community.nekro.ai/me', '_blank')
                    setActiveStep(2)
                  }}
                  sx={{ ...BUTTON_VARIANTS.primary.styles, mt: 1 }}
                >
                  前往NekroAI社区获取API Key
                </Button>
              </>
            )}

            {activeStep === 2 && (
              <>
                <Typography variant="body2" paragraph sx={{ mt: 1 }}>
                  将获取的 API Key 填入系统设置中的 "NekroAI 云服务 API Key"
                  字段并启用云服务，然后刷新验证状态 Key"字段并启用云服务，然后刷新验证状态
                </Typography>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<KeyIcon />}
                  onClick={goToSettings}
                  sx={{ ...BUTTON_VARIANTS.primary.styles, mt: 1, mr: 1 }}
                >
                  前往系统设置填写API Key
                </Button>
                <Button
                  variant="outlined"
                  color="primary"
                  startIcon={checking ? <CircularProgress size={20} /> : <RefreshIcon />}
                  onClick={() => handleCheckStatus(true, true, true)}
                  disabled={checking}
                  sx={{ mt: 1 }}
                >
                  {checking ? '检查中...' : '刷新验证状态'}
                </Button>
              </>
            )}
          </Box>
        </Box>

        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between' }}>
          <Button
            disabled={activeStep === 0}
            onClick={() => setActiveStep(prev => Math.max(0, prev - 1))}
          >
            上一步
          </Button>
          <Button
            disabled={activeStep === 2}
            onClick={() => setActiveStep(prev => Math.min(2, prev + 1))}
          >
            下一步
          </Button>
        </Box>

        {checking && (
          <Typography variant="caption" sx={{ display: 'block', mt: 2, color: 'text.secondary' }}>
            正在检查验证状态，请稍候...
          </Typography>
        )}
      </Paper>
    </Box>
  )
}

export default GitHubStarWarning
