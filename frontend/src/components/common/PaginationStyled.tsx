import { Pagination, PaginationProps, Stack, Typography } from '@mui/material'

interface PaginationStyledProps extends PaginationProps {
  totalPages: number
  currentPage: number
  onPageChange: (event: React.ChangeEvent<unknown>, page: number) => void
  loading?: boolean
  alwaysShow?: boolean
  showPageInfo?: boolean  // 是否显示页码信息文本
}

/**
 * 统一风格的分页器组件
 * 提供美观的样式和统一的用户体验
 */
const PaginationStyled = ({
  totalPages,
  currentPage,
  onPageChange,
  loading = false,
  alwaysShow = true,
  siblingCount = 1,  // 当前页码两侧显示的页码数量
  boundaryCount = 1, // 最前和最后显示的页码数量
  showPageInfo = true, // 默认显示页码信息
  ...props
}: PaginationStyledProps) => {
  // 如果只有一页或没有页且不是始终显示模式，则不显示分页器
  if (totalPages <= 1 && !alwaysShow) return null

  // 验证并确保页数为有效的正整数
  const isValidPageCount = !isNaN(Number(totalPages)) && Number(totalPages) > 0 && Number.isFinite(totalPages);
  const pageCount = isValidPageCount ? Math.max(Math.floor(totalPages), 1) : 1;
  
  // 验证当前页是否为有效数字
  const validCurrentPage = !isNaN(Number(currentPage)) && Number(currentPage) > 0 
    ? Math.min(Math.floor(Number(currentPage)), pageCount) 
    : 1;
  
  return (
    <Stack 
      direction="column" 
      spacing={1} 
      alignItems="center" 
      sx={{ mt: 4 }}
    >
      {/* 如果需要显示页码信息 */}
      {showPageInfo && (
        <Typography 
          variant="body2" 
          color="text.secondary"
          sx={{ mb: 0.5 }}
        >
          第 {validCurrentPage} 页 / 共 {pageCount} 页
        </Typography>
      )}
      
      <Pagination
        count={pageCount}
        page={validCurrentPage}
        onChange={onPageChange}
        color="primary"
        disabled={loading}
        size="large"
        showFirstButton
        showLastButton
        siblingCount={siblingCount}
        boundaryCount={boundaryCount}
        hideNextButton={false}
        hidePrevButton={false}
        sx={{
          '& .MuiPaginationItem-root': {
            borderRadius: 1.5,
            mx: 0.5,
            transition: 'all 0.2s',
            fontSize: '0.9rem',
            '&.Mui-selected': {
              fontWeight: 'bold',
              background: theme => theme.palette.primary.main,
              color: 'white',
              minWidth: '34px',
              height: '34px',
              transform: 'scale(1.05)',
            },
            '&.MuiPaginationItem-page': {
              minWidth: '34px',
              height: '34px',
            }
          },
        }}
        {...props}
      />
    </Stack>
  )
}

export default PaginationStyled 