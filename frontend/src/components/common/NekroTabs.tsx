import { Box, BoxProps, SxProps, Theme, Tabs, TabsProps } from '@mui/material'
import { TAB_BAR_VARIANTS } from '../../theme/variants'

function mergeTabsSx(base: TabsProps['sx'], extra?: TabsProps['sx']): TabsProps['sx'] {
  return (extra ? [base, extra] : base) as SxProps<Theme>
}

function mergeBoxSx(base: BoxProps['sx'], extra?: BoxProps['sx']): BoxProps['sx'] {
  return (extra ? [base, extra] : base) as SxProps<Theme>
}

export function PageTabs(props: TabsProps) {
  const { sx, ...rest } = props
  return <Tabs {...rest} sx={mergeTabsSx(TAB_BAR_VARIANTS.page, sx)} />
}

export function PanelTabs(props: TabsProps) {
  const { sx, ...rest } = props
  return <Tabs {...rest} sx={mergeTabsSx(TAB_BAR_VARIANTS.panel, sx)} />
}

export function InlineTabs(props: TabsProps) {
  const { sx, ...rest } = props
  return <Tabs {...rest} sx={mergeTabsSx(TAB_BAR_VARIANTS.inline, sx)} />
}

export function EditorTabs(props: TabsProps) {
  const { sx, ...rest } = props
  return <Tabs {...rest} sx={mergeTabsSx(TAB_BAR_VARIANTS.editor, sx)} />
}

export function PanelTabsContainer(props: BoxProps) {
  const { sx, ...rest } = props
  return <Box {...rest} sx={mergeBoxSx(TAB_BAR_VARIANTS.panelContainer, sx)} />
}
