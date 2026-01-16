import { useContext } from 'react'
import {
  CopyableTextDialogContext,
  CopyableTextDialogContextType,
} from '../components/common/CopyableTextDialogProvider'

/**
 * Hook to access the copyable text dialog context
 * Must be used within a CopyableTextDialogProvider
 *
 * @throws Error if used outside of CopyableTextDialogProvider
 * @returns The dialog context with showDialog and hideDialog methods
 *
 * @example
 * ```tsx
 * const { showDialog } = useCopyableTextDialog()
 * showDialog('text to copy', 'Dialog Title')
 * ```
 */
export function useCopyableTextDialog(): CopyableTextDialogContextType {
  const context = useContext(CopyableTextDialogContext)

  if (!context) {
    throw new Error(
      'useCopyableTextDialog must be used within a CopyableTextDialogProvider. ' +
        'Make sure CopyableTextDialogProvider is wrapping your component tree.',
    )
  }

  return context
}
