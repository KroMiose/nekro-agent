import { useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { unifiedConfigApi } from '../services/api/unified-config'

export function useKbEmbeddingGuard(
  messageKey: string,
) {
  const { t } = useTranslation('workspace')

  const systemConfigQuery = useQuery({
    queryKey: ['system-configs'],
    queryFn: () => unifiedConfigApi.getConfigList('system'),
    staleTime: 60_000,
  })

  const modelGroupsQuery = useQuery({
    queryKey: ['model-groups'],
    queryFn: () => unifiedConfigApi.getModelGroups(),
    staleTime: 60_000,
  })

  const isChecking = systemConfigQuery.isLoading || modelGroupsQuery.isLoading
  const hasQueryError = systemConfigQuery.isError || modelGroupsQuery.isError

  const isValid = useMemo(() => {
    if (!systemConfigQuery.data || !modelGroupsQuery.data) {
      return false
    }

    const item = systemConfigQuery.data.find(config => config.key === 'KB_EMBEDDING_MODEL_GROUP')
    const groupName = typeof item?.value === 'string' ? item.value.trim() : ''
    if (!groupName) {
      return false
    }

    const group = modelGroupsQuery.data[groupName]
    return group?.MODEL_TYPE === 'embedding'
  }, [modelGroupsQuery.data, systemConfigQuery.data])

  const kbEmbeddingActionsDisabled = !isChecking && !hasQueryError && !isValid
  const kbEmbeddingShowWarning = kbEmbeddingActionsDisabled
  const kbEmbeddingConfigMessage = t(messageKey)

  const withEmbeddingGuard = useCallback(
    (disabled?: boolean) => kbEmbeddingActionsDisabled || !!disabled,
    [kbEmbeddingActionsDisabled],
  )

  return {
    kbEmbeddingActionsDisabled,
    kbEmbeddingConfigMessage,
    kbEmbeddingShowWarning,
    withEmbeddingGuard,
  }
}
