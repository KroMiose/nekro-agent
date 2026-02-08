import axios from './axios'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserInfo {
  username: string
  userId: number
  perm_level: number
  perm_role: string
}

export interface UpdatePasswordParams {
  user_id?: number
  password: string
}

export interface ActionResponse {
  ok: boolean
}

export const authApi = {
  login: async (params: LoginParams) => {
    const response = await axios.post<LoginResponse>('/user/login', params)
    return response.data
  },

  getUserInfo: async () => {
    const response = await axios.get<UserInfo>('/user/me')
    return response.data
  },

  updatePassword: async (params: UpdatePasswordParams) => {
    const response = await axios.put<ActionResponse>('/user/password', params)
    return response.data
  },
}
