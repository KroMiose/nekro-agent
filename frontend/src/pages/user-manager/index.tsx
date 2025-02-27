import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Button, 
  TextField, 
  InputAdornment, 
  Snackbar,
  Alert
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import UserTable from './components/UserTable';
import UserDetail from './components/UserDetail';
import { useUserData } from './hooks/useUserData';

const UserManagerPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error'}>({
    open: false,
    message: '',
    severity: 'success'
  });

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
    refetch
  } = useUserData(searchTerm);

  const handleSearch = () => {
    refetch();
  };

  const handleViewDetail = (userId: number) => {
    setSelectedUserId(userId);
    setIsDetailOpen(true);
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  return (
    <Box className="h-[calc(100vh-90px)] flex flex-col gap-3 overflow-hidden p-3">
      <Typography variant="h4" gutterBottom>
        用户管理
      </Typography>
      
      <Paper className="flex-1 flex flex-col overflow-hidden">
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              placeholder="搜索用户名或QQ号"
              size="small"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
            <Button variant="contained" onClick={handleSearch}>
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
          />
        </Box>
      </Paper>
      
      {/* 用户详情抽屉 */}
      <UserDetail
        userId={selectedUserId || 0}
        open={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
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
  );
};

export default UserManagerPage; 