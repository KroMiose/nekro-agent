import axios from '../axios'

export interface WebMcpExternalAuthStatus {
  enabled: boolean
  configured: boolean
  token_preview: string | null
  updated_at: string | null
}

export interface WebMcpAuthStatusResponse {
  ok: boolean
  mcp_url: string
  external: WebMcpExternalAuthStatus
}

export interface WebMcpExternalAuthUpdateRequest {
  enabled: boolean
  token?: string
}

export interface WebMcpExternalAuthGenerateResponse extends WebMcpAuthStatusResponse {
  token: string
}

export const webAdapterApi = {
  getMcpAuth: async (): Promise<WebMcpAuthStatusResponse> => {
    const { data } = await axios.get<WebMcpAuthStatusResponse>('/adapters/web/mcp-auth')
    return data
  },

  updateExternalMcpAuth: async (
    payload: WebMcpExternalAuthUpdateRequest
  ): Promise<WebMcpAuthStatusResponse> => {
    const { data } = await axios.put<WebMcpAuthStatusResponse>('/adapters/web/mcp-auth/external', payload)
    return data
  },

  generateExternalMcpAuth: async (): Promise<WebMcpExternalAuthGenerateResponse> => {
    const { data } = await axios.post<WebMcpExternalAuthGenerateResponse>('/adapters/web/mcp-auth/external/generate')
    return data
  },

  clearExternalMcpAuth: async (): Promise<WebMcpAuthStatusResponse> => {
    const { data } = await axios.delete<WebMcpAuthStatusResponse>('/adapters/web/mcp-auth/external')
    return data
  },
}
