import axios from './axios'

export type EmailProvider = 'QQ邮箱' | '163邮箱' | 'Gmail' | 'Outlook' | '自定义'
export type EmailAuthType = 'password' | 'oauth2'
export type EmailTransportType = 'imap_smtp' | 'gmail_api' | 'microsoft_graph'
export type EmailOAuthProvider = '' | 'google' | 'microsoft'

export interface EmailAccount {
  index?: number
  EMAIL_ACCOUNT: EmailProvider
  CUSTOM_IMAP_HOST: string
  CUSTOM_IMAP_PORT: number
  CUSTOM_SMTP_HOST: string
  CUSTOM_SMTP_PORT: number
  CUSTOM_SMTP_SSL_PORT: number
  CUSTOM_SMTP_USE_SSL: boolean
  ENABLED: boolean
  RECEIVE_ENABLED?: boolean
  USE_PROXY: boolean
  USERNAME: string
  PASSWORD?: string
  HAS_PASSWORD?: boolean
  AUTH_TYPE: EmailAuthType
  TRANSPORT_TYPE: EmailTransportType
  OAUTH_PROVIDER: EmailOAuthProvider
  CLIENT_ID: string
  CLIENT_SECRET?: string
  TENANT_ID: string
  ACCESS_TOKEN?: string
  REFRESH_TOKEN?: string
  TOKEN_EXPIRES_AT: number
  LAST_TEST_SUCCESS?: boolean | null
  LAST_TEST_MESSAGE?: string
  LAST_TEST_TIME?: number
  SEND_ENABLED: boolean
  IS_DEFAULT_SENDER: boolean
}

export interface EmailAccountsResponse {
  accounts: EmailAccount[]
}

export interface EmailAuthorizeUrlResponse {
  authorize_url: string
  state: string
}

export interface EmailPullError {
  stage: string
  email_id?: string
  message: string
}

export interface EmailPullDebugStep {
  stage: string
  [key: string]: unknown
}

export interface EmailPullResult {
  success: boolean
  account_index?: number
  account_username: string
  provider?: EmailProvider
  auth_type?: EmailAuthType
  transport_type?: EmailTransportType
  mailbox: string
  search_unseen_only: boolean
  mark_as_seen_after_fetch: boolean
  max_per_poll: number
  requested_limit?: number | null
  effective_limit: number
  found_count: number
  processed_count: number
  failed_count: number
  marked_seen_count: number
  mark_seen_failed_count: number
  skipped_count: number
  reconnect_attempted: boolean
  reconnect_success?: boolean | null
  started_at: number
  finished_at: number
  duration_ms: number
  errors: EmailPullError[]
  debug_steps: EmailPullDebugStep[]
}

export const emailApi = {
  getAccounts: async (): Promise<EmailAccountsResponse> => {
    const response = await axios.get<EmailAccountsResponse>('/adapters/email/accounts')
    return response.data
  },

  createAccount: async (account: EmailAccount): Promise<{ success: boolean; index: number }> => {
    const response = await axios.post<{ success: boolean; index: number }>('/adapters/email/accounts', account)
    return response.data
  },

  updateAccount: async (index: number, account: Partial<EmailAccount>): Promise<{ success: boolean }> => {
    const response = await axios.put<{ success: boolean }>(`/adapters/email/accounts/${index}`, account)
    return response.data
  },

  deleteAccount: async (index: number): Promise<{ success: boolean }> => {
    const response = await axios.delete<{ success: boolean }>(`/adapters/email/accounts/${index}`)
    return response.data
  },

  testAccount: async (index: number): Promise<{ success: boolean; message: string; tested_at: number }> => {
    const response = await axios.post<{ success: boolean; message: string; tested_at: number }>(`/adapters/email/accounts/${index}/test`)
    return response.data
  },

  pullAccountInbox: async (
    index: number,
    payload: { unseen_only?: boolean; limit?: number } = { unseen_only: false }
  ): Promise<EmailPullResult> => {
    const response = await axios.post<EmailPullResult>(`/adapters/email/accounts/${index}/pull`, payload)
    return response.data
  },

  createAuthorizeUrl: async (
    index: number,
    redirectUri: string,
    state: string
  ): Promise<EmailAuthorizeUrlResponse> => {
    const response = await axios.post<EmailAuthorizeUrlResponse>(`/adapters/email/accounts/${index}/oauth/authorize-url`, {
      redirect_uri: redirectUri,
      state,
    })
    return response.data
  },

  handleOAuthCallback: async (index: number, code: string, redirectUri: string): Promise<{ success: boolean }> => {
    const response = await axios.post<{ success: boolean }>(`/adapters/email/accounts/${index}/oauth/callback`, {
      code,
      redirect_uri: redirectUri,
    })
    return response.data
  },
}
