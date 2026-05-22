import type { ConfigItem, ModelGroupConfig } from '../../components/common/ConfigTable'
import { unifiedConfigApi } from './unified-config'

export interface OobeStatus {
  completed: boolean
  skipped: boolean
  shouldShow: boolean
}

export interface OobeSystemSettings {
  systemLang: 'zh-CN' | 'en-US'
  enableNekroCloud: boolean
  nekroCloudApiKey: string
  defaultProxy: string
}

export interface OobeModelSettings extends ModelGroupConfig {
  groupName: string
}

export interface OobeSetupState {
  status: OobeStatus
  system: OobeSystemSettings
  chatModel: OobeModelSettings
  embeddingModel: OobeModelSettings
  memoryEmbeddingDimension: number
  kbEmbeddingDimension: number
  configItems: ConfigItem[]
}

const CHAT_GROUP_NAME = 'default'
const EMBEDDING_GROUP_NAME = 'text-embedding'
const OOBE_STORAGE_KEY = 'nekro-agent-oobe-state'

interface StoredOobeStatus {
  completed: boolean
  skipped: boolean
}

const getItem = (items: ConfigItem[], key: string): ConfigItem | undefined =>
  items.find(item => item.key === key)

const hasItem = (items: ConfigItem[], key: string): boolean =>
  items.some(item => item.key === key)

const readStoredOobeStatus = (): StoredOobeStatus => {
  if (typeof window === 'undefined') {
    return { completed: false, skipped: false }
  }

  try {
    const raw = window.localStorage.getItem(OOBE_STORAGE_KEY)
    if (!raw) {
      return { completed: false, skipped: false }
    }
    const parsed = JSON.parse(raw) as Partial<StoredOobeStatus>
    return {
      completed: parsed.completed === true,
      skipped: parsed.skipped === true,
    }
  } catch {
    return { completed: false, skipped: false }
  }
}

const writeStoredOobeStatus = (status: StoredOobeStatus): void => {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.localStorage.setItem(OOBE_STORAGE_KEY, JSON.stringify(status))
  } catch {
    // 本地存储不可用时不阻断配置保存。
  }
}

const filterExistingSystemConfig = (
  configs: Record<string, string>,
  configItems: ConfigItem[],
): Record<string, string> => {
  const existingKeys = new Set(configItems.map(item => item.key))
  return Object.fromEntries(
    Object.entries(configs).filter(([key]) => existingKeys.has(key)),
  )
}

const batchUpdateExistingSystemConfig = async (
  configs: Record<string, string>,
): Promise<Record<string, string>> => {
  const configItems = await unifiedConfigApi.getConfigList('system')
  const existingConfigs = filterExistingSystemConfig(configs, configItems)
  if (Object.keys(existingConfigs).length > 0) {
    await unifiedConfigApi.batchUpdateConfig('system', existingConfigs)
  }
  return existingConfigs
}

const getStringValue = (items: ConfigItem[], key: string, fallback = ''): string => {
  const value = getItem(items, key)?.value
  return typeof value === 'string' ? value : fallback
}

const getBoolValue = (items: ConfigItem[], key: string, fallback = false): boolean => {
  const value = getItem(items, key)?.value
  return typeof value === 'boolean' ? value : fallback
}

const getNumberValue = (items: ConfigItem[], key: string, fallback: number): number => {
  const value = getItem(items, key)?.value
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

const normalizeModelGroup = (
  groupName: string,
  config: ModelGroupConfig | undefined,
  modelType: 'chat' | 'embedding',
): OobeModelSettings => ({
  groupName,
  CHAT_MODEL: config?.CHAT_MODEL ?? '',
  CHAT_PROXY: config?.CHAT_PROXY ?? '',
  BASE_URL: config?.BASE_URL ?? 'https://api.nekro.ai/v1',
  API_KEY: config?.API_KEY ?? '',
  MODEL_TYPE: config?.MODEL_TYPE ?? modelType,
  TEMPERATURE: config?.TEMPERATURE ?? null,
  TOP_P: config?.TOP_P ?? null,
  TOP_K: config?.TOP_K ?? null,
  PRESENCE_PENALTY: config?.PRESENCE_PENALTY ?? null,
  FREQUENCY_PENALTY: config?.FREQUENCY_PENALTY ?? null,
  EXTRA_BODY: config?.EXTRA_BODY ?? null,
  ENABLE_VISION: config?.ENABLE_VISION ?? modelType === 'chat',
  ENABLE_COT: config?.ENABLE_COT ?? false,
})

const serializeModelConfig = (model: OobeModelSettings, modelType: 'chat' | 'embedding'): ModelGroupConfig => ({
  CHAT_MODEL: model.CHAT_MODEL.trim(),
  CHAT_PROXY: model.CHAT_PROXY.trim(),
  BASE_URL: model.BASE_URL.trim(),
  API_KEY: model.API_KEY.trim(),
  MODEL_TYPE: modelType,
  TEMPERATURE: model.TEMPERATURE ?? null,
  TOP_P: model.TOP_P ?? null,
  TOP_K: model.TOP_K ?? null,
  PRESENCE_PENALTY: model.PRESENCE_PENALTY ?? null,
  FREQUENCY_PENALTY: model.FREQUENCY_PENALTY ?? null,
  EXTRA_BODY: model.EXTRA_BODY?.trim() || null,
  ENABLE_VISION: modelType === 'chat' ? Boolean(model.ENABLE_VISION) : false,
  ENABLE_COT: modelType === 'chat' ? Boolean(model.ENABLE_COT) : false,
})

export const oobeApi = {
  getSetupState: async (): Promise<OobeSetupState> => {
    const [configItems, modelGroups] = await Promise.all([
      unifiedConfigApi.getConfigList('system'),
      unifiedConfigApi.getModelGroups(),
    ])

    const storedOobeStatus = readStoredOobeStatus()
    const completed = (
      hasItem(configItems, 'OOBE_COMPLETED')
        ? getBoolValue(configItems, 'OOBE_COMPLETED')
        : false
    ) || storedOobeStatus.completed
    const skipped = (
      hasItem(configItems, 'OOBE_SKIPPED')
        ? getBoolValue(configItems, 'OOBE_SKIPPED')
        : false
    ) || storedOobeStatus.skipped
    const systemLang = getStringValue(configItems, 'SYSTEM_LANG', 'zh-CN')

    return {
      status: {
        completed,
        skipped,
        shouldShow: !completed && !skipped,
      },
      system: {
        systemLang: systemLang === 'en-US' ? 'en-US' : 'zh-CN',
        enableNekroCloud: getBoolValue(configItems, 'ENABLE_NEKRO_CLOUD', true),
        nekroCloudApiKey: getStringValue(configItems, 'NEKRO_CLOUD_API_KEY'),
        defaultProxy: getStringValue(configItems, 'DEFAULT_PROXY'),
      },
      chatModel: normalizeModelGroup(CHAT_GROUP_NAME, modelGroups[CHAT_GROUP_NAME], 'chat'),
      embeddingModel: normalizeModelGroup(
        EMBEDDING_GROUP_NAME,
        modelGroups[EMBEDDING_GROUP_NAME],
        'embedding',
      ),
      memoryEmbeddingDimension: getNumberValue(configItems, 'MEMORY_EMBEDDING_DIMENSION', 1024),
      kbEmbeddingDimension: getNumberValue(configItems, 'KB_EMBEDDING_DIMENSION', 1024),
      configItems,
    }
  },

  markSkipped: async (): Promise<void> => {
    await batchUpdateExistingSystemConfig({
      OOBE_SKIPPED: 'true',
    })
    writeStoredOobeStatus({ completed: false, skipped: true })
  },

  completeSetup: async (
    system: OobeSystemSettings,
    chatModel: OobeModelSettings,
    embeddingModel: OobeModelSettings,
    memoryEmbeddingDimension: number,
    kbEmbeddingDimension: number,
  ): Promise<void> => {
    const chatGroupName = chatModel.groupName.trim() || CHAT_GROUP_NAME
    const embeddingGroupName = embeddingModel.groupName.trim() || EMBEDDING_GROUP_NAME

    await unifiedConfigApi.updateModelGroup(chatGroupName, serializeModelConfig(chatModel, 'chat'))
    await unifiedConfigApi.updateModelGroup(
      embeddingGroupName,
      serializeModelConfig(embeddingModel, 'embedding'),
    )

    await batchUpdateExistingSystemConfig({
      SYSTEM_LANG: system.systemLang,
      ENABLE_NEKRO_CLOUD: String(system.enableNekroCloud),
      NEKRO_CLOUD_API_KEY: system.nekroCloudApiKey.trim(),
      DEFAULT_PROXY: system.defaultProxy.trim(),
      USE_MODEL_GROUP: chatGroupName,
      DEBUG_MIGRATION_MODEL_GROUP: chatGroupName,
      FALLBACK_MODEL_GROUP: chatGroupName,
      MEMORY_CONSOLIDATION_MODEL_GROUP: chatGroupName,
      MEMORY_EMBEDDING_MODEL_GROUP: embeddingGroupName,
      KB_EMBEDDING_MODEL_GROUP: embeddingGroupName,
      MEMORY_EMBEDDING_DIMENSION: String(memoryEmbeddingDimension),
      KB_EMBEDDING_DIMENSION: String(kbEmbeddingDimension),
      OOBE_COMPLETED: 'true',
      OOBE_SKIPPED: 'false',
    })
    writeStoredOobeStatus({ completed: true, skipped: false })
  },
}

export const buildOobeInlineTestRequest = (
  model: OobeModelSettings,
  modelType: 'chat' | 'embedding',
) => ({
  group_name: model.groupName.trim() || (modelType === 'chat' ? CHAT_GROUP_NAME : EMBEDDING_GROUP_NAME),
  chat_model: model.CHAT_MODEL.trim(),
  base_url: model.BASE_URL.trim(),
  api_key: model.API_KEY.trim(),
  model_type: modelType,
  chat_proxy: model.CHAT_PROXY.trim() || undefined,
  temperature: model.TEMPERATURE ?? undefined,
  top_p: model.TOP_P ?? undefined,
  top_k: model.TOP_K ?? undefined,
  presence_penalty: model.PRESENCE_PENALTY ?? undefined,
  frequency_penalty: model.FREQUENCY_PENALTY ?? undefined,
  extra_body: model.EXTRA_BODY?.trim() || undefined,
})
