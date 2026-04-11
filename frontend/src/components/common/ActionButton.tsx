import { Button, ButtonProps, SxProps, Theme } from '@mui/material'
import { forwardRef } from 'react'
import { ACTION_BUTTON_VARIANTS } from '../../theme/variants'

export type ActionButtonTone = 'primary' | 'secondary' | 'ghost' | 'danger'

interface ActionButtonProps extends Omit<ButtonProps, 'color'> {
  tone?: ActionButtonTone
}

const DEFAULT_VARIANT: Record<ActionButtonTone, ButtonProps['variant']> = {
  primary: 'contained',
  secondary: 'outlined',
  ghost: 'text',
  danger: 'outlined',
}

const ActionButton = forwardRef<HTMLButtonElement, ActionButtonProps>(function ActionButton(
  { tone = 'secondary', variant, sx, ...props },
  ref,
) {
  const mergedSx = (
    sx
      ? [ACTION_BUTTON_VARIANTS[tone].styles, sx]
      : ACTION_BUTTON_VARIANTS[tone].styles
  ) as SxProps<Theme>

  return (
    <Button
      {...props}
      ref={ref}
      variant={variant ?? DEFAULT_VARIANT[tone]}
      sx={mergedSx}
    />
  )
})

export default ActionButton
