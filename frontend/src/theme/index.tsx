import { createTheme, ThemeProvider } from '@mui/material/styles'
import { CssBaseline } from '@mui/material'
import { ReactNode } from 'react'
import { useColorMode } from '../stores/theme'

const PRIMARY_COLOR = '#EA5252'

// 定义全局字体
const globalFonts = {
  sans: [
    '"Microsoft YaHei"',
    '-apple-system',
    'BlinkMacSystemFont',
    '"Segoe UI"',
    'Roboto',
    '"Helvetica Neue"',
    'Arial',
    'sans-serif',
  ].join(','),
}

export default function ThemeConfig({ children }: { children: ReactNode }) {
  const { mode } = useColorMode()

  const theme = createTheme({
    palette: {
      mode,
      primary: {
        main: PRIMARY_COLOR,
        contrastText: '#fff',
      },
      background: {
        default: mode === 'dark' ? '#1A1A1A' : '#f5f5f5',
        paper: mode === 'dark' ? '#161616' : '#fff',
      },
    },
    typography: {
      fontFamily: globalFonts.sans,
      h1: { fontFamily: globalFonts.sans },
      h2: { fontFamily: globalFonts.sans },
      h3: { fontFamily: globalFonts.sans },
      h4: { fontFamily: globalFonts.sans },
      h5: { fontFamily: globalFonts.sans },
      h6: { fontFamily: globalFonts.sans },
      subtitle1: { fontFamily: globalFonts.sans },
      subtitle2: { fontFamily: globalFonts.sans },
      body1: { fontFamily: globalFonts.sans },
      body2: { fontFamily: globalFonts.sans },
      button: { fontFamily: globalFonts.sans },
      caption: { fontFamily: globalFonts.sans },
      overline: { fontFamily: globalFonts.sans },
    },
    components: {
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: mode === 'dark' ? '#1A1A1A' : PRIMARY_COLOR,
          },
        },
      },
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            fontFamily: globalFonts.sans,
          },
          '*::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '*::-webkit-scrollbar-track': {
            background: mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : '#f5f5f5',
            borderRadius: '4px',
          },
          '*::-webkit-scrollbar-thumb': {
            background: mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.2)',
            borderRadius: '4px',
            '&:hover': {
              background: mode === 'dark' ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.3)',
            },
          },
          '*': {
            scrollbarWidth: 'thin',
            scrollbarColor: mode === 'dark' 
              ? 'rgba(255, 255, 255, 0.1) rgba(255, 255, 255, 0.05)'
              : 'rgba(0, 0, 0, 0.2) #f5f5f5',
          },
        },
      },
    },
  })

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  )
}
