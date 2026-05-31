import { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  OpenInNew as OpenInNewIcon,
  Refresh as RefreshIcon,
  Science as TestIcon,
} from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { CARD_VARIANTS } from '../../../theme/variants'
import { useNotification } from '../../../hooks/useNotification'
import { EmailAccount, EmailProvider, emailApi } from '../../../services/api/email'

const providers: EmailProvider[] = ['QQ邮箱', '163邮箱', 'Gmail', 'Outlook', '自定义']

const providerLinks: Partial<Record<EmailProvider, Array<{ labelKey: string; url: string }>>> = {
  Gmail: [
    { labelKey: 'emailAccounts.providerLinks.googleCloud', url: 'https://console.cloud.google.com/apis/credentials' },
  ],
  Outlook: [
    { labelKey: 'emailAccounts.providerLinks.microsoftAzure', url: 'https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade' },
  ],
}

function getOAuthRedirectUri() {
  const { protocol, hostname, origin, pathname } = window.location
  const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]'
  if (protocol === 'https:' || isLocalhost) {
    return `${origin}${pathname}`
  }
  return 'http://localhost'
}

const defaultAccount: EmailAccount = {
  EMAIL_ACCOUNT: 'QQ邮箱',
  AUTH_TYPE: 'password',
  TRANSPORT_TYPE: 'imap_smtp',
  OAUTH_PROVIDER: '',
  CLIENT_ID: '',
  CLIENT_SECRET: '',
  TENANT_ID: 'common',
  ACCESS_TOKEN: '',
  REFRESH_TOKEN: '',
  TOKEN_EXPIRES_AT: 0,
  CUSTOM_IMAP_HOST: '',
  CUSTOM_IMAP_PORT: 993,
  CUSTOM_SMTP_HOST: '',
  CUSTOM_SMTP_PORT: 587,
  CUSTOM_SMTP_SSL_PORT: 465,
  CUSTOM_SMTP_USE_SSL: true,
  ENABLED: true,
  USERNAME: '',
  PASSWORD: '',
  SEND_ENABLED: false,
  IS_DEFAULT_SENDER: false,
}

function buildPayload(form: EmailAccount, editing: boolean): Partial<EmailAccount> {
  const payload: Partial<EmailAccount> = { ...form }
  delete payload.index
  delete payload.HAS_PASSWORD
  if (editing && !payload.PASSWORD?.trim()) {
    delete payload.PASSWORD
  }
  if (editing && !payload.CLIENT_SECRET?.trim()) {
    delete payload.CLIENT_SECRET
  }
  if (editing && !payload.ACCESS_TOKEN?.trim()) {
    delete payload.ACCESS_TOKEN
  }
  if (editing && !payload.REFRESH_TOKEN?.trim()) {
    delete payload.REFRESH_TOKEN
  }
  return payload
}

export default function EmailAccountsPage() {
  const { t } = useTranslation('adapter')
  const notification = useNotification()
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [form, setForm] = useState<EmailAccount>(defaultAccount)
  const [deleteIndex, setDeleteIndex] = useState<number | null>(null)
  const [callbackDialogOpen, setCallbackDialogOpen] = useState(false)
  const [callbackText, setCallbackText] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['email-accounts'],
    queryFn: emailApi.getAccounts,
  })

  const invalidateAccounts = async () => {
    await queryClient.invalidateQueries({ queryKey: ['email-accounts'] })
  }

  const createMutation = useMutation({
    mutationFn: emailApi.createAccount,
    onSuccess: async () => {
      notification.success(t('emailAccounts.saveSuccess'))
      setDialogOpen(false)
      await invalidateAccounts()
    },
    onError: (err: Error) => notification.error(err.message || t('emailAccounts.saveFailed')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ index, account }: { index: number; account: Partial<EmailAccount> }) =>
      emailApi.updateAccount(index, account),
    onSuccess: async () => {
      notification.success(t('emailAccounts.saveSuccess'))
      setDialogOpen(false)
      await invalidateAccounts()
    },
    onError: (err: Error) => notification.error(err.message || t('emailAccounts.saveFailed')),
  })

  const deleteMutation = useMutation({
    mutationFn: emailApi.deleteAccount,
    onSuccess: async () => {
      notification.success(t('emailAccounts.deleteSuccess'))
      setDeleteIndex(null)
      await invalidateAccounts()
    },
    onError: (err: Error) => notification.error(err.message || t('emailAccounts.deleteFailed')),
  })

  const testMutation = useMutation({
    mutationFn: emailApi.testAccount,
    onSuccess: async result => {
      if (result.success) {
        notification.success(t('emailAccounts.testSuccess'))
      } else {
        notification.error(result.message || t('emailAccounts.testFailed'))
      }
      await invalidateAccounts()
    },
    onError: (err: Error) => notification.error(err.message || t('emailAccounts.testFailed')),
  })

  const openCreateDialog = () => {
    setEditingIndex(null)
    setForm(defaultAccount)
    setDialogOpen(true)
  }

  const openEditDialog = (account: EmailAccount) => {
    setEditingIndex(account.index ?? null)
    setForm({ ...defaultAccount, ...account, PASSWORD: '' })
    setDialogOpen(true)
  }

  const buildAccountPayload = (editing: boolean) => {
    const payload = buildPayload(form, editing)
    if (form.EMAIL_ACCOUNT === 'Gmail') {
      payload.AUTH_TYPE = 'oauth2'
      payload.TRANSPORT_TYPE = 'imap_smtp'
      payload.OAUTH_PROVIDER = 'google'
      payload.USERNAME = form.USERNAME.trim() || `pending-google-${Date.now()}`
    } else if (form.EMAIL_ACCOUNT === 'Outlook') {
      payload.AUTH_TYPE = 'oauth2'
      payload.TRANSPORT_TYPE = 'imap_smtp'
      payload.OAUTH_PROVIDER = 'microsoft'
      payload.USERNAME = form.USERNAME.trim() || `pending-microsoft-${Date.now()}`
    }
    return payload
  }

  const handleSave = () => {
    const editing = editingIndex !== null
    const payload = buildAccountPayload(editing)
    if (editing) {
      updateMutation.mutate({ index: editingIndex, account: payload })
    } else {
      createMutation.mutate(payload as EmailAccount)
    }
  }

  const updateForm = <K extends keyof EmailAccount>(key: K, value: EmailAccount[K]) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')
    if (!code || !state?.startsWith('email:')) return

    const index = Number(state.replace('email:', ''))
    if (!Number.isInteger(index)) return

    const redirectUri = getOAuthRedirectUri()
    emailApi.handleOAuthCallback(index, code, redirectUri)
      .then(async () => {
        notification.success(t('emailAccounts.authorizeSuccess'))
        window.history.replaceState({}, document.title, `${window.location.pathname}#/adapters/email/accounts`)
        await queryClient.invalidateQueries({ queryKey: ['email-accounts'] })
      })
      .catch((err: Error) => notification.error(err.message || t('emailAccounts.authorizeFailed')))
  }, [notification, queryClient, t])

  const accounts = data?.accounts ?? []
  const isSaving = createMutation.isPending || updateMutation.isPending
  const isGmail = form.EMAIL_ACCOUNT === 'Gmail'
  const isOutlook = form.EMAIL_ACCOUNT === 'Outlook'
  const isOauthProvider = isGmail || isOutlook
  const currentProviderLinks = providerLinks[form.EMAIL_ACCOUNT] ?? []

  const handleOpenAuthorizeUrl = async () => {
    try {
      const editing = editingIndex !== null
      const payload = buildAccountPayload(editing)
      const savedIndex = editing
        ? editingIndex
        : (await emailApi.createAccount(payload as EmailAccount)).index
      if (editing) {
        await emailApi.updateAccount(editingIndex, payload)
      }
      setEditingIndex(savedIndex)
      const redirectUri = getOAuthRedirectUri()
      const response = await emailApi.createAuthorizeUrl(savedIndex, redirectUri, `email:${savedIndex}`)
      if (redirectUri === 'http://localhost') {
        setCallbackDialogOpen(true)
        setCallbackText('')
        window.open(response.authorize_url, '_blank', 'noopener,noreferrer')
        return
      }
      window.location.href = response.authorize_url
    } catch (err) {
      notification.error(err instanceof Error ? err.message : t('emailAccounts.authorizeUrlFailed'))
    }
  }

  const getConnectionStatus = (account: EmailAccount) => {
    if (account.LAST_TEST_SUCCESS === true) {
      return { color: 'success' as const, label: t('emailAccounts.testConnected') }
    }
    if (account.LAST_TEST_SUCCESS === false) {
      return { color: 'error' as const, label: t('emailAccounts.testFailedStatus') }
    }
    return { color: 'default' as const, label: t('emailAccounts.testNotRun') }
  }

  const handleManualOAuthCallback = async () => {
    let callbackUrl: URL
    try {
      callbackUrl = new URL(callbackText.trim())
    } catch {
      notification.error(t('emailAccounts.invalidCallbackUrl'))
      return
    }

    const code = callbackUrl.searchParams.get('code')
    const state = callbackUrl.searchParams.get('state')
    if (!code || !state?.startsWith('email:')) {
      notification.error(t('emailAccounts.invalidCallbackUrl'))
      return
    }
    const index = Number(state.replace('email:', ''))
    if (!Number.isInteger(index)) {
      notification.error(t('emailAccounts.invalidCallbackUrl'))
      return
    }

    try {
      await emailApi.handleOAuthCallback(index, code, 'http://localhost')
      notification.success(t('emailAccounts.authorizeSuccess'))
      setCallbackDialogOpen(false)
      setCallbackText('')
      setDialogOpen(false)
      await queryClient.invalidateQueries({ queryKey: ['email-accounts'] })
    } catch (err) {
      notification.error(err instanceof Error ? err.message : t('emailAccounts.authorizeFailed'))
    }
  }

  return (
    <Box sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }} spacing={2}>
        <Box>
          <Typography variant="h6">{t('emailAccounts.title')}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t('emailAccounts.description')}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button startIcon={<RefreshIcon />} onClick={() => refetch()} disabled={isLoading}>
            {t('emailAccounts.refresh')}
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreateDialog}>
            {t('emailAccounts.add')}
          </Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{t('emailAccounts.loadError')}</Alert>}

      <TableContainer component={Paper} sx={{ ...CARD_VARIANTS.default.styles }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>{t('emailAccounts.enabled')}</TableCell>
              <TableCell>{t('emailAccounts.provider')}</TableCell>
              <TableCell>{t('emailAccounts.username')}</TableCell>
              <TableCell>{t('emailAccounts.authType')}</TableCell>
              <TableCell>{t('emailAccounts.transportType')}</TableCell>
              <TableCell>{t('emailAccounts.connectionStatus')}</TableCell>
              <TableCell>{t('emailAccounts.sendEnabled')}</TableCell>
              <TableCell>{t('emailAccounts.defaultSender')}</TableCell>
              <TableCell align="right">{t('emailAccounts.actions')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {accounts.length > 0 ? accounts.map(account => {
              const connectionStatus = getConnectionStatus(account)
              return (
              <TableRow key={account.index} hover>
                <TableCell>
                  <Chip
                    size="small"
                    color={account.ENABLED ? 'success' : 'default'}
                    label={account.ENABLED ? t('emailAccounts.enabledYes') : t('emailAccounts.enabledNo')}
                  />
                </TableCell>
                <TableCell>{account.EMAIL_ACCOUNT}</TableCell>
                <TableCell>{account.USERNAME || '-'}</TableCell>
                <TableCell>{t(`emailAccounts.authTypes.${account.AUTH_TYPE || 'password'}`)}</TableCell>
                <TableCell>{t(`emailAccounts.transportTypes.${account.TRANSPORT_TYPE || 'imap_smtp'}`)}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    color={connectionStatus.color}
                    label={connectionStatus.label}
                    title={account.LAST_TEST_MESSAGE || undefined}
                  />
                </TableCell>
                <TableCell>{account.SEND_ENABLED ? t('emailAccounts.yes') : t('emailAccounts.no')}</TableCell>
                <TableCell>{account.IS_DEFAULT_SENDER ? t('emailAccounts.yes') : t('emailAccounts.no')}</TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    onClick={() => account.index !== undefined && testMutation.mutate(account.index)}
                    disabled={account.index === undefined || testMutation.isPending}
                    title={t('emailAccounts.testConnection')}
                  >
                    <TestIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => openEditDialog(account)}>
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" color="error" onClick={() => setDeleteIndex(account.index ?? null)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
              )
            }) : (
              <TableRow>
                <TableCell colSpan={9} align="center">
                  <Typography color="text.secondary">{t('emailAccounts.empty')}</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingIndex === null ? t('emailAccounts.add') : t('emailAccounts.edit')}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>{t('emailAccounts.provider')}</InputLabel>
              <Select
                label={t('emailAccounts.provider')}
                value={form.EMAIL_ACCOUNT}
                onChange={event => {
                  const provider = event.target.value as EmailProvider
                  setForm(prev => ({
                    ...prev,
                    EMAIL_ACCOUNT: provider,
                    AUTH_TYPE: provider === 'Gmail' || provider === 'Outlook' ? 'oauth2' : 'password',
                    TRANSPORT_TYPE: 'imap_smtp',
                    OAUTH_PROVIDER: provider === 'Gmail' ? 'google' : provider === 'Outlook' ? 'microsoft' : '',
                  }))
                }}
              >
                {providers.map(provider => (
                  <MenuItem key={provider} value={provider}>{provider}</MenuItem>
                ))}
              </Select>
            </FormControl>
            {currentProviderLinks.length > 0 && (
              <Alert severity="info">
                <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="center">
                  <Typography variant="body2">{t('emailAccounts.providerLinks.description')}</Typography>
                  {currentProviderLinks.map(link => (
                    <Button
                      key={link.url}
                      component="a"
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      size="small"
                      endIcon={<OpenInNewIcon fontSize="small" />}
                    >
                      {t(link.labelKey)}
                    </Button>
                  ))}
                </Stack>
              </Alert>
            )}
            {!isOauthProvider && (
              <TextField
                label={t('emailAccounts.username')}
                value={form.USERNAME}
                onChange={event => updateForm('USERNAME', event.target.value)}
                fullWidth
                required
              />
            )}
            {isOauthProvider && (
              <Alert severity="info">{t(`emailAccounts.oauthHints.${form.EMAIL_ACCOUNT}`)}</Alert>
            )}
            {isOauthProvider ? (
              <Stack spacing={2}>
                <TextField
                  label={t('emailAccounts.clientId')}
                  value={form.CLIENT_ID}
                  onChange={event => updateForm('CLIENT_ID', event.target.value)}
                  fullWidth
                />
                <TextField
                  label={t('emailAccounts.clientSecret')}
                  value={form.CLIENT_SECRET ?? ''}
                  onChange={event => updateForm('CLIENT_SECRET', event.target.value)}
                  fullWidth
                  type="password"
                  helperText={editingIndex !== null ? t('emailAccounts.clientSecretHelp') : undefined}
                />
                {isOutlook && (
                  <TextField
                    label={t('emailAccounts.tenantId')}
                    value={form.TENANT_ID}
                    onChange={event => updateForm('TENANT_ID', event.target.value)}
                    fullWidth
                    helperText={t('emailAccounts.tenantIdHelp')}
                  />
                )}
                <Stack direction="row" spacing={1}>
                  <Button variant="outlined" onClick={handleOpenAuthorizeUrl} disabled={!form.CLIENT_ID.trim()}>
                    {isGmail ? t('emailAccounts.connectGoogle') : t('emailAccounts.connectMicrosoft')}
                  </Button>
                </Stack>
                <Alert severity="warning">{t('emailAccounts.oauthPending')}</Alert>
              </Stack>
            ) : (
              <TextField
                label={t('emailAccounts.password')}
                value={form.PASSWORD ?? ''}
                onChange={event => updateForm('PASSWORD', event.target.value)}
                fullWidth
                type="password"
                placeholder={editingIndex !== null && form.HAS_PASSWORD ? t('emailAccounts.passwordPlaceholder') : undefined}
                helperText={editingIndex !== null && form.HAS_PASSWORD ? t('emailAccounts.passwordHelp') : undefined}
              />
            )}
            <Stack direction="row" spacing={2} flexWrap="wrap">
              <FormControlLabel
                control={<Switch checked={form.ENABLED} onChange={event => updateForm('ENABLED', event.target.checked)} />}
                label={t('emailAccounts.enabled')}
              />
              <FormControlLabel
                control={<Switch checked={form.SEND_ENABLED} onChange={event => updateForm('SEND_ENABLED', event.target.checked)} />}
                label={t('emailAccounts.sendEnabled')}
              />
              <FormControlLabel
                control={<Switch checked={form.IS_DEFAULT_SENDER} onChange={event => updateForm('IS_DEFAULT_SENDER', event.target.checked)} />}
                label={t('emailAccounts.defaultSender')}
              />
            </Stack>

            {form.EMAIL_ACCOUNT === '自定义' && (
              <Stack spacing={2}>
                <Typography variant="subtitle2">{t('emailAccounts.customServer')}</Typography>
                <TextField
                  label={t('emailAccounts.customImapHost')}
                  value={form.CUSTOM_IMAP_HOST}
                  onChange={event => updateForm('CUSTOM_IMAP_HOST', event.target.value)}
                  fullWidth
                />
                <TextField
                  label={t('emailAccounts.customImapPort')}
                  value={form.CUSTOM_IMAP_PORT}
                  onChange={event => updateForm('CUSTOM_IMAP_PORT', Number(event.target.value))}
                  type="number"
                  fullWidth
                />
                <TextField
                  label={t('emailAccounts.customSmtpHost')}
                  value={form.CUSTOM_SMTP_HOST}
                  onChange={event => updateForm('CUSTOM_SMTP_HOST', event.target.value)}
                  fullWidth
                />
                <Stack direction="row" spacing={2}>
                  <TextField
                    label={t('emailAccounts.customSmtpPort')}
                    value={form.CUSTOM_SMTP_PORT}
                    onChange={event => updateForm('CUSTOM_SMTP_PORT', Number(event.target.value))}
                    type="number"
                    fullWidth
                  />
                  <TextField
                    label={t('emailAccounts.customSmtpSslPort')}
                    value={form.CUSTOM_SMTP_SSL_PORT}
                    onChange={event => updateForm('CUSTOM_SMTP_SSL_PORT', Number(event.target.value))}
                    type="number"
                    fullWidth
                  />
                </Stack>
                <FormControlLabel
                  control={
                    <Switch
                      checked={form.CUSTOM_SMTP_USE_SSL}
                      onChange={event => updateForm('CUSTOM_SMTP_USE_SSL', event.target.checked)}
                    />
                  }
                  label={t('emailAccounts.customSmtpUseSsl')}
                />
              </Stack>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t('emailAccounts.cancel')}</Button>
          <Button onClick={handleSave} variant="contained" disabled={isSaving || (!isOauthProvider && !form.USERNAME.trim())}>
            {t('emailAccounts.save')}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={callbackDialogOpen} onClose={() => setCallbackDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('emailAccounts.manualCallbackTitle')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Alert severity="info">{t('emailAccounts.manualCallbackDescription')}</Alert>
            <TextField
              label={t('emailAccounts.manualCallbackUrl')}
              value={callbackText}
              onChange={event => setCallbackText(event.target.value)}
              fullWidth
              multiline
              minRows={3}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCallbackDialogOpen(false)}>{t('emailAccounts.cancel')}</Button>
          <Button onClick={handleManualOAuthCallback} variant="contained" disabled={!callbackText.trim()}>
            {t('emailAccounts.completeAuthorize')}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteIndex !== null} onClose={() => setDeleteIndex(null)}>
        <DialogTitle>{t('emailAccounts.delete')}</DialogTitle>
        <DialogContent>
          <Typography>{t('emailAccounts.deleteConfirm')}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteIndex(null)}>{t('emailAccounts.cancel')}</Button>
          <Button
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
            onClick={() => deleteIndex !== null && deleteMutation.mutate(deleteIndex)}
          >
            {t('emailAccounts.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
