import React, { useState } from 'react'
import {
  Box,
  Paper,
  Button,
  TextField,
  InputAdornment,
  Snackbar,
  Alert,
  useMediaQuery,
  useTheme,
  SxProps,
  Theme,
  TableContainer,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import UserTable from './components/UserTable'
import UserDetail from './components/UserDetail'
import UserForm from './components/UserForm'
import { useUserData } from './hooks/useUserData'
import { UserFormData } from '../../services/api/user-manager'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'

const UserManagerPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)
  const [isUserFormOpen, setIsUserFormOpen] = useState(false)
  const [snackbar, setSnackbar] = useState<{
    open: boolean
    message: string
    severity: 'success' | 'error'
  }>({
    open: false,
    message: '',
    severity: 'success',
  })

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))

  const {
    users,
    total,
    isLoading,
    pagination,
    setPagination,
    sorting,
    setSorting,
    updateUser,
    deleteUser,
    banUser,
    setPreventTrigger,
    resetPassword,
    createUser,
    refetch,
  } = useUserData(searchTerm)

  const handleSearch = () => {
    refetch()
  }

  const handleViewDetail = (userId: number) => {
    setSelectedUserId(userId)
    setIsDetailOpen(true)
  }

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false })
  }

  const handleShowSuccess = (message: string) => {
    setSnackbar({
      open: true,
      message,
      severity: 'success',
    })
  }

  const handleShowError = (message: string) => {
    setSnackbar({
      open: true,
      message,
      severity: 'error',
    })
  }

  const handleCreateUser = async (data: UserFormData) => {
    try {
      await createUser(data)
      handleShowSuccess('用户创建成功喵～')
      refetch()
      return Promise.resolve()
    } catch (error) {
      handleShowError(`创建失败: ${error instanceof Error ? error.message : '未知错误'}`)
      return Promise.reject(error)
    }
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 90px)',
        p: 2,
        gap: 2,
      }}
    >
      {/* 搜索栏 */}
      <Box
        sx={{
          display: 'flex',
          gap: 1,
          pl: 1,
          flexShrink: 0,
          flexDirection: 'row',
          alignItems: 'center',
        }}
      >
        <TextField
          placeholder="搜索用户名或QQ号"
          size="small"
          sx={{ flex: 1 }}
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && handleSearch()}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        <Button
          variant="contained"
          onClick={handleSearch}
          size={isSmall ? 'small' : 'medium'}
          sx={{
            minWidth: isSmall ? '60px' : '80px',
            flexShrink: 0,
          }}
        >
          搜索
        </Button>
      </Box>

      {/* 用户表格 */}
      <Paper
        elevation={3}
        sx={{
          flexGrow: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          ...(UNIFIED_TABLE_STYLES.paper as SxProps<Theme>),
        }}
      >
        <TableContainer
          sx={{
            height: 'calc(100vh - 170px)',
            maxHeight: 'calc(100vh - 170px)',
            overflow: 'auto',
            borderRadius: 1,
            ...(UNIFIED_TABLE_STYLES.scrollbar as SxProps<Theme>),
          }}
        >
          <UserTable
            users={users}
            total={total}
            loading={isLoading}
            pagination={pagination}
            onPaginationChange={setPagination}
            sorting={sorting}
            onSortingChange={setSorting}
            onViewDetail={handleViewDetail}
            onDeleteUser={deleteUser}
            onBanUser={banUser}
            onSetPreventTrigger={setPreventTrigger}
            onResetPassword={resetPassword}
            onUpdateUser={updateUser}
            showEditButton={!isMobile && false}
            tableProps={{
              stickyHeader: true,
              sx: {
                tableLayout: 'fixed',
                minWidth: '800px',
              },
            }}
          />
        </TableContainer>
      </Paper>

      {/* 用户详情抽屉 */}
      <UserDetail
        userId={selectedUserId || 0}
        open={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
      />

      {/* 创建用户表单 */}
      <UserForm
        open={isUserFormOpen}
        onClose={() => setIsUserFormOpen(false)}
        onSubmit={handleCreateUser}
      />

      {/* 提示消息 */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}

export default UserManagerPage
