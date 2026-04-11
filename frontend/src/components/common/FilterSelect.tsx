import { FormControl, FormControlProps, InputLabel, MenuItem, Select } from '@mui/material'

export interface FilterSelectOption {
  value: string
  label: string
}

interface FilterSelectProps extends Omit<FormControlProps, 'onChange'> {
  label: string
  value: string
  options: FilterSelectOption[]
  onChange: (value: string) => void
}

export default function FilterSelect({
  label,
  value,
  options,
  onChange,
  size = 'small',
  fullWidth = true,
  ...props
}: FilterSelectProps) {
  return (
    <FormControl {...props} size={size} fullWidth={fullWidth}>
      <InputLabel>{label}</InputLabel>
      <Select
        value={value}
        label={label}
        onChange={event => onChange(String(event.target.value))}
      >
        {options.map(option => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}
