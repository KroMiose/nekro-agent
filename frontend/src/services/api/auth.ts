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

export interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

export const authApi = {
  login: async (params: LoginParams) => {
    try {
      const response = await axios.post<ApiResponse<LoginResponse>>('/user/login', params)
      if (response.data.code !== 200) {
        throw new Error(response.data.msg)
      }
      return response.data.data
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  },

  getUserInfo: async () => {
    try {
      const response = await axios.get<ApiResponse<UserInfo>>('/user/me')
      if (response.data.code !== 200) {
        throw new Error(response.data.msg)
      }
      return response.data.data
    } catch (error) {
      console.error('Get user info failed:', error)
      throw error
    }
  },
}
