import { ReactNode } from 'react'
import {
  Box,
  SxProps,
  Theme,
  ToggleButtonProps,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
} from '@mui/material'
import {
  SEGMENTED_CONTROL_VARIANTS,
  SegmentedControlDensity,
} from '../../theme/variants'

export interface SegmentedControlOption<T extends string> {
  value: T
  label?: ReactNode
  icon?: ReactNode
  tooltip?: ReactNode
  disabled?: boolean
  ariaLabel?: string
  iconOnly?: boolean
  sx?: SxProps<Theme>
}

interface SegmentedControlProps<T extends string> {
  value: T
  options: SegmentedControlOption<T>[]
  onChange: (value: T) => void
  density?: SegmentedControlDensity
  disabled?: boolean
  fullWidth?: boolean
  sx?: SxProps<Theme>
}

export default function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  density = 'compact',
  disabled = false,
  fullWidth = false,
  sx,
}: SegmentedControlProps<T>) {
  const baseGroupSx = SEGMENTED_CONTROL_VARIANTS.container(density) as Record<string, unknown>

  return (
    <ToggleButtonGroup
      exclusive
      value={value}
      onChange={(_, nextValue: T | null) => {
        if (nextValue !== null) {
          onChange(nextValue)
        }
      }}
      disabled={disabled}
      sx={{
        ...baseGroupSx,
        width: fullWidth ? '100%' : 'auto',
        '& .MuiToggleButtonGroup-grouped': {
          ...(baseGroupSx['& .MuiToggleButtonGroup-grouped'] as object),
          flex: fullWidth ? 1 : undefined,
        },
        ...sx,
      }}
    >
      {options.map(option => {
        const content = (
          <Box className="segmented-control-content">
            {option.icon ? (
              <Box className="segmented-control-icon">{option.icon}</Box>
            ) : null}
            {option.label ? <Box component="span">{option.label}</Box> : null}
          </Box>
        )

        const buttonContent = option.tooltip ? (
          <Tooltip title={option.tooltip}>
            <Box component="span">{content}</Box>
          </Tooltip>
        ) : (
          content
        )

        return (
          <ToggleButton
            key={option.value}
            value={option.value}
            disabled={option.disabled}
            aria-label={option.ariaLabel}
            sx={
              (
                option.sx
                  ? [
                      SEGMENTED_CONTROL_VARIANTS.item(
                        density,
                        option.iconOnly ?? (!option.label && Boolean(option.icon))
                      ),
                      option.sx,
                    ]
                  : SEGMENTED_CONTROL_VARIANTS.item(
                      density,
                      option.iconOnly ?? (!option.label && Boolean(option.icon))
                    )
              ) as ToggleButtonProps['sx']
            }
          >
            {buttonContent}
          </ToggleButton>
        )
      })}
    </ToggleButtonGroup>
  )
}
