import { RouterProvider } from 'react-router-dom'
import router from './router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ThemeConfig from './theme'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeConfig>
        <RouterProvider router={router} />
      </ThemeConfig>
    </QueryClientProvider>
  )
}

export default App
