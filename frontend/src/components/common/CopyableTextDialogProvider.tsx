import React, { createContext, useState, useCallback, useEffect, ReactNode } from 'react'
import CopyableTextDialog from './CopyableTextDialog'

export interface CopyableTextDialogEventDetail {
  text: string
  title?: string
  description?: string
}

export const COPYABLE_TEXT_DIALOG_EVENT = 'nekro:showCopyableTextDialog'

interface DialogState {
  open: boolean
  text: string
  title?: string
  description?: string
}

export interface CopyableTextDialogContextType {
  showDialog: (text: string, title?: string, description?: string) => void
  hideDialog: () => void
}

export const CopyableTextDialogContext = createContext<CopyableTextDialogContextType | undefined>(
  undefined,
)

export interface CopyableTextDialogProviderProps {
  children: ReactNode
}

export const CopyableTextDialogProvider: React.FC<CopyableTextDialogProviderProps> = ({
  children,
}) => {
  const [dialogState, setDialogState] = useState<DialogState>({
    open: false,
    text: '',
  })

  const showDialog = useCallback(
    (text: string, title?: string, description?: string) => {
      setDialogState({
        open: true,
        text,
        title,
        description,
      })
    },
    [],
  )

  const hideDialog = useCallback(() => {
    setDialogState(prev => ({
      ...prev,
      open: false,
    }))
  }, [])

  // 监听全局事件
  useEffect(() => {
    const handleEvent = (event: Event) => {
      const customEvent = event as CustomEvent<CopyableTextDialogEventDetail>
      showDialog(customEvent.detail.text, customEvent.detail.title, customEvent.detail.description)
    }

    window.addEventListener(COPYABLE_TEXT_DIALOG_EVENT, handleEvent)

    return () => {
      window.removeEventListener(COPYABLE_TEXT_DIALOG_EVENT, handleEvent)
    }
  }, [showDialog])

  return (
    <CopyableTextDialogContext.Provider value={{ showDialog, hideDialog }}>
      {children}
      <CopyableTextDialog
        open={dialogState.open}
        onClose={hideDialog}
        text={dialogState.text}
        title={dialogState.title}
        description={dialogState.description}
      />
    </CopyableTextDialogContext.Provider>
  )
}

export default CopyableTextDialogProvider
