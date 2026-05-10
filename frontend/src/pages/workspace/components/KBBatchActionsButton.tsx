import { useState } from 'react'
import { Menu, MenuItem } from '@mui/material'
import { ArrowDropDown as ArrowDropDownIcon } from '@mui/icons-material'
import ActionButton from '../../../components/common/ActionButton'

export interface KBBatchActionItem {
  key: string
  label: string
  onClick: () => void
  disabled?: boolean
}

interface KBBatchActionsButtonProps {
  label: string
  actions: KBBatchActionItem[]
  disabled?: boolean
}

export default function KBBatchActionsButton({
  label,
  actions,
  disabled = false,
}: KBBatchActionsButtonProps) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const open = anchorEl != null

  return (
    <>
      <ActionButton
        size="small"
        tone="secondary"
        endIcon={<ArrowDropDownIcon />}
        onClick={event => setAnchorEl(event.currentTarget)}
        disabled={disabled}
      >
        {label}
      </ActionButton>
      <Menu anchorEl={anchorEl} open={open} onClose={() => setAnchorEl(null)}>
        {actions.map(action => (
          <MenuItem
            key={action.key}
            onClick={() => {
              setAnchorEl(null)
              action.onClick()
            }}
            disabled={action.disabled}
          >
            {action.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  )
}
