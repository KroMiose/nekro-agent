import { useState, useCallback } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Chip,
  Grid2,
  Tooltip,
} from '@mui/material'
import { Refresh as RefreshIcon, Casino as CasinoIcon } from '@mui/icons-material'
import { CHIP_VARIANTS } from '../../theme/variants'
import { alpha } from '@mui/material'
import { useTheme } from '@mui/material/styles'
import SegmentedControl from './SegmentedControl'
import ActionButton from './ActionButton'
import IconActionButton from './IconActionButton'

// ── 词库 ──────────────────────────────────────────────────────────────────
const ZH_ADJ = ['迅捷', '智慧', '灵动', '稳健', '深邃', '晨曦', '星辰', '幽蓝', '赤炎', '翠影', '霜月', '涌浪', '碧玉', '苍穹', '烈风']
const ZH_NOUN_ANIMALS = ['猎豹', '游龙', '雄鹰', '玄狐', '苍狼', '虎鲸', '凤凰', '麒麟', '白鹤', '神马']
const ZH_NOUN_COSMOS = ['星云', '流光', '天穹', '银河', '晨星', '幻影', '极光', '彗迹', '暗能', '时隙']
const ZH_NOUN_ITEMS = ['玄玑', '灵枢', '碧落', '乾坤', '紫霄', '虚空', '轮回', '混沌', '奇点', '熵核']

const EN_ADJ = ['swift', 'bright', 'cosmic', 'radiant', 'silent', 'vivid', 'bold', 'sleek', 'sharp', 'deep', 'calm', 'rapid', 'keen', 'stellar', 'noble']
const EN_NOUN_ANIMALS = ['falcon', 'lynx', 'raven', 'wolf', 'hawk', 'orca', 'cobra', 'viper', 'panther', 'phoenix']
const EN_NOUN_COSMOS = ['nebula', 'quasar', 'pulsar', 'aurora', 'comet', 'horizon', 'vertex', 'zenith', 'orbit', 'nova']
const EN_NOUN_TECH = ['cipher', 'vector', 'node', 'core', 'nexus', 'forge', 'matrix', 'pulse', 'grid', 'arc']

type Language = 'zh' | 'en'
type NounCategory = 'animals' | 'cosmos' | 'items'

function getRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

function generateName(lang: Language, nounCat: NounCategory): string {
  if (lang === 'zh') {
    const adj = getRandom(ZH_ADJ)
    const noun = nounCat === 'animals' ? getRandom(ZH_NOUN_ANIMALS)
      : nounCat === 'cosmos' ? getRandom(ZH_NOUN_COSMOS)
      : getRandom(ZH_NOUN_ITEMS)
    return `${adj}${noun}`
  } else {
    const adj = getRandom(EN_ADJ)
    const noun = nounCat === 'animals' ? getRandom(EN_NOUN_ANIMALS)
      : nounCat === 'cosmos' ? getRandom(EN_NOUN_COSMOS)
      : getRandom(EN_NOUN_TECH)
    return `${adj}-${noun}`
  }
}

function generateBatch(lang: Language, nounCat: NounCategory, count = 12): string[] {
  const results = new Set<string>()
  let tries = 0
  while (results.size < count && tries < 60) {
    results.add(generateName(lang, nounCat))
    tries++
  }
  return Array.from(results)
}

// ── Props ─────────────────────────────────────────────────────────────────
export interface NameGeneratorDialogProps {
  open: boolean
  onClose: () => void
  onSelect: (name: string) => void
}

// ── Component ─────────────────────────────────────────────────────────────
export default function NameGeneratorDialog({ open, onClose, onSelect }: NameGeneratorDialogProps) {
  const theme = useTheme()
  const [lang, setLang] = useState<Language>('zh')
  const [nounCat, setNounCat] = useState<NounCategory>('cosmos')
  const [candidates, setCandidates] = useState<string[]>(() => generateBatch('zh', 'cosmos'))
  const [selected, setSelected] = useState<string | null>(null)

  const refresh = useCallback(() => {
    setCandidates(generateBatch(lang, nounCat))
    setSelected(null)
  }, [lang, nounCat])

  const handleLangChange = (val: Language) => {
    setLang(val)
    const newCandidates = generateBatch(val, nounCat)
    setCandidates(newCandidates)
    setSelected(null)
  }

  const handleNounCatChange = (val: NounCategory) => {
    setNounCat(val)
    const newCandidates = generateBatch(lang, val)
    setCandidates(newCandidates)
    setSelected(null)
  }

  const handleConfirm = () => {
    if (selected) {
      onSelect(selected)
      onClose()
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CasinoIcon sx={{ color: 'primary.main' }} />
        随机名称生成器
      </DialogTitle>
      <DialogContent>
        {/* 配置行 */}
        <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>语言</Typography>
            <SegmentedControl
              value={lang}
              options={[
                { value: 'zh', label: '中文' },
                { value: 'en', label: 'English' },
              ]}
              onChange={handleLangChange}
            />
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>词库</Typography>
            <SegmentedControl
              value={nounCat}
              options={[
                { value: 'cosmos', label: '宇宙' },
                { value: 'animals', label: '动物' },
                { value: 'items', label: lang === 'zh' ? '器物' : '科技' },
              ]}
              onChange={handleNounCatChange}
            />
          </Box>
          <Box sx={{ ml: 'auto' }}>
            <Tooltip title="重新生成">
              <IconActionButton onClick={refresh} size="small">
                <RefreshIcon />
              </IconActionButton>
            </Tooltip>
          </Box>
        </Box>

        {/* 候选名称网格 */}
        <Grid2 container spacing={1}>
          {candidates.map(name => (
            <Grid2 key={name} size={{ xs: 6, sm: 4 }}>
              <Box
                onClick={() => setSelected(name)}
                sx={{
                  px: 1.5,
                  py: 1,
                  borderRadius: 1.5,
                  cursor: 'pointer',
                  border: '1px solid',
                  borderColor: selected === name
                    ? theme.palette.primary.main
                    : alpha(theme.palette.divider, 0.8),
                  bgcolor: selected === name
                    ? alpha(theme.palette.primary.main, 0.08)
                    : 'transparent',
                  transition: 'all 0.15s ease',
                  '&:hover': {
                    borderColor: theme.palette.primary.light,
                    bgcolor: alpha(theme.palette.primary.main, 0.05),
                  },
                  textAlign: 'center',
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: selected === name ? 600 : 400,
                    color: selected === name ? 'primary.main' : 'text.primary',
                    fontSize: lang === 'zh' ? '1rem' : '0.85rem',
                    fontFamily: lang === 'en' ? 'monospace' : 'inherit',
                  }}
                >
                  {name}
                </Typography>
              </Box>
            </Grid2>
          ))}
        </Grid2>

        {selected && (
          <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="caption" color="text.secondary">已选择：</Typography>
            <Chip
              label={selected}
              size="small"
              color="primary"
              variant="outlined"
              sx={CHIP_VARIANTS.base(true)}
              onDelete={() => setSelected(null)}
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <ActionButton onClick={onClose}>取消</ActionButton>
        <ActionButton variant="contained" disabled={!selected} onClick={handleConfirm}>
          使用此名称
        </ActionButton>
      </DialogActions>
    </Dialog>
  )
}
