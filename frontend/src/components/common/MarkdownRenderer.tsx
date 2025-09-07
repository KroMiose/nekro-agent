import React, { memo, useMemo } from 'react'
import { Box, useTheme, Link, SxProps, Theme } from '@mui/material'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { useColorMode } from '../../stores/theme'

// 将常用的插件数组提取为常量，避免每次渲染都创建新数组
const REMARK_PLUGINS = [remarkGfm]
const REHYPE_PLUGINS = [rehypeRaw]

// 优化样式函数，使用更高效的样式生成
const createMarkdownStyles = (theme: Theme): SxProps<Theme> => ({
  '& h1': {
    fontSize: '1.75rem',
    fontWeight: 600,
    color: theme.palette.text.primary,
    marginTop: theme.spacing(3),
    marginBottom: theme.spacing(2),
    borderBottom: `1px solid ${theme.palette.divider}`,
    paddingBottom: theme.spacing(1),
    '&:first-of-type': { marginTop: 0 },
  },
  '& h2': {
    fontSize: '1.5rem',
    fontWeight: 600,
    color: theme.palette.text.primary,
    marginTop: theme.spacing(3),
    marginBottom: theme.spacing(2),
    borderBottom: `1px solid ${theme.palette.divider}`,
    paddingBottom: theme.spacing(1),
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
  '& a': {
    color: theme.palette.secondary.main,
    textDecoration: 'none',
    fontWeight: 500,
    '&:hover': {
      textDecoration: 'underline',
    },
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
    backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
    color: theme.palette.mode === 'dark' ? '#ff6b6b' : '#d73a49',
    padding: '2px 6px',
    borderRadius: '4px',
    fontFamily: 'Consolas, Monaco, "Courier New", monospace',
    fontSize: '0.875rem',
  },
  '& pre': {
    backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
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
    backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
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
  // HTML 元素样式
  '& img': {
    maxWidth: '100%',
    height: 'auto',
    borderRadius: '4px',
    marginBottom: theme.spacing(1),
  },
  '& hr': {
    border: 'none',
    borderTop: `1px solid ${theme.palette.divider}`,
    margin: theme.spacing(3, 0),
  },
  '& strong, & b': {
    fontWeight: 600,
    color: theme.palette.text.primary,
  },
  '& em, & i': {
    fontStyle: 'italic',
  },
  '& mark': {
    backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255, 235, 59, 0.3)' : 'rgba(255, 235, 59, 0.5)',
    color: theme.palette.text.primary,
    padding: '2px 4px',
    borderRadius: '2px',
  },
  '& del': {
    textDecoration: 'line-through',
    color: theme.palette.text.disabled,
  },
  '& kbd': {
    backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
    border: `1px solid ${theme.palette.divider}`,
    borderRadius: '3px',
    padding: '2px 6px',
    fontFamily: 'Consolas, Monaco, "Courier New", monospace',
    fontSize: '0.875rem',
    color: theme.palette.text.primary,
  },
  '& sub, & sup': {
    fontSize: '0.75rem',
    lineHeight: 0,
    position: 'relative',
    verticalAlign: 'baseline',
  },
  '& sub': {
    bottom: '-0.25em',
  },
  '& sup': {
    top: '-0.5em',
  },
  '& details': {
    marginBottom: theme.spacing(2),
    '& summary': {
      cursor: 'pointer',
      fontWeight: 600,
      color: theme.palette.text.primary,
      marginBottom: theme.spacing(1),
      '&:hover': {
        color: theme.palette.primary.main,
      },
    },
  },
  // 标准 HTML 元素样式
  '& div[align="center"]': {
    textAlign: 'center',
    margin: theme.spacing(2, 0),
  },
  '& center': {
    display: 'block',
    textAlign: 'center',
    margin: theme.spacing(2, 0),
  },
  '& u': {
    textDecoration: 'underline',
  },
})

interface MarkdownRendererProps {
  children: string
  sx?: SxProps<Theme>
  /**
   * 是否启用语法高亮（默认：true）
   * 在大文档中禁用可以提升性能
   */
  enableSyntaxHighlight?: boolean
  /**
   * 是否启用HTML渲染（默认：true）
   */
  enableHtml?: boolean
  /**
   * 自定义类名
   */
  className?: string
}

// 代码组件单独抽离，提升性能
interface CodeComponentProps {
  inline?: boolean
  className?: string
  children?: React.ReactNode
  enableSyntaxHighlight: boolean
  syntaxStyle: any
}

const CodeComponent = memo<CodeComponentProps>(({ 
  inline, 
  className, 
  children, 
  enableSyntaxHighlight,
  syntaxStyle,
  ...props 
}) => {
  const match = /language-(\w+)/.exec(className || '')
  
  if (!inline && match && enableSyntaxHighlight) {
    return (
      <SyntaxHighlighter
        style={syntaxStyle}
        language={match[1]}
        PreTag="div"
        {...props}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    )
  }
  
  return (
    <code className={className} {...props}>
      {children}
    </code>
  )
})
CodeComponent.displayName = 'CodeComponent'

// 链接组件单独抽离
interface LinkComponentProps {
  href?: string
  children?: React.ReactNode
}

const LinkComponent = memo<LinkComponentProps>(({ href, children }) => (
  <Link 
    href={href} 
    target="_blank" 
    rel="noopener noreferrer"
  >
    {children}
  </Link>
))
LinkComponent.displayName = 'LinkComponent'

const MarkdownRenderer = memo<MarkdownRendererProps>(({
  children,
  sx,
  enableSyntaxHighlight = true,
  enableHtml = true,
  className
}) => {
  const theme = useTheme()
  const { mode } = useColorMode()
  
  // 使用 useMemo 缓存样式，避免每次渲染都重新计算
  const markdownStyles = useMemo(
    () => createMarkdownStyles(theme),
    [theme]
  )
  
  // 使用 useMemo 缓存语法高亮样式
  const syntaxStyle = useMemo(
    () => mode === 'dark' ? vscDarkPlus : oneLight,
    [mode]
  )
  
  // 使用 useMemo 缓存组件配置，避免每次渲染都创建新对象
  const markdownComponents = useMemo(
    () => ({
      code: (props: any) => (
        <CodeComponent
          {...props}
          enableSyntaxHighlight={enableSyntaxHighlight}
          syntaxStyle={syntaxStyle}
        />
      ),
      a: LinkComponent,
    }),
    [enableSyntaxHighlight, syntaxStyle]
  )
  
  // 使用 useMemo 缓存插件配置
  const plugins = useMemo(
    () => ({
      remarkPlugins: REMARK_PLUGINS,
      rehypePlugins: enableHtml ? REHYPE_PLUGINS : undefined,
    }),
    [enableHtml]
  )
  
  // 使用 useMemo 缓存最终样式
  const finalStyles = useMemo(
    () => [markdownStyles, ...(Array.isArray(sx) ? sx : [sx])],
    [markdownStyles, sx]
  )

  return (
    <Box 
      className={className}
      sx={finalStyles}
    >
      <ReactMarkdown 
        components={markdownComponents}
        remarkPlugins={plugins.remarkPlugins}
        rehypePlugins={plugins.rehypePlugins}
      >
        {children}
      </ReactMarkdown>
    </Box>
  )
})
MarkdownRenderer.displayName = 'MarkdownRenderer'

export default MarkdownRenderer
