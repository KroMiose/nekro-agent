import { useParams, useLocation } from 'react-router-dom'
import { getAdapterConfig } from '../../config/adapters'

export default function AdapterTabPage() {
  const { adapterKey } = useParams<{ adapterKey: string }>()
  const location = useLocation()

  if (!adapterKey) {
    return <div>适配器不存在</div>
  }

  // 获取当前适配器配置
  const adapterConfig = getAdapterConfig(adapterKey)

  // 根据当前路径找到对应的选项卡配置
  const currentPath = location.pathname
  const basePath = `/adapters/${adapterKey}`

  // 确定当前选项卡的路径部分
  const tabPath = currentPath === basePath ? '' : currentPath.replace(`${basePath}/`, '')

  // 找到匹配的选项卡配置
  const currentTab = adapterConfig.tabs.find(tab => tab.path === tabPath)

  if (!currentTab) {
    return <div>页面不存在</div>
  }

  // 渲染对应的组件
  return currentTab.component
}
