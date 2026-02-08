import axios from '../axios'

export interface StarCheckData {
  allStarred: boolean
  starredRepositories: string[]
  unstarredRepositories: string[]
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
): Promise<StarCheckData> => {
  const response = await axios.get<StarCheckData>('/cloud/auth/github-stars', {
    params: { force, clear_cache: clearCache },
  })

  response.data.allStarred = Boolean(response.data.allStarred)
  return response.data
}

// 导出API接口
export default {
  checkGitHubStars,
}
