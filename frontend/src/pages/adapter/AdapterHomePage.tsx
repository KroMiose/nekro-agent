import {
  Box,
  Card,
  CardContent,
  Typography,
  Alert,
  useTheme,
  CircularProgress,
} from '@mui/material'
import { Description as DescriptionIcon } from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { useOutletContext, useParams } from 'react-router-dom'
import MarkdownRenderer from '../../components/common/MarkdownRenderer'
import { adaptersApi, AdapterDetailInfo } from '../../services/api/adapters'
import { CARD_VARIANTS } from '../../theme/variants'
import { useTranslation } from 'react-i18next'

interface AdapterContextType {
  adapterInfo: AdapterDetailInfo
}

export default function AdapterHomePage() {
  const { adapterKey } = useParams<{ adapterKey: string }>()
  const { adapterInfo } = useOutletContext<AdapterContextType>()
  const theme = useTheme()
  const { t } = useTranslation('adapter')

  // 获取适配器文档
  const {
    data: docs,
    isLoading: docsLoading,
    error: docsError,
  } = useQuery({
    queryKey: ['adapter-docs', adapterKey],
    queryFn: () => adaptersApi.getAdapterDocs(adapterKey!),
    enabled: !!adapterKey,
  })

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        p: 2,
        '&::-webkit-scrollbar': { width: '6px' },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: theme.palette.divider,
          borderRadius: '3px',
        },
      }}
    >
      {/* 适配器基本信息 */}
      <Card sx={{ ...CARD_VARIANTS.default.styles, mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            {adapterInfo.name}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.6 }}>
            {adapterInfo.description}
          </Typography>
          {adapterInfo.version && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              {t('home.version')}: {adapterInfo.version}
              {adapterInfo.author && ` • ${t('home.author')}: ${adapterInfo.author}`}
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* 适配器文档 */}
      {docsLoading ? (
        <Card sx={CARD_VARIANTS.default.styles}>
          <CardContent sx={{ p: 3, textAlign: 'center' }}>
            <CircularProgress size={32} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              {t('home.loadingDocs')}
            </Typography>
          </CardContent>
        </Card>
      ) : docsError ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          {t('home.loadDocsFailed')}：{docsError.message}
        </Alert>
      ) : docs?.exists ? (
        <Card sx={CARD_VARIANTS.default.styles}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
              <DescriptionIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {t('home.adapterDocs')}
              </Typography>
            </Box>
            <MarkdownRenderer>{docs.content}</MarkdownRenderer>
          </CardContent>
        </Card>
      ) : (
        <Alert severity="info">{t('home.noDocs')}</Alert>
      )}
    </Box>
  )
}
