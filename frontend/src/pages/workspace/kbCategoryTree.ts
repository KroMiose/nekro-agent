export interface KBCategoryTreeNode<T> {
  key: string
  path: string
  label: string
  depth: number
  children: KBCategoryTreeNode<T>[]
  items: T[]
  allItems: T[]
  itemCount: number
}

export function normalizeCategoryPath(category: string | null | undefined): string {
  const parts = (category ?? '')
    .replace(/\\/g, '/')
    .split('/')
    .map(part => part.trim())
    .filter(Boolean)

  return parts.length > 0 ? `${parts.join('/')}/` : ''
}

function compareCategoryPath(left: string, right: string): number {
  if (!left && !right) return 0
  if (!left) return 1
  if (!right) return -1
  return left.localeCompare(right, undefined, { sensitivity: 'base' })
}

export function buildCategoryTree<T>(
  items: T[],
  getCategory: (item: T) => string | null | undefined,
): KBCategoryTreeNode<T>[] {
  const nodeMap = new Map<string, KBCategoryTreeNode<T>>()
  const roots: KBCategoryTreeNode<T>[] = []

  const ensureNode = (
    path: string,
    parent: KBCategoryTreeNode<T> | null,
    label: string,
    depth: number,
  ): KBCategoryTreeNode<T> => {
    const existing = nodeMap.get(path)
    if (existing) return existing

    const node: KBCategoryTreeNode<T> = {
      key: path || '__uncategorized__',
      path,
      label,
      depth,
      children: [],
      items: [],
      allItems: [],
      itemCount: 0,
    }

    nodeMap.set(path, node)
    if (parent) {
      parent.children.push(node)
    } else {
      roots.push(node)
    }
    return node
  }

  for (const item of items) {
    const categoryPath = normalizeCategoryPath(getCategory(item))
    const segments = categoryPath ? categoryPath.slice(0, -1).split('/') : []

    if (segments.length === 0) {
      ensureNode('', null, '', 0).items.push(item)
      continue
    }

    let parent: KBCategoryTreeNode<T> | null = null
    let currentPath = ''
    segments.forEach((segment, index) => {
      currentPath = `${currentPath}${segment}/`
      parent = ensureNode(currentPath, parent, segment, index)
    })

    parent?.items.push(item)
  }

  const finalize = (node: KBCategoryTreeNode<T>) => {
    node.children.sort((left, right) => compareCategoryPath(left.path, right.path))
    node.children.forEach(finalize)
    node.allItems = [...node.items, ...node.children.flatMap(child => child.allItems)]
    node.itemCount = node.allItems.length
  }

  roots.sort((left, right) => compareCategoryPath(left.path, right.path))
  roots.forEach(finalize)
  return roots
}
