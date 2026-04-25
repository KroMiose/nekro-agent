import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  workspaceApi,
  type WorkspaceDetail,
  type McpServerConfig,
} from '../../../services/api/workspace'
import { useNotification } from '../../../hooks/useNotification'
import { useTranslation } from 'react-i18next'
import { McpServerManager } from '../components/McpShared'

export default function MCPTab({ workspace }: { workspace: WorkspaceDetail }) {
  const notification = useNotification()
  const queryClient = useQueryClient()
  const { t } = useTranslation('workspace')

  const { data: servers = [], isLoading } = useQuery({
    queryKey: ['workspace-mcp-servers', workspace.id],
    queryFn: () => workspaceApi.getMcpServers(workspace.id),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['workspace-mcp-servers', workspace.id] })
    queryClient.invalidateQueries({ queryKey: ['workspace-mcp', workspace.id] })
    queryClient.invalidateQueries({ queryKey: ['workspace', workspace.id] })
  }

  const handleAdd = async (server: McpServerConfig) => {
    try {
      await workspaceApi.addMcpServer(workspace.id, server)
      notification.success(t('detail.mcp.addSuccess'))
      invalidate()
    } catch (e) {
      notification.error(t('detail.mcp.addFailed', { message: (e as Error).message }))
      throw e
    }
  }

  const handleEdit = async (oldName: string, server: McpServerConfig) => {
    try {
      await workspaceApi.updateMcpServer(workspace.id, oldName, server)
      notification.success(t('detail.mcp.updateSuccess'))
      invalidate()
    } catch (e) {
      notification.error(t('detail.mcp.updateFailed', { message: (e as Error).message }))
      throw e
    }
  }

  const handleDelete = async (name: string) => {
    try {
      await workspaceApi.deleteMcpServer(workspace.id, name)
      notification.success(t('detail.mcp.deleteSuccess'))
      invalidate()
    } catch (e) {
      notification.error(t('detail.mcp.deleteFailed', { message: (e as Error).message }))
      throw e
    }
  }

  const handleToggleEnabled = async (server: McpServerConfig) => {
    try {
      await workspaceApi.updateMcpServer(workspace.id, server.name, { ...server, enabled: !server.enabled })
      invalidate()
    } catch (e) {
      notification.error((e as Error).message)
      throw e
    }
  }

  const handleImport = async (newServers: McpServerConfig[]) => {
    let added = 0
    for (const server of newServers) {
      try {
        await workspaceApi.addMcpServer(workspace.id, server)
        added++
      } catch { /* skip duplicates */ }
    }
    invalidate()
    notification.success(t('mcpServices.import.success', { count: added }))
  }

  const handleSyncToSandbox = async () => {
    try {
      await workspaceApi.syncMcpToSandbox(workspace.id)
      notification.success(t('detail.mcp.syncSuccess'))
    } catch (e) {
      notification.error(t('detail.mcp.syncFailed', { message: (e as Error).message }))
      throw e
    }
  }

  return (
    <McpServerManager
      servers={servers}
      loading={isLoading}
      onAdd={handleAdd}
      onEdit={handleEdit}
      onDelete={handleDelete}
      onToggleEnabled={handleToggleEnabled}
      onImport={handleImport}
      onSyncToSandbox={handleSyncToSandbox}
      cardVariant="workspace"
      emptyText={t('detail.mcp.empty')}
      jsonTitle={t('detail.mcp.title')}
      jsonHint={t('detail.mcp.jsonHint')}
      deleteTitle={t('detail.mcp.deleteTitle')}
      deleteContent={name => t('detail.mcp.deleteConfirm', { name })}
      t={t}
    />
  )
}
