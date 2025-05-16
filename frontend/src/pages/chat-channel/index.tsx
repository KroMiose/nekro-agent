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
  useTheme,
  useMediaQuery,
  Drawer,
  Fab,
  AppBar,
  Toolbar,
  Button,
  Tabs,
  Tab,
} from '@mui/material'
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  ArrowBack as ArrowBackIcon,
  List as ListIcon,
  Info as InfoIcon,
  Block as BlockIcon,
  RestartAlt as RestartAltIcon,
  Group as GroupIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { chatChannelApi } from '../../services/api/chat-channel'
import ChatChannelList from './components/ChatChannelList'
import ChatChannelDetail from './components/ChatChannelDetail'
import MessageHistory from './components/detail-tabs/MessageHistory'
import BasicInfo from './components/detail-tabs/BasicInfo'
import TablePaginationStyled from '../../components/common/TablePaginationStyled'

export default function ChatChannelPage() {
  const [search, setSearch] = useState('')
  const [chatType, setChatType] = useState<string>('')
  const [isActive, setIsActive] = useState<string>('')
  const [selectedChatKey, setSelectedChatKey] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [activeTab, setActiveTab] = useState(0)

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

  // 查询当前选中会话的详情
  const { data: channelDetail } = useQuery({
    queryKey: ['chat-channel-detail', selectedChatKey],
    queryFn: () => selectedChatKey ? chatChannelApi.getDetail(selectedChatKey) : null,
    enabled: !!selectedChatKey,
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

  // 切换抽屉状态（移动端）
  const toggleDrawer = () => {
    setDrawerOpen(!drawerOpen)
  }

  // 处理标签页切换
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue)
  }

  // 渲染会话列表组件
  const renderChannelList = () => (
    <Box className="h-full flex flex-col overflow-hidden">
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
          onPageChange={(_, newPage) => setPage(newPage + 1)}
          onRowsPerPageChange={event => {
            setPageSize(parseInt(event.target.value, 10))
            setPage(1)
          }}
          loading={isLoading}
          showFirstLastPageButtons={false}
          rowsPerPageOptions={[10, 25]}
          sx={{
            '.MuiTablePagination-selectLabel': {
              display: 'none', // 隐藏「每页」标签
            },
            '.MuiTablePagination-toolbar': {
              minHeight: '48px',
              padding: '0 8px',
            },
            '.MuiTablePagination-actions': {
              marginLeft: '8px', // 减少操作区域的左边距
            },
          }}
        />
      )}
    </Box>
  )

  // 渲染会话详情组件
  const renderChannelDetail = () => (
    <Box className="h-full flex flex-col overflow-hidden">
      {isMobile && selectedChatKey && (
        <Box sx={{ bgcolor: 'background.paper' }}>
          {/* 顶部导航栏 */}
          <AppBar
            position="static"
            color="primary"
            elevation={0}
            sx={{
              boxShadow: 1,
              background: theme =>
                theme.palette.mode === 'dark'
                  ? 'linear-gradient(90deg, rgba(234,82,82,0.8) 0%, rgba(234,82,82,0.6) 100%)'
                  : 'linear-gradient(90deg, rgba(234,82,82,0.9) 0%, rgba(234,82,82,0.7) 100%)',
              color: '#fff',
            }}
          >
            <Toolbar variant="dense" sx={{ minHeight: { xs: 48, sm: 56 }, py: 0.5 }}>
              <IconButton
                edge="start"
                color="inherit"
                onClick={handleBackToList}
                sx={{ mr: 1 }}
                size={isSmall ? 'small' : 'medium'}
              >
                <ArrowBackIcon />
              </IconButton>
              <Typography
                variant={isSmall ? 'subtitle2' : 'subtitle1'}
                component="div"
                sx={{ flexGrow: 1 }}
                noWrap
              >
                会话详情
              </Typography>
            </Toolbar>
          </AppBar>

          {/* 会话标题信息 - 调整为单列布局，垂直方向排列 */}
          <Box sx={{ p: 2 }}>
            {/* 会话名称和状态 */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <GroupIcon color="primary" sx={{ mr: 1.5, fontSize: isSmall ? 20 : 24 }} />
              <Typography
                variant={isSmall ? 'h6' : 'h5'}
                component="h1"
                sx={{
                  fontWeight: 'medium',
                  lineHeight: 1.3,
                  wordBreak: 'break-word',
                }}
              >
                {channelDetail?.channel_name || '未命名会话'}
              </Typography>
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  bgcolor: channelDetail?.is_active ? 'success.main' : 'text.disabled',
                  ml: 1.5,
                  flexShrink: 0,
                }}
              />
            </Box>

            {/* 会话ID，放在名称下方 */}
            <Typography
              variant="caption"
              color="text.secondary"
              component="div"
              sx={{
                fontFamily: 'monospace',
                mb: 2,
                display: 'block',
              }}
            >
              {selectedChatKey}
            </Typography>

            {/* 操作按钮组，垂直方向排列 */}
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Button
                color="error"
                variant="outlined"
                startIcon={<BlockIcon />}
                size={isSmall ? 'small' : 'medium'}
                sx={{ flex: 1 }}
                onClick={() => channelDetail && chatChannelApi.setActive(selectedChatKey!, !channelDetail.is_active)}
              >
                {channelDetail?.is_active ? '停用' : '激活'}
              </Button>
              <Button
                color="warning"
                variant="outlined"
                startIcon={<RestartAltIcon />}
                size={isSmall ? 'small' : 'medium'}
                sx={{ flex: 1 }}
                onClick={() => selectedChatKey && chatChannelApi.reset(selectedChatKey)}
              >
                重置
              </Button>
            </Box>
          </Box>

          {/* 标签页切换 */}
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="fullWidth"
            sx={{
              borderBottom: 1,
              borderColor: 'divider',
              minHeight: isSmall ? 40 : 48,
              '& .MuiTab-root': {
                minHeight: isSmall ? 40 : 48,
                fontSize: isSmall ? '0.8rem' : '0.875rem',
              },
            }}
          >
            <Tab label="基础信息" />
            <Tab label="消息记录" />
          </Tabs>

          {/* 基础信息标签页 */}
          {activeTab === 0 && channelDetail && (
            <Box sx={{ p: 0, overflow: 'auto' }}>
              <BasicInfo channel={channelDetail} />
            </Box>
          )}

          {/* 消息记录标签页内容 */}
          {activeTab === 1 && selectedChatKey && (
            <Box
              sx={{
                p: 1.5,
                height: 'calc(100vh - 250px)',
                overflow: 'auto',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <Box
                sx={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <MessageHistory chatKey={selectedChatKey} />
              </Box>

              <Typography
                variant="caption"
                align="center"
                color="text.secondary"
                sx={{ mt: 1, opacity: 0.7, fontSize: '0.7rem' }}
              >
                上滑加载更多消息 • 最多显示200条
              </Typography>
            </Box>
          )}
        </Box>
      )}

      {selectedChatKey ? (
        <Box className="flex-1 overflow-auto">
          {!isMobile && <ChatChannelDetail chatKey={selectedChatKey} />}
        </Box>
      ) : (
        <Box className="h-full flex items-center justify-center flex-col">
          <InfoIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.7 }} />
          <Typography color="textSecondary">请选择一个会话查看详情</Typography>
          {isMobile && (
            <Button
              onClick={toggleDrawer}
              variant="outlined"
              startIcon={<ListIcon />}
              sx={{ mt: 2 }}
            >
              查看会话列表
            </Button>
          )}
        </Box>
      )}
    </Box>
  )

  return (
    <Box className="h-[calc(100vh-90px)] flex gap-3 overflow-hidden p-2">
      {isMobile ? (
        // 移动端布局
        <>
          {/* 主内容区 - 会话详情 */}
          <Paper className="w-full flex-1 overflow-hidden">{renderChannelDetail()}</Paper>

          {/* 抽屉式侧边栏 - 会话列表 */}
          <Drawer
            anchor="right"
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            PaperProps={{
              sx: {
                width: isSmall ? '85%' : '320px',
                maxWidth: '100%',
              },
            }}
          >
            {renderChannelList()}
          </Drawer>

          {/* 浮动按钮 - 打开会话列表 */}
          {!selectedChatKey && (
            <Fab
              color="primary"
              size={isSmall ? 'medium' : 'large'}
              onClick={toggleDrawer}
              sx={{
                position: 'fixed',
                bottom: 16,
                right: 16,
                zIndex: 1099,
              }}
            >
              <ListIcon />
            </Fab>
          )}
        </>
      ) : (
        // 桌面端布局
        <>
          {/* 左侧详情面板 */}
          <Paper className="flex-1 overflow-hidden">{renderChannelDetail()}</Paper>

          {/* 右侧会话列表 */}
          <Paper className="w-[320px] flex-shrink-0 flex flex-col overflow-hidden">
            {renderChannelList()}
          </Paper>
        </>
      )}
    </Box>
  )
}
