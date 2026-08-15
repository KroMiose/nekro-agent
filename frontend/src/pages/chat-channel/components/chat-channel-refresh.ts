import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { chatChannelApi, type ChatChannelDetail } from '../../../services/api/chat-channel'
import { useNotification } from '../../../hooks/useNotification'

/**
 * 聊天频道信息刷新编排：平台同步频道名称 + 失败回退 + 缓存更新。
 * 组件只需调用 refresh 并自行管理加载状态。
 */
export function useChatChannelRefresh(chatKey: string) {
  const queryClient = useQueryClient()
  const notification = useNotification()
  const { t } = useTranslation('chat-channel')

  const refresh = async (): Promise<void> => {
    let refreshedDetail: ChatChannelDetail | null = null
    try {
      // 请求后端从平台实时同步频道名称（适配器不支持或获取失败时保留原名称）
      refreshedDetail = await chatChannelApi.refreshDetail(chatKey)
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error)
      console.error('[ChatChannelDetail] refreshDetail failed, falling back to invalidateQueries', { chatKey, error })
      notification.warning(t('channelDetail.refreshFallback', { reason }))
    }

    if (refreshedDetail) {
      // 返回的详情已是后端同步后的权威数据，直接更新详情缓存；仅使列表失效以同步名称展示
      queryClient.setQueryData(['chat-channel-detail', chatKey], refreshedDetail)
    } else {
      // 同步失败时回退为普通缓存失效，仍从数据库刷新当前状态
      await queryClient.invalidateQueries({ queryKey: ['chat-channel-detail', chatKey] })
    }
    await queryClient.invalidateQueries({ queryKey: ['chat-channel-management-list'] })
    await queryClient.invalidateQueries({ queryKey: ['channel-directory'] })
  }

  return { refresh }
}
