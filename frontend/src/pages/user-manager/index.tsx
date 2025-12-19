import React, { useState } from 'react'
import {
  Box,
  Paper,
  Button,
  TextField,
  InputAdornment,
  useMediaQuery,
  useTheme,
  TableContainer,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import UserTable from './components/UserTable'
import UserDetail from './components/UserDetail'
import UserForm from './components/UserForm'
import { useUserData } from './hooks/useUserData'
import { UserFormData } from '../../services/api/user-manager'
import { UNIFIED_TABLE_STYLES } from '../../theme/variants'
import { useNotification } from '../../hooks/useNotification'
import { useTranslation } from 'react-i18next'
import TablePaginationStyled from '../../components/common/TablePaginationStyled'

const UserManagerPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)
  const [isUserFormOpen, setIsUserFormOpen] = useState(false)

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const notification = useNotification()
  const { t } = useTranslation('user-manager')

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

  const handleShowSuccess = (message: string) => {
    notification.success(message)
  }

  const handleShowError = (message: string) => {
    notification.error(message)
  }

  const handleCreateUser = async (data: UserFormData) => {
    try {
      await createUser(data)
      handleShowSuccess(t('messages.createSuccess'))
      refetch()
      return Promise.resolve()
    } catch (error) {
      handleShowError(
        t('messages.createFailed', {
          error:
            error instanceof Error ? error.message : t('common.unknownError', { ns: 'common' }),
        })
      )
      return Promise.reject(error)
    }
  }

  return (
    <Box
      sx={{
        ...UNIFIED_TABLE_STYLES.tableLayoutContainer,
        p: 2,
        height: 'calc(100vh - 64px)',
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
          placeholder={t('search.placeholder')}
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
          {t('actions.search')}
        </Button>
      </Box>

      {/* 用户表格 */}
      <Paper sx={UNIFIED_TABLE_STYLES.tableContentContainer}>
        <TableContainer sx={UNIFIED_TABLE_STYLES.tableViewport}>
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
                ...UNIFIED_TABLE_STYLES.getTableBase(isMobile, isSmall),
                p: 0,
              },
            }}
          />
        </TableContainer>
        <TablePaginationStyled
          rowsPerPageOptions={isMobile ? [5, 10, 25] : [5, 10, 25, 50]}
          component="div"
          count={total}
          rowsPerPage={pagination.page_size}
          page={pagination.page - 1}
          onPageChange={(_, newPage) => setPagination({ ...pagination, page: newPage + 1 })}
          onRowsPerPageChange={event =>
            setPagination({ page: 1, page_size: parseInt(event.target.value, 10) })
          }
          loading={isLoading}
          showFirstLastPageButtons={true}
        />
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
    </Box>
  )
}

export default UserManagerPage
