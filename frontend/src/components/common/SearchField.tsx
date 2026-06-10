import { useState } from 'react'
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
  const [isComposing, setIsComposing] = useState(false)
  const [compositionValue, setCompositionValue] = useState(value)
  const displayValue = isComposing ? compositionValue : value
  const mergedSx = (
    sx
      ? [INPUT_VARIANTS.default.styles, sx]
      : INPUT_VARIANTS.default.styles
  ) as SxProps<Theme>

  return (
    <TextField
      {...props}
      value={displayValue}
      size={size}
      onCompositionStart={event => {
        const nextValue = event.target instanceof HTMLInputElement ? event.target.value : ''
        setIsComposing(true)
        setCompositionValue(nextValue)
      }}
      onCompositionEnd={event => {
        const nextValue = event.target instanceof HTMLInputElement ? event.target.value : ''
        setIsComposing(false)
        setCompositionValue(nextValue)
        onChange(nextValue)
      }}
      onChange={event => {
        const nextValue = event.target.value
        if (isComposing || event.nativeEvent.isComposing) {
          setCompositionValue(nextValue)
          return
        }
        onChange(nextValue)
      }}
      sx={mergedSx}
      InputProps={{
        ...InputProps,
        startAdornment: (
          <InputAdornment position="start">
            <SearchIcon fontSize="small" />
          </InputAdornment>
        ),
        endAdornment:
          displayValue && onClear ? (
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
