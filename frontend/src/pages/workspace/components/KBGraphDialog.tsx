import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Box, IconButton, Stack, Tooltip, Typography } from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  CenterFocusStrong as FitIcon,
} from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import type { KBDocumentListItem, KBAssetListItem } from '../../../services/api/workspace'
import type { KbIndexProgressInfo } from '../../../contexts/SystemEventsContext'

// ─── types ───────────────────────────────────────────────────────────────────

type NodeKind = 'center' | 'category' | 'document' | 'asset'
type EntryKind = 'document' | 'asset'

interface LayoutNode {
  id: string
  kind: NodeKind
  entryKind: 'document' | 'asset' | null
  numericId: number
  label: string
  category: string
  status: string
  isEnabled: boolean
  x: number
  y: number
  subtreeCount?: number
}

interface HierarchyEdge {
  fromId: string
  toId: string
  x1: number
  y1: number
  x2: number
  y2: number
  level: 'hub' | 'branch'
  color: string
}

interface RefEdge {
  key: string
  path: string
  strokeWidth: number
}

interface ReferenceRouteCandidate {
  key: string
  from: LayoutNode
  to: LayoutNode
  corridorKey: string
  minY: number
  maxY: number
}

interface ReferenceLaneAssignment {
  laneIndex: number
  laneCount: number
  laneX: number
}

export interface KBGraphReferenceEdge {
  fromId: number
  toId: number
  fromKind?: EntryKind
  toKind?: EntryKind
}

export interface KBGraphDialogProps {
  documents: KBDocumentListItem[]
  boundGlobalAssets: KBAssetListItem[]
  progressByDocumentId: Map<number, KbIndexProgressInfo>
  onOpenDocument: (kind: 'document' | 'asset', id: number) => void
  references?: KBGraphReferenceEdge[]
}

// ─── constants ────────────────────────────────────────────────────────────────

const CENTER_R = 26
const CAT_R = 15
const DOC_R = 8
const CATEGORY_LABEL_GAP = 14
const CATEGORY_LABEL_FONT_SIZE = 10.5
const CATEGORY_LEVEL_X = 210
const ENTRY_SPACING = 34
const ROOT_GAP = 28

// ─── utils ────────────────────────────────────────────────────────────────────

function categoryHue(name: string): number {
  let h = 5381
  for (let i = 0; i < name.length; i++) h = ((h << 5) + h) ^ name.charCodeAt(i)
  return Math.abs(h) % 360
}

function categoryColor(name: string, isDark: boolean): string {
  if (!name) return isDark ? 'hsl(0,0%,55%)' : 'hsl(0,0%,40%)'
  const hue = categoryHue(name)
  return isDark ? `hsl(${hue},50%,62%)` : `hsl(${hue},46%,44%)`
}

function normalizeCategoryPath(category: string): string {
  const parts = category
    .replace(/\\/g, '/')
    .split('/')
    .map(part => part.trim())
    .filter(Boolean)
  return parts.length ? `${parts.join('/')}/` : ''
}

function splitCategoryPath(category: string): string[] {
  const normalized = normalizeCategoryPath(category)
  if (!normalized) return []
  return normalized.slice(0, -1).split('/')
}

function compareCategoryPath(left: string, right: string): number {
  if (!left && !right) return 0
  if (!left) return 1
  if (!right) return -1
  return left.localeCompare(right, undefined, { sensitivity: 'base' })
}

function getCategoryBranchKey(category: string): string {
  const segments = splitCategoryPath(category)
  return segments[0] ?? ''
}

function isCategoryInScope(candidateCategory: string, sourceCategory: string): boolean {
  const normalizedCandidate = normalizeCategoryPath(candidateCategory)
  const normalizedSource = normalizeCategoryPath(sourceCategory)
  if (!normalizedSource) {
    return normalizedCandidate === ''
  }
  return normalizedCandidate === normalizedSource || normalizedCandidate.startsWith(normalizedSource)
}

function isCategoryHidden(category: string, collapsedCategories: Set<string>): boolean {
  const normalizedCategory = normalizeCategoryPath(category)
  for (const collapsed of collapsedCategories) {
    const normalizedCollapsed = normalizeCategoryPath(collapsed)
    if (
      normalizedCollapsed &&
      isCategoryInScope(normalizedCategory, normalizedCollapsed) &&
      normalizedCategory !== normalizedCollapsed
    ) {
      return true
    }
  }
  return false
}

function isEntryHidden(category: string, collapsedCategories: Set<string>): boolean {
  const normalizedCategory = normalizeCategoryPath(category)
  for (const collapsed of collapsedCategories) {
    if (isCategoryInScope(normalizedCategory, collapsed)) {
      return true
    }
  }
  return false
}

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

function getReferenceCorridorKey(from: LayoutNode, to: LayoutNode): string {
  const leftX = Math.min(from.x, to.x)
  const rightX = Math.max(from.x, to.x)
  if (Math.abs(leftX - rightX) < 1) {
    return `same:${leftX}`
  }
  return `between:${leftX}:${rightX}`
}

function computeReferenceLaneX(
  from: LayoutNode,
  to: LayoutNode,
  laneIndex: number,
  laneCount: number,
): number {
  if (Math.abs(from.x - to.x) < 1) {
    return from.x - (DOC_R + 34 + laneIndex * 14)
  }

  const minX = Math.min(from.x, to.x)
  const maxX = Math.max(from.x, to.x)
  const laneStart = minX + DOC_R + 24
  const laneEnd = maxX - DOC_R - 24
  if (laneCount <= 1 || laneEnd <= laneStart) {
    return (laneStart + laneEnd) / 2
  }

  return laneStart + ((laneIndex + 1) / (laneCount + 1)) * (laneEnd - laneStart)
}

function buildReferencePortOffset(index: number, total: number): number {
  if (total <= 1) return 0
  const step = Math.min(3.2, 10 / Math.max(total - 1, 1))
  return (index - (total - 1) / 2) * step
}

function buildReferenceEdges(
  references: KBGraphReferenceEdge[],
  nodeMap: Map<string, LayoutNode>,
  hiddenNodeIds: Set<string>,
): RefEdge[] {
  const resolveNodeForRef = (id: number, kind?: EntryKind) => {
    if (kind != null) {
      return nodeMap.get(`${kind}::${id}`)
    }
    return nodeMap.get(`document::${id}`) ?? nodeMap.get(`asset::${id}`)
  }

  const candidates: ReferenceRouteCandidate[] = references
    .map((ref, index) => {
      const from = resolveNodeForRef(ref.fromId, ref.fromKind)
      const to = resolveNodeForRef(ref.toId, ref.toKind)
      if (!from || !to) return null
      if (!isCategoryInScope(to.category, from.category)) return null
      if (hiddenNodeIds.has(from.id) || hiddenNodeIds.has(to.id)) return null

      return {
        key: `${ref.fromKind ?? 'unknown'}:${ref.fromId}->${ref.toKind ?? 'unknown'}:${ref.toId}:${index}`,
        from,
        to,
        corridorKey: getReferenceCorridorKey(from, to),
        minY: Math.min(from.y, to.y),
        maxY: Math.max(from.y, to.y),
      }
    })
    .filter((candidate): candidate is ReferenceRouteCandidate => candidate !== null)

  const laneAssignments = new Map<string, ReferenceLaneAssignment>()
  const corridorGroups = new Map<string, ReferenceRouteCandidate[]>()

  candidates.forEach(candidate => {
    const current = corridorGroups.get(candidate.corridorKey)
    if (current) {
      current.push(candidate)
      return
    }
    corridorGroups.set(candidate.corridorKey, [candidate])
  })

  corridorGroups.forEach(group => {
    const sorted = [...group].sort((left, right) => {
      if (left.minY !== right.minY) return left.minY - right.minY
      if (left.maxY !== right.maxY) return left.maxY - right.maxY
      return left.key.localeCompare(right.key)
    })

    const laneMaxY: number[] = []
    const resolved = sorted.map(candidate => {
      let laneIndex = laneMaxY.findIndex(maxY => candidate.minY > maxY + 12)
      if (laneIndex === -1) {
        laneIndex = laneMaxY.length
        laneMaxY.push(candidate.maxY)
      } else {
        laneMaxY[laneIndex] = candidate.maxY
      }
      return { candidate, laneIndex }
    })

    const laneCount = Math.max(laneMaxY.length, 1)
    resolved.forEach(({ candidate, laneIndex }) => {
      laneAssignments.set(candidate.key, {
        laneIndex,
        laneCount,
        laneX: computeReferenceLaneX(candidate.from, candidate.to, laneIndex, laneCount),
      })
    })
  })

  const routeMeta = new Map<string, {
    candidate: ReferenceRouteCandidate
    laneX: number
    sourceSide: 'left' | 'right'
    targetSide: 'left' | 'right'
  }>()

  const sourcePortGroups = new Map<string, Array<{ edgeKey: string; anchorY: number }>>()
  const registerSourcePortGroup = (
    nodeId: string,
    side: 'left' | 'right',
    edgeKey: string,
    anchorY: number,
  ) => {
    const groupKey = `${nodeId}:${side}`
    const current = sourcePortGroups.get(groupKey)
    if (current) {
      current.push({ edgeKey, anchorY })
      return
    }
    sourcePortGroups.set(groupKey, [{ edgeKey, anchorY }])
  }

  const targetPortGroups = new Map<string, Array<{ edgeKey: string; anchorY: number }>>()
  const registerTargetPortGroup = (
    nodeId: string,
    side: 'left' | 'right',
    edgeKey: string,
    anchorY: number,
  ) => {
    const groupKey = `${nodeId}:${side}`
    const current = targetPortGroups.get(groupKey)
    if (current) {
      current.push({ edgeKey, anchorY })
      return
    }
    targetPortGroups.set(groupKey, [{ edgeKey, anchorY }])
  }

  const sourceMergeGroups = new Map<string, Array<{ edgeKey: string; laneX: number; node: LayoutNode; side: 'left' | 'right' }>>()
  const targetMergeGroups = new Map<string, Array<{ edgeKey: string; laneX: number; node: LayoutNode; side: 'left' | 'right' }>>()

  candidates.forEach(candidate => {
    const lane = laneAssignments.get(candidate.key)
    if (!lane) return
    const sourceSide: 'left' | 'right' = lane.laneX >= candidate.from.x ? 'right' : 'left'
    const targetSide: 'left' | 'right' = lane.laneX >= candidate.to.x ? 'right' : 'left'

    routeMeta.set(candidate.key, {
      candidate,
      laneX: lane.laneX,
      sourceSide,
      targetSide,
    })

    registerSourcePortGroup(
      candidate.from.id,
      sourceSide,
      candidate.key,
      candidate.to.y,
    )
    registerTargetPortGroup(
      candidate.to.id,
      targetSide,
      candidate.key,
      candidate.from.y,
    )

    const sourceGroupKey = `${candidate.from.id}:${sourceSide}`
    const currentSourceGroup = sourceMergeGroups.get(sourceGroupKey)
    const sourceMember = { edgeKey: candidate.key, laneX: lane.laneX, node: candidate.from, side: sourceSide }
    if (currentSourceGroup) currentSourceGroup.push(sourceMember)
    else sourceMergeGroups.set(sourceGroupKey, [sourceMember])

    const targetGroupKey = `${candidate.to.id}:${targetSide}`
    const currentTargetGroup = targetMergeGroups.get(targetGroupKey)
    const targetMember = { edgeKey: candidate.key, laneX: lane.laneX, node: candidate.to, side: targetSide }
    if (currentTargetGroup) currentTargetGroup.push(targetMember)
    else targetMergeGroups.set(targetGroupKey, [targetMember])
  })

  const sourcePortOffsets = new Map<string, number>()
  sourcePortGroups.forEach(group => {
    const sorted = [...group].sort((left, right) => {
      if (left.anchorY !== right.anchorY) return left.anchorY - right.anchorY
      return left.edgeKey.localeCompare(right.edgeKey)
    })
    sorted.forEach((item, index) => {
      sourcePortOffsets.set(item.edgeKey, buildReferencePortOffset(index, sorted.length))
    })
  })

  const targetPortOffsets = new Map<string, number>()
  targetPortGroups.forEach(group => {
    const sorted = [...group].sort((left, right) => {
      if (left.anchorY !== right.anchorY) return left.anchorY - right.anchorY
      return left.edgeKey.localeCompare(right.edgeKey)
    })
    sorted.forEach((item, index) => {
      targetPortOffsets.set(item.edgeKey, buildReferencePortOffset(index, sorted.length))
    })
  })

  const edges: RefEdge[] = []

  const sourceMergeXByEdge = new Map<string, number>()
  sourceMergeGroups.forEach(group => {
    if (group.length <= 1) return
    const first = group[0]
    const mergeX = first.side === 'right'
      ? Math.min(...group.map(item => item.laneX))
      : Math.max(...group.map(item => item.laneX))
    const portX = first.side === 'right'
      ? first.node.x + DOC_R + 5
      : first.node.x - DOC_R - 5
    const branchYs = group.map(item => item.node.y + (sourcePortOffsets.get(item.edgeKey) ?? 0))
    const trunkMinY = Math.min(first.node.y, ...branchYs)
    const trunkMaxY = Math.max(first.node.y, ...branchYs)

    const connectorPath = buildPolylinePath([
      { x: portX, y: first.node.y },
      { x: mergeX, y: first.node.y },
    ])
    if (connectorPath && portX !== mergeX) {
      edges.push({
        key: `source-merge-connector:${first.node.id}:${first.side}`,
        path: connectorPath,
        strokeWidth: 1.3,
      })
    }

    const trunkPath = buildPolylinePath([
      { x: mergeX, y: trunkMinY },
      { x: mergeX, y: trunkMaxY },
    ])
    if (trunkPath && trunkMinY !== trunkMaxY) {
      edges.push({
        key: `source-merge-trunk:${first.node.id}:${first.side}`,
        path: trunkPath,
        strokeWidth: 1.3,
      })
    }

    group.forEach(item => {
      sourceMergeXByEdge.set(item.edgeKey, mergeX)
    })
  })

  const targetMergeXByEdge = new Map<string, number>()
  targetMergeGroups.forEach(group => {
    if (group.length <= 1) return
    const first = group[0]
    const mergeX = first.side === 'right'
      ? Math.min(...group.map(item => item.laneX))
      : Math.max(...group.map(item => item.laneX))
    const portX = first.side === 'right'
      ? first.node.x + DOC_R + 5
      : first.node.x - DOC_R - 5
    const branchYs = group.map(item => item.node.y + (targetPortOffsets.get(item.edgeKey) ?? 0))
    const trunkMinY = Math.min(first.node.y, ...branchYs)
    const trunkMaxY = Math.max(first.node.y, ...branchYs)

    const connectorPath = buildPolylinePath([
      { x: mergeX, y: first.node.y },
      { x: portX, y: first.node.y },
    ])
    if (connectorPath && portX !== mergeX) {
      edges.push({
        key: `target-merge-connector:${first.node.id}:${first.side}`,
        path: connectorPath,
        strokeWidth: 1.3,
      })
    }

    const trunkPath = buildPolylinePath([
      { x: mergeX, y: trunkMinY },
      { x: mergeX, y: trunkMaxY },
    ])
    if (trunkPath && trunkMinY !== trunkMaxY) {
      edges.push({
        key: `target-merge-trunk:${first.node.id}:${first.side}`,
        path: trunkPath,
        strokeWidth: 1.3,
      })
    }

    group.forEach(item => {
      targetMergeXByEdge.set(item.edgeKey, mergeX)
    })
  })

  routeMeta.forEach(route => {
    const fromOffset = sourcePortOffsets.get(route.candidate.key) ?? 0
    const toOffset = targetPortOffsets.get(route.candidate.key) ?? 0
    const fromPortX = route.sourceSide === 'right'
      ? route.candidate.from.x + DOC_R + 5
      : route.candidate.from.x - DOC_R - 5
    const toPortX = route.targetSide === 'right'
      ? route.candidate.to.x + DOC_R + 5
      : route.candidate.to.x - DOC_R - 5
    const startX = sourceMergeXByEdge.get(route.candidate.key) ?? fromPortX
    const endX = targetMergeXByEdge.get(route.candidate.key) ?? toPortX

    const path = buildPolylinePath([
      { x: startX, y: route.candidate.from.y + fromOffset },
      { x: route.laneX, y: route.candidate.from.y + fromOffset },
      { x: route.laneX, y: route.candidate.to.y + toOffset },
      { x: endX, y: route.candidate.to.y + toOffset },
    ])
    if (!path) {
      return
    }
    edges.push({
      key: route.candidate.key,
      path,
      strokeWidth: 1.2,
    })
  })

  return edges.filter(edge => edge.path)
}

function estimateSvgTextWidth(text: string, fontSize: number): number {
  return Array.from(text).reduce((sum, ch) => {
    if (/\s/.test(ch)) return sum + fontSize * 0.35
    if (/[A-Z]/.test(ch)) return sum + fontSize * 0.72
    if (/[a-z0-9]/.test(ch)) return sum + fontSize * 0.58
    return sum + fontSize * 0.95
  }, 0)
}

function getStatusColor(
  status: string,
  palette: { success: { main: string }; warning: { main: string }; error: { main: string } },
): string {
  if (status === 'ready') return palette.success.main
  if (status === 'failed') return palette.error.main
  return palette.warning.main
}

function resolveDocStatus(
  doc: KBDocumentListItem,
  progressMap: Map<number, KbIndexProgressInfo>,
): string {
  const prog = progressMap.get(doc.id)
  if (!prog) {
    if (doc.extract_status === 'failed' || doc.sync_status === 'failed') return 'failed'
    if (doc.extract_status !== 'ready') return doc.extract_status
    return doc.sync_status
  }
  if (prog.phase === 'failed') return 'failed'
  if (prog.phase === 'ready') return 'ready'
  return prog.phase
}

function resolveAssetStatus(asset: KBAssetListItem): string {
  if (asset.extract_status === 'failed' || asset.sync_status === 'failed') return 'failed'
  if (asset.extract_status !== 'ready') return asset.extract_status
  return asset.sync_status
}

// ─── layout ───────────────────────────────────────────────────────────────────

interface CategoryEntry {
  kind: EntryKind
  id: number
  title: string
  status: string
  isEnabled: boolean
  category: string
}

interface CategoryTreeNode {
  path: string
  label: string
  depth: number
  children: CategoryTreeNode[]
  entries: CategoryEntry[]
  subtreeCount: number
}

interface CategoryLayoutInfo {
  nodeId: string
  centerY: number
  minY: number
  maxY: number
  x: number
  color: string
}

function getVisibleSlotCount(node: CategoryTreeNode, collapsedCategories: Set<string>): number {
  if (collapsedCategories.has(node.path)) {
    return 1
  }

  const childSlotCount = node.children.reduce(
    (sum, child) => sum + getVisibleSlotCount(child, collapsedCategories),
    0,
  )
  const entrySlotCount = node.entries.length
  return Math.max(1, childSlotCount + entrySlotCount)
}

function buildCategoryForest(entries: CategoryEntry[]): CategoryTreeNode[] {
  const nodeMap = new Map<string, CategoryTreeNode>()
  const roots: CategoryTreeNode[] = []

  const ensureCategoryNode = (
    path: string,
    parent: CategoryTreeNode | null,
    label: string,
    depth: number,
  ): CategoryTreeNode => {
    const existing = nodeMap.get(path)
    if (existing) return existing
    const created: CategoryTreeNode = {
      path,
      label,
      depth,
      children: [],
      entries: [],
      subtreeCount: 0,
    }
    nodeMap.set(path, created)
    if (parent) {
      parent.children.push(created)
    } else {
      roots.push(created)
    }
    return created
  }

  for (const entry of entries) {
    const category = normalizeCategoryPath(entry.category)
    const segments = splitCategoryPath(category)
    if (segments.length === 0) {
      ensureCategoryNode('', null, '', 1).entries.push({ ...entry, category })
      continue
    }

    let parent: CategoryTreeNode | null = null
    let currentPath = ''
    segments.forEach((segment, index) => {
      currentPath = `${currentPath}${segment}/`
      parent = ensureCategoryNode(currentPath, parent, segment, index + 1)
    })

    parent?.entries.push({ ...entry, category })
  }

  const finalize = (node: CategoryTreeNode) => {
    node.children.sort((left, right) => compareCategoryPath(left.path, right.path))
    node.entries.sort((left, right) => left.title.localeCompare(right.title, undefined, { sensitivity: 'base' }))
    node.children.forEach(finalize)
    node.subtreeCount =
      node.entries.length + node.children.reduce((sum, child) => sum + child.subtreeCount, 0)
  }

  roots.sort((left, right) => compareCategoryPath(left.path, right.path))
  roots.forEach(finalize)
  return roots
}

function computeLayout(
  documents: KBDocumentListItem[],
  assets: KBAssetListItem[],
  progressMap: Map<number, KbIndexProgressInfo>,
  isDark: boolean,
  collapsedCategories: Set<string>,
): { nodes: LayoutNode[]; edges: HierarchyEdge[] } {
  const nodes: LayoutNode[] = []
  const edges: HierarchyEdge[] = []
  const entries: CategoryEntry[] = []

  for (const doc of documents) {
    entries.push({
      kind: 'document',
      id: doc.id,
      title: doc.title || doc.file_name || `#${doc.id}`,
      status: resolveDocStatus(doc, progressMap),
      isEnabled: doc.is_enabled,
      category: normalizeCategoryPath(doc.category?.trim() || ''),
    })
  }

  for (const asset of assets) {
    entries.push({
      kind: 'asset',
      id: asset.id,
      title: asset.title || asset.file_name || `#${asset.id}`,
      status: resolveAssetStatus(asset),
      isEnabled: asset.is_enabled,
      category: normalizeCategoryPath(asset.category?.trim() || ''),
    })
  }

  nodes.push({
    id: 'center',
    kind: 'center',
    entryKind: null,
    numericId: -1,
    label: '',
    category: '',
    status: 'ready',
    isEnabled: true,
    x: 0,
    y: 0,
  })

  const roots = buildCategoryForest(entries)
  if (roots.length === 0) return { nodes, edges }

  const totalHeight =
    roots.reduce((sum, root) => sum + getVisibleSlotCount(root, collapsedCategories) * ENTRY_SPACING, 0) +
    (roots.length - 1) * ROOT_GAP
  let cursorY = -totalHeight / 2 + ENTRY_SPACING / 2

  const layoutCategory = (node: CategoryTreeNode): CategoryLayoutInfo => {
    const nodeId = `category::${node.path || '__uncategorized__'}`
    const nodeX = node.depth * CATEGORY_LEVEL_X
    const branchColor = categoryColor(getCategoryBranchKey(node.path), isDark)
    const isCollapsed = collapsedCategories.has(node.path)
    const childInfos = isCollapsed ? [] : node.children.map(child => layoutCategory(child))
    const entryInfos = isCollapsed
      ? []
      : node.entries.map(entry => {
          const entryY = cursorY
          cursorY += ENTRY_SPACING
          const entryId = `${entry.kind}::${entry.id}`
          nodes.push({
            id: entryId,
            kind: entry.kind,
            entryKind: entry.kind,
            numericId: entry.id,
            label: entry.title,
            category: entry.category,
            status: entry.status,
            isEnabled: entry.isEnabled,
            x: (node.depth + 1) * CATEGORY_LEVEL_X,
            y: entryY,
          })
          return {
            nodeId: entryId,
            centerY: entryY,
            minY: entryY,
            maxY: entryY,
            x: (node.depth + 1) * CATEGORY_LEVEL_X,
            color: branchColor,
          }
        })

    const allChildInfos = [...childInfos, ...entryInfos]
    let minY: number
    let maxY: number
    let centerY: number
    if (allChildInfos.length === 0) {
      centerY = cursorY
      minY = centerY
      maxY = centerY
      cursorY += ENTRY_SPACING
    } else {
      minY = Math.min(...allChildInfos.map(item => item.minY))
      maxY = Math.max(...allChildInfos.map(item => item.maxY))
      centerY = (minY + maxY) / 2
    }

    nodes.push({
      id: nodeId,
      kind: 'category',
      entryKind: null,
      numericId: node.depth,
      label: node.label,
      category: node.path,
      status: 'ready',
      isEnabled: true,
      x: nodeX,
      y: centerY,
      subtreeCount: node.subtreeCount,
    })

    allChildInfos.forEach(child => {
      edges.push({
        fromId: nodeId,
        toId: child.nodeId,
        x1: nodeX,
        y1: centerY,
        x2: child.x,
        y2: child.centerY,
        level: 'branch',
        color: branchColor,
      })
    })

    return {
      nodeId,
      centerY,
      minY,
      maxY,
      x: nodeX,
      color: branchColor,
    }
  }

  roots.forEach((root, index) => {
    if (index > 0) {
      cursorY += ROOT_GAP
    }
    const rootInfo = layoutCategory(root)
    edges.push({
      fromId: 'center',
      toId: rootInfo.nodeId,
      x1: 0,
      y1: 0,
      x2: rootInfo.x,
      y2: rootInfo.centerY,
      level: 'hub',
      color: rootInfo.color,
    })
  })

  return { nodes, edges }
}

// ─── main component ───────────────────────────────────────────────────────────

export default function KBGraphDialog({
  documents,
  boundGlobalAssets,
  progressByDocumentId,
  onOpenDocument,
  references = [],
}: KBGraphDialogProps) {
  const theme = useTheme()
  const { t } = useTranslation('workspace')
  const isDark = theme.palette.mode === 'dark'
  const containerRef = useRef<HTMLDivElement>(null)
  const panRef = useRef<{ startX: number; startY: number; tx: number; ty: number } | null>(null)
  const isPanningRef = useRef(false)
  const lastPanEndedAtRef = useRef(0)

  const [size, setSize] = useState({ w: 600, h: 400 })
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 })
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(() => new Set())

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      if (width > 0 && height > 0) setSize({ w: width, h: height })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const layout = useMemo(
    () => computeLayout(documents, boundGlobalAssets, progressByDocumentId, isDark, collapsedCategories),
    [documents, boundGlobalAssets, progressByDocumentId, isDark, collapsedCategories],
  )

  // Build node position map for reference edge lookup
  const nodeMap = useMemo(
    () => new Map(layout.nodes.map(n => [n.id, n])),
    [layout.nodes],
  )

  const hiddenNodeIds = useMemo(() => {
    const next = new Set<string>()
    layout.nodes.forEach(node => {
      if (node.kind === 'center') return
      const hidden = node.kind === 'category'
        ? isCategoryHidden(node.category, collapsedCategories)
        : isEntryHidden(node.category, collapsedCategories)
      if (hidden) next.add(node.id)
    })
    return next
  }, [layout.nodes, collapsedCategories])

  // Reference edges: only within the source category subtree, and hidden together with collapsed descendants.
  const refEdges = useMemo(
    () => buildReferenceEdges(references, nodeMap, hiddenNodeIds),
    [references, nodeMap, hiddenNodeIds],
  )

  const visibleHierarchyEdges = useMemo(
    () =>
      layout.edges.filter(edge => !hiddenNodeIds.has(edge.toId)),
    [layout.edges, hiddenNodeIds],
  )

  const nodesForFit = useMemo(
    () =>
      layout.nodes.filter(node => !hiddenNodeIds.has(node.id)),
    [layout.nodes, hiddenNodeIds],
  )
  const uncategorizedLabel = t('knowledge.list.uncategorized')

  const fitTransform = useMemo(() => {
    if (nodesForFit.length === 0) return { x: size.w / 2, y: size.h / 2, scale: 1 }
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const nd of nodesForFit) {
      if (nd.kind === 'center') {
        const pad = CENTER_R + 4
        minX = Math.min(minX, nd.x - pad)
        minY = Math.min(minY, nd.y - pad)
        maxX = Math.max(maxX, nd.x + pad)
        maxY = Math.max(maxY, nd.y + pad)
        continue
      }

      if (nd.kind === 'category') {
        const categoryLabel = nd.label || uncategorizedLabel
        const circlePad = CAT_R + 14
        const labelWidth = estimateSvgTextWidth(categoryLabel, CATEGORY_LABEL_FONT_SIZE)
        minX = Math.min(minX, nd.x - circlePad)
        minY = Math.min(minY, nd.y - circlePad)
        maxX = Math.max(maxX, nd.x + circlePad + CATEGORY_LABEL_GAP + labelWidth + 12)
        maxY = Math.max(maxY, nd.y + circlePad)
        continue
      }

      const labelWidth = estimateSvgTextWidth(nd.label, 9)
      minX = Math.min(minX, nd.x - DOC_R - 8)
      minY = Math.min(minY, nd.y - DOC_R - 8)
      maxX = Math.max(maxX, nd.x + DOC_R + 10 + labelWidth)
      maxY = Math.max(maxY, nd.y + DOC_R + 8)
    }
    const margin = 24
    const sc = Math.min(
      (size.w - margin * 2) / Math.max(maxX - minX, 1),
      (size.h - margin * 2) / Math.max(maxY - minY, 1),
      1.8,
    )
    return {
      x: size.w / 2 - ((minX + maxX) / 2) * sc,
      y: size.h / 2 - ((minY + maxY) / 2) * sc,
      scale: sc,
    }
  }, [nodesForFit, size, uncategorizedLabel])

  useEffect(() => { setTransform(fitTransform) }, [fitTransform])

  const doFit = useCallback(() => setTransform(fitTransform), [fitTransform])

  const zoom = useCallback((factor: number) => {
    setTransform(prev => ({ ...prev, scale: Math.max(0.1, Math.min(6, prev.scale * factor)) }))
  }, [])

  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault()
    const factor = e.deltaY > 0 ? 0.88 : 1.12
    setTransform(prev => {
      const newScale = Math.max(0.1, Math.min(6, prev.scale * factor))
      const rect = containerRef.current?.getBoundingClientRect()
      if (!rect) return { ...prev, scale: newScale }
      const mx = e.clientX - rect.left
      const my = e.clientY - rect.top
      return {
        x: mx - (mx - prev.x) * (newScale / prev.scale),
        y: my - (my - prev.y) * (newScale / prev.scale),
        scale: newScale,
      }
    })
  }, [])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    el.addEventListener('wheel', handleWheel, { passive: false })
    return () => {
      el.removeEventListener('wheel', handleWheel)
    }
  }, [handleWheel])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return
    isPanningRef.current = false
    panRef.current = { startX: e.clientX, startY: e.clientY, tx: transform.x, ty: transform.y }
  }, [transform])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const pan = panRef.current
    if (!pan) return
    const dx = e.clientX - pan.startX
    const dy = e.clientY - pan.startY
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) isPanningRef.current = true
    setTransform(prev => ({ ...prev, x: pan.tx + dx, y: pan.ty + dy }))
  }, [])

  const handleMouseUp = useCallback(() => {
    if (isPanningRef.current) {
      lastPanEndedAtRef.current = typeof performance !== 'undefined' ? performance.now() : Date.now()
    }
    panRef.current = null
    isPanningRef.current = false
  }, [])

  const shouldIgnoreClickAfterPan = useCallback(() => {
    const now = typeof performance !== 'undefined' ? performance.now() : Date.now()
    return now - lastPanEndedAtRef.current < 120
  }, [])

  const handleNodeClick = useCallback(
    (e: React.MouseEvent, node: LayoutNode) => {
      e.stopPropagation()
      if (isPanningRef.current || shouldIgnoreClickAfterPan()) return
      if (node.entryKind !== null) {
        onOpenDocument(node.entryKind, node.numericId)
      }
    },
    [onOpenDocument, shouldIgnoreClickAfterPan],
  )

  const toggleCategoryCollapse = useCallback((category: string) => {
    setCollapsedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
  }, [])

  const handleCategoryClick = useCallback(
    (e: React.MouseEvent, category: string) => {
      e.stopPropagation()
      e.preventDefault()
      if (isPanningRef.current || shouldIgnoreClickAfterPan()) return
      toggleCategoryCollapse(category)
    },
    [toggleCategoryCollapse, shouldIgnoreClickAfterPan],
  )

  const catColorMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const nd of layout.nodes) {
      if (nd.kind === 'category') {
        map.set(nd.category, categoryColor(getCategoryBranchKey(nd.category), isDark))
      }
    }
    return map
  }, [layout.nodes, isDark])

  const totalCount = documents.length + boundGlobalAssets.length
  const catCount = layout.nodes.filter(node => node.kind === 'category').length
  const statsLabels = [
    t('knowledge.graph.totalCount', { count: totalCount }),
    t('knowledge.graph.categoryCount', { count: catCount }),
  ]

  if (refEdges.length > 0) {
    statsLabels.push(t('knowledge.graph.referenceCount', { count: refEdges.length }))
  }

  if (collapsedCategories.size > 0) {
    statsLabels.push(t('knowledge.graph.collapsedCount', { count: collapsedCategories.size }))
  }

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        userSelect: 'none',
      }}
    >
      {/* Stats — top left */}
      <Box
        sx={{
          position: 'absolute',
          top: 10,
          left: 12,
          zIndex: 10,
          bgcolor: alpha(theme.palette.background.paper, 0.82),
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          borderRadius: 1.5,
          border: '1px solid',
          borderColor: 'divider',
          px: 1.25,
          py: 0.6,
          pointerEvents: 'none',
        }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.68rem' }}>
          {statsLabels.join(' · ')}
        </Typography>
      </Box>

      {/* Controls — top right */}
      <Stack
        direction="row"
        sx={{
          position: 'absolute',
          top: 10,
          right: 12,
          zIndex: 10,
          bgcolor: alpha(theme.palette.background.paper, 0.82),
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          borderRadius: 1.5,
          border: '1px solid',
          borderColor: 'divider',
          px: 0.5,
          py: 0.25,
        }}
      >
        <Tooltip title={t('knowledge.graph.zoomIn')}>
          <IconButton size="small" onClick={() => zoom(1.2)} sx={{ color: 'text.secondary' }}>
            <ZoomInIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Tooltip>
        <Tooltip title={t('knowledge.graph.zoomOut')}>
          <IconButton size="small" onClick={() => zoom(0.83)} sx={{ color: 'text.secondary' }}>
            <ZoomOutIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Tooltip>
        <Tooltip title={t('knowledge.graph.fit')}>
          <IconButton size="small" onClick={doFit} sx={{ color: 'text.secondary' }}>
            <FitIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Tooltip>
      </Stack>

      {/* SVG canvas */}
      <Box
        ref={containerRef}
        sx={{ width: '100%', height: '100%', cursor: 'grab', '&:active': { cursor: 'grabbing' } }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* writingMode forces horizontal text regardless of any inherited CSS writing-mode */}
        <svg
          width="100%"
          height="100%"
          style={{ display: 'block', writingMode: 'horizontal-tb' }}
        >
          <g transform={`translate(${transform.x},${transform.y}) scale(${transform.scale})`}>

            {/* Layer 1: hierarchy edges — left-to-right directory tree */}
            {visibleHierarchyEdges.map((edge, i) => {
              const mx = (edge.x1 + edge.x2) / 2
              return (
                <path
                  key={i}
                  d={`M ${edge.x1},${edge.y1} C ${mx},${edge.y1} ${mx},${edge.y2} ${edge.x2},${edge.y2}`}
                  fill="none"
                  stroke={alpha(edge.color, edge.level === 'hub' ? 0.35 : 0.22)}
                  strokeWidth={edge.level === 'hub' ? 1.5 : 1}
                  strokeLinecap="round"
                  pointerEvents="none"
                />
              )
            })}

            {/* Layer 2: reference edges (dashed curves) */}
            {refEdges.map((edge, i) => (
              <path
                key={edge.key || `ref-${i}`}
                d={edge.path}
                fill="none"
                stroke={alpha(theme.palette.primary.main, 0.45)}
                strokeWidth={edge.strokeWidth}
                strokeDasharray="5,3"
                strokeLinejoin="round"
                strokeLinecap="round"
                pointerEvents="none"
              />
            ))}

            {/* Layer 3: nodes */}
            {layout.nodes.map(node => {
              const isHovered = hoveredId === node.id

              if (hiddenNodeIds.has(node.id)) {
                return null
              }

              if (node.kind === 'center') {
                return (
                  <g key={node.id}>
                    <circle
                      cx={0} cy={0} r={CENTER_R + 5}
                      fill={alpha(theme.palette.primary.main, 0.1)}
                      stroke={alpha(theme.palette.primary.main, 0.28)}
                      strokeWidth={1}
                      pointerEvents="none"
                    />
                    <circle cx={0} cy={0} r={CENTER_R} fill={theme.palette.primary.main} />
                    <text
                      x={0} y={4.5} textAnchor="middle"
                      fill={theme.palette.primary.contrastText}
                      fontSize={11} fontWeight={700}
                      pointerEvents="none"
                      style={{ userSelect: 'none', writingMode: 'horizontal-tb' }}
                    >
                      {t('knowledge.graph.center')}
                    </text>
                    <text
                      x={0} y={CENTER_R + 15} textAnchor="middle"
                      fill={alpha(theme.palette.text.secondary, 0.65)}
                      fontSize={9} pointerEvents="none"
                      style={{ userSelect: 'none', writingMode: 'horizontal-tb' }}
                    >
                      {t('knowledge.graph.entryCount', { count: totalCount })}
                    </text>
                  </g>
                )
              }

              if (node.kind === 'category') {
                const color = catColorMap.get(node.category) ?? '#888'
                const isCollapsed = collapsedCategories.has(node.category)
                const categoryLabel = node.label || uncategorizedLabel
                const docsInCat = node.subtreeCount ?? 0

                return (
                  <g
                    key={node.id}
                    onMouseEnter={() => setHoveredId(node.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onMouseDown={e => { e.stopPropagation() }}
                    onClick={e => handleCategoryClick(e, node.category)}
                    style={{ cursor: 'pointer' }}
                  >
                    <title>
                      {isCollapsed
                        ? t('knowledge.graph.expandCategory', { category: categoryLabel })
                        : t('knowledge.graph.collapseCategory', { category: categoryLabel })}
                    </title>
                    {isHovered && (
                      <circle cx={node.x} cy={node.y} r={CAT_R + 6}
                        fill={alpha(color, 0.15)} stroke={color} strokeWidth={1.5}
                        pointerEvents="none" />
                    )}
                    <circle
                      cx={node.x} cy={node.y} r={CAT_R + 14}
                      fill="transparent"
                    />
                    <circle
                      cx={node.x} cy={node.y} r={CAT_R}
                      fill={isDark ? alpha(color, isCollapsed ? 0.18 : 0.3) : alpha(color, isCollapsed ? 0.12 : 0.18)}
                      stroke={color}
                      strokeWidth={isHovered ? 1.8 : 1.2}
                      strokeDasharray={isCollapsed ? '4 3' : undefined}
                      opacity={isCollapsed ? 0.85 : 1}
                    />
                    {/* doc count inside circle */}
                    <text
                      x={node.x} y={node.y + 4.5} textAnchor="middle"
                      fill={color} fontSize={9} fontWeight={700}
                      pointerEvents="none"
                      style={{ userSelect: 'none', writingMode: 'horizontal-tb' }}
                    >
                      {docsInCat}
                    </text>
                    {/* category name to the right, folder-tree style */}
                    <text
                      x={node.x + CAT_R + CATEGORY_LABEL_GAP}
                      y={node.y}
                      textAnchor="start"
                      dominantBaseline="middle"
                      fill={isDark
                        ? alpha(theme.palette.text.primary, 0.85)
                        : alpha(theme.palette.text.primary, 0.78)}
                      fontSize={CATEGORY_LABEL_FONT_SIZE}
                      fontWeight={600}
                      pointerEvents="none"
                      style={{ userSelect: 'none', writingMode: 'horizontal-tb' }}
                    >
                      {categoryLabel}
                    </text>
                  </g>
                )
              }

              // document / asset node — label to the right
              const sColor = getStatusColor(node.status, theme.palette)
              const catColor = catColorMap.get(node.category) ?? '#888'

              return (
                <g
                  key={node.id}
                  onClick={e => handleNodeClick(e, node)}
                  onMouseEnter={() => setHoveredId(node.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  style={{ cursor: 'pointer' }}
                >
                  {isHovered && (
                    <circle cx={node.x} cy={node.y} r={DOC_R + 5}
                      fill={alpha(catColor, 0.2)} stroke={catColor} strokeWidth={1.5}
                      pointerEvents="none" />
                  )}
                  <circle
                    cx={node.x} cy={node.y} r={DOC_R}
                    fill={isDark ? alpha(catColor, 0.45) : alpha(catColor, 0.3)}
                    stroke={sColor}
                    strokeWidth={isHovered ? 2 : 1.2}
                  />
                  {!node.isEnabled && (
                    <line
                      x1={node.x - DOC_R * 0.65} y1={node.y - DOC_R * 0.65}
                      x2={node.x + DOC_R * 0.65} y2={node.y + DOC_R * 0.65}
                      stroke={alpha(theme.palette.text.disabled, 0.7)} strokeWidth={1.5}
                      strokeLinecap="round" pointerEvents="none"
                    />
                  )}
                  <text
                    x={node.x + DOC_R + 10} y={node.y + 4} textAnchor="start"
                    fill={isDark
                      ? alpha(theme.palette.text.primary, isHovered ? 0.92 : 0.72)
                      : alpha(theme.palette.text.primary, isHovered ? 0.88 : 0.65)}
                    fontSize={isHovered ? 9.5 : 8.5}
                    fontWeight={isHovered ? 600 : 400}
                    pointerEvents="none"
                    style={{ userSelect: 'none', writingMode: 'horizontal-tb' }}
                  >
                    {node.label}
                  </text>
                </g>
              )
            })}
          </g>
        </svg>
      </Box>

      {/* Hint */}
      <Typography
        variant="caption"
        sx={{
          position: 'absolute',
          bottom: 10,
          right: 14,
          color: 'text.disabled',
          fontSize: '0.62rem',
          pointerEvents: 'none',
          userSelect: 'none',
        }}
      >
        {t('knowledge.graph.hint')}
      </Typography>
    </Box>
  )
}
