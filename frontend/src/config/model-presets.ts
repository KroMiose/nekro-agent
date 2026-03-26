export interface EnvPair {
  key: string
  value: string
}

export interface LocalizedText {
  'zh-CN': string
  'en-US': string
}

export interface OpenAICompatProvider {
  id: string
  url: string
  label: LocalizedText
}

export interface CCModelSourcePreset {
  id: string
  label: LocalizedText
  note: LocalizedText
  form: {
    base_url: string
    api_timeout_ms: string
    model_type: 'preset' | 'manual'
    preset_model: string
    anthropic_model: string
    small_fast_model: string
    default_sonnet: string
    default_opus: string
    default_haiku: string
    extra_env: EnvPair[]
  }
}

export function getLocalizedText(text: LocalizedText, language?: string): string {
  return language?.startsWith('zh') ? text['zh-CN'] : text['en-US']
}

export const OPENAI_COMPAT_PROVIDERS: OpenAICompatProvider[] = [
  {
    id: 'nekroAI',
    url: 'https://api.nekro.ai/v1',
    label: { 'zh-CN': 'NekroAI中转', 'en-US': 'NekroAI Relay' },
  },
  {
    id: 'googleGemini',
    url: 'https://generativelanguage.googleapis.com/v1beta/openai',
    label: { 'zh-CN': '谷歌Gemini', 'en-US': 'Google Gemini' },
  },
  {
    id: 'tongyiQianwen',
    url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    label: { 'zh-CN': '通义千问', 'en-US': 'Tongyi Qianwen' },
  },
  {
    id: 'doubao',
    url: 'https://ark.cn-beijing.volces.com/api/v3',
    label: { 'zh-CN': '豆包', 'en-US': 'Doubao' },
  },
  {
    id: 'kimi',
    url: 'https://api.moonshot.cn/v1',
    label: { 'zh-CN': 'Kimi', 'en-US': 'Kimi' },
  },
  {
    id: 'zhipuQingyan',
    url: 'https://open.bigmodel.cn/api/paas/v4',
    label: { 'zh-CN': '智谱清言', 'en-US': 'Zhipu Qingyan' },
  },
  {
    id: 'baiduQianfan',
    url: 'https://qianfan.baidubce.com/v2',
    label: { 'zh-CN': '百度千帆', 'en-US': 'Baidu Qianfan' },
  },
  {
    id: 'iflytekSpark',
    url: 'https://spark-api-open.xf-yun.com/v1',
    label: { 'zh-CN': '科大讯飞', 'en-US': 'iFlytek Spark' },
  },
  {
    id: 'baichuan',
    url: 'https://api.baichuan-ai.com/v1',
    label: { 'zh-CN': '百川', 'en-US': 'Baichuan' },
  },
  {
    id: 'tencentHunyuan',
    url: 'https://api.hunyuan.cloud.tencent.com/v1',
    label: { 'zh-CN': '腾讯混元', 'en-US': 'Tencent Hunyuan' },
  },
  {
    id: 'sensetimeRixin',
    url: 'https://api.sensenova.cn/compatible-mode/v1',
    label: { 'zh-CN': '商汤日日新', 'en-US': 'SenseTime Rixin' },
  },
]

export const DEFAULT_CC_EXTRA_ENV: EnvPair[] = [
  { key: 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC', value: '1' },
  { key: 'CLAUDE_CODE_ATTRIBUTION_HEADER', value: '0' },
]

export const CC_MODEL_SOURCE_PRESETS: CCModelSourcePreset[] = [
  {
    id: 'nekroai-relay-sonnet',
    label: {
      'zh-CN': 'NekroAI 官方中转 Sonnet 版',
      'en-US': 'NekroAI official relay Sonnet profile',
    },
    note: {
      'zh-CN':
        'NekroAI 自有 Claude 中转入口，默认主模型偏向 Sonnet 成本档，Haiku / Sonnet / Opus 三档映射已预填。',
      'en-US':
        "NekroAI's own Claude relay endpoint with a Sonnet-cost default primary model. Haiku / Sonnet / Opus mappings are prefilled.",
    },
    form: {
      base_url: 'https://api.nekro.ai/claude',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'sonnet',
      anthropic_model: 'claude-sonnet-4-6',
      small_fast_model: 'claude-haiku-4-5',
      default_sonnet: 'claude-sonnet-4-6',
      default_opus: 'claude-opus-4-6',
      default_haiku: 'claude-haiku-4-5',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'nekroai-relay-opus',
    label: {
      'zh-CN': 'NekroAI 官方中转 Opus 版',
      'en-US': 'NekroAI official relay Opus profile',
    },
    note: {
      'zh-CN':
        'NekroAI 自有 Claude 中转入口，默认主模型偏向 Opus 能力档，Haiku / Sonnet / Opus 三档映射已预填。',
      'en-US':
        "NekroAI's own Claude relay endpoint with an Opus-capability default primary model. Haiku / Sonnet / Opus mappings are prefilled.",
    },
    form: {
      base_url: 'https://api.nekro.ai/claude',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'claude-opus-4-6',
      small_fast_model: 'claude-haiku-4-5',
      default_sonnet: 'claude-sonnet-4-6',
      default_opus: 'claude-opus-4-6',
      default_haiku: 'claude-haiku-4-5',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'anthropic-official-tiered',
    label: {
      'zh-CN': 'Anthropic 官方三档映射',
      'en-US': 'Anthropic official tiered mapping',
    },
    note: {
      'zh-CN': 'Anthropic 官方 API，按当前公开模型手动映射为 Opus 4.1 / Sonnet 4 / Haiku 3.5。',
      'en-US':
        'Anthropic official API mapped to the current public Opus 4.1 / Sonnet 4 / Haiku 3.5 lineup.',
    },
    form: {
      base_url: 'https://api.anthropic.com',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'claude-sonnet-4-20250514',
      small_fast_model: 'claude-3-5-haiku-latest',
      default_sonnet: 'claude-sonnet-4-20250514',
      default_opus: 'claude-opus-4-1-20250805',
      default_haiku: 'claude-3-5-haiku-latest',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'minimax-m2.5-cn',
    label: {
      'zh-CN': 'MiniMax M2.5（官方兼容）',
      'en-US': 'MiniMax M2.5 (official compatible)',
    },
    note: {
      'zh-CN': 'MiniMax 官方 Anthropic 兼容入口，全部角色统一映射到 MiniMax-M2.5。',
      'en-US':
        'MiniMax official Anthropic-compatible endpoint with all roles mapped to MiniMax-M2.5.',
    },
    form: {
      base_url: 'https://api.minimaxi.com/anthropic',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'MiniMax-M2.5',
      small_fast_model: 'MiniMax-M2.5',
      default_sonnet: 'MiniMax-M2.5',
      default_opus: 'MiniMax-M2.5',
      default_haiku: 'MiniMax-M2.5',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'minimax-m2.5-highspeed-cn',
    label: {
      'zh-CN': 'MiniMax M2.5 HighSpeed（官方兼容）',
      'en-US': 'MiniMax M2.5 HighSpeed (official compatible)',
    },
    note: {
      'zh-CN': 'MiniMax 官方 Anthropic 兼容入口，全部角色统一映射到 MiniMax-M2.5-highspeed。',
      'en-US':
        'MiniMax official Anthropic-compatible endpoint with all roles mapped to MiniMax-M2.5-highspeed.',
    },
    form: {
      base_url: 'https://api.minimaxi.com/anthropic',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'MiniMax-M2.5-highspeed',
      small_fast_model: 'MiniMax-M2.5-highspeed',
      default_sonnet: 'MiniMax-M2.5-highspeed',
      default_opus: 'MiniMax-M2.5-highspeed',
      default_haiku: 'MiniMax-M2.5-highspeed',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'kimi-code-plan',
    label: {
      'zh-CN': 'Kimi K2.5（KimiCode 登月计划）',
      'en-US': 'Kimi K2.5 (KimiCode Lunar Program)',
    },
    note: {
      'zh-CN':
        'Kimi 官方编码助手端点（api.kimi.com/coding），全部角色与子代理统一映射到 kimi-k2.5。仅适用于在 Kimi 官网订阅了登月计划的用户，密钥格式通常为 sk-kimi-xxxxx。',
      'en-US':
        "Kimi's official coding assistant endpoint (api.kimi.com/coding) with all roles and subagent mapped to kimi-k2.5. Only for users subscribed to the KimiCode Lunar Program, API key format is usually sk-kimi-xxxxx.",
    },
    form: {
      base_url: 'https://api.kimi.com/coding',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'kimi-k2.5',
      small_fast_model: 'kimi-k2.5',
      default_sonnet: 'kimi-k2.5',
      default_opus: 'kimi-k2.5',
      default_haiku: 'kimi-k2.5',
      extra_env: [
        ...DEFAULT_CC_EXTRA_ENV,
        { key: 'CLAUDE_CODE_SUBAGENT_MODEL', value: 'kimi-k2.5' },
      ],
    },
  },
  {
    id: 'moonshot-kimi-k2.5',
    label: {
      'zh-CN': 'Kimi K2.5（Moonshot Anthropic 兼容）',
      'en-US': 'Kimi K2.5 (Moonshot Anthropic compatible)',
    },
    note: {
      'zh-CN':
        '月之暗面官方 Anthropic 兼容入口（api.moonshot.cn），全部角色与子代理统一映射到 kimi-k2.5；关闭工具搜索以匹配官方 Claude Code 启动示例。适用于 Moonshot 平台按需计费用户。',
      'en-US':
        "Moonshot's official Anthropic-compatible endpoint (api.moonshot.cn) with all roles and subagent mapped to kimi-k2.5; tool search disabled to match the official Claude Code launch example. For Moonshot platform pay-as-you-go users.",
    },
    form: {
      base_url: 'https://api.moonshot.cn/anthropic',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'kimi-k2.5',
      small_fast_model: 'kimi-k2.5',
      default_sonnet: 'kimi-k2.5',
      default_opus: 'kimi-k2.5',
      default_haiku: 'kimi-k2.5',
      extra_env: [
        ...DEFAULT_CC_EXTRA_ENV,
        { key: 'CLAUDE_CODE_SUBAGENT_MODEL', value: 'kimi-k2.5' },
        { key: 'ENABLE_TOOL_SEARCH', value: 'false' },
      ],
    },
  },
  {
    id: 'zhipu-glm5-latest',
    label: {
      'zh-CN': '智谱 GLM-5（最新旗舰）',
      'en-US': 'Zhipu GLM-5 (latest flagship)',
    },
    note: {
      'zh-CN':
        '智谱官方 Claude API 兼容接入页与模型总览里的当前旗舰模型，全部角色统一映射到 glm-5。',
      'en-US':
        "Zhipu's current flagship from its official Claude-compatible docs and model overview, with all roles mapped to glm-5.",
    },
    form: {
      base_url: 'https://open.bigmodel.cn/api/anthropic',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'glm-5',
      small_fast_model: 'glm-5',
      default_sonnet: 'glm-5',
      default_opus: 'glm-5',
      default_haiku: 'glm-5',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'zhipu-glm-coder',
    label: {
      'zh-CN': '智谱 GLM-4.6（编码向）',
      'en-US': 'Zhipu GLM-4.6 (coding-focused)',
    },
    note: {
      'zh-CN': '智谱模型总览中的当前编码向模型，全部角色统一映射到 glm-4.6。',
      'en-US':
        "Zhipu's current coding-oriented model from its official model overview, with all roles mapped to glm-4.6.",
    },
    form: {
      base_url: 'https://open.bigmodel.cn/api/anthropic',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'glm-4.6',
      small_fast_model: 'glm-4.6',
      default_sonnet: 'glm-4.6',
      default_opus: 'glm-4.6',
      default_haiku: 'glm-4.6',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'qwen-coder-next',
    label: {
      'zh-CN': '阿里百炼 Qwen3 Coder Next',
      'en-US': 'DashScope Qwen3 Coder Next',
    },
    note: {
      'zh-CN':
        '阿里百炼官方 Anthropic 兼容入口，Claude Code 接入文档当前推荐的高性能编码模型 qwen3-coder-next。',
      'en-US':
        "DashScope's official Anthropic-compatible endpoint using qwen3-coder-next, the current high-performance coding recommendation in Alibaba Cloud's Claude Code guide.",
    },
    form: {
      base_url: 'https://dashscope.aliyuncs.com/apps/anthropic',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'qwen3-coder-next',
      small_fast_model: 'qwen3-coder-next',
      default_sonnet: 'qwen3-coder-next',
      default_opus: 'qwen3-coder-next',
      default_haiku: 'qwen3-coder-next',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'qwen-coder-flash',
    label: {
      'zh-CN': '阿里百炼 Qwen3 Coder Flash',
      'en-US': 'DashScope Qwen3 Coder Flash',
    },
    note: {
      'zh-CN':
        '阿里百炼官方 Anthropic 兼容入口，Claude Code 接入文档当前推荐的高性价比编码模型 qwen3-coder-flash。',
      'en-US':
        "DashScope's official Anthropic-compatible endpoint using qwen3-coder-flash, the current cost-efficient coding recommendation in Alibaba Cloud's Claude Code guide.",
    },
    form: {
      base_url: 'https://dashscope.aliyuncs.com/apps/anthropic',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'qwen3-coder-flash',
      small_fast_model: 'qwen3-coder-flash',
      default_sonnet: 'qwen3-coder-flash',
      default_opus: 'qwen3-coder-flash',
      default_haiku: 'qwen3-coder-flash',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'tencent-hunyuan-instruct',
    label: {
      'zh-CN': '腾讯混元官方 Instruct',
      'en-US': 'Tencent Hunyuan official Instruct',
    },
    note: {
      'zh-CN':
        '腾讯混元官方 Anthropic 兼容入口，全部角色统一映射到 hunyuan-2.0-instruct-20251111。',
      'en-US':
        'Tencent Hunyuan official Anthropic-compatible endpoint with all roles mapped to hunyuan-2.0-instruct-20251111.',
    },
    form: {
      base_url: 'https://api.hunyuan.cloud.tencent.com/anthropic',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'hunyuan-2.0-instruct-20251111',
      small_fast_model: 'hunyuan-2.0-instruct-20251111',
      default_sonnet: 'hunyuan-2.0-instruct-20251111',
      default_opus: 'hunyuan-2.0-instruct-20251111',
      default_haiku: 'hunyuan-2.0-instruct-20251111',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
  {
    id: 'tencent-hunyuan-thinking',
    label: {
      'zh-CN': '腾讯混元官方 Thinking',
      'en-US': 'Tencent Hunyuan official Thinking',
    },
    note: {
      'zh-CN':
        '腾讯混元官方 Anthropic 兼容入口，全部角色统一映射到 hunyuan-2.0-thinking-20251109。',
      'en-US':
        'Tencent Hunyuan official Anthropic-compatible endpoint with all roles mapped to hunyuan-2.0-thinking-20251109.',
    },
    form: {
      base_url: 'https://api.hunyuan.cloud.tencent.com/anthropic',
      api_timeout_ms: '3000000',
      model_type: 'manual',
      preset_model: 'opus',
      anthropic_model: 'hunyuan-2.0-thinking-20251109',
      small_fast_model: 'hunyuan-2.0-thinking-20251109',
      default_sonnet: 'hunyuan-2.0-thinking-20251109',
      default_opus: 'hunyuan-2.0-thinking-20251109',
      default_haiku: 'hunyuan-2.0-thinking-20251109',
      extra_env: DEFAULT_CC_EXTRA_ENV,
    },
  },
]
