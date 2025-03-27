import React, { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  InputAdornment,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Divider,
  SelectChangeEvent,
  TablePagination,
} from '@mui/material'
import { Search as SearchIcon, Clear as ClearIcon } from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { chatChannelApi } from '../../services/api/chat-channel'
import ChatChannelList from './components/ChatChannelList'
import ChatChannelDetail from './components/ChatChannelDetail'

export default function ChatChannelPage() {
  const [search, setSearch] = useState('')
  const [chatType, setChatType] = useState<string>('')
  const [isActive, setIsActive] = useState<string>('')
  const [selectedChatKey, setSelectedChatKey] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  // 查询会话列表
  const { data: channelList, isLoading } = useQuery({
    queryKey: ['chat-channels', search, chatType, isActive, page, pageSize],
    queryFn: () =>
      chatChannelApi.getList({
        page,
        page_size: pageSize,
        search: search || undefined,
        chat_type: chatType || undefined,
        is_active: isActive === '' ? undefined : isActive === 'true',
      }),
  })

  // 处理搜索
  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(event.target.value)
    setPage(1)
  }

  // 处理清除搜索
  const handleClearSearch = () => {
    setSearch('')
    setPage(1)
  }

  // 处理类型筛选
  const handleChatTypeChange = (event: SelectChangeEvent) => {
    setChatType(event.target.value)
    setPage(1)
  }

  // 处理状态筛选
  const handleActiveChange = (event: SelectChangeEvent) => {
    setIsActive(event.target.value)
    setPage(1)
  }

  // 处理选择会话
  const handleSelectChannel = (chatKey: string) => {
    setSelectedChatKey(chatKey)
  }

  return (
    <Box className="h-[calc(100vh-90px)] flex gap-3 overflow-hidden p-2">
      {/* 左侧详情面板 */}
      <Paper className="flex-1 overflow-hidden">
        {selectedChatKey ? (
          <ChatChannelDetail chatKey={selectedChatKey} />
        ) : (
          <Box className="h-full flex items-center justify-center">
            <Typography color="textSecondary">请选择一个会话查看详情</Typography>
          </Box>
        )}
      </Paper>

      {/* 右侧会话列表 */}
      <Paper className="w-[320px] flex-shrink-0 flex flex-col overflow-hidden">
        <Box className="p-2 flex-shrink-0">
          <Stack spacing={1.5}>
            {/* 搜索框 */}
            <TextField
              fullWidth
              size="small"
              placeholder="搜索会话..."
              value={search}
              onChange={handleSearch}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
                endAdornment: search && (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={handleClearSearch}>
                      <ClearIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            {/* 筛选选项 */}
            <Stack direction="row" spacing={1}>
              <FormControl size="small" fullWidth>
                <InputLabel>类型</InputLabel>
                <Select value={chatType} label="类型" onChange={handleChatTypeChange}>
                  <MenuItem value="">全部</MenuItem>
                  <MenuItem value="group">群聊</MenuItem>
                  <MenuItem value="private">私聊</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" fullWidth>
                <InputLabel>状态</InputLabel>
                <Select value={isActive} label="状态" onChange={handleActiveChange}>
                  <MenuItem value="">全部</MenuItem>
                  <MenuItem value="true">已激活</MenuItem>
                  <MenuItem value="false">未激活</MenuItem>
                </Select>
              </FormControl>
            </Stack>
          </Stack>
        </Box>

        <Divider />

        {/* 会话列表 */}
        <Box className="flex-1 overflow-auto">
          <ChatChannelList
            channels={channelList?.items || []}
            selectedChatKey={selectedChatKey}
            onSelectChannel={handleSelectChannel}
            isLoading={isLoading}
          />
        </Box>

        {/* 分页器 */}
        {channelList && channelList.items.length > 0 && (
          <TablePagination
            component="div"
            count={channelList.total}
            page={page - 1}
            rowsPerPage={pageSize}
            onPageChange={(_, newPage) => setPage(newPage + 1)}
            onRowsPerPageChange={event => {
              setPageSize(parseInt(event.target.value, 10))
              setPage(1)
            }}
            labelRowsPerPage="每页"
            sx={{
              '.MuiTablePagination-selectLabel': {
                marginBottom: 0,
              },
              '.MuiTablePagination-displayedRows': {
                marginBottom: 0,
              },
            }}
          />
        )}
      </Paper>
    </Box>
  )
}
