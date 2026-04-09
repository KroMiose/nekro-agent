import SearchIcon from '@mui/icons-material/Search'
import CloseRoundedIcon from '@mui/icons-material/CloseRounded'
import { InputAdornment, SxProps, TextField, TextFieldProps, Theme } from '@mui/material'
import IconActionButton from './IconActionButton'
import { INPUT_VARIANTS } from '../../theme/variants'

interface SearchFieldProps extends Omit<TextFieldProps, 'value' | 'onChange'> {
  value: string
  onChange: (value: string) => void
  onClear?: () => void
  clearAriaLabel?: string
}

export default function SearchField({
  value,
  onChange,
  onClear,
  clearAriaLabel,
  sx,
  InputProps,
  size = 'small',
  ...props
}: SearchFieldProps) {
  const mergedSx = (
    sx
      ? [INPUT_VARIANTS.default.styles, sx]
      : INPUT_VARIANTS.default.styles
  ) as SxProps<Theme>

  return (
    <TextField
      {...props}
      value={value}
      size={size}
      onChange={event => onChange(event.target.value)}
      sx={mergedSx}
      InputProps={{
        ...InputProps,
        startAdornment: (
          <InputAdornment position="start">
            <SearchIcon fontSize="small" />
          </InputAdornment>
        ),
        endAdornment:
          value && onClear ? (
            <InputAdornment position="end">
              <IconActionButton
                tone="subtle"
                size="small"
                onClick={onClear}
                aria-label={clearAriaLabel}
              >
                <CloseRoundedIcon fontSize="small" />
              </IconActionButton>
            </InputAdornment>
          ) : InputProps?.endAdornment,
      }}
    />
  )
}
