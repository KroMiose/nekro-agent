import { Box } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { wechatOpenILinkApi } from '../../../services/api/adapters/wechat_openilink'
import OpenILinkLoginCard from './OpenILinkLoginCard'

export default function WechatOpenILinkLoginPage() {
  const { data: status, isLoading } = useQuery({
    queryKey: ['wechat-openilink-login-status'],
    queryFn: () => wechatOpenILinkApi.getLoginStatus(),
    refetchInterval: 5000,
  })

  return (
    <Box sx={{ p: 2, height: '100%', boxSizing: 'border-box' }}>
      <OpenILinkLoginCard status={status} isLoading={isLoading} />
    </Box>
  )
}
