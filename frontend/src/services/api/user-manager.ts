import axios from './axios'

export enum UserStatus {
  Normal = 'normal',
  Passive = 'passive',
  Banned = 'banned',
}

export interface User {
  id: number
  username: string
  adapter_key: string
  platform_userid: string
  unique_id: string
  perm_level: number
  perm_role: string
  login_time: string
  ban_until: string | null
  prevent_trigger_until: string | null
  is_active: boolean
  is_prevent_trigger: boolean
  create_time: string
  update_time: string
  ext_data?: Record<string, unknown>
}

export interface UserListParams {
  page: number
  page_size: number
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface UserListResponse {
  total: number
  items: User[]
  page: number
  page_size: number
}

export interface UserFormData {
  username: string
  password: string
  adapter_key: string
  platform_userid: string
  access_key: string
}

export interface UserUpdateData {
  username: string
  perm_level: number
  access_key: string
}

export interface ActionResponse {
  ok: boolean
}

export const getUserStatus = (user: User): UserStatus => {
  if (!user.is_active) {
    return UserStatus.Banned
  }
  if (user.is_prevent_trigger) {
    return UserStatus.Passive
  }
  return UserStatus.Normal
}

export const getUserList = async (params: UserListParams) => {
  const response = await axios.get<UserListResponse>('/user-manager/list', { params })
  return response.data
}

export const getUserDetail = async (id: number) => {
  const response = await axios.get<User>(`/user-manager/${id}`)
  return response.data
}

export const createUser = async (data: UserFormData) => {
  const response = await axios.post<ActionResponse>('/user-manager/create', data)
  return response.data
}

export const updateUser = async (id: number, data: UserUpdateData) => {
  const response = await axios.put<ActionResponse>(`/user-manager/${id}`, data)
  return response.data
}

export const deleteUser = async (id: number) => {
  const response = await axios.delete<ActionResponse>(`/user-manager/${id}`)
  return response.data
}

export const banUser = async (id: number, banUntil: string | null) => {
  const formattedBanUntil = banUntil ? new Date(banUntil).toISOString() : null
  const response = await axios.post<ActionResponse>(`/user-manager/${id}/ban`, {
    ban_until: formattedBanUntil,
  })
  return response.data
}

export const setPreventTrigger = async (id: number, preventTriggerUntil: string | null) => {
  const formattedPreventTriggerUntil = preventTriggerUntil
    ? new Date(preventTriggerUntil).toISOString()
    : null
  const response = await axios.post<ActionResponse>(`/user-manager/${id}/prevent-trigger`, {
    prevent_trigger_until: formattedPreventTriggerUntil,
  })
  return response.data
}

export const resetPassword = async (id: number, password: string) => {
  const response = await axios.post<ActionResponse>(`/user-manager/${id}/reset-password`, { password })
  return response.data
}
