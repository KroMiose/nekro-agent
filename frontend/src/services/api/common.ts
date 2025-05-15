import axios from './axios'

// 壁纸信息结构
export interface Wallpaper {
  id: string
  url: string
  filename: string
}

// 壁纸API响应结构
export interface WallpaperResponse {
  code: number
  msg: string
  data: Wallpaper[] | Wallpaper | null
}

// 壁纸可访问性缓存 - 避免频繁重复请求同一URL
const accessibilityCache: Record<string, { valid: boolean, timestamp: number }> = {};
// 缓存过期时间 - 30分钟
const CACHE_EXPIRY = 30 * 60 * 1000;

/**
 * 上传壁纸
 * @param file 壁纸文件
 * @returns Promise<WallpaperResponse>
 */
export const uploadWallpaper = async (file: File): Promise<WallpaperResponse> => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await axios.post<WallpaperResponse>('/common/wallpaper/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 60000,
    onUploadProgress: (progressEvent) => {
      const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1))
      console.log(`上传进度: ${percentCompleted}%`)
    }
  })
  return response.data
}

/**
 * 获取壁纸列表
 * @returns Promise<WallpaperResponse>
 */
export const getWallpapers = async (): Promise<WallpaperResponse> => {
  const response = await axios.get<WallpaperResponse>('/common/wallpaper/list')
  return response.data
}

/**
 * 删除壁纸
 * @param wallpaperId 壁纸ID
 * @returns Promise<WallpaperResponse>
 */
export const deleteWallpaper = async (wallpaperId: string): Promise<WallpaperResponse> => {
  const response = await axios.delete<WallpaperResponse>(`/common/wallpaper/${wallpaperId}`)
  return response.data
}

/**
 * 检查壁纸是否可访问
 * @param url 壁纸URL
 * @returns Promise<boolean>
 */
export const checkWallpaperAccessible = async (url: string): Promise<boolean> => {
  // 检查缓存中是否有有效记录
  const cached = accessibilityCache[url];
  const now = Date.now();
  if (cached && (now - cached.timestamp < CACHE_EXPIRY)) {
    return cached.valid;
  }

  try {
    // 尝试直接创建图片加载，这种方式更宽容，可以处理跨域问题
    return new Promise((resolve) => {
      const img = new Image();
      
      // 成功加载图片
      img.onload = () => {
        accessibilityCache[url] = { valid: true, timestamp: now };
        resolve(true);
      };
      
      // 如果加载失败，尝试使用fetch作为后备检查方法
      img.onerror = async () => {
        try {
          // 使用 HEAD 请求检查图片可访问性（节省带宽）
          const response = await fetch(url, { 
            method: 'HEAD',
            // 添加缓存控制，避免每次都从服务器拉取
            cache: 'force-cache'
          });
          const valid = response.ok;
          accessibilityCache[url] = { valid, timestamp: now };
          resolve(valid);
        } catch (error) {
          console.error('检查壁纸可访问性失败:', error);
          // 如果之前成功加载过，保持缓存记录
          if (cached && cached.valid) {
            console.log('网络请求失败，但使用历史缓存记录');
            resolve(true);
          } else {
            accessibilityCache[url] = { valid: false, timestamp: now };
            resolve(false);
          }
        }
      };
      
      // 开始加载图片
      img.src = url;
    });
  } catch (error) {
    console.error('检查壁纸可访问性失败:', error);
    // 如果之前成功加载过，保持缓存记录
    if (cached && cached.valid) {
      return true;
    }
    accessibilityCache[url] = { valid: false, timestamp: now };
    return false;
  }
}

// 导出常用接口
export const commonApi = {
  uploadWallpaper,
  getWallpapers,
  deleteWallpaper,
  checkWallpaperAccessible,
}
