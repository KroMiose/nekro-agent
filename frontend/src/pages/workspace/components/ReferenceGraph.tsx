import { useCallback, useEffect, useRef, useState } from 'react'
import { Box, IconButton, Tooltip, Typography } from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import { Add as AddIcon, AutoAwesome as AutoIcon, Close as CloseIcon, Edit as EditIcon } from '@mui/icons-material'
import type { KBReferenceItem } from '../../../services/api/workspace'

const NODE_W = 130
const NODE_H = 38
const CENTER_W = 150
const CENTER_H = 46
const ROW_H = 54
const PADDING_V = 28

function buildPolylinePath(points: Array<{ x: number; y: number }>): string {
  const normalized = points.filter((point, index) => {
    if (index === 0) return true
    const prev = points[index - 1]
    return prev.x !== point.x || prev.y !== point.y
  })
  if (normalized.length === 0) return ''
  return normalized.reduce(
    (path, point, index) => path + `${index === 0 ? 'M' : ' L'} ${point.x},${point.y}`,
    '',
  )
}

function useContainerWidth(ref: React.RefObject<HTMLDivElement | null>): number {
  const [width, setWidth] = useState(400)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    setWidth(el.clientWidth || 400)
    const observer = new ResizeObserver(entries => {
      const w = entries[0]?.contentRect.width
      if (w) setWidth(w)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [ref])
  return width
}

interface ReferenceGraphProps {
  currentTitle: string
  referencesTo: KBReferenceItem[]
  referencedBy: KBReferenceItem[]
  onNavigate: (id: number) => void
  onAdd: () => void
  onEdit: (ref: KBReferenceItem) => void
  onRemove: (id: number) => void
  disabled?: boolean
}

export default function ReferenceGraph({
  currentTitle,
  referencesTo,
  referencedBy,
  onNavigate,
  onAdd,
  onEdit,
  onRemove,
  disabled = false,
}: ReferenceGraphProps) {
  const theme = useTheme()
  const containerRef = useRef<HTMLDivElement>(null)
  const width = useContainerWidth(containerRef)
  const [hoveredId, setHoveredId] = useState<number | null>(null)

  const leftCount = referencedBy.length
  const rightCount = referencesTo.length
  const rows = Math.max(leftCount, rightCount, 1)
  const svgH = rows * ROW_H + PADDING_V * 2

  const centerY = svgH / 2
  const centerX = width / 2 - CENTER_W / 2
  const leftX = 0
  const rightX = Math.max(width - NODE_W, centerX + CENTER_W + 20)

  const getNodeY = useCallback(
    (count: number, i: number) => {
      if (count === 1) return centerY - NODE_H / 2
      const span = svgH - PADDING_V * 2
      return PADDING_V + (i / (count - 1)) * span - NODE_H / 2
    },
    [centerY, svgH],
  )

  const isDark = theme.palette.mode === 'dark'
  const inColor = theme.palette.warning.main
  const outColor = theme.palette.info.main
  const primaryColor = theme.palette.primary.main
  const bgColor = theme.palette.background.paper

  const inColorFaded = alpha(inColor, 0.55)
  const outColorFaded = alpha(outColor, 0.55)
  const incomingEntries = referencedBy.map((ref, i) => ({
    ref,
    y: getNodeY(leftCount, i) + NODE_H / 2,
  }))
  const outgoingEntries = referencesTo.map((ref, i) => ({
    ref,
    y: getNodeY(rightCount, i) + NODE_H / 2,
  }))

  const renderIncomingGroup = useCallback((
    entries: Array<{ ref: KBReferenceItem; y: number }>,
    joinX: number,
    stroke: string,
    markerEnd: string,
    strokeWidth: number,
    strokeOpacity: number,
    strokeDasharray?: string,
  ) => {
    const x1 = leftX + NODE_W
    const x2 = centerX

    if (entries.length === 0) return []
    if (entries.length === 1) {
      const only = entries[0]
      const cx = (x1 + x2) / 2
      return [
        <path
          key={`incoming-single-${only.ref.ref_id}`}
          d={`M${x1},${only.y} C${cx},${only.y} ${cx},${centerY} ${x2},${centerY}`}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeOpacity={strokeOpacity}
          strokeDasharray={strokeDasharray}
          markerEnd={markerEnd}
        />,
      ]
    }

    const ys = entries.map(item => item.y)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    const elements: JSX.Element[] = []

    const connectorPath = buildPolylinePath([
      { x: joinX, y: centerY },
      { x: x2, y: centerY },
    ])
    if (connectorPath && joinX !== x2) {
      elements.push(
        <path
          key={`incoming-connector-${joinX}`}
          d={connectorPath}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeOpacity={strokeOpacity}
          strokeDasharray={strokeDasharray}
          markerEnd={markerEnd}
        />,
      )
    }

    const trunkPath = buildPolylinePath([
      { x: joinX, y: minY },
      { x: joinX, y: maxY },
    ])
    if (trunkPath && minY !== maxY) {
      elements.push(
        <path
          key={`incoming-trunk-${joinX}`}
          d={trunkPath}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeOpacity={strokeOpacity}
          strokeDasharray={strokeDasharray}
        />,
      )
    }

    entries.forEach(({ ref, y }) => {
      const branchPath = buildPolylinePath([
        { x: x1, y },
        { x: joinX, y },
      ])
      if (!branchPath || x1 === joinX) return
      elements.push(
        <path
          key={`incoming-branch-${ref.ref_id}`}
          d={branchPath}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeOpacity={strokeOpacity}
          strokeDasharray={strokeDasharray}
        />,
      )
    })

    return elements
  }, [centerX, centerY, leftX])

  const renderOutgoingGroup = useCallback((
    entries: Array<{ ref: KBReferenceItem; y: number }>,
    joinX: number,
    stroke: string,
    markerEnd: string,
    strokeWidth: number,
    strokeOpacity: number,
    strokeDasharray?: string,
  ) => {
    const x1 = centerX + CENTER_W
    const x2 = rightX

    if (entries.length === 0) return []
    if (entries.length === 1) {
      const only = entries[0]
      const cx = (x1 + x2) / 2
      return [
        <path
          key={`outgoing-single-${only.ref.ref_id}`}
          d={`M${x1},${centerY} C${cx},${centerY} ${cx},${only.y} ${x2},${only.y}`}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeOpacity={strokeOpacity}
          strokeDasharray={strokeDasharray}
          markerEnd={markerEnd}
        />,
      ]
    }

    const ys = entries.map(item => item.y)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    const elements: JSX.Element[] = []

    const connectorPath = buildPolylinePath([
      { x: x1, y: centerY },
      { x: joinX, y: centerY },
    ])
    if (connectorPath && x1 !== joinX) {
      elements.push(
        <path
          key={`outgoing-connector-${joinX}`}
          d={connectorPath}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeOpacity={strokeOpacity}
          strokeDasharray={strokeDasharray}
        />,
      )
    }

    const trunkPath = buildPolylinePath([
      { x: joinX, y: minY },
      { x: joinX, y: maxY },
    ])
    if (trunkPath && minY !== maxY) {
      elements.push(
        <path
          key={`outgoing-trunk-${joinX}`}
          d={trunkPath}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeOpacity={strokeOpacity}
          strokeDasharray={strokeDasharray}
        />,
      )
    }

    entries.forEach(({ ref, y }) => {
      const branchPath = buildPolylinePath([
        { x: joinX, y },
        { x: x2, y },
      ])
      if (!branchPath || joinX === x2) return
      elements.push(
        <path
          key={`outgoing-branch-${ref.ref_id}`}
          d={branchPath}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeOpacity={strokeOpacity}
          strokeDasharray={strokeDasharray}
          markerEnd={markerEnd}
        />,
      )
    })

    return elements
  }, [centerX, centerY, rightX])

  return (
    <Box
      ref={containerRef}
      sx={{ position: 'relative', width: '100%', height: svgH, userSelect: 'none', minWidth: 0 }}
    >
      {/* SVG layer for bezier connections */}
      <svg
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: svgH,
          overflow: 'visible',
          pointerEvents: 'none',
        }}
      >
        <defs>
          <marker id="rg-arrow-in" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 Z" fill={inColor} opacity={0.75} />
          </marker>
          <marker id="rg-arrow-in-auto" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 Z" fill={inColor} opacity={0.4} />
          </marker>
          <marker id="rg-arrow-out" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 Z" fill={outColor} opacity={0.75} />
          </marker>
          <marker id="rg-arrow-out-auto" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 Z" fill={outColor} opacity={0.4} />
          </marker>
        </defs>

        {/* referenced_by: left node → center node */}
        {renderIncomingGroup(
          incomingEntries.filter(item => !item.ref.is_auto),
          centerX - 30,
          inColor,
          'url(#rg-arrow-in)',
          1.7,
          0.7,
        )}
        {renderIncomingGroup(
          incomingEntries.filter(item => item.ref.is_auto),
          centerX - 46,
          inColorFaded,
          'url(#rg-arrow-in-auto)',
          1.2,
          0.5,
          '5,4',
        )}

        {/* references_to: center node → right node */}
        {renderOutgoingGroup(
          outgoingEntries.filter(item => !item.ref.is_auto),
          centerX + CENTER_W + 30,
          outColor,
          'url(#rg-arrow-out)',
          1.7,
          0.7,
        )}
        {renderOutgoingGroup(
          outgoingEntries.filter(item => item.ref.is_auto),
          centerX + CENTER_W + 46,
          outColorFaded,
          'url(#rg-arrow-out-auto)',
          1.2,
          0.5,
          '5,4',
        )}
      </svg>

      {/* Center node */}
      <Tooltip title={currentTitle} placement="top">
        <Box
          onClick={disabled ? undefined : onAdd}
          sx={{
            position: 'absolute',
            left: centerX,
            top: centerY - CENTER_H / 2,
            width: CENTER_W,
            height: CENTER_H,
            borderRadius: '10px',
            bgcolor: primaryColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 0.5,
            px: 1.25,
            cursor: disabled ? 'default' : 'pointer',
            boxShadow: `0 2px 10px ${alpha(primaryColor, 0.35)}`,
            transition: 'filter 0.15s',
            '&:hover': disabled ? undefined : { filter: 'brightness(1.08)' },
            overflow: 'hidden',
            zIndex: 1,
          }}
        >
          {!disabled && <AddIcon sx={{ fontSize: 13, color: 'primary.contrastText', opacity: 0.8, flexShrink: 0 }} />}
          <Typography
            variant="caption"
            fontWeight={600}
            noWrap
            sx={{ color: 'primary.contrastText', fontSize: '0.78rem', letterSpacing: 0.1 }}
          >
            {currentTitle}
          </Typography>
        </Box>
      </Tooltip>

      {/* Left nodes: referenced_by (incoming) */}
      {referencedBy.map((ref, i) => {
        const nodeTop = getNodeY(leftCount, i)
        const isHovered = hoveredId === ref.ref_id
        return (
          <Tooltip
            key={ref.ref_id}
            title={ref.description ? `${ref.title}\n${ref.description}` : ref.title}
            placement="top"
            arrow
          >
            <Box
              onMouseEnter={() => setHoveredId(ref.ref_id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => onNavigate(ref.document_id)}
              sx={{
                position: 'absolute',
                left: leftX,
                top: nodeTop,
                width: NODE_W,
                height: NODE_H,
                borderRadius: '8px',
                border: `1.5px solid ${alpha(inColor, isHovered ? 0.85 : 0.4)}`,
                bgcolor: isHovered ? alpha(inColor, isDark ? 0.15 : 0.07) : alpha(bgColor, 0.95),
                display: 'flex',
                alignItems: 'center',
                px: 1.25,
                gap: 0.5,
                cursor: 'pointer',
                transition: 'border-color 0.15s, background-color 0.15s',
                overflow: 'hidden',
                zIndex: 2,
              }}
            >
              {ref.is_auto && (
                <AutoIcon sx={{ fontSize: 11, color: alpha(inColor, 0.55), flexShrink: 0 }} />
              )}
              <Typography
                variant="caption"
                noWrap
                sx={{ color: 'text.primary', fontSize: '0.74rem', fontWeight: 500, flex: 1, minWidth: 0 }}
              >
                {ref.title}
              </Typography>
            </Box>
          </Tooltip>
        )
      })}

      {/* Right nodes: references_to (outgoing) */}
      {referencesTo.map((ref, i) => {
        const nodeTop = getNodeY(rightCount, i)
        const isHovered = hoveredId === ref.ref_id
        const showActions = isHovered && !ref.is_auto && !disabled
        return (
          <Box
            key={ref.ref_id}
            onMouseEnter={() => setHoveredId(ref.ref_id)}
            onMouseLeave={() => setHoveredId(null)}
            sx={{
              position: 'absolute',
              left: rightX,
              top: nodeTop,
              width: NODE_W,
              height: NODE_H,
              borderRadius: '8px',
              border: `1.5px solid ${alpha(outColor, isHovered ? 0.85 : 0.4)}`,
              bgcolor: isHovered ? alpha(outColor, isDark ? 0.15 : 0.07) : alpha(bgColor, 0.95),
              display: 'flex',
              alignItems: 'center',
              pl: 1.25,
              pr: showActions ? 0.25 : 1.25,
              gap: 0.5,
              cursor: 'pointer',
              transition: 'border-color 0.15s, background-color 0.15s, padding-right 0.1s',
              overflow: 'hidden',
              zIndex: 2,
            }}
            onClick={() => onNavigate(ref.document_id)}
          >
            {ref.is_auto && (
              <AutoIcon sx={{ fontSize: 11, color: alpha(outColor, 0.55), flexShrink: 0 }} />
            )}
            <Tooltip
              title={ref.description ? `${ref.title} · ${ref.description}` : ref.title}
              placement="top"
              arrow
            >
              <Typography
                variant="caption"
                noWrap
                sx={{ color: 'text.primary', fontSize: '0.74rem', fontWeight: 500, flex: 1, minWidth: 0 }}
              >
                {ref.title}
              </Typography>
            </Tooltip>
            {showActions && (
              <Box
                sx={{ display: 'flex', alignItems: 'center', gap: 0.25, flexShrink: 0 }}
                onClick={e => e.stopPropagation()}
              >
                <IconButton
                  size="small"
                  sx={{ p: '2px', '&:hover': { color: 'text.primary' } }}
                  onClick={() => onEdit(ref)}
                >
                  <EditIcon sx={{ fontSize: 12 }} />
                </IconButton>
                <IconButton
                  size="small"
                  sx={{ p: '2px', '&:hover': { color: 'error.main' } }}
                  onClick={() => onRemove(ref.document_id)}
                >
                  <CloseIcon sx={{ fontSize: 12 }} />
                </IconButton>
              </Box>
            )}
          </Box>
        )
      })}

      {/* Empty state hint */}
      {leftCount === 0 && rightCount === 0 && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.72rem' }}>
            点击中心节点添加引用
          </Typography>
        </Box>
      )}

      {/* Legend */}
      <Box
        sx={{
          position: 'absolute',
          bottom: 4,
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: 1.5,
          alignItems: 'center',
          pointerEvents: 'none',
          opacity: leftCount + rightCount > 0 ? 0.6 : 0,
          transition: 'opacity 0.2s',
        }}
      >
        {leftCount > 0 && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
            <Box sx={{ width: 16, height: 1.5, bgcolor: inColor, borderRadius: 999 }} />
            <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.disabled' }}>
              被引用
            </Typography>
          </Box>
        )}
        {rightCount > 0 && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
            <Box sx={{ width: 16, height: 1.5, bgcolor: outColor, borderRadius: 999 }} />
            <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.disabled' }}>
              引用
            </Typography>
          </Box>
        )}
        {(referencedBy.some(r => r.is_auto) || referencesTo.some(r => r.is_auto)) && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
            <Box
              sx={{
                width: 16,
                height: 1.5,
                background: `repeating-linear-gradient(to right, ${alpha(theme.palette.text.secondary, 0.5)} 0 4px, transparent 4px 8px)`,
              }}
            />
            <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.disabled' }}>
              自动检测
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  )
}
