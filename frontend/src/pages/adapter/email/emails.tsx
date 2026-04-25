import { useState } from 'react'
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material'
import { AttachFile as AttachFileIcon } from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { CARD_VARIANTS } from '../../../theme/variants'
import TablePaginationStyled from '../../../components/common/TablePaginationStyled'

interface Email {
  id: number
  account_username: string
  subject: string
  sender: string
  date: string | null
  body_preview: string
  has_attachments: boolean
  create_time: string
}

interface EmailListResponse {
  items: Email[]
  pagination: {
    offset: number
    limit: number
    total: number
    has_more: boolean
  }
}

export default function EmailsPage() {
  const { t } = useTranslation('adapter')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(25)

  const { data, isLoading, error } = useQuery<EmailListResponse>({
    queryKey: ['emails', page, rowsPerPage],
    queryFn: async () => {
      const response = await fetch(
        `/api/emails?offset=${page * rowsPerPage}&limit=${rowsPerPage}`
      )
      if (!response.ok) throw new Error('Failed to fetch emails')
      return response.json()
    },
    refetchInterval: 30000,
  })

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage)
  }

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10))
    setPage(0)
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    try {
      return new Date(dateStr).toLocaleString()
    } catch {
      return dateStr
    }
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">{t('emails.loadError')}</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        {t('emails.title')}
      </Typography>
      <TableContainer component={Paper} sx={{ ...CARD_VARIANTS.default.styles }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>{t('emails.subject')}</TableCell>
              <TableCell>{t('emails.sender')}</TableCell>
              <TableCell>{t('emails.account')}</TableCell>
              <TableCell>{t('emails.date')}</TableCell>
              <TableCell align="center">{t('emails.attachments')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data?.items && data.items.length > 0 ? (
              data.items.map(email => (
                <TableRow key={email.id} hover>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                      {email.subject || t('emails.noSubject')}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                      {email.sender}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={email.account_username} size="small" />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ whiteSpace: 'nowrap' }}>
                      {formatDate(email.date)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    {email.has_attachments && <AttachFileIcon fontSize="small" color="action" />}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography color="text.secondary">{t('emails.noEmails')}</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <TablePaginationStyled
          component="div"
          count={data?.pagination.total ?? -1}
          page={page}
          onPageChange={handleChangePage}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </TableContainer>
    </Box>
  )
}
