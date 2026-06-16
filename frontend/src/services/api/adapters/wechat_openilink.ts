import axios from '../axios'

export type OpenILinkLoginState = 'idle' | 'waiting' | 'qr' | 'scanned' | 'expired' | 'error' | 'logged_in' | 'stopped' | 'unavailable'

export interface WechatOpenILinkLoginStatus {
  state: OpenILinkLoginState
  logged_in: boolean
  login_url: string | null
  error_message: string | null
  updated_at: number | null
  self_user_id: string | null
  self_user_name: string | null
}

export const wechatOpenILinkApi = {
  getLoginStatus: async () => {
    const { data } = await axios.get<WechatOpenILinkLoginStatus>('/adapters/wechat_openilink/login/status')
    return data
  },
}
