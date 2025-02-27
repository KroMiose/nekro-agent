import React, { useState } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button, 
  TextField,
  Box
} from '@mui/material';
import { UserFormData } from '../../../services/api/user-manager';

interface UserFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: UserFormData) => Promise<void>;
}

const UserForm: React.FC<UserFormProps> = ({ open, onClose, onSubmit }) => {
  const [formData, setFormData] = useState<UserFormData>({
    username: '',
    password: '',
    bind_qq: '',
    access_key: ''
  });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | { name?: string; value: unknown }>) => {
    const { name, value } = e.target;
    if (name) {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
      
      // 清除对应字段的错误
      if (errors[name]) {
        setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors[name];
          return newErrors;
        });
      }
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.username.trim()) {
      newErrors.username = '用户名不能为空';
    }
    
    if (!formData.password) {
      newErrors.password = '密码不能为空';
    } else if (formData.password.length < 6) {
      newErrors.password = '密码长度至少为6位';
    }
    
    if (formData.password !== confirmPassword) {
      newErrors.confirmPassword = '两次输入的密码不一致';
    }
    
    if (!formData.bind_qq.trim()) {
      newErrors.bind_qq = 'QQ号不能为空';
    } else if (!/^\d+$/.test(formData.bind_qq)) {
      newErrors.bind_qq = 'QQ号必须为数字';
    }
    
    if (!formData.access_key) {
      newErrors.access_key = '访问密钥不能为空';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;
    
    setIsSubmitting(true);
    try {
      await onSubmit(formData);
      handleReset();
      onClose();
    } catch (error) {
      console.error('创建用户失败:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setFormData({
      username: '',
      password: '',
      bind_qq: '',
      access_key: ''
    });
    setConfirmPassword('');
    setErrors({});
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>创建新用户</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          <TextField
            fullWidth
            margin="normal"
            label="用户名"
            name="username"
            value={formData.username}
            onChange={handleChange}
            error={!!errors.username}
            helperText={errors.username}
            required
          />
          
          <TextField
            fullWidth
            margin="normal"
            label="密码"
            name="password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            error={!!errors.password}
            helperText={errors.password}
            required
          />
          
          <TextField
            fullWidth
            margin="normal"
            label="确认密码"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={!!errors.confirmPassword}
            helperText={errors.confirmPassword}
            required
          />
          
          <TextField
            fullWidth
            margin="normal"
            label="QQ号"
            name="bind_qq"
            value={formData.bind_qq}
            onChange={handleChange}
            error={!!errors.bind_qq}
            helperText={errors.bind_qq}
            required
          />
          
          <TextField
            fullWidth
            margin="normal"
            label="访问密钥"
            name="access_key"
            type="password"
            value={formData.access_key}
            onChange={handleChange}
            error={!!errors.access_key}
            helperText={errors.access_key || "请输入超级访问密钥以确认创建"}
            required
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>取消</Button>
        <Button 
          onClick={handleSubmit} 
          color="primary" 
          disabled={isSubmitting}
        >
          {isSubmitting ? '创建中...' : '创建'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default UserForm; 