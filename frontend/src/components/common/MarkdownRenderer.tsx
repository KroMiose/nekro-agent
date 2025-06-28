import React from 'react'
import { Box, useTheme, Link, SxProps, Theme } from '@mui/material'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useColorMode } from '../../stores/theme'

const markdownStyles = (theme: Theme): SxProps<Theme> => ({
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
})

interface MarkdownRendererProps {
  children: string
  sx?: SxProps<Theme>
}

export default function MarkdownRenderer({ children, sx }: MarkdownRendererProps) {
  const theme = useTheme()
  const { mode } = useColorMode()

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
    a: (props: { href?: string; children?: React.ReactNode }) => (
      <Link href={props.href} target="_blank" rel="noopener noreferrer">
        {props.children}
      </Link>
    ),
  }

  return (
    <Box sx={[markdownStyles(theme), ...(Array.isArray(sx) ? sx : [sx])]}>
      <ReactMarkdown components={markdownComponents}>{children}</ReactMarkdown>
    </Box>
  )
}
