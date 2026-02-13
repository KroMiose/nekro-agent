import axios from './axios'

export interface Wallpaper {
  id: string
  url: string
  filename: string
}

export interface ActionResponse {
  ok: boolean
}

const accessibilityCache: Record<string, { valid: boolean; timestamp: number }> = {}
const CACHE_EXPIRY = 30 * 60 * 1000

export const uploadWallpaper = async (file: File): Promise<Wallpaper> => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await axios.post<Wallpaper>('/common/wallpaper/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 60000,
  })
  return response.data
}

export const getWallpapers = async (): Promise<Wallpaper[]> => {
  const response = await axios.get<Wallpaper[]>('/common/wallpaper/list')
  return response.data
}

export const deleteWallpaper = async (wallpaperId: string): Promise<ActionResponse> => {
  const response = await axios.delete<ActionResponse>(`/common/wallpaper/${wallpaperId}`)
  return response.data
}

export const checkWallpaperAccessible = async (url: string): Promise<boolean> => {
  const cached = accessibilityCache[url]
  const now = Date.now()
  if (cached && now - cached.timestamp < CACHE_EXPIRY) {
    return cached.valid
  }

  try {
    return new Promise(resolve => {
      const img = new Image()

      img.onload = () => {
        accessibilityCache[url] = { valid: true, timestamp: now }
        resolve(true)
      }

      img.onerror = async () => {
        try {
          const response = await fetch(url, {
            method: 'HEAD',
            cache: 'force-cache',
          })
          const valid = response.ok
          accessibilityCache[url] = { valid, timestamp: now }
          resolve(valid)
        } catch (error) {
          if (cached && cached.valid) {
            resolve(true)
          } else {
            accessibilityCache[url] = { valid: false, timestamp: now }
            resolve(false)
          }
        }
      }

      img.src = url
    })
  } catch (error) {
    if (cached && cached.valid) {
      return true
    }
    accessibilityCache[url] = { valid: false, timestamp: now }
    return false
  }
}

export const commonApi = {
  uploadWallpaper,
  getWallpapers,
  deleteWallpaper,
  checkWallpaperAccessible,
}
