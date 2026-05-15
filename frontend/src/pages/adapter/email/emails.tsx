import { useEffect, useState, type ChangeEvent } from 'react'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Chip,
  CircularProgress,
  Divider,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material'
import {
  AttachFile as AttachFileIcon,
  MailOutline as MailOutlineIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import MarkdownRenderer from '../../../components/common/MarkdownRenderer'
import ActionButton from '../../../components/common/ActionButton'
import NekroDialog from '../../../components/common/NekroDialog'
import TablePaginationStyled from '../../../components/common/TablePaginationStyled'
import {
  emailsApi,
  type EmailAttachment,
  type EmailDetail,
  type EmailListResponse,
  type EmailRawContent,
} from '../../../services/api/emails'
import { CARD_VARIANTS } from '../../../theme/variants'

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleString()
  } catch {
    return dateStr
  }
}

function parseStringList(raw: string): string[] {
  if (!raw.trim()) return []
  try {
    const parsed = JSON.parse(raw) as unknown
    return Array.isArray(parsed) ? parsed.filter(item => typeof item === 'string') : []
  } catch {
    return raw
      .split(',')
      .map(item => item.trim())
      .filter(Boolean)
  }
}

function DetailSkeleton() {
  return (
    <Stack spacing={2}>
      <Skeleton variant="text" width="45%" height={36} />
      <Skeleton variant="rounded" height={84} />
      <Skeleton variant="rounded" height={220} />
      <Skeleton variant="rounded" height={220} />
    </Stack>
  )
}

function DetailContent({
  detail,
  rawContent,
  rawLoading,
  isLoading,
  hasError,
  t,
}: {
  detail?: EmailDetail
  rawContent?: EmailRawContent
  rawLoading: boolean
  isLoading: boolean
  hasError: boolean
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  const [bodyView, setBodyView] = useState<'html' | 'text'>('html')
  const [expandedAttachment, setExpandedAttachment] = useState<string | null>(null)

  useEffect(() => {
    setExpandedAttachment(null)
    setBodyView(rawContent?.html_content ? 'html' : 'text')
  }, [detail?.id, rawContent?.html_content])

  if (isLoading) {
    return <DetailSkeleton />
  }

  if (hasError) {
    return <Alert severity="error">{t('emails.detailLoadError')}</Alert>
  }

  if (!detail) {
    return (
      <Stack
        spacing={1}
        justifyContent="center"
        alignItems="center"
        sx={{ minHeight: 360, textAlign: 'center', color: 'text.secondary' }}
      >
        <MailOutlineIcon color="disabled" />
        <Typography variant="body2">{t('emails.selectHint')}</Typography>
      </Stack>
    )
  }

  const recipients = parseStringList(detail.recipients)
  const attachments = detail.attachments ?? []
  const hasHtmlBody = Boolean(rawContent?.html_content?.trim())
  const displayTextBody = rawContent?.text_content || detail.body_text

  return (
    <Stack spacing={2.5}>
      <Stack spacing={1}>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip label={detail.account_username} size="small" color="primary" variant="outlined" />
          <Chip label={formatDate(detail.date)} size="small" variant="outlined" />
          {detail.has_attachments && (
            <Chip
              icon={<AttachFileIcon fontSize="small" />}
              label={t('emails.attachmentsCount', { count: attachments.length })}
              size="small"
              variant="outlined"
            />
          )}
        </Stack>
        <Typography variant="h5" sx={{ fontWeight: 700, wordBreak: 'break-word' }}>
          {detail.subject || t('emails.noSubject')}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {detail.sender}
        </Typography>
      </Stack>

      <Paper sx={{ ...CARD_VARIANTS.default.styles, p: 2 }}>
        <Stack spacing={1.5}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {t('emails.recipients')}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 0.75 }}>
              {recipients.length > 0 ? (
                recipients.map(recipient => <Chip key={recipient} label={recipient} size="small" variant="outlined" />)
              ) : (
                <Typography variant="body2">-</Typography>
              )}
            </Stack>
          </Box>

          <Divider />

          <Box>
            <Typography variant="caption" color="text.secondary">
              {t('emails.inReplyToLabel')}
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5, wordBreak: 'break-all', fontFamily: 'monospace' }}>
              {detail.in_reply_to || '-'}
            </Typography>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary">
              {t('emails.referencesLabel')}
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5, wordBreak: 'break-all', fontFamily: 'monospace' }}>
              {detail.references || '-'}
            </Typography>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary">
              {t('emails.createdAt')}
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5 }}>
              {formatDate(detail.create_time)}
            </Typography>
          </Box>
        </Stack>
      </Paper>

      <Paper sx={{ ...CARD_VARIANTS.default.styles, p: 2 }}>
        <Stack spacing={1.5}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
            <Typography variant="subtitle2">{t('emails.body')}</Typography>
            <Stack direction="row" spacing={0.5}>
              {hasHtmlBody && (
                <ActionButton
                  tone={bodyView === 'html' ? 'primary' : 'secondary'}
                  onClick={() => setBodyView('html')}
                  sx={{ minWidth: 88 }}
                >
                  {t('emails.bodyHtml')}
                </ActionButton>
              )}
              <ActionButton
                tone={bodyView === 'text' ? 'primary' : 'secondary'}
                onClick={() => setBodyView('text')}
                sx={{ minWidth: 88 }}
              >
                {t('emails.bodyText')}
              </ActionButton>
            </Stack>
          </Stack>

          {rawLoading ? (
            <Skeleton variant="rounded" height={220} />
          ) : bodyView === 'html' && hasHtmlBody ? (
            <Box
              sx={{
                p: 1.5,
                borderRadius: 2,
                border: theme => `1px solid ${theme.palette.divider}`,
                backgroundColor: 'background.paper',
                '& img': {
                  maxWidth: '100%',
                  height: 'auto',
                },
              }}
              dangerouslySetInnerHTML={{ __html: rawContent?.html_content || '' }}
            />
          ) : (
            <Typography
              variant="body2"
              sx={{
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                lineHeight: 1.75,
                color: displayTextBody ? 'text.primary' : 'text.secondary',
              }}
            >
              {displayTextBody || t('emails.bodyEmpty')}
            </Typography>
          )}

          <Accordion
            disableGutters
            elevation={0}
            sx={{
              mt: 1,
              bgcolor: 'transparent',
              '&:before': { display: 'none' },
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              sx={{
                px: 0,
                minHeight: 40,
                '& .MuiAccordionSummary-content': {
                  my: 0,
                  alignItems: 'center',
                },
              }}
            >
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="subtitle2">{t('emails.attachments')}</Typography>
                <Chip
                  size="small"
                  label={attachments.length > 0 ? t('emails.attachmentsCount', { count: attachments.length }) : t('emails.noAttachments')}
                  variant="outlined"
                />
              </Stack>
            </AccordionSummary>
            <AccordionDetails sx={{ px: 0, pt: 0.5, pb: 0 }}>
              {attachments.length > 0 ? (
                <Stack spacing={1.25}>
                  {attachments.map(attachment => (
                    <AttachmentPreview
                      key={attachment}
                      attachment={attachment}
                      expanded={expandedAttachment === attachment.name}
                      onToggle={() =>
                        setExpandedAttachment(prev => (prev === attachment.name ? null : attachment.name))
                      }
                      t={t}
                    />
                  ))}
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  {t('emails.noAttachments')}
                </Typography>
              )}
            </AccordionDetails>
          </Accordion>
        </Stack>
      </Paper>
    </Stack>
  )
}

export default function EmailsPage() {
  const { t } = useTranslation('adapter')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(25)
  const [selectedEmailId, setSelectedEmailId] = useState<number | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const { data, isLoading, error } = useQuery<EmailListResponse>({
    queryKey: ['emails', page, rowsPerPage],
    queryFn: () => emailsApi.getEmails({ offset: page * rowsPerPage, limit: rowsPerPage }),
    refetchInterval: 30000,
  })

  useEffect(() => {
    const firstEmailId = data?.items[0]?.id ?? null
    if (!data?.items.length) {
      setSelectedEmailId(null)
      setDetailOpen(false)
      return
    }
    if (selectedEmailId === null || !data.items.some(email => email.id === selectedEmailId)) {
      setSelectedEmailId(firstEmailId)
    }
  }, [data, selectedEmailId])

  const {
    data: detail,
    isLoading: detailLoading,
    error: detailError,
  } = useQuery<EmailDetail>({
    queryKey: ['email-detail', selectedEmailId],
    queryFn: () => emailsApi.getEmailDetail(selectedEmailId as number),
    enabled: selectedEmailId !== null,
  })

  const { data: rawContent, isLoading: rawLoading } = useQuery<EmailRawContent>({
    queryKey: ['email-raw-content', selectedEmailId],
    queryFn: () => emailsApi.getEmailRawContent(selectedEmailId as number),
    enabled: selectedEmailId !== null,
  })

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage)
  }

  const handleChangeRowsPerPage = (event: ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10))
    setPage(0)
  }

  const handleSelectEmail = (emailId: number) => {
    setSelectedEmailId(emailId)
    setDetailOpen(true)
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
    <Box sx={{ p: { xs: 1.5, md: 2 }, display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Paper sx={{ ...CARD_VARIANTS.default.styles, p: { xs: 2, md: 2.5 } }}>
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={1.5}
          alignItems={{ xs: 'flex-start', md: 'center' }}
          justifyContent="space-between"
        >
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              {t('emails.title')}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
              {t('emails.subtitle')}
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={t('emails.total', { count: data?.pagination.total ?? 0 })} size="small" variant="outlined" />
            <Chip label={t('emails.refreshHint')} size="small" variant="outlined" />
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ ...CARD_VARIANTS.default.styles, overflow: 'hidden' }}>
        <Box sx={{ px: 2, py: 1.5 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {t('emails.listTitle')}
          </Typography>
        </Box>
        <Divider />

        {data?.items.length ? (
          <>
            <List disablePadding>
              {data.items.map(email => {
                const isSelected = email.id === selectedEmailId && detailOpen
                return (
                  <ListItemButton
                    key={email.id}
                    selected={isSelected}
                    onClick={() => handleSelectEmail(email.id)}
                    sx={{
                      px: 2,
                      py: 1.75,
                      alignItems: 'flex-start',
                      borderLeft: '3px solid',
                      borderLeftColor: isSelected ? 'primary.main' : 'transparent',
                      '&.Mui-selected': {
                        backgroundColor: 'action.selected',
                      },
                      '&.Mui-selected:hover': {
                        backgroundColor: 'action.selected',
                      },
                    }}
                  >
                    <Box sx={{ width: '100%' }}>
                      <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                        <Typography
                          variant="subtitle2"
                          sx={{ fontWeight: 600, pr: 1, flex: 1, minWidth: 0 }}
                          noWrap
                        >
                          {email.subject || t('emails.noSubject')}
                        </Typography>
                        {email.has_attachments && <AttachFileIcon fontSize="small" color="action" />}
                      </Stack>

                      <ListItemText
                        sx={{ my: 0.75 }}
                        primary={
                          <Typography variant="body2" color="text.secondary" noWrap>
                            {email.sender}
                          </Typography>
                        }
                        secondary={
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              mt: 0.75,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }}
                          >
                            {email.body_preview || t('emails.bodyEmpty')}
                          </Typography>
                        }
                      />

                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                        <Chip label={email.account_username} size="small" variant="outlined" />
                        <Chip label={formatDate(email.date)} size="small" variant="outlined" />
                      </Stack>
                    </Box>
                  </ListItemButton>
                )
              })}
            </List>

            <Divider />
            <TablePaginationStyled
              component="div"
              count={data?.pagination.total ?? -1}
              page={page}
              onPageChange={handleChangePage}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={handleChangeRowsPerPage}
              rowsPerPageOptions={[10, 25, 50, 100]}
            />
          </>
        ) : (
          <Box sx={{ px: 2, py: 8, textAlign: 'center' }}>
            <Typography color="text.secondary">{t('emails.noEmails')}</Typography>
          </Box>
        )}
      </Paper>

      <NekroDialog
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={t('emails.detailTitle')}
        maxWidth="md"
        fullWidth
        dividers
      >
        <DetailContent
          detail={detail}
          rawContent={rawContent}
          rawLoading={rawLoading}
          isLoading={detailLoading}
          hasError={Boolean(detailError)}
          t={t}
        />
      </NekroDialog>
    </Box>
  )
}

function AttachmentPreview({
  attachment,
  expanded,
  onToggle,
  t,
}: {
  attachment: EmailAttachment
  expanded: boolean
  onToggle: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  const { data: textContent, isLoading } = useQuery({
    queryKey: ['email-attachment-text', attachment.url],
    queryFn: () => emailsApi.getAttachmentText(attachment.url),
    enabled: expanded && (attachment.preview_type === 'text' || attachment.preview_type === 'markdown'),
  })
  const accessUrl = emailsApi.getAttachmentAccessUrl(attachment.url)

  return (
    <Paper sx={{ ...CARD_VARIANTS.default.styles, p: 1.25 }}>
      <Stack spacing={1}>
        <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" flexWrap="wrap" useFlexGap>
          <Chip
            icon={<AttachFileIcon fontSize="small" />}
            label={attachment.name}
            size="small"
            variant="outlined"
            onClick={onToggle}
            clickable
          />
          <Stack direction="row" spacing={1}>
            <Chip
              label={t(`emails.previewType.${attachment.preview_type}`)}
              size="small"
              variant="outlined"
            />
            <Chip
              label={expanded ? t('emails.collapseAttachment') : t('emails.expandAttachment')}
              size="small"
              variant="outlined"
              onClick={onToggle}
              clickable
            />
          </Stack>
        </Stack>

        {expanded && (
          <Box sx={{ pt: 0.5 }}>
            {attachment.preview_type === 'image' && (
              <Box component="img" src={accessUrl} alt={attachment.name} sx={{ maxWidth: '100%', borderRadius: 2 }} />
            )}
            {attachment.preview_type === 'pdf' && (
              <Box
                component="iframe"
                src={accessUrl}
                title={attachment.name}
                sx={{ width: '100%', minHeight: 480, border: 0, borderRadius: 2 }}
              />
            )}
            {attachment.preview_type === 'markdown' && (
              isLoading ? <Skeleton variant="rounded" height={180} /> : <MarkdownRenderer>{textContent || ''}</MarkdownRenderer>
            )}
            {attachment.preview_type === 'text' && (
              isLoading ? (
                <Skeleton variant="rounded" height={180} />
              ) : (
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.7 }}>
                  {textContent || t('emails.attachmentEmpty')}
                </Typography>
              )
            )}
            {attachment.preview_type === 'download' && (
              <Typography variant="body2" color="text.secondary">
                <a href={accessUrl} target="_blank" rel="noreferrer">
                  {t('emails.openAttachment')}
                </a>
              </Typography>
            )}
          </Box>
        )}
      </Stack>
    </Paper>
  )
}
