import React from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  useTheme,
  alpha,
} from '@mui/material'
import {
  DeleteForever as DeleteForeverIcon,
  WarningAmber as WarningAmberIcon,
  ChatBubbleOutline as ChatBubbleOutlineIcon,
  TimerOutlined as TimerOutlinedIcon,
  ExtensionOutlined as ExtensionOutlinedIcon,
  PsychologyOutlined as PsychologyOutlinedIcon,
  ArticleOutlined as ArticleOutlinedIcon,
  FolderOutlined as FolderOutlinedIcon,
} from '@mui/icons-material'
import { useMutation } from '@tanstack/react-query'
import { chatChannelApi, type ChannelDeletePreview } from '../../../../services/api/chat-channel'
import { CARD_VARIANTS } from '../../../../theme/variants'
import ActionButton from '../../../../components/common/ActionButton'
import { useNotification } from '../../../../hooks/useNotification'

interface DangerZoneProps {
  chatKey: string
  channelName: string | null
  onDeleted: () => void
}

interface StatItem {
  icon: React.ReactNode
  label: string
  value: string | number
  color: 'error' | 'warning' | 'info' | 'success'
}

export default function DangerZone({ chatKey, channelName, onDeleted }: DangerZoneProps) {
  const theme = useTheme()
  const notification = useNotification()
  const [dialogOpen, setDialogOpen] = React.useState(false)
  const [preview, setPreview] = React.useState<ChannelDeletePreview | null>(null)
  const [previewLoading, setPreviewLoading] = React.useState(false)

  const { mutate: doDelete, isPending: isDeleting } = useMutation({
    mutationFn: () => chatChannelApi.deleteChannel(chatKey),
    onSuccess: () => {
      notification.success(`频道 ${channelName || chatKey} 已永久删除`)
      setDialogOpen(false)
      onDeleted()
    },
    onError: () => {
      notification.error('删除频道失败，请重试')
    },
  })

  const handleOpenDeleteDialog = async () => {
    setPreviewLoading(true)
    try {
      const data = await chatChannelApi.getDeletePreview(chatKey)
      setPreview(data)
      setDialogOpen(true)
    } catch {
      notification.error('获取删除预览失败，请重试')
    } finally {
      setPreviewLoading(false)
    }
  }

  const statItems: StatItem[] = preview
    ? [
        {
          icon: <ChatBubbleOutlineIcon fontSize="small" />,
          label: '消息记录',
          value: `${preview.message_count} 条`,
          color: 'error',
        },
        {
          icon: <TimerOutlinedIcon fontSize="small" />,
          label: '定时任务',
          value: `${preview.timer_job_count} 个`,
          color: 'warning',
        },
        {
          icon: <ExtensionOutlinedIcon fontSize="small" />,
          label: '插件数据',
          value: `${preview.plugin_data_count} 条`,
          color: 'info',
        },
        {
          icon: <ArticleOutlinedIcon fontSize="small" />,
          label: '记忆段落',
          value: `${preview.mem_paragraph_count} 条`,
          color: 'info',
        },
        {
          icon: <PsychologyOutlinedIcon fontSize="small" />,
          label: '记忆片段',
          value: `${preview.mem_episode_count} 条`,
          color: 'info',
        },
        {
          icon: <FolderOutlinedIcon fontSize="small" />,
          label: '上传文件目录',
          value: preview.upload_dir_exists ? '存在' : '无',
          color: preview.upload_dir_exists ? 'warning' : 'success',
        },
      ]
    : []

  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>

      {/* 危险区 Card */}
      <Card
        sx={{
          ...CARD_VARIANTS.default.styles,
          border: '1px solid',
          borderColor: alpha(theme.palette.error.main, 0.5),
        }}
      >
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
            <DeleteForeverIcon sx={{ color: 'error.main', fontSize: 18 }} />
            <Typography variant="subtitle2" color="error.main" fontWeight={600}>
              永久删除频道
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            删除后该频道所有聊天记录、定时任务、插件数据及文件目录将被永久清除，此操作
            <strong>不可撤销</strong>。
          </Typography>
          <ActionButton
            tone="danger"
            size="small"
            startIcon={previewLoading ? <CircularProgress size={14} color="inherit" /> : <DeleteForeverIcon />}
            disabled={previewLoading}
            onClick={handleOpenDeleteDialog}
          >
            删除此频道
          </ActionButton>
        </CardContent>
      </Card>

      {/* 删除确认对话框 */}
      <Dialog open={dialogOpen} onClose={() => !isDeleting && setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ pb: 1 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <WarningAmberIcon color="error" />
            <Typography variant="h6" fontWeight={600} color="error.main">
              确认永久删除频道
            </Typography>
          </Stack>
        </DialogTitle>

        <DialogContent>
          <Stack spacing={2}>
            {/* 不可逆警告 */}
            <Alert severity="error" sx={{ mt: 0.5 }}>
              此操作不可逆！删除后所有数据将永久丢失，无法通过任何方式恢复。
            </Alert>

            {/* 频道标识 */}
            <Box
              sx={{
                px: 1.5,
                py: 1,
                borderRadius: 1,
                bgcolor: alpha(theme.palette.text.primary, 0.04),
              }}
            >
              <Typography variant="caption" color="text.secondary" display="block">
                频道标识
              </Typography>
              <Typography
                variant="body2"
                sx={{ fontFamily: 'monospace', fontWeight: 600, wordBreak: 'break-all' }}
              >
                {chatKey}
              </Typography>
              {channelName && (
                <Typography variant="caption" color="text.secondary">
                  {channelName}
                </Typography>
              )}
            </Box>

            {/* 资源统计 */}
            {preview && (
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  将删除的资源
                </Typography>
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: 1,
                  }}
                >
                  {statItems.map((item) => (
                    <Box
                      key={item.label}
                      sx={{
                        px: 1.5,
                        py: 1,
                        borderRadius: 1,
                        bgcolor: alpha(theme.palette[item.color].main, 0.08),
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 0.25,
                      }}
                    >
                      <Stack direction="row" spacing={0.5} alignItems="center">
                        <Box sx={{ color: `${item.color}.main`, display: 'flex' }}>{item.icon}</Box>
                        <Typography variant="caption" color="text.secondary" noWrap>
                          {item.label}
                        </Typography>
                      </Stack>
                      <Typography
                        variant="body2"
                        fontWeight={600}
                        sx={{ color: `${item.color}.main` }}
                      >
                        {item.value}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
            )}

            {/* 注意事项 */}
            <Alert severity="warning">
              <Typography variant="body2" component="div">
                <Box component="ul" sx={{ m: 0, pl: 2 }}>
                  <li>关联工作区的频道绑定将同步解除</li>
                  <li>沙盒共享目录文件将被物理删除</li>
                  <li>记忆数据将保留，但来源频道信息会被清除</li>
                </Box>
              </Typography>
            </Alert>
          </Stack>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <ActionButton
            tone="secondary"
            onClick={() => setDialogOpen(false)}
            disabled={isDeleting}
          >
            取消
          </ActionButton>
          <ActionButton
            tone="danger"
            disabled={isDeleting}
            onClick={() => doDelete()}
            startIcon={isDeleting ? <CircularProgress size={16} color="inherit" /> : <DeleteForeverIcon />}
          >
            永久删除
          </ActionButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
