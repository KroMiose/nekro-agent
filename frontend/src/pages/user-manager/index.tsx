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
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import UserTable from './components/UserTable'
import UserDetail from './components/UserDetail'
import UserForm from './components/UserForm'
import { useUserData } from './hooks/useUserData'
import { UserFormData } from '../../services/api/user-manager'

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
    <Box className="h-[calc(100vh-90px)] flex flex-col gap-3 overflow-hidden p-3">
      <Paper className="flex-1 flex flex-col overflow-hidden">
        <Box
          sx={{
            p: isSmall ? 1.5 : 2,
            borderBottom: 1,
            borderColor: 'divider',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              gap: 1,
              flexDirection: isSmall ? 'column' : 'row',
            }}
          >
            <TextField
              placeholder="搜索用户名或QQ号"
              size="small"
              fullWidth={isSmall}
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
              sx={{ minWidth: isSmall ? '100%' : 'auto' }}
            >
              搜索
            </Button>
          </Box>
        </Box>

        <Box className="flex-1 flex flex-col overflow-hidden">
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
            showEditButton={!isMobile}
          />
        </Box>
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
