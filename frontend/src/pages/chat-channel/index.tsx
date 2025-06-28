import React, { useState } from 'react'
import {
  Box,
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
  useTheme,
  useMediaQuery,
  Drawer,
  Fab,
  Card,
  Button,
} from '@mui/material'
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  List as ListIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { chatChannelApi } from '../../services/api/chat-channel'
import ChatChannelList from './components/ChatChannelList'
import ChatChannelDetail from './components/ChatChannelDetail'
import TablePaginationStyled from '../../components/common/TablePaginationStyled'
import { CARD_VARIANTS } from '../../theme/variants'

export default function ChatChannelPage() {
  const [search, setSearch] = useState('')
  const [chatType, setChatType] = useState<string>('')
  const [isActive, setIsActive] = useState<string>('')
  const [selectedChatKey, setSelectedChatKey] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

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
    if (isMobile) {
      setDrawerOpen(false)
    }
  }

  // 返回会话列表（移动端）
  const handleBackToList = () => {
    setSelectedChatKey(null)
  }

  // 渲染会话列表组件
  const renderChannelList = () => (
    <>
      <Box className="p-2 flex-shrink-0">
        <Stack spacing={1.5}>
          {/* 搜索框 */}
          <TextField
            fullWidth
            size={isSmall ? 'small' : 'medium'}
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
          <Stack direction={isSmall ? 'column' : 'row'} spacing={1}>
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
        <TablePaginationStyled
          component="div"
          count={channelList.total}
          page={page - 1}
          rowsPerPage={pageSize}
          onPageChange={(_: React.MouseEvent<HTMLButtonElement> | null, newPage: number) =>
            setPage(newPage + 1)
          }
          onRowsPerPageChange={(
            event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
          ) => {
            setPageSize(parseInt(event.target.value, 10))
            setPage(1)
          }}
          loading={isLoading}
          showFirstLastPageButtons={false}
          rowsPerPageOptions={[10, 25]}
        />
      )}
    </>
  )

  // 渲染会话详情组件
  const renderChannelDetail = () => (
    <>
      {selectedChatKey ? (
        <ChatChannelDetail chatKey={selectedChatKey} onBack={handleBackToList} />
      ) : (
        <Card
          sx={{
            ...CARD_VARIANTS.default.styles,
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
          }}
        >
          <InfoIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.7 }} />
          <Typography color="textSecondary">请选择一个会话查看详情</Typography>
          {isMobile && (
            <Button
              onClick={() => setDrawerOpen(true)}
              variant="outlined"
              startIcon={<ListIcon />}
              sx={{ mt: 2 }}
            >
              查看会话列表
            </Button>
          )}
        </Card>
      )}
    </>
  )

  return (
    <Box className="h-full flex gap-2 overflow-hidden p-2">
      {isMobile ? (
        // 移动端布局
        <>
          {/* 主内容区 - 根据是否选择会话，显示详情或提示 */}
          <Box className="w-full flex-1 overflow-hidden">
            {selectedChatKey ? (
              <ChatChannelDetail chatKey={selectedChatKey} onBack={handleBackToList} />
            ) : (
              <Card
                sx={{
                  ...CARD_VARIANTS.default.styles,
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexDirection: 'column',
                }}
              >
                <InfoIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.7 }} />
                <Typography color="textSecondary">请选择一个会话查看详情</Typography>
                <Button
                  onClick={() => setDrawerOpen(true)}
                  variant="outlined"
                  startIcon={<ListIcon />}
                  sx={{ mt: 2 }}
                >
                  查看会话列表
                </Button>
              </Card>
            )}
          </Box>

          {/* 抽屉式侧边栏 - 会话列表 */}
          <Drawer
            anchor="left"
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            PaperProps={{
              sx: {
                width: isSmall ? '85%' : '320px',
                maxWidth: '100%',
                backgroundColor: 'transparent',
                backdropFilter: 'blur(20px)',
                borderRight: `1px solid ${theme.palette.divider}`,
              },
            }}
          >
            {renderChannelList()}
          </Drawer>

          {/* 浮动按钮 - 打开会话列表 */}
          <Fab
            color="primary"
            size={isSmall ? 'medium' : 'large'}
            onClick={() => setDrawerOpen(true)}
            sx={{
              position: 'fixed',
              bottom: 16,
              right: 16,
              zIndex: 1099,
            }}
          >
            <ListIcon />
          </Fab>
        </>
      ) : (
        // 桌面端布局
        <>
          <Box className="flex-1 overflow-hidden">{renderChannelDetail()}</Box>
          <Card
            sx={{
              ...CARD_VARIANTS.default.styles,
              width: '360px',
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {renderChannelList()}
          </Card>
        </>
      )}
    </Box>
  )
}
