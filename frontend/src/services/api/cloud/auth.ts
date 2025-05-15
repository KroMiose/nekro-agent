import axios from '../axios'

export interface StarCheckData {
  allStarred: boolean
  starredRepositories: string[]
  unstarredRepositories: string[]
}

export interface StarCheckResponse {
  code: number
  msg: string
  data: StarCheckData
}

/**
 * 检查用户是否已Star官方GitHub仓库
 * @param {boolean} force 是否强制检查（忽略缓存）
 * @param {boolean} clearCache 是否清除缓存后再检查
 * @returns {Promise<StarCheckResponse>} 响应结果
 */
export const checkGitHubStars = async (
  force: boolean = false,
  clearCache: boolean = false
): Promise<StarCheckResponse> => {
  const response = await axios.get<StarCheckResponse>('/cloud/auth/github-stars', {
    params: { force, clear_cache: clearCache },
  })

  // 确保数据类型正确
  if (response.data && response.data.data) {
    // 转换为布尔值以确保一致性
    response.data.data.allStarred = Boolean(response.data.data.allStarred)
  }

  return response.data
}

// 导出API接口
export default {
  checkGitHubStars,
}
