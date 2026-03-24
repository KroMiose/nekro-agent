import {
  Terminal as TerminalIcon,
  Http as HttpIcon,
} from '@mui/icons-material'
import type { McpServerConfig, McpServerType } from '../../../services/api/workspace'

/** JSONC 注释剥离（逐字符解析，正确处理字符串内的 //） */
export const stripJsoncComments = (text: string): string => {
  let result = ''
  let i = 0
  let inString = false
  let escaped = false
  while (i < text.length) {
    const ch = text[i]
    if (escaped) { result += ch; escaped = false; i++; continue }
    if (ch === '\\' && inString) { result += ch; escaped = true; i++; continue }
    if (ch === '"') { inString = !inString; result += ch; i++; continue }
    if (!inString) {
      if (ch === '/' && text[i + 1] === '/') {
        while (i < text.length && text[i] !== '\n') i++
        continue
      }
      if (ch === '/' && text[i + 1] === '*') {
        i += 2
        while (i < text.length && !(text[i] === '*' && text[i + 1] === '/')) i++
        i += 2
        continue
      }
    }
    result += ch; i++
  }
  return result
}

export const typeColor = (type: McpServerType) => {
  switch (type) {
    case 'stdio': return 'info'
    case 'sse': return 'warning'
    case 'http': return 'success'
    default: return 'default'
  }
}

export const typeIcon = (type: McpServerType) => {
  switch (type) {
    case 'stdio': return <TerminalIcon sx={{ fontSize: 16 }} />
    case 'sse': case 'http': return <HttpIcon sx={{ fontSize: 16 }} />
    default: return <TerminalIcon sx={{ fontSize: 16 }} />
  }
}

export const emptyServer = (): McpServerConfig => ({
  name: '',
  type: 'stdio',
  enabled: true,
  command: '',
  args: [],
  env: {},
  url: '',
  headers: {},
})
