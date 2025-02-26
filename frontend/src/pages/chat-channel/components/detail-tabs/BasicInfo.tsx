import React from 'react'
import {
  Box,
  Typography,
  Stack,
  Paper,
} from '@mui/material'
import {
  Message as MessageIcon,
  Person as PersonIcon,
  AccessTime as AccessTimeIcon,
  Update as UpdateIcon,
} from '@mui/icons-material'
import { ChatChannelDetail } from '../../../../services/api/chat-channel'

interface BasicInfoProps {
  channel: ChatChannelDetail
}

export default function BasicInfo({ channel }: BasicInfoProps) {
  const InfoItem = ({
    icon,
    label,
    value,
  }: {
    icon: React.ReactNode
    label: string
    value: React.ReactNode
  }) => (
    <Paper variant="outlined" className="p-3">
      <Stack direction="row" spacing={2} alignItems="center">
        {icon}
        <Box className="flex-1">
          <Typography variant="body2" color="textSecondary" className="mb-1">
            {label}
          </Typography>
          <Typography variant="body1">{value}</Typography>
        </Box>
      </Stack>
    </Paper>
  )

  return (
    <Box className="p-4">
      <Stack spacing={2}>
        <InfoItem
          icon={<MessageIcon color="primary" />}
          label="消息数量"
          value={`${channel.message_count} 条消息`}
        />
        <InfoItem
          icon={<PersonIcon color="info" />}
          label="参与用户数"
          value={`${channel.unique_users} 位用户`}
        />
        <InfoItem
          icon={<AccessTimeIcon color="success" />}
          label="对话开始时间"
          value={channel.conversation_start_time}
        />
        <InfoItem
          icon={<UpdateIcon color="warning" />}
          label="最后活跃时间"
          value={channel.last_message_time || '暂无消息'}
        />
      </Stack>
    </Box>
  )
} 