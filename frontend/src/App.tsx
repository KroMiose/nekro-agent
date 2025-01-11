import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { useColorMode } from './stores/theme'
import router from './router.tsx'

const queryClient = new QueryClient()

export default function App() {
  const { mode } = useColorMode()

  const theme = createTheme({
    palette: {
      mode,
    },
  })

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <RouterProvider router={router} />
      </ThemeProvider>
    </QueryClientProvider>
  )
}
