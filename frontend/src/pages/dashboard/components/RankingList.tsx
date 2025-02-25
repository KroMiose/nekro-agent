import React from 'react'
import {
  Card,
  CardContent,
  Typography,
  Box,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  CircularProgress,
  Divider
} from '@mui/material'
import { Person as PersonIcon, Group as GroupIcon } from '@mui/icons-material'
import { RankingItem } from '../../../services/api/dashboard'

interface RankingListProps {
  title: string
  data?: RankingItem[]
  loading?: boolean
  type: 'users' | 'groups'
}

export const RankingList: React.FC<RankingListProps> = ({
  title,
  data = [],
  loading = false,
  type
}) => {
  // 获取默认图标
  const getDefaultIcon = () => {
    return type === 'users' ? <PersonIcon /> : <GroupIcon />
  }

  return (
    <Card className="w-full h-full">
      <CardContent className="h-full">
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        
        {loading ? (
          <Box className="flex items-center justify-center h-[300px]">
            <CircularProgress />
          </Box>
        ) : data.length === 0 ? (
          <Box className="flex items-center justify-center h-[300px]">
            <Typography variant="body2" color="text.secondary">
              暂无数据
            </Typography>
          </Box>
        ) : (
          <List className="overflow-auto max-h-[300px]">
            {data.map((item, index) => (
              <React.Fragment key={item.id}>
                <ListItem>
                  <Box className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-light mr-2">
                    <Typography variant="body2" fontWeight="bold">
                      {index + 1}
                    </Typography>
                  </Box>
                  <ListItemAvatar>
                    <Avatar src={item.avatar}>
                      {getDefaultIcon()}
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={item.name}
                    secondary={`${item.value} 次互动`}
                  />
                </ListItem>
                {index < data.length - 1 && <Divider variant="inset" component="li" />}
              </React.Fragment>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  )
} 