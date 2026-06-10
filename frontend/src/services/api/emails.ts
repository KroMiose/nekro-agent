import axios from './axios'
import { useAuthStore } from '../../stores/auth'

export interface Email {
  id: number
  account_username: string
  subject: string
  sender: string
  date: string | null
  body_preview: string
  has_attachments: boolean
  create_time: string
}

export interface EmailListResponse {
  items: Email[]
  pagination: {
    offset: number
    limit: number
    total: number
    has_more: boolean
  }
}

export interface EmailDetail {
  id: number
  account_username: string
  email_uid: string
  message_id: string
  subject: string
  sender: string
  recipients: string
  date: string | null
  body_text: string
  has_attachments: boolean
  attachment_names: string
  attachments: EmailAttachment[]
  in_reply_to: string
  references: string
  create_time: string
}

export interface EmailAttachment {
  name: string
  url: string
  extension: string
  preview_type: 'image' | 'markdown' | 'text' | 'pdf' | 'download'
}

export interface EmailRawContent {
  html_content: string
  text_content: string
}

function withAuthToken(url: string) {
  const token = useAuthStore.getState().token
  if (!token) {
    return url
  }
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}token=${encodeURIComponent(token)}`
}

export const emailsApi = {
  getEmails: async (params: { offset: number; limit: number; account?: string }) => {
    const response = await axios.get<EmailListResponse>('/emails', { params })
    return response.data
  },

  getEmailDetail: async (emailId: number) => {
    const response = await axios.get<EmailDetail>(`/emails/${emailId}`)
    return response.data
  },

  getEmailRawContent: async (emailId: number) => {
    const response = await axios.get<EmailRawContent>(`/emails/${emailId}/raw-content`)
    return response.data
  },

  getAttachmentText: async (url: string) => {
    const response = await fetch(withAuthToken(url), {
      headers: {
        Accept: 'text/plain, text/markdown, text/*;q=0.9, */*;q=0.8',
      },
    })
    if (!response.ok) {
      throw new Error(`Failed to fetch attachment text: ${response.status}`)
    }
    return response.text()
  },

  getAttachmentAccessUrl: (url: string) => withAuthToken(url),
}
