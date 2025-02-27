import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  getUserList, 
  createUser, 
  updateUser, 
  deleteUser, 
  banUser, 
  setPreventTrigger, 
  resetPassword,
  User,
  UserFormData,
  UserUpdateData
} from '../../../services/api/user-manager';

interface Pagination {
  page: number;
  page_size: number;
}

interface Sorting {
  field: string;
  order: 'asc' | 'desc';
}

export const useUserData = (searchTerm: string) => {
  const queryClient = useQueryClient();
  const [pagination, setPagination] = useState<Pagination>({ page: 1, page_size: 10 });
  const [sorting, setSorting] = useState<Sorting>({ field: 'id', order: 'desc' });

  // 获取用户列表
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['users', pagination.page, pagination.page_size, sorting.field, sorting.order, searchTerm],
    queryFn: () => getUserList({
      page: pagination.page,
      page_size: pagination.page_size,
      search: searchTerm,
      sort_by: sorting.field,
      sort_order: sorting.order
    }),
    refetchOnWindowFocus: false,
    staleTime: 0,
  });

  // 创建用户
  const createUserMutation = useMutation({
    mutationFn: (userData: UserFormData) => createUser(userData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });

  // 更新用户
  const updateUserMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: UserUpdateData }) => updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });

  // 删除用户
  const deleteUserMutation = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });

  // 封禁/解封用户
  const banUserMutation = useMutation({
    mutationFn: ({ id, banUntil }: { id: number; banUntil: string | null }) => banUser(id, banUntil),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });

  // 设置触发权限
  const setPreventTriggerMutation = useMutation({
    mutationFn: ({ id, preventTriggerUntil }: { id: number; preventTriggerUntil: string | null }) => 
      setPreventTrigger(id, preventTriggerUntil),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });

  // 重置密码
  const resetPasswordMutation = useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) => resetPassword(id, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });

  return {
    users: (data?.data?.items || []) as User[],
    total: data?.data?.total || 0,
    isLoading,
    pagination,
    setPagination,
    sorting,
    setSorting,
    createUser: createUserMutation.mutateAsync,
    updateUser: updateUserMutation.mutateAsync,
    deleteUser: deleteUserMutation.mutateAsync,
    banUser: banUserMutation.mutateAsync,
    setPreventTrigger: setPreventTriggerMutation.mutateAsync,
    resetPassword: resetPasswordMutation.mutateAsync,
    refetch
  };
}; 