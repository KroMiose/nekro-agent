import React from 'react'
import {
  TablePagination,
  IconButton,
  Box,
  Tooltip,
  useMediaQuery,
  useTheme,
  SxProps,
  Theme,
} from '@mui/material'
import {
  FirstPage as FirstPageIcon,
  LastPage as LastPageIcon,
  KeyboardArrowLeft as KeyboardArrowLeftIcon,
  KeyboardArrowRight as KeyboardArrowRightIcon,
} from '@mui/icons-material'
import { useTranslation } from 'react-i18next'

interface TablePaginationStyledProps {
  count: number
  page: number
  rowsPerPage: number
  onPageChange: (event: React.MouseEvent<HTMLButtonElement> | null, newPage: number) => void
  onRowsPerPageChange?: (event: React.ChangeEvent<HTMLInputElement>) => void
  rowsPerPageOptions?: number[]
  component?: React.ElementType
  labelRowsPerPage?: string
  labelDisplayedRows?: (from: { from: number; to: number; count: number }) => string
  sx?: SxProps<Theme>
  loading?: boolean
  showFirstLastPageButtons?: boolean
}

/**
 * 统一风格的表格分页器组件
 * 封装了MUI的TablePagination组件，解决分页按钮无法点击和页大小选择器问题，并添加直接翻页到首尾页的功能
 */
const TablePaginationStyled: React.FC<TablePaginationStyledProps> = ({
  count,
  page,
  rowsPerPage,
  onPageChange,
  onRowsPerPageChange,
  rowsPerPageOptions = [10, 25, 50],
  component = 'div',
  labelRowsPerPage,
  labelDisplayedRows,
  sx,
  loading = false,
  showFirstLastPageButtons = true,
}) => {
  const theme = useTheme()
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'))
  const { t } = useTranslation('common')

  // 自定义分页导航按钮
  function TablePaginationActions(props: {
    count: number
    page: number
    rowsPerPage: number
    onPageChange: (event: React.MouseEvent<HTMLButtonElement>, newPage: number) => void
  }) {
    const { count, page, rowsPerPage, onPageChange } = props
    
    const handleFirstPageButtonClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      onPageChange(event, 0)
    }
    
    const handleBackButtonClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      onPageChange(event, page - 1)
    }
    
    const handleNextButtonClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      onPageChange(event, page + 1)
    }
    
    const handleLastPageButtonClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      onPageChange(event, Math.max(0, Math.ceil(count / rowsPerPage) - 1))
    }
    
    return (
      <Box sx={{ display: 'flex' }}>
        {showFirstLastPageButtons && (
          <Tooltip title={t('pagination.firstPage')}>
            <span>
              <IconButton
                onClick={handleFirstPageButtonClick}
                disabled={page === 0 || loading}
                aria-label={t('pagination.firstPage')}
                size={isSmall ? 'small' : 'medium'}
              >
                {theme.direction === 'rtl' ? <LastPageIcon /> : <FirstPageIcon />}
              </IconButton>
            </span>
          </Tooltip>
        )}
        
        <Tooltip title={t('pagination.previousPage')}>
          <span>
            <IconButton
              onClick={handleBackButtonClick}
              disabled={page === 0 || loading}
              aria-label={t('pagination.previousPage')}
              size={isSmall ? 'small' : 'medium'}
            >
              {theme.direction === 'rtl' ? <KeyboardArrowRightIcon /> : <KeyboardArrowLeftIcon />}
            </IconButton>
          </span>
        </Tooltip>
        
        <Tooltip title={t('pagination.nextPage')}>
          <span>
            <IconButton
              onClick={handleNextButtonClick}
              disabled={page >= Math.ceil(count / rowsPerPage) - 1 || loading}
              aria-label={t('pagination.nextPage')}
              size={isSmall ? 'small' : 'medium'}
            >
              {theme.direction === 'rtl' ? <KeyboardArrowLeftIcon /> : <KeyboardArrowRightIcon />}
            </IconButton>
          </span>
        </Tooltip>
        
        {showFirstLastPageButtons && (
          <Tooltip title={t('pagination.lastPage')}>
            <span>
              <IconButton
                onClick={handleLastPageButtonClick}
                disabled={page >= Math.ceil(count / rowsPerPage) - 1 || loading}
                aria-label={t('pagination.lastPage')}
                size={isSmall ? 'small' : 'medium'}
              >
                {theme.direction === 'rtl' ? <FirstPageIcon /> : <LastPageIcon />}
              </IconButton>
            </span>
          </Tooltip>
        )}
      </Box>
    )
  }

  return (
    <TablePagination
      component={component}
      count={count}
      rowsPerPage={rowsPerPage}
      page={page}
      onPageChange={onPageChange}
      onRowsPerPageChange={onRowsPerPageChange}
      rowsPerPageOptions={rowsPerPageOptions}
      labelRowsPerPage={
        labelRowsPerPage ||
        (isSmall ? t('common.pagination.labelRowsPerPageShort') : t('common.pagination.labelRowsPerPage'))
      }
      labelDisplayedRows={
        labelDisplayedRows ||
        (({ from, to, count }) => {
          const key = isSmall
            ? 'common.pagination.displayedRowsShort'
            : 'common.pagination.displayedRows'
          return t(key, { from, to, count })
        })
      }
      ActionsComponent={TablePaginationActions}
      disabled={loading}
      sx={{
        borderTop: '1px solid',
        borderColor: 'divider',
        flexShrink: 0,
        '.MuiTablePagination-selectLabel': {
          marginBottom: 0,
          display: isSmall ? 'none' : 'block',
        },
        '.MuiTablePagination-displayedRows': {
          marginBottom: 0,
          fontSize: isSmall ? '0.75rem' : 'inherit',
        },
        ...sx,
      }}
    />
  )
}

export default TablePaginationStyled 