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
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useColorMode } from '../../stores/theme'
import { adaptersApi, AdapterDetailInfo } from '../../services/api/adapters'
import { CARD_VARIANTS } from '../../theme/variants'

interface AdapterContextType {
  adapterInfo: AdapterDetailInfo
}

export default function AdapterHomePage() {
  const { adapterKey } = useParams<{ adapterKey: string }>()
  const { adapterInfo } = useOutletContext<AdapterContextType>()
  const theme = useTheme()
  const { mode } = useColorMode()

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

  const markdownComponents = {
    code({
      inline,
      className,
      children,
      ...props
    }: {
      inline?: boolean
      className?: string
      children?: React.ReactNode
    }) {
      const match = /language-(\w+)/.exec(className || '')
      return !inline && match ? (
        <SyntaxHighlighter
          style={mode === 'dark' ? vscDarkPlus : oneLight}
          language={match[1]}
          PreTag="div"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      )
    },
  }

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
              版本: {adapterInfo.version}
              {adapterInfo.author && ` • 作者: ${adapterInfo.author}`}
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
              加载文档中...
            </Typography>
          </CardContent>
        </Card>
      ) : docsError ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          加载文档失败：{docsError.message}
        </Alert>
      ) : docs?.exists ? (
        <Card sx={CARD_VARIANTS.default.styles}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
              <DescriptionIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                适配器文档
              </Typography>
            </Box>
            <Box
              sx={{
                '& h1': {
                  fontSize: '1.75rem',
                  fontWeight: 600,
                  color: theme.palette.text.primary,
                  marginTop: theme.spacing(3),
                  marginBottom: theme.spacing(2),
                  '&:first-child': { marginTop: 0 },
                },
                '& h2': {
                  fontSize: '1.5rem',
                  fontWeight: 600,
                  color: theme.palette.text.primary,
                  marginTop: theme.spacing(3),
                  marginBottom: theme.spacing(2),
                },
                '& h3': {
                  fontSize: '1.25rem',
                  fontWeight: 600,
                  color: theme.palette.text.primary,
                  marginTop: theme.spacing(2),
                  marginBottom: theme.spacing(1),
                },
                '& h4, & h5, & h6': {
                  fontSize: '1.125rem',
                  fontWeight: 600,
                  color: theme.palette.text.primary,
                  marginTop: theme.spacing(2),
                  marginBottom: theme.spacing(1),
                },
                '& p': {
                  color: theme.palette.text.secondary,
                  lineHeight: 1.7,
                  marginBottom: theme.spacing(2),
                },
                '& ul, & ol': {
                  color: theme.palette.text.secondary,
                  paddingLeft: theme.spacing(3),
                  marginBottom: theme.spacing(2),
                },
                '& li': {
                  marginBottom: theme.spacing(0.5),
                  lineHeight: 1.6,
                },
                '& code': {
                  backgroundColor:
                    theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
                  color: theme.palette.mode === 'dark' ? '#ff6b6b' : '#d73a49',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                  fontSize: '0.875rem',
                },
                '& pre': {
                  backgroundColor:
                    theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                  padding: theme.spacing(2),
                  borderRadius: '8px',
                  overflow: 'auto',
                  marginBottom: theme.spacing(2),
                  border: `1px solid ${theme.palette.divider}`,
                  '& code': {
                    backgroundColor: 'transparent',
                    color: 'inherit',
                    padding: 0,
                  },
                },
                '& blockquote': {
                  borderLeft: `4px solid ${theme.palette.primary.main}`,
                  paddingLeft: theme.spacing(2),
                  margin: 0,
                  marginBottom: theme.spacing(2),
                  fontStyle: 'italic',
                  color: theme.palette.text.secondary,
                  backgroundColor:
                    theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
                  padding: theme.spacing(1, 2),
                  borderRadius: '0 4px 4px 0',
                },
                '& table': {
                  width: '100%',
                  borderCollapse: 'collapse',
                  marginBottom: theme.spacing(2),
                  '& th, & td': {
                    border: `1px solid ${theme.palette.divider}`,
                    padding: theme.spacing(1),
                    textAlign: 'left',
                  },
                  '& th': {
                    backgroundColor:
                      theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
                    fontWeight: 600,
                  },
                },
              }}
            >
              <ReactMarkdown components={markdownComponents}>{docs.content}</ReactMarkdown>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Alert severity="info">该适配器暂无文档说明。</Alert>
      )}
    </Box>
  )
}
