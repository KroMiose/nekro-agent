import { useState } from 'react'
import {
  Box,
  Paper,
  TextField,
  Switch,
  FormControlLabel,
  Stack,
  Alert,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  MenuItem,
  InputAdornment,
  Typography,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
} from '@mui/material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { configApi, ConfigItem } from '../../services/api/config'
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [message, setMessage] = useState<string>('')
  const [editingValues, setEditingValues] = useState<Record<string, string>>({})
  const [visibleSecrets, setVisibleSecrets] = useState<Record<string, boolean>>({})
  const [reloadConfirmOpen, setReloadConfirmOpen] = useState(false)

  // 获取配置列表
  const { data: configs = [] } = useQuery({
    queryKey: ['configs'],
    queryFn: () => configApi.getConfigList(),
  })

  // 获取模型组列表
  const { data: modelGroups = {} } = useQuery({
    queryKey: ['model-groups'],
    queryFn: () => configApi.getModelGroups(),
  })

  // 保存所有修改的配置
  const handleSaveAllChanges = async () => {
    try {
      // 使用批量更新API
      await configApi.batchUpdateConfig(editingValues)
      // 同时保存到配置文件
      await configApi.saveConfig()
      setMessage('所有修改已保存并导出到配置文件')
      // 更新本地缓存中的配置值
      queryClient.setQueryData(['configs'], (oldData: ConfigItem[] | undefined) => {
        if (!oldData) return oldData
        return oldData.map(item =>
          editingValues[item.key] !== undefined ? { ...item, value: editingValues[item.key] } : item
        )
      })
      // 清除编辑状态
      setEditingValues({})
    } catch (error) {
      if (error instanceof Error) {
        setMessage(error.message)
      } else {
        setMessage('保存失败')
      }
    }
  }

  // 重载配置
  const handleReloadConfig = async () => {
    try {
      await configApi.reloadConfig()
      setMessage('配置已重载')
      queryClient.invalidateQueries({ queryKey: ['configs'] })
      queryClient.invalidateQueries({ queryKey: ['model-groups'] })
      setReloadConfirmOpen(false)
      // 清除编辑状态
      setEditingValues({})
    } catch (error) {
      if (error instanceof Error) {
        setMessage(error.message)
      } else {
        setMessage('重载失败')
      }
    }
  }

  // 切换密钥显示状态
  const toggleSecretVisibility = (key: string) => {
    setVisibleSecrets(prev => ({
      ...prev,
      [key]: !prev[key],
    }))
  }

  // 处理配置修改
  const handleConfigChange = (key: string, value: string) => {
    setEditingValues(prev => ({
      ...prev,
      [key]: value,
    }))
  }

  // 渲染配置输入框
  const renderConfigInput = (config: ConfigItem) => {
    console.log('Config placeholder:', config.key, config.placeholder) // 添加调试日志
    const isEditing = config.key in editingValues
    const displayValue = isEditing ? editingValues[config.key] : String(config.value)
    const isSecret = config.is_secret

    // 如果是模型组引用，显示模型组选择器
    if (config.ref_model_groups) {
      const modelGroupNames = Object.keys(modelGroups)
      const isInvalidValue = !modelGroupNames.includes(displayValue)

      return (
        <TextField
          select
          value={displayValue}
          onChange={e => handleConfigChange(config.key, e.target.value)}
          size="small"
          fullWidth
          error={isInvalidValue}
          helperText={isInvalidValue ? '当前选择的模型组已不存在' : undefined}
          placeholder={config.placeholder}
        >
          {modelGroupNames.map(name => (
            <MenuItem key={name} value={name}>
              {name}
            </MenuItem>
          ))}
        </TextField>
      )
    }

    // 如果是枚举类型，显示选择器
    if (config.enum) {
      return (
        <TextField
          select
          value={displayValue}
          onChange={e => handleConfigChange(config.key, e.target.value)}
          size="small"
          fullWidth
          placeholder={config.placeholder}
        >
          {config.enum.map(option => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </TextField>
      )
    }

    switch (config.type) {
      case 'bool':
        return (
          <FormControlLabel
            control={
              <Switch
                checked={displayValue === 'true'}
                onChange={e => handleConfigChange(config.key, String(e.target.checked))}
                color="primary"
              />
            }
            label={displayValue === 'true' ? '是' : '否'}
          />
        )
      case 'int':
      case 'float':
        return (
          <TextField
            type="number"
            value={displayValue}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            fullWidth
            placeholder={config.placeholder}
            autoComplete="off"
          />
        )
      default:
        return (
          <TextField
            value={displayValue}
            onChange={e => handleConfigChange(config.key, e.target.value)}
            size="small"
            fullWidth
            type={isSecret && !visibleSecrets[config.key] ? 'password' : 'text'}
            placeholder={config.placeholder}
            autoComplete="off"
            InputProps={
              isSecret
                ? {
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={() => toggleSecretVisibility(config.key)} edge="end">
                          {visibleSecrets[config.key] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }
                : undefined
            }
          />
        )
    }
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 120px)', // 减去顶部导航和页头的高度
      }}
    >
      {/* 顶部工具栏 */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'flex-end',
          mb: 2,
          flexShrink: 0, // 防止工具栏被压缩
        }}
      >
        <Stack direction="row" spacing={2}>
          <Tooltip title="保存修改">
            <IconButton
              onClick={handleSaveAllChanges}
              color="primary"
              disabled={Object.keys(editingValues).length === 0}
            >
              <SaveIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="重载配置">
            <IconButton onClick={() => setReloadConfirmOpen(true)} color="primary">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* 表格容器 */}
      <Paper
        elevation={3}
        sx={{
          flexGrow: 1, // 占用剩余空间
          overflow: 'hidden', // 防止内容溢出
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <TableContainer sx={{ flexGrow: 1 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell width="25%">配置项</TableCell>
                <TableCell width="10%">类型</TableCell>
                <TableCell width="65%">值</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {configs
                .filter(config => !config.is_hidden)
                .map(config => (
                  <TableRow key={config.key}>
                    <TableCell>
                      <Box>
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                          {config.title || config.key}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {config.key}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={config.type}
                        size="small"
                        color={
                          config.type === 'bool'
                            ? 'success'
                            : config.type === 'int' || config.type === 'float'
                              ? 'info'
                              : 'default'
                        }
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {renderConfigInput(config)}
                        {config.ref_model_groups && (
                          <Chip label="模型组" size="small" color="primary" variant="outlined" />
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 添加重载确认对话框 */}
      <Dialog open={reloadConfirmOpen} onClose={() => setReloadConfirmOpen(false)}>
        <DialogTitle>确认重载配置？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            重载配置将从配置文件中重新读取所有配置项，包括基本配置和模型组配置，未保存的修改将会丢失。是否继续？
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReloadConfirmOpen(false)}>取消</Button>
          <Button onClick={handleReloadConfig} color="primary">
            确认
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={!!message}
        autoHideDuration={3000}
        onClose={() => setMessage('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setMessage('')}
          severity="info"
          variant="filled"
          sx={{ width: '100%' }}
        >
          {message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
