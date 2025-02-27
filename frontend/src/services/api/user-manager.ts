import axios from './axios'

// 用户状态枚举
export enum UserStatus {
  Normal = '正常',
  Passive = '消极',
  Banned = '封禁'
}

// 用户类型定义
export interface User {
  id: number
  username: string
  bind_qq: string
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
  bind_qq: string
  access_key: string
}

export interface UserUpdateData {
  username: string
  perm_level: number
  access_key: string
}

// 获取用户状态
export const getUserStatus = (user: User): UserStatus => {
  if (!user.is_active) {
    return UserStatus.Banned
  }
  if (user.is_prevent_trigger) {
    return UserStatus.Passive
  }
  return UserStatus.Normal
}

// 获取用户列表
export const getUserList = async (params: UserListParams) => {
  const response = await axios.get('/user-manager/list', { params })
  return response.data
}

// 获取用户详情
export const getUserDetail = async (id: number) => {
  const response = await axios.get(`/user-manager/${id}`)
  return response.data
}

// 创建用户
export const createUser = async (data: UserFormData) => {
  const response = await axios.post('/user-manager/create', data)
  return response.data
}

// 更新用户
export const updateUser = async (id: number, data: UserUpdateData) => {
  const response = await axios.put(`/user-manager/${id}`, data)
  return response.data
}

// 删除用户
export const deleteUser = async (id: number) => {
  const response = await axios.delete(`/user-manager/${id}`)
  return response.data
}

// 封禁/解封用户
export const banUser = async (id: number, banUntil: string | null) => {
  // 如果有日期，确保添加 UTC 时区信息
  const formattedBanUntil = banUntil ? new Date(banUntil).toISOString() : null
  const response = await axios.post(`/user-manager/${id}/ban`, { ban_until: formattedBanUntil })
  return response.data
}

// 设置触发权限
export const setPreventTrigger = async (id: number, preventTriggerUntil: string | null) => {
  // 如果有日期，确保添加 UTC 时区信息
  const formattedPreventTriggerUntil = preventTriggerUntil
    ? new Date(preventTriggerUntil).toISOString()
    : null
  const response = await axios.post(`/user-manager/${id}/prevent-trigger`, {
    prevent_trigger_until: formattedPreventTriggerUntil,
  })
  return response.data
}

// 重置密码
export const resetPassword = async (id: number, password: string) => {
  const response = await axios.post(`/user-manager/${id}/reset-password`, { password })
  return response.data
}
