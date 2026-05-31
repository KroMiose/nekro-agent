import { type ReactNode, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Alert,
  Autocomplete,
  Box,
  ButtonBase,
  CircularProgress,
  Collapse,
  FormControlLabel,
  InputAdornment,
  Link,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import { alpha } from '@mui/material/styles'
import {
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  CloudQueue as CloudQueueIcon,
  ContentCopy as ContentCopyIcon,
  DoneAll as DoneAllIcon,
  ExpandMore as ExpandMoreIcon,
  Hub as HubIcon,
  Language as LanguageIcon,
  Launch as LaunchIcon,
  Memory as MemoryIcon,
  NetworkCheck as NetworkCheckIcon,
  Psychology as PsychologyIcon,
  RocketLaunch as RocketLaunchIcon,
  Science as ScienceIcon,
  SettingsSuggest as SettingsSuggestIcon,
  SkipNext as SkipNextIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material'
import ActionButton from '../../components/common/ActionButton'
import IconActionButton from '../../components/common/IconActionButton'
import LocaleToggleButton from '../../components/common/LocaleToggleButton'
import ThemeToggleButton from '../../theme/ThemeToggleButton'
import { useNotification } from '../../hooks/useNotification'
import { useAuthStore } from '../../stores/auth'
import { useLocaleStore } from '../../stores/locale'
import { OPENAI_COMPAT_PROVIDERS, getLocalizedText } from '../../config/model-presets'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'
import { getAnimationDuration } from '../../theme/themeApi'
import { unifiedConfigApi, type ModelGroupTestItem } from '../../services/api/unified-config'
import {
  buildOobeInlineTestRequest,
  oobeApi,
  type OobeModelSettings,
  type OobeSystemSettings,
} from '../../services/api/oobe'

type OobeStep = 'welcome' | 'language' | 'system' | 'chat' | 'embedding' | 'finish'
type ModelEditMode = 'chat' | 'embedding'

interface ModelDraftProps {
  model: OobeModelSettings
  mode: ModelEditMode
  testResult: ModelGroupTestItem | null
  testing: boolean
  fetchingModels: boolean
  modelOptions: string[]
  onChange: (model: OobeModelSettings) => void
  onFetchModels: () => void
  onTest: () => void
}

interface LanguageOption {
  value: OobeSystemSettings['systemLang']
  title: string
  nativeName: string
  greeting: string
  sample: string
}

const steps: OobeStep[] = ['welcome', 'language', 'system', 'chat', 'embedding', 'finish']

const animationEase = [0.4, 0, 0.2, 1] as const

const helloWords = [
  '你好',         // 简体中文
  'Hello',        // 英语
  'こんにちは',     // 日语
  'Bonjour',      // 法语
  '哈囉',         // 繁体中文 (港台)
  'Hola',         // 西班牙语
  '안녕하세요',      // 韩语
  'Guten Tag',    // 德语
  '您好',         // 中文敬称
  'Ciao',         // 意大利语
  'Olá',          // 葡萄牙语
  'Xin chào',     // 越南语
  'Привет',       // 俄语
  'สวัสดี',        // 泰语
  'Merhaba',      // 土耳其语
  'مرحبا',        // 阿拉伯语
  'नमस्ते',        // 印地语
  'Shalom',       // 希伯来语
  'Hallå',        // 瑞典语
  'Aloha',        // 夏威夷语
  'Szia',         // 匈牙利语
  'Hei',          // 芬兰语
  'Sawubona',     // 祖鲁语
  'Jambo',        // 斯瓦希里语
  'Ahoj',         // 捷克语
  'Kamusta',      // 菲律宾语
  'Kia Ora',      // 毛利语
  'Goddag',       // 丹麦语
  'Bună ziua',    // 罗马尼亚语
  'Dobry dzień',  // 波兰语
  'Namaste',      // 尼泊尔语
]

const languageOptions: LanguageOption[] = [
  {
    value: 'zh-CN',
    title: '简体中文',
    nativeName: 'Chinese',
    greeting: '你好',
    sample: '系统基础 · 主聊天模型 · Embedding 模型',
  },
  {
    value: 'en-US',
    title: 'English',
    nativeName: 'English',
    greeting: 'Hello',
    sample: 'System Basics · Primary Chat Model · Embedding Model',
  },
]

const MotionPaper = motion(Paper)

const getHelloFontSize = (word: string) => {
  if (word.length >= 5) {
    return { xs: 60, sm: 112, md: 146, lg: 174 }
  }
  if (word.length >= 4) {
    return { xs: 68, sm: 126, md: 166, lg: 192 }
  }
  return { xs: 82, sm: 150, md: 210 }
}

const defaultChatModel: OobeModelSettings = {
  groupName: 'default',
  CHAT_MODEL: 'gemini-2.5-flash',
  CHAT_PROXY: '',
  BASE_URL: 'https://api.nekro.ai/v1',
  API_KEY: '',
  MODEL_TYPE: 'chat',
  TEMPERATURE: null,
  TOP_P: null,
  TOP_K: null,
  PRESENCE_PENALTY: null,
  FREQUENCY_PENALTY: null,
  EXTRA_BODY: null,
  ENABLE_VISION: true,
  ENABLE_COT: true,
}

const defaultEmbeddingModel: OobeModelSettings = {
  groupName: 'text-embedding',
  CHAT_MODEL: 'text-embedding-v3',
  CHAT_PROXY: '',
  BASE_URL: 'https://api.nekro.ai/v1',
  API_KEY: '',
  MODEL_TYPE: 'embedding',
  TEMPERATURE: null,
  TOP_P: null,
  TOP_K: null,
  PRESENCE_PENALTY: null,
  FREQUENCY_PENALTY: null,
  EXTRA_BODY: null,
  ENABLE_VISION: false,
  ENABLE_COT: false,
}

const defaultSystemSettings: OobeSystemSettings = {
  systemLang: 'zh-CN',
  enableNekroCloud: true,
  nekroCloudApiKey: '',
  defaultProxy: '',
}

const isModelReady = (model: OobeModelSettings) =>
  Boolean(model.groupName.trim() && model.CHAT_MODEL.trim() && model.BASE_URL.trim() && model.API_KEY.trim())

function isValidJsonOrEmpty(value: string | null | undefined): boolean {
  if (!value?.trim()) return true
  try {
    JSON.parse(value)
    return true
  } catch {
    return false
  }
}

function readModelsResponse(payload: unknown): string[] {
  const source = payload as {
    data?: Array<string | { id?: string }>
    models?: Array<string | { id?: string }>
  }
  const pick = (items: Array<string | { id?: string }> | undefined) =>
    (items ?? [])
      .map(item => (typeof item === 'string' ? item : item.id))
      .filter((item): item is string => Boolean(item))

  return Array.from(new Set([...pick(source.data), ...pick(source.models)])).sort()
}

function OobePageContent() {
  const { t } = useTranslation('settings')
  const navigate = useNavigate()
  const notification = useNotification()
  const theme = useTheme()
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const { logout } = useAuthStore()
  const { setLocaleLocal } = useLocaleStore()

  const [activeStep, setActiveStep] = useState<OobeStep>('welcome')
  const [systemSettings, setSystemSettings] = useState<OobeSystemSettings>(defaultSystemSettings)
  const [chatModel, setChatModel] = useState<OobeModelSettings>(defaultChatModel)
  const [embeddingModel, setEmbeddingModel] = useState<OobeModelSettings>(defaultEmbeddingModel)
  const [memoryEmbeddingDimension, setMemoryEmbeddingDimension] = useState(1024)
  const [kbEmbeddingDimension, setKbEmbeddingDimension] = useState(1024)
  const [chatModelOptions, setChatModelOptions] = useState<string[]>([])
  const [embeddingModelOptions, setEmbeddingModelOptions] = useState<string[]>([])
  const [chatTestResult, setChatTestResult] = useState<ModelGroupTestItem | null>(null)
  const [embeddingTestResult, setEmbeddingTestResult] = useState<ModelGroupTestItem | null>(null)
  const [showCloudKey, setShowCloudKey] = useState(false)

  const setupQuery = useQuery({
    queryKey: ['oobe-setup-state'],
    queryFn: oobeApi.getSetupState,
  })

  useEffect(() => {
    const state = setupQuery.data
    if (!state) return

    setSystemSettings(state.system)
    setChatModel(state.chatModel)
    setEmbeddingModel(state.embeddingModel)
    setMemoryEmbeddingDimension(state.memoryEmbeddingDimension)
    setKbEmbeddingDimension(state.kbEmbeddingDimension)
  }, [setupQuery.data])

  const currentStepIndex = steps.indexOf(activeStep)
  const isCompactContentStep = activeStep === 'language' || activeStep === 'system'
  const contentFrameMaxWidth = isCompactContentStep ? 760 : 920
  const contentFramePadding = isCompactContentStep ? 0 : isSmall ? 10 : 20
  const contentFrameRadius = isCompactContentStep ? 0 : isSmall ? 24 : 32
  const contentFrameBackground = isCompactContentStep
    ? alpha(theme.palette.background.paper, 0)
    : alpha(theme.palette.background.paper, 0.46)
  const contentFrameShadow = isCompactContentStep
    ? `inset 0 1px 0 ${alpha(theme.palette.common.white, 0)}`
    : `inset 0 1px 0 ${alpha(theme.palette.common.white, 0.24)}`
  const mainFrameHeight = {
    xs: 'calc(100dvh - 16px)',
    sm: 'calc(100dvh - 24px)',
    md: 'min(940px, calc(100dvh - 32px))',
  }

  const stepMeta = useMemo(
    () => ({
      welcome: {
        title: t('oobe.steps.welcome.title'),
        description: t('oobe.steps.welcome.description'),
        icon: <RocketLaunchIcon />,
      },
      language: {
        title: t('oobe.steps.language.title'),
        description: t('oobe.steps.language.description'),
        icon: <LanguageIcon />,
      },
      system: {
        title: t('oobe.steps.system.title'),
        description: t('oobe.steps.system.description'),
        icon: <SettingsSuggestIcon />,
      },
      chat: {
        title: t('oobe.steps.chat.title'),
        description: t('oobe.steps.chat.description'),
        icon: <PsychologyIcon />,
      },
      embedding: {
        title: t('oobe.steps.embedding.title'),
        description: t('oobe.steps.embedding.description'),
        icon: <MemoryIcon />,
      },
      finish: {
        title: t('oobe.steps.finish.title'),
        description: t('oobe.steps.finish.description'),
        icon: <DoneAllIcon />,
      },
    }),
    [t],
  )

  const completionMutation = useMutation({
    mutationFn: () =>
      oobeApi.completeSetup(
        systemSettings,
        chatModel,
        embeddingModel,
        memoryEmbeddingDimension,
        kbEmbeddingDimension,
      ),
    onSuccess: () => {
      setLocaleLocal(systemSettings.systemLang)
      notification.success(t('oobe.notifications.completeSuccess'))
      navigate('/dashboard', { replace: true })
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('oobe.notifications.completeFailed'))
    },
  })

  const skipMutation = useMutation({
    mutationFn: oobeApi.markSkipped,
    onSuccess: () => {
      notification.info(t('oobe.notifications.skipped'))
      navigate('/dashboard', { replace: true })
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('oobe.notifications.skipFailed'))
    },
  })

  const testChatMutation = useMutation({
    mutationFn: () => unifiedConfigApi.testModelGroupInline(buildOobeInlineTestRequest(chatModel, 'chat')),
    onSuccess: result => {
      setChatTestResult(result)
      notification[result.success ? 'success' : 'warning'](
        result.success ? t('oobe.notifications.testPassed') : t('oobe.notifications.testFailed'),
      )
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('oobe.notifications.testError'))
    },
  })

  const testEmbeddingMutation = useMutation({
    mutationFn: () => unifiedConfigApi.testModelGroupInline(buildOobeInlineTestRequest(embeddingModel, 'embedding')),
    onSuccess: result => {
      setEmbeddingTestResult(result)
      notification[result.success ? 'success' : 'warning'](
        result.success ? t('oobe.notifications.testPassed') : t('oobe.notifications.testFailed'),
      )
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('oobe.notifications.testError'))
    },
  })

  const fetchChatModelsMutation = useMutation({
    mutationFn: () => unifiedConfigApi.fetchModels({
      base_url: chatModel.BASE_URL,
      api_key: chatModel.API_KEY,
      proxy_url: chatModel.CHAT_PROXY || undefined,
    }),
    onSuccess: models => {
      setChatModelOptions(models)
      notification.success(t('oobe.notifications.fetchSuccess', { count: models.length }))
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('oobe.notifications.fetchFailed'))
    },
  })

  const fetchEmbeddingModelsMutation = useMutation({
    mutationFn: () => unifiedConfigApi.fetchModels({
      base_url: embeddingModel.BASE_URL,
      api_key: embeddingModel.API_KEY,
      proxy_url: embeddingModel.CHAT_PROXY || undefined,
    }),
    onSuccess: models => {
      setEmbeddingModelOptions(models)
      notification.success(t('oobe.notifications.fetchSuccess', { count: models.length }))
    },
    onError: error => {
      notification.error(error instanceof Error ? error.message : t('oobe.notifications.fetchFailed'))
    },
  })

  const handleClientFetchModels = async (mode: ModelEditMode) => {
    const model = mode === 'chat' ? chatModel : embeddingModel
    const setOptions = mode === 'chat' ? setChatModelOptions : setEmbeddingModelOptions
    if (!model.BASE_URL || !model.API_KEY) {
      notification.warning(t('oobe.validation.modelFetchRequired'))
      return
    }

    const url = `${model.BASE_URL.trim().replace(/\/$/, '')}/models`
    try {
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${model.API_KEY}`,
          'Content-Type': 'application/json',
        },
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const models = readModelsResponse(await response.json())
      setOptions(models)
      notification.success(t('oobe.notifications.fetchSuccess', { count: models.length }))
    } catch (error) {
      notification.error(error instanceof Error ? error.message : t('oobe.notifications.fetchFailed'))
    }
  }

  const runFetchModels = (mode: ModelEditMode) => {
    const model = mode === 'chat' ? chatModel : embeddingModel
    if (!model.BASE_URL || !model.API_KEY) {
      notification.warning(t('oobe.validation.modelFetchRequired'))
      return
    }

    if (model.CHAT_PROXY.trim()) {
      if (mode === 'chat') {
        fetchChatModelsMutation.mutate()
      } else {
        fetchEmbeddingModelsMutation.mutate()
      }
      return
    }

    void handleClientFetchModels(mode)
  }

  const canComplete = isModelReady(chatModel)
    && isModelReady(embeddingModel)
    && memoryEmbeddingDimension > 0
    && kbEmbeddingDimension > 0
    && isValidJsonOrEmpty(chatModel.EXTRA_BODY)
    && isValidJsonOrEmpty(embeddingModel.EXTRA_BODY)

  const goNext = () => {
    const nextStep = steps[Math.min(currentStepIndex + 1, steps.length - 1)]
    setActiveStep(nextStep)
  }

  const goBack = () => {
    const nextStep = steps[Math.max(currentStepIndex - 1, 0)]
    setActiveStep(nextStep)
  }

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const renderStepPanel = () => {
    switch (activeStep) {
      case 'language':
        return (
          <LanguageStep
            settings={systemSettings}
            onChange={(nextSettings) => {
              setSystemSettings(nextSettings)
              setLocaleLocal(nextSettings.systemLang)
            }}
          />
        )
      case 'system':
        return (
          <SystemStep
            settings={systemSettings}
            showCloudKey={showCloudKey}
            onToggleCloudKey={() => setShowCloudKey(value => !value)}
            onChange={setSystemSettings}
          />
        )
      case 'chat':
        return (
          <ModelDraft
            model={chatModel}
            mode="chat"
            testResult={chatTestResult}
            testing={testChatMutation.isPending}
            fetchingModels={fetchChatModelsMutation.isPending}
            modelOptions={chatModelOptions}
            onChange={(nextModel) => {
              setChatModel(nextModel)
              setChatTestResult(null)
            }}
            onFetchModels={() => runFetchModels('chat')}
            onTest={() => testChatMutation.mutate()}
          />
        )
      case 'embedding':
        return (
          <EmbeddingStep
            model={embeddingModel}
            memoryDimension={memoryEmbeddingDimension}
            kbDimension={kbEmbeddingDimension}
            testResult={embeddingTestResult}
            testing={testEmbeddingMutation.isPending}
            fetchingModels={fetchEmbeddingModelsMutation.isPending}
            modelOptions={embeddingModelOptions}
            onModelChange={(nextModel) => {
              setEmbeddingModel(nextModel)
              setEmbeddingTestResult(null)
            }}
            onMemoryDimensionChange={setMemoryEmbeddingDimension}
            onKbDimensionChange={setKbEmbeddingDimension}
            onFetchModels={() => runFetchModels('embedding')}
            onTest={() => testEmbeddingMutation.mutate()}
          />
        )
      case 'finish':
        return (
          <FinishStep
            system={systemSettings}
            chatModel={chatModel}
            embeddingModel={embeddingModel}
            memoryDimension={memoryEmbeddingDimension}
            kbDimension={kbEmbeddingDimension}
            canComplete={canComplete}
          />
        )
      default:
        return null
    }
  }

  if (setupQuery.isLoading) {
    return (
      <PageShell>
        <Box
          sx={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <CircularProgress />
        </Box>
      </PageShell>
    )
  }

  return (
    <PageShell>
      <AnimatePresence initial={false} mode="wait">
        {activeStep === 'welcome' ? (
          <motion.div
            key="welcome-step-wrapper"
            initial={{ opacity: 1, scale: 1 }}
            exit={{
              opacity: 0,
              scale: 0.94,
              y: -24,
              filter: 'blur(8px)',
              transition: { duration: 0.45, ease: animationEase },
            }}
            style={{ width: '100%' }}
          >
            <WelcomeStep onContinue={() => setActiveStep('language')} />
          </motion.div>
        ) : (
          <Box
            key="oobe-main-frame"
            component={motion.div}
            initial={{ opacity: 0, y: 35, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.98 }}
            transition={{ duration: 0.5, ease: animationEase }}
            sx={{
              minHeight: '100vh',
              p: { xs: 1, sm: 1.5, md: 2 },
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxSizing: 'border-box',
              width: '100%',
            }}
          >
            <MotionPaper
              layout
              elevation={0}
              transition={{
                layout: { duration: getAnimationDuration(0.42), ease: animationEase },
                duration: getAnimationDuration(0.42),
                ease: animationEase,
              }}
              sx={{
                width: 'min(100%, 1280px)',
                height: mainFrameHeight,
                minHeight: mainFrameHeight,
                maxHeight: mainFrameHeight,
                borderRadius: { xs: 4, md: 5 },
                overflow: 'hidden',
                position: 'relative',
                display: 'grid',
                gridTemplateRows: 'auto auto minmax(0, 1fr) auto',
                p: { xs: 2, sm: 2.5, md: 3 },
                background: `linear-gradient(145deg, ${alpha(theme.palette.background.paper, 0.92)}, ${alpha(theme.palette.primary.main, 0.12)})`,
                border: `1px solid ${alpha(theme.palette.common.white, 0.42)}`,
                boxShadow: `0 28px 90px ${alpha(theme.palette.primary.main, 0.2)}`,
              }}
            >
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                spacing={1}
                sx={{
                  zIndex: 1,
                  minHeight: 44,
                  px: { xs: 0.25, sm: 0.5 },
                }}
              >
                <Stack direction="row" spacing={0.75} alignItems="center">
                  {steps.slice(1).map(step => (
                    <Box
                      key={step}
                      sx={{
                        width: step === activeStep ? 30 : 9,
                        height: 9,
                        borderRadius: 999,
                        backgroundColor: step === activeStep
                          ? theme.palette.primary.main
                          : alpha(theme.palette.primary.main, 0.2),
                        boxShadow: step === activeStep ? `0 6px 18px ${alpha(theme.palette.primary.main, 0.28)}` : 'none',
                        transition: 'all 0.24s ease',
                      }}
                    />
                  ))}
                </Stack>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <ActionButton
                    tone="secondary"
                    startIcon={skipMutation.isPending ? <CircularProgress size={16} /> : <SkipNextIcon />}
                    onClick={() => skipMutation.mutate()}
                    disabled={skipMutation.isPending || completionMutation.isPending}
                    sx={{
                      height: 38,
                      minWidth: { xs: 82, sm: 96 },
                      borderRadius: 999,
                      px: { xs: 1.25, sm: 1.75 },
                      backgroundColor: alpha(theme.palette.background.paper, 0.62),
                      boxShadow: `0 10px 26px ${alpha(theme.palette.text.primary, 0.06)}`,
                    }}
                  >
                    {t('oobe.actions.skip')}
                  </ActionButton>
                  {!isSmall && <LocaleToggleButton />}
                  <ThemeToggleButton size="small" />
                  <IconActionButton aria-label="Exit" size="small" onClick={handleLogout}>
                    <ArrowForwardIcon sx={{ transform: 'rotate(180deg)' }} />
                  </IconActionButton>
                </Stack>
              </Stack>

              <Box sx={{ textAlign: 'center', pt: { xs: 3.5, md: 4.5 }, pb: { xs: 2, md: 3 }, zIndex: 1 }}>
                <Stack spacing={1.2} alignItems="center">
                  <Box
                    sx={{
                      width: { xs: 52, md: 58 },
                      height: { xs: 52, md: 58 },
                      borderRadius: 3,
                      display: 'grid',
                      placeItems: 'center',
                      color: theme.palette.primary.main,
                      backgroundColor: alpha(theme.palette.primary.main, 0.12),
                      boxShadow: `inset 0 1px 0 ${alpha(theme.palette.common.white, 0.34)}`,
                      '& svg': { fontSize: { xs: 28, md: 32 } },
                    }}
                  >
                    {stepMeta[activeStep].icon}
                  </Box>
                  <Typography variant={isSmall ? 'h5' : 'h4'} sx={{ fontWeight: 900, letterSpacing: 0 }}>
                    {stepMeta[activeStep].title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 520 }}>
                    {stepMeta[activeStep].description}
                  </Typography>
                </Stack>
              </Box>

              <Box
                sx={{
                  minHeight: 0,
                  overflow: 'auto',
                  px: { xs: 0, md: 6 },
                  pt: { xs: 1.5, md: 2.5 },
                  pb: { xs: 1, md: 2 },
                  zIndex: 1,
                }}
              >
                <Box
                  sx={{
                    width: '100%',
                    display: 'flex',
                    justifyContent: 'center',
                  }}
                >
                  <motion.div
                    layout
                    animate={{
                      maxWidth: contentFrameMaxWidth,
                      padding: contentFramePadding,
                      borderRadius: contentFrameRadius,
                      backgroundColor: contentFrameBackground,
                      boxShadow: contentFrameShadow,
                    }}
                    transition={{
                      duration: getAnimationDuration(0.42),
                      ease: animationEase,
                      layout: { duration: getAnimationDuration(0.42), ease: animationEase },
                    }}
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      overflow: 'hidden',
                    }}
                  >
                    <AnimatePresence initial={false} mode="popLayout">
                      <motion.div
                        key={activeStep}
                        layout
                        initial={{ opacity: 0, y: 14, scale: 0.985 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -8, scale: 0.992 }}
                        transition={{
                          duration: getAnimationDuration(0.22),
                          ease: animationEase,
                          layout: { duration: getAnimationDuration(0.42), ease: animationEase },
                        }}
                        style={{ width: '100%' }}
                      >
                        {renderStepPanel()}
                      </motion.div>
                    </AnimatePresence>
                  </motion.div>
                </Box>
              </Box>

              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                spacing={1.5}
                sx={{
                  pt: { xs: 1.25, md: 2 },
                  zIndex: 1,
                  minHeight: 64,
                }}
              >
                <IconActionButton
                  aria-label={t('oobe.actions.back')}
                  onClick={goBack}
                  disabled={activeStep === 'language' || completionMutation.isPending}
                  sx={{
                    width: 50,
                    height: 46,
                    borderRadius: 999,
                    border: `1px solid ${alpha(theme.palette.text.primary, 0.22)}`,
                    backgroundColor: alpha(theme.palette.background.paper, 0.28),
                  }}
                >
                  <ArrowBackIcon />
                </IconActionButton>
                <Stack direction="row" spacing={1} alignItems="center">
                  {activeStep === 'finish' ? (
                    <ActionButton
                      tone="primary"
                      startIcon={completionMutation.isPending ? <CircularProgress size={16} /> : <DoneAllIcon />}
                      onClick={() => completionMutation.mutate()}
                      disabled={!canComplete || completionMutation.isPending}
                      sx={{
                        minWidth: 138,
                        height: 50,
                        borderRadius: 999,
                        boxShadow: `0 14px 34px ${alpha(theme.palette.primary.main, 0.3)}`,
                      }}
                    >
                      {t('oobe.actions.complete')}
                    </ActionButton>
                  ) : (
                    <IconActionButton
                      tone="primary"
                      aria-label={t('oobe.actions.next')}
                      onClick={goNext}
                      disabled={completionMutation.isPending}
                      sx={{
                        width: 72,
                        height: 52,
                        borderRadius: 999,
                        color: theme.palette.primary.contrastText,
                        backgroundColor: theme.palette.primary.main,
                        boxShadow: `0 14px 34px ${alpha(theme.palette.primary.main, 0.34)}`,
                        '&:hover': {
                          backgroundColor: theme.palette.primary.dark,
                        },
                        '& svg': { fontSize: 30 },
                      }}
                    >
                      <ArrowForwardIcon />
                    </IconActionButton>
                  )}
                </Stack>
              </Stack>
            </MotionPaper>
          </Box>
        )}
      </AnimatePresence>
    </PageShell>
  )
}

function PageShell({ children }: { children: ReactNode }) {
  const theme = useTheme()
  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.08)}, ${alpha(theme.palette.secondary.main, 0.06)} 46%, ${theme.palette.background.default})`,
        color: 'text.primary',
      }}
    >
      {children}
    </Box>
  )
}

function WelcomeStep({
  onContinue,
}: {
  onContinue: () => void
}) {
  const theme = useTheme()
  const [displayText, setDisplayText] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [loopNum, setLoopNum] = useState(0)
  const [typingSpeed, setTypingSpeed] = useState(120)

  // 优雅的过渡与 AI 载入状态
  const [isExiting, setIsExiting] = useState(false)
  const [showLoader, setShowLoader] = useState(false)

  useEffect(() => {
    if (isExiting) return // 转场中停止打字计时器，节省开销

    const handleType = () => {
      const i = loopNum % helloWords.length
      const fullText = helloWords[i]

      if (!isDeleting) {
        // 逐字输入
        const nextText = fullText.substring(0, displayText.length + 1)
        setDisplayText(nextText)
        // 打字速度在 100ms - 150ms 之间微小浮动，增加自然度
        setTypingSpeed(100 + Math.random() * 50)

        if (nextText === fullText) {
          // 输入完毕，停顿 1.5 秒
          setTypingSpeed(1500)
          setIsDeleting(true)
        }
      } else {
        // 逐字删除
        const nextText = fullText.substring(0, displayText.length - 1)
        setDisplayText(nextText)
        // 删除速度比输入更快，约 60ms
        setTypingSpeed(60)

        if (nextText === '') {
          // 删除完毕，停顿 300ms 后切换到下一个词
          setIsDeleting(false)
          setLoopNum(loopNum + 1)
          setTypingSpeed(300)
        }
      }
    }

    const timer = window.setTimeout(handleType, typingSpeed)
    return () => window.clearTimeout(timer)
  }, [displayText, isDeleting, loopNum, typingSpeed, isExiting])

  const currentWord = helloWords[loopNum % helloWords.length]
  const helloFontSize = getHelloFontSize(currentWord)

  const handleStartTransition = () => {
    setIsExiting(true)

    // 250ms 后，文字模糊淡出完毕，展示优雅的 AI 配置加载条
    window.setTimeout(() => {
      setShowLoader(true)
    }, 250)

    // 再持续 950ms (总计 1.2 秒) 的缓冲，极度顺滑地转场至系统语言设置步骤
    window.setTimeout(() => {
      onContinue()
    }, 1200)
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        p: { xs: 1.5, sm: 2.5, md: 4 },
        boxSizing: 'border-box',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Paper
        elevation={0}
        sx={{
          width: 'min(100%, 1280px)',
          minHeight: { xs: 'calc(100vh - 24px)', sm: 'calc(100vh - 40px)', md: 'min(760px, calc(100vh - 64px))' },
          borderRadius: { xs: 4, md: 5 },
          overflow: 'hidden',
          position: 'relative',
          display: 'grid',
          gridTemplateRows: 'minmax(0, 1fr)',
          p: { xs: 2, sm: 2.5, md: 3 },
          background: `linear-gradient(145deg, ${alpha(theme.palette.background.paper, 0.92)}, ${alpha(theme.palette.primary.main, 0.13)})`,
          border: `1px solid ${alpha(theme.palette.common.white, 0.42)}`,
          boxShadow: `0 28px 90px ${alpha(theme.palette.primary.main, 0.2)}`,
        }}
      >
        <Box
          sx={{
            minHeight: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            position: 'relative',
            zIndex: 1,
          }}
        >
          <AnimatePresence mode="wait">
            {showLoader ? (
              <motion.div
                key="loader"
                initial={{ opacity: 0, scale: 0.9, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.35, ease: animationEase }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '24px',
                }}
              >
                <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                  <CircularProgress
                    size={56}
                    thickness={4.5}
                    sx={{
                      color: theme.palette.primary.main,
                      filter: `drop-shadow(0 0 12px ${alpha(theme.palette.primary.main, 0.55)})`,
                    }}
                  />
                </Box>
                <Typography
                  variant="body2"
                  sx={{
                    color: 'text.secondary',
                    fontWeight: 700,
                    letterSpacing: '0.8px',
                    animation: 'pulse 1.6s infinite ease-in-out',
                    '@keyframes pulse': {
                      '0%, 100%': { opacity: 0.55, transform: 'scale(0.985)' },
                      '50%': { opacity: 1, transform: 'scale(1.015)' },
                    },
                  }}
                >
                  请稍候 Please hang on for a brief second...
                </Typography>
              </motion.div>
            ) : (
              <motion.div
                key="welcome-text"
                animate={{
                  opacity: isExiting ? 0 : 1,
                  scale: isExiting ? 0.94 : 1,
                  filter: isExiting ? 'blur(10px)' : 'blur(0px)'
                }}
                transition={{ duration: 0.3, ease: animationEase }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Box
                  sx={{
                    width: '100%',
                    maxWidth: { xs: 760, md: 1000, lg: 1080 },
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    px: { xs: 2, sm: 3, md: 4 },
                  }}
                >
                  <Box
                    sx={{
                      minHeight: { xs: 116, sm: 178, md: 230 },
                      minWidth: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '100%',
                    }}
                  >
                    <Typography
                      component={motion.h1}
                      initial={{ opacity: 0, scale: 0.96 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.6, ease: animationEase }}
                      sx={{
                        m: 0,
                        fontSize: helloFontSize,
                        lineHeight: 0.88,
                        fontWeight: 900,
                        letterSpacing: 0,
                        color: theme.palette.primary.main,
                        textShadow: `0 24px 62px ${alpha(theme.palette.primary.main, 0.25)}`,
                        wordBreak: 'keep-all',
                        whiteSpace: 'nowrap',
                        maxWidth: '100%',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <span>{displayText}</span>
                    </Typography>
                  </Box>
                </Box>
              </motion.div>
            )}
          </AnimatePresence>
        </Box>

        <AnimatePresence>
          {!isExiting && (
            <Box
              component={motion.div}
              initial={{ opacity: 0, scale: 0.85, x: '-50%' }}
              animate={{ opacity: 1, scale: 1, x: '-50%' }}
              exit={{ opacity: 0, scale: 0.8, filter: 'blur(4px)', x: '-50%' }}
              transition={{ duration: 0.25 }}
              sx={{
                position: 'absolute',
                bottom: { xs: 80, sm: 120, md: 160 },
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: 2
              }}
            >
              <IconActionButton
                tone="primary"
                aria-label="Continue"
                onClick={handleStartTransition}
                sx={{
                  width: { xs: 68, md: 76 },
                  height: { xs: 52, md: 60 },
                  borderRadius: 999,
                  color: theme.palette.primary.contrastText,
                  backgroundColor: theme.palette.primary.main,
                  boxShadow: `0 14px 34px ${alpha(theme.palette.primary.main, 0.3)}`,
                  '&:hover': {
                    backgroundColor: theme.palette.primary.dark,
                    boxShadow: `0 14px 34px ${alpha(theme.palette.primary.main, 0.3)}`,
                  },
                  '& svg': { fontSize: { xs: 28, md: 32 } },
                }}
              >
                <ArrowForwardIcon />
              </IconActionButton>
            </Box>
          )}
        </AnimatePresence>
      </Paper>
    </Box>
  )
}

function LanguageStep({
  settings,
  onChange,
}: {
  settings: OobeSystemSettings
  onChange: (settings: OobeSystemSettings) => void
}) {
  const theme = useTheme()

  return (
    <Box
      sx={{
        minHeight: { xs: 300, sm: 360, md: 420 },
        display: 'grid',
        placeItems: 'center',
        px: { xs: 0.5, sm: 1, md: 2 },
        py: { xs: 1, md: 2 },
      }}
    >
      <Box
        sx={{
          width: 'min(100%, 820px)',
        }}
      >
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
            gap: 1.75,
          }}
        >
          {languageOptions.map(option => {
            const selected = option.value === settings.systemLang
            return (
              <ButtonBase
                key={option.value}
                onClick={() => onChange({ ...settings, systemLang: option.value })}
                sx={{
                  borderRadius: 3,
                  textAlign: 'left',
                  display: 'block',
                  transition: 'box-shadow 0.22s ease, background-color 0.22s ease',
                  '&:hover': {
                    boxShadow: `0 18px 46px ${alpha(theme.palette.primary.main, 0.12)}`,
                  },
                }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    minHeight: { xs: 138, sm: 172 },
                    height: '100%',
                    borderRadius: 3,
                    p: { xs: 2, sm: 2.5 },
                    display: 'grid',
                    gridTemplateRows: 'auto 1fr auto',
                    gap: 1.5,
                    position: 'relative',
                    overflow: 'hidden',
                    background: selected
                      ? `linear-gradient(150deg, ${alpha(theme.palette.primary.main, 0.14)}, ${alpha(theme.palette.background.paper, 0.92)} 38%, ${alpha(theme.palette.background.paper, 0.78)})`
                      : `linear-gradient(150deg, ${alpha(theme.palette.background.paper, 0.76)}, ${alpha(theme.palette.background.paper, 0.5)})`,
                    border: `1px solid ${alpha(theme.palette.common.white, selected ? 0.66 : 0.44)}`,
                    boxShadow: selected
                      ? `0 24px 58px ${alpha(theme.palette.primary.main, 0.18)}, inset 0 1px 0 ${alpha(theme.palette.common.white, 0.76)}`
                      : `0 14px 34px ${alpha(theme.palette.text.primary, 0.06)}, inset 0 1px 0 ${alpha(theme.palette.common.white, 0.54)}`,
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      inset: '0 auto 0 0',
                      width: 5,
                      backgroundColor: selected ? theme.palette.primary.main : 'transparent',
                      opacity: selected ? 0.9 : 0,
                    },
                  }}
                >
                  <Stack direction="row" alignItems="center" spacing={1.5}>
                    <Box
                      sx={{
                        width: 42,
                        height: 42,
                        borderRadius: 2,
                        display: 'grid',
                        placeItems: 'center',
                        color: selected ? theme.palette.primary.contrastText : theme.palette.primary.main,
                        backgroundColor: selected
                          ? theme.palette.primary.main
                          : alpha(theme.palette.primary.main, 0.1),
                      }}
                    >
                      <LanguageIcon />
                    </Box>
                  </Stack>
                  <Stack spacing={0.5} justifyContent="center">
                    <Typography
                      sx={{
                        fontSize: { xs: 38, sm: 48, md: 56 },
                        lineHeight: 1,
                        fontWeight: 900,
                        letterSpacing: 0,
                        color: selected ? theme.palette.primary.main : theme.palette.text.primary,
                      }}
                    >
                      {option.greeting}
                    </Typography>
                    <Stack direction="row" spacing={1} alignItems="baseline" sx={{ minWidth: 0 }}>
                      <Typography variant="h6" sx={{ fontWeight: 850 }}>
                        {option.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {option.nativeName}
                      </Typography>
                    </Stack>
                  </Stack>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 650 }}>
                    {option.sample}
                  </Typography>
                </Paper>
              </ButtonBase>
            )
          })}
        </Box>
      </Box>
    </Box>
  )
}

function SystemStep({
  settings,
  showCloudKey,
  onToggleCloudKey,
  onChange,
}: {
  settings: OobeSystemSettings
  showCloudKey: boolean
  onToggleCloudKey: () => void
  onChange: (settings: OobeSystemSettings) => void
}) {
  const { t } = useTranslation('settings')
  const theme = useTheme()

  const sectionSx = {
    p: { xs: 2, sm: 2.5 },
    minWidth: 0,
  }

  const iconSx = {
    width: 36,
    height: 36,
    borderRadius: 2,
    display: 'grid',
    placeItems: 'center',
    color: theme.palette.primary.main,
    backgroundColor: alpha(theme.palette.primary.main, 0.1),
    boxShadow: `inset 0 1px 0 ${alpha(theme.palette.common.white, 0.46)}`,
  }

  const fieldSx = {
    '& .MuiOutlinedInput-root': {
      borderRadius: 2,
      backgroundColor: alpha(theme.palette.background.paper, 0.42),
      transition: 'background-color 0.2s ease, box-shadow 0.2s ease',
      '& fieldset': {
        borderColor: alpha(theme.palette.primary.main, 0.14),
      },
      '&:hover fieldset': {
        borderColor: alpha(theme.palette.primary.main, 0.26),
      },
      '&.Mui-focused': {
        boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.1)}`,
      },
      '&.Mui-focused fieldset': {
        borderColor: alpha(theme.palette.primary.main, 0.38),
      },
      '&.Mui-disabled': {
        backgroundColor: alpha(theme.palette.text.primary, 0.04),
      },
    },
  }

  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: 820,
        mx: 'auto',
      }}
    >
      <Paper
        elevation={0}
        sx={{
          borderRadius: { xs: 3, md: 4 },
          overflow: 'hidden',
          background: `linear-gradient(145deg, ${alpha(theme.palette.background.paper, 0.66)}, ${alpha(theme.palette.background.paper, 0.36)})`,
          border: `1px solid ${alpha(theme.palette.common.white, 0.48)}`,
          boxShadow: `0 24px 68px ${alpha(theme.palette.primary.main, 0.1)}, inset 0 1px 0 ${alpha(theme.palette.common.white, 0.6)}`,
          backdropFilter: 'blur(18px)',
          WebkitBackdropFilter: 'blur(18px)',
        }}
      >
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
          }}
        >
          <Box
            sx={{
              ...sectionSx,
              borderRight: { xs: 'none', md: `1px solid ${alpha(theme.palette.primary.main, 0.1)}` },
              borderBottom: { xs: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`, md: 'none' },
            }}
          >
            <Stack spacing={1.75}>
              <Stack direction="row" spacing={1.25} alignItems="center">
                <Box sx={iconSx}>
                  <CloudQueueIcon fontSize="small" />
                </Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 850 }}>
                  {t('oobe.system.cloudTitle')}
                </Typography>
              </Stack>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 1.5,
                  minHeight: 46,
                  px: 1.5,
                  py: 0.75,
                  borderRadius: 2,
                  backgroundColor: alpha(theme.palette.background.paper, 0.28),
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {t('oobe.system.enableCloud')}
                </Typography>
                <Switch
                  checked={settings.enableNekroCloud}
                  onChange={event => onChange({ ...settings, enableNekroCloud: event.target.checked })}
                />
              </Box>
              <TextField
                fullWidth
                label={t('oobe.system.cloudKey')}
                value={settings.nekroCloudApiKey}
                type={showCloudKey ? 'text' : 'password'}
                onChange={event => onChange({ ...settings, nekroCloudApiKey: event.target.value })}
                disabled={!settings.enableNekroCloud}
                sx={fieldSx}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconActionButton
                        size="small"
                        aria-label={showCloudKey ? t('oobe.actions.hideSecret') : t('oobe.actions.showSecret')}
                        onClick={onToggleCloudKey}
                      >
                        {showCloudKey ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconActionButton>
                    </InputAdornment>
                  ),
                }}
              />
              <Link
                href="https://cloud.nekro.ai/me"
                target="_blank"
                rel="noopener noreferrer"
                underline="none"
                sx={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 0.5,
                  width: 'fit-content',
                  px: 1,
                  py: 0.65,
                  borderRadius: 1.5,
                  color: theme.palette.primary.main,
                  fontSize: theme.typography.body2.fontSize,
                  fontWeight: 700,
                  backgroundColor: alpha(theme.palette.primary.main, 0.08),
                  transition: 'background-color 0.2s ease, color 0.2s ease',
                  '&:hover': {
                    backgroundColor: alpha(theme.palette.primary.main, 0.14),
                  },
                }}
              >
                <LaunchIcon fontSize="small" />
                <span>{t('oobe.system.cloudLink')}</span>
              </Link>
            </Stack>
          </Box>
          <Box sx={sectionSx}>
            <Stack spacing={1.75}>
              <Stack direction="row" spacing={1.25} alignItems="center">
                <Box sx={iconSx}>
                  <HubIcon fontSize="small" />
                </Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 850 }}>
                  {t('oobe.system.proxyTitle')}
                </Typography>
              </Stack>
              <TextField
                fullWidth
                label={t('oobe.system.proxy')}
                placeholder="http://127.0.0.1:7890"
                value={settings.defaultProxy}
                onChange={event => onChange({ ...settings, defaultProxy: event.target.value })}
                sx={fieldSx}
              />
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  px: 0.25,
                  lineHeight: 1.7,
                }}
              >
                {t('oobe.system.proxyHint')}
              </Typography>
            </Stack>
          </Box>
        </Box>
      </Paper>
    </Box>
  )
}

function ModelDraft({
  model,
  mode,
  testResult,
  testing,
  fetchingModels,
  modelOptions,
  onChange,
  onFetchModels,
  onTest,
}: ModelDraftProps) {
  const { t, i18n } = useTranslation('settings')
  const theme = useTheme()
  const [showApiKey, setShowApiKey] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const providerOptions = useMemo(() => OPENAI_COMPAT_PROVIDERS.map(provider => provider.url), [])
  const providerMetaByUrl = useMemo(
    () => new Map(OPENAI_COMPAT_PROVIDERS.map(provider => [
      provider.url,
      getLocalizedText(provider.label, i18n.resolvedLanguage),
    ])),
    [i18n.resolvedLanguage],
  )
  const canTest = isModelReady(model) && !testing
  const isChat = mode === 'chat'

  return (
    <Stack spacing={2.5}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
          gap: 2,
        }}
      >
        <TextField
          label={t('oobe.model.groupName')}
          value={model.groupName}
          onChange={event => onChange({ ...model, groupName: event.target.value })}
          fullWidth
        />
        <Autocomplete
          freeSolo
          options={providerOptions}
          value={model.BASE_URL}
          onChange={(_, value) => onChange({ ...model, BASE_URL: value ?? '' })}
          onInputChange={(_, value) => onChange({ ...model, BASE_URL: value })}
          getOptionLabel={option => option}
          renderOption={(props, option) => (
            <li {...props} key={option}>
              <Stack spacing={0.25}>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {providerMetaByUrl.get(option) ?? option}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {option}
                </Typography>
              </Stack>
            </li>
          )}
          renderInput={params => (
            <TextField
              {...params}
              label={t('oobe.model.baseUrl')}
              placeholder="https://api.nekro.ai/v1"
            />
          )}
        />
        <TextField
          label={t('oobe.model.apiKey')}
          value={model.API_KEY}
          type={showApiKey ? 'text' : 'password'}
          onChange={event => onChange({ ...model, API_KEY: event.target.value })}
          fullWidth
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconActionButton
                  size="small"
                  aria-label={showApiKey ? t('oobe.actions.hideSecret') : t('oobe.actions.showSecret')}
                  onClick={() => setShowApiKey(value => !value)}
                >
                  {showApiKey ? <VisibilityOffIcon /> : <VisibilityIcon />}
                </IconActionButton>
              </InputAdornment>
            ),
          }}
        />
        <TextField
          label={t('oobe.model.proxy')}
          value={model.CHAT_PROXY}
          onChange={event => onChange({ ...model, CHAT_PROXY: event.target.value })}
          placeholder="http://127.0.0.1:7890"
          fullWidth
        />
      </Box>

      <Paper elevation={0} sx={{ ...(UNIFIED_TABLE_STYLES.paper as object), borderRadius: 2, p: 2 }}>
        <Stack spacing={2}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems={{ sm: 'center' }}>
            <Autocomplete
              freeSolo
              options={modelOptions}
              value={model.CHAT_MODEL}
              onChange={(_, value) => onChange({ ...model, CHAT_MODEL: value ?? '' })}
              onInputChange={(_, value) => onChange({ ...model, CHAT_MODEL: value })}
              sx={{ flex: 1 }}
              renderInput={params => (
                <TextField
                  {...params}
                  label={isChat ? t('oobe.model.chatModel') : t('oobe.model.embeddingModel')}
                  placeholder={isChat ? 'gpt-4o' : 'text-embedding-3-large'}
                />
              )}
            />
            <ActionButton
              tone="secondary"
              startIcon={fetchingModels ? <CircularProgress size={16} /> : <ContentCopyIcon />}
              onClick={onFetchModels}
              disabled={fetchingModels}
              sx={{ minHeight: 48 }}
            >
              {t('oobe.actions.fetchModels')}
            </ActionButton>
            <ActionButton
              tone="primary"
              startIcon={testing ? <CircularProgress size={16} /> : <NetworkCheckIcon />}
              onClick={onTest}
              disabled={!canTest}
              sx={{ minHeight: 48 }}
            >
              {t('oobe.actions.test')}
            </ActionButton>
          </Stack>

          {isChat && (
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <FormControlLabel
                control={
                  <Switch
                    checked={Boolean(model.ENABLE_VISION)}
                    onChange={event => onChange({ ...model, ENABLE_VISION: event.target.checked })}
                  />
                }
                label={t('oobe.model.vision')}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={Boolean(model.ENABLE_COT)}
                    onChange={event => onChange({ ...model, ENABLE_COT: event.target.checked })}
                  />
                }
                label={t('oobe.model.cot')}
              />
            </Stack>
          )}

          <ActionButton
            tone="ghost"
            size="small"
            endIcon={
              <ExpandMoreIcon
                fontSize="small"
                sx={{
                  transform: showAdvanced ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s ease',
                }}
              />
            }
            onClick={() => setShowAdvanced(value => !value)}
            sx={{ alignSelf: 'flex-start' }}
          >
            {t('oobe.model.advancedConfig')}
          </ActionButton>

          <Collapse in={showAdvanced} timeout={220} unmountOnExit>
            <Stack
              spacing={2}
              sx={{
                mt: 1,
                pl: { xs: 0, sm: 2 },
                borderLeft: { sm: `2px solid ${alpha(theme.palette.primary.main, 0.14)}` },
              }}
            >
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' },
                  gap: 1.5,
                }}
              >
                <TextField
                  type="number"
                  label="Temperature"
                  value={model.TEMPERATURE ?? ''}
                  onChange={event => onChange({ ...model, TEMPERATURE: event.target.value === '' ? null : Number(event.target.value) })}
                />
                <TextField
                  type="number"
                  label="Top P"
                  value={model.TOP_P ?? ''}
                  onChange={event => onChange({ ...model, TOP_P: event.target.value === '' ? null : Number(event.target.value) })}
                />
                <TextField
                  type="number"
                  label="Top K"
                  value={model.TOP_K ?? ''}
                  onChange={event => onChange({ ...model, TOP_K: event.target.value === '' ? null : Number(event.target.value) })}
                />
              </Box>
              <TextField
                label="Extra Body"
                value={model.EXTRA_BODY ?? ''}
                onChange={event => onChange({ ...model, EXTRA_BODY: event.target.value || null })}
                multiline
                minRows={3}
                error={!isValidJsonOrEmpty(model.EXTRA_BODY)}
                helperText={!isValidJsonOrEmpty(model.EXTRA_BODY) ? t('oobe.validation.invalidJson') : t('oobe.model.extraBodyHint')}
              />
            </Stack>
          </Collapse>
        </Stack>
      </Paper>

      {testResult && (
        <Alert
          severity={testResult.success ? 'success' : 'warning'}
          sx={{ borderRadius: 1.5 }}
        >
          <Stack spacing={0.5}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
              {testResult.success ? t('oobe.testResult.success') : t('oobe.testResult.failed')}
            </Typography>
            <Typography variant="body2">
              {testResult.success
                ? t('oobe.testResult.detail', { model: testResult.used_model || testResult.model_name, ms: testResult.latency_ms })
                : testResult.error_message}
            </Typography>
            {testResult.response_text && (
              <Typography variant="body2" sx={{ color: alpha(theme.palette.text.primary, 0.82) }}>
                {testResult.response_text}
              </Typography>
            )}
          </Stack>
        </Alert>
      )}
    </Stack>
  )
}

function EmbeddingStep({
  model,
  memoryDimension,
  kbDimension,
  testResult,
  testing,
  fetchingModels,
  modelOptions,
  onModelChange,
  onMemoryDimensionChange,
  onKbDimensionChange,
  onFetchModels,
  onTest,
}: {
  model: OobeModelSettings
  memoryDimension: number
  kbDimension: number
  testResult: ModelGroupTestItem | null
  testing: boolean
  fetchingModels: boolean
  modelOptions: string[]
  onModelChange: (model: OobeModelSettings) => void
  onMemoryDimensionChange: (value: number) => void
  onKbDimensionChange: (value: number) => void
  onFetchModels: () => void
  onTest: () => void
}) {
  const { t } = useTranslation('settings')

  return (
    <Stack spacing={2.5}>
      <ModelDraft
        model={model}
        mode="embedding"
        testResult={testResult}
        testing={testing}
        fetchingModels={fetchingModels}
        modelOptions={modelOptions}
        onChange={onModelChange}
        onFetchModels={onFetchModels}
        onTest={onTest}
      />
      <Paper elevation={0} sx={{ ...(UNIFIED_TABLE_STYLES.paper as object), borderRadius: 2, p: 2 }}>
        <Stack spacing={2}>
          <Stack direction="row" spacing={1} alignItems="center">
            <ScienceIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 850 }}>
              {t('oobe.embedding.dimensionTitle')}
            </Typography>
          </Stack>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
              gap: 2,
            }}
          >
            <TextField
              type="number"
              label={t('oobe.embedding.memoryDimension')}
              value={memoryDimension}
              onChange={event => onMemoryDimensionChange(Number(event.target.value) || 0)}
            />
            <TextField
              type="number"
              label={t('oobe.embedding.kbDimension')}
              value={kbDimension}
              onChange={event => onKbDimensionChange(Number(event.target.value) || 0)}
            />
          </Box>
          <Typography variant="body2" color="text.secondary">
            {t('oobe.embedding.dimensionHint')}
          </Typography>
        </Stack>
      </Paper>
    </Stack>
  )
}

function FinishStep({
  system,
  chatModel,
  embeddingModel,
  memoryDimension,
  kbDimension,
  canComplete,
}: {
  system: OobeSystemSettings
  chatModel: OobeModelSettings
  embeddingModel: OobeModelSettings
  memoryDimension: number
  kbDimension: number
  canComplete: boolean
}) {
  const { t } = useTranslation('settings')

  return (
    <Stack spacing={2}>
      {!canComplete && (
        <Alert severity="warning" sx={{ borderRadius: 1.5 }}>
          {t('oobe.validation.completeRequired')}
        </Alert>
      )}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
          gap: 2,
        }}
      >
        <ReviewCard
          icon={<SettingsSuggestIcon />}
          title={t('oobe.finish.system')}
          rows={[
            [t('oobe.system.languageTitle'), system.systemLang],
            [t('oobe.system.enableCloud'), system.enableNekroCloud ? t('oobe.common.enabled') : t('oobe.common.disabled')],
            [t('oobe.system.proxy'), system.defaultProxy || '-'],
          ]}
        />
        <ReviewCard
          icon={<PsychologyIcon />}
          title={t('oobe.finish.chat')}
          rows={[
            [t('oobe.model.groupName'), chatModel.groupName],
            [t('oobe.model.baseUrl'), chatModel.BASE_URL],
            [t('oobe.model.chatModel'), chatModel.CHAT_MODEL || '-'],
          ]}
        />
        <ReviewCard
          icon={<MemoryIcon />}
          title={t('oobe.finish.embedding')}
          rows={[
            [t('oobe.model.groupName'), embeddingModel.groupName],
            [t('oobe.model.baseUrl'), embeddingModel.BASE_URL],
            [t('oobe.model.embeddingModel'), embeddingModel.CHAT_MODEL || '-'],
          ]}
        />
        <ReviewCard
          icon={<ScienceIcon />}
          title={t('oobe.finish.dimensions')}
          rows={[
            [t('oobe.embedding.memoryDimension'), String(memoryDimension)],
            [t('oobe.embedding.kbDimension'), String(kbDimension)],
          ]}
        />
      </Box>
    </Stack>
  )
}

function ReviewCard({
  icon,
  title,
  rows,
}: {
  icon: ReactNode
  title: string
  rows: Array<[string, string]>
}) {
  const theme = useTheme()
  return (
    <Paper elevation={0} sx={{ ...(UNIFIED_TABLE_STYLES.paper as object), borderRadius: 2, p: 2 }}>
      <Stack spacing={1.25}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Box sx={{ color: theme.palette.primary.main, display: 'flex' }}>{icon}</Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            {title}
          </Typography>
        </Stack>
        {rows.map(([label, value]) => (
          <Stack key={label} direction="row" spacing={1} justifyContent="space-between" sx={{ minWidth: 0 }}>
            <Typography variant="body2" color="text.secondary" sx={{ flexShrink: 0 }}>
              {label}
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, minWidth: 0, wordBreak: 'break-word', textAlign: 'right' }}>
              {value}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Paper>
  )
}

export default function OobePage() {
  return <OobePageContent />
}
